#!/usr/bin/env python3
"""
Model management: training, loading, and retraining for each coin/horizon.
"""

import os
import json
import time
import joblib
import numpy as np
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any

from .utils import setup_logging

logger = setup_logging("ModelManager")


class EnsembleRegressor:
    """Ensemble of XGBoost and LightGBM regressors for return forecasting."""

    def __init__(self, xgb_m, lgb_m=None):
        self.xgb_m = xgb_m
        self.lgb_m = lgb_m

    def predict(self, X):
        p1 = self.xgb_m.predict(X)
        if self.lgb_m is not None:
            try:
                p2 = self.lgb_m.predict(X)
                return 0.50 * p1 + 0.50 * p2
            except Exception:
                pass
        return p1


class EnsembleBinaryClassifier:
    """Ensemble binary classifier for high-accuracy Kalshi directional probability."""

    def __init__(self, xgb_m, lgb_m=None, classes=None):
        self.xgb_m = xgb_m
        self.lgb_m = lgb_m
        self.classes_ = np.array(classes if classes is not None else [0, 1])

    def predict_proba(self, X):
        p1 = self.xgb_m.predict_proba(X)
        if self.lgb_m is not None:
            try:
                p2 = self.lgb_m.predict_proba(X)
                return 0.50 * p1 + 0.50 * p2
            except Exception:
                pass
        return p1

    def predict(self, X):
        proba = self.predict_proba(X)
        return (proba[:, 1] >= 0.50).astype(int)


class ModelManager:
    """Trains/loads XGBoost models per horizon and handles feature mismatch."""

    def __init__(self, coin_cfg, data_store, feature_engine):
        self.cfg = coin_cfg
        self.symbol = coin_cfg.symbol
        self.data_store = data_store
        self.feature_engine = feature_engine
        self.models: Dict[int, Dict[str, Any]] = {}
        self.classifiers: Dict[int, Dict[str, Any]] = {}
        self.model_dir = coin_cfg.model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        self.last_train_counts = self._load_counts()
        self.last_train_times: Dict[int, float] = {}

    def _model_path(self, horizon: int) -> str:
        return os.path.join(self.model_dir, f"xgb_{horizon}min_latest.pkl")

    def _counts_path(self) -> str:
        return os.path.join(self.model_dir, ".last_train_counts.json")

    def _clf_path(self, horizon: int) -> str:
        return os.path.join(self.model_dir, f"xgb_{horizon}min_clf.pkl")

    def _load_counts(self) -> Dict[str, int]:
        try:
            if os.path.exists(self._counts_path()):
                with open(self._counts_path(), "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"[{self.symbol}] Could not load train counts: {e}")
        return {}

    def _save_counts(self) -> None:
        try:
            with open(self._counts_path(), "w") as f:
                json.dump(self.last_train_counts, f)
        except Exception as e:
            logger.warning(f"[{self.symbol}] Could not save train counts: {e}")

    def should_train(self, horizon: int) -> bool:
        """Decide if a retrain is needed."""
        path = self._model_path(horizon)
        if not os.path.exists(path):
            return True

        current_count = self.data_store.count_prices()
        last_count = self.last_train_counts.get(str(horizon), 0)
        if current_count - last_count >= self.cfg.retrain_min_bars:
            return True

        last_time = self.last_train_times.get(horizon)
        if last_time and (time.time() - last_time) > 3600:
            return True

        return False

    def train(self, horizon: int, force: bool = False) -> bool:
        """Train an XGBRegressor for the given horizon."""
        if not force and not self.should_train(horizon):
            logger.info(f"[{self.symbol}:{horizon}m] No retrain needed")
            return True

        X, y, feature_names = self.feature_engine.get_training_data(
            horizon=horizon,
            lookback_hours=self.cfg.train_lookback_hours
        )
        if X is None or len(X) < 30:
            logger.warning(
                f"[{self.symbol}:{horizon}m] Not enough data to train "
                f"(got {0 if X is None else len(X)} samples)"
            )
            return False

        try:
            model, metrics = self.fit_model(X, y)
            path = self._model_path(horizon)
            joblib.dump((model, feature_names), path)

            self.models[horizon] = {
                'model': model,
                'feature_names': feature_names,
                'path': path,
                'val_mae': metrics['val_mae'],
                'feature_count': len(feature_names),
            }

            count = self.data_store.count_prices()
            self.last_train_counts[str(horizon)] = count
            self.last_train_times[horizon] = time.time()
            self._save_counts()

            logger.info(
                f"[{self.symbol}:{horizon}m] Trained model "
                f"({len(feature_names)} features, {len(X)} samples, "
                f"{self.cfg.train_lookback_hours}h lookback, "
                f"val_mae={metrics['val_mae']:.6f}, "
                f"val_dir_acc={metrics['val_dir_acc']:.3f}, "
                f"trees={metrics['n_trees']}) -> {path}"
            )
            return True
        except Exception as e:
            logger.error(f"[{self.symbol}:{horizon}m] Training failed: {e}")
            return False

    def train_classifier(self, horizon: int, force: bool = False) -> bool:
        """Train a fee-aware direction classifier for the given horizon."""
        if not force and not self.should_train(horizon):
            logger.info(f"[{self.symbol}:{horizon}m] No classifier retrain needed")
            return True

        X, y, feature_names = self.feature_engine.get_training_data(
            horizon=horizon,
            lookback_hours=self.cfg.train_lookback_hours
        )
        if X is None or len(X) < 30:
            logger.warning(
                f"[{self.symbol}:{horizon}m] Not enough data to train classifier "
                f"(got {0 if X is None else len(X)} samples)"
            )
            return False

        try:
            model, metrics, le = self.fit_classifier(
                X, y,
                fee_pct=getattr(self.cfg, 'fee_pct', 0.05)
            )
            path = self._clf_path(horizon)
            joblib.dump((model, feature_names, le), path)

            self.classifiers[horizon] = {
                'model': model,
                'feature_names': feature_names,
                'le': le,
                'path': path,
                'val_logloss': metrics['val_logloss'],
                'val_acc': metrics['val_acc'],
                'feature_count': len(feature_names),
            }

            count = self.data_store.count_prices()
            self.last_train_counts[str(horizon)] = count
            self.last_train_times[horizon] = time.time()
            self._save_counts()

            logger.info(
                f"[{self.symbol}:{horizon}m] Trained classifier "
                f"({len(feature_names)} features, {len(X)} samples, "
                f"val_acc={metrics['val_acc']:.3f}, "
                f"val_logloss={metrics['val_logloss']:.4f}, "
                f"classes={metrics['classes']}, trees={metrics['n_trees']}) -> {path}"
            )
            return True
        except Exception as e:
            logger.error(f"[{self.symbol}:{horizon}m] Classifier training failed: {e}")
            return False

    @staticmethod
    def fit_model(X: np.ndarray, y: np.ndarray, val_frac: float = 0.15):
        """Fit an ensemble of XGBRegressor + LGBMRegressor with a time-ordered hold-out."""
        import xgboost as xgb
        from sklearn.metrics import mean_absolute_error

        n = len(X)
        split_idx = int(n * (1 - val_frac))
        X_train, y_train = X[:split_idx], y[:split_idx]
        X_val, y_val = X[split_idx:], y[split_idx:]

        # 1. XGBoost Regressor
        xgb_m = xgb.XGBRegressor(
            n_estimators=350,
            max_depth=4,
            learning_rate=0.025,
            subsample=0.85,
            colsample_bytree=0.85,
            min_child_weight=15,
            reg_lambda=3.0,
            objective='reg:squarederror',
            eval_metric='mae',
            n_jobs=2,
            random_state=42,
            early_stopping_rounds=30,
        )
        eval_set = [(X_val, y_val)] if len(X_val) > 0 else None
        xgb_m.fit(X_train, y_train, eval_set=eval_set, verbose=False)

        # 2. LightGBM Regressor
        lgb_m = None
        try:
            import lightgbm as lgb
            lgb_m = lgb.LGBMRegressor(
                n_estimators=350,
                max_depth=4,
                num_leaves=15,
                learning_rate=0.025,
                subsample=0.85,
                colsample_bytree=0.85,
                min_child_samples=20,
                reg_lambda=3.0,
                objective='regression',
                random_state=42,
                verbose=-1,
                n_jobs=2,
            )
            eval_lgb = [(X_val, y_val)] if len(X_val) > 0 else None
            cbs = [lgb.early_stopping(30, verbose=False)] if eval_lgb else None
            lgb_m.fit(X_train, y_train, eval_set=eval_lgb, callbacks=cbs)
        except Exception as e:
            logger.debug(f"LightGBM regressor skipped: {e}")

        model = EnsembleRegressor(xgb_m, lgb_m)

        metrics = {'val_mae': None, 'val_dir_acc': float('nan'), 'n_trees': 0}
        try:
            metrics['n_trees'] = int(xgb_m.get_booster().num_boosted_rounds())
        except Exception:
            pass
        if len(X_val) > 0:
            preds = model.predict(X_val)
            metrics['val_mae'] = float(mean_absolute_error(y_val, preds))
            metrics['val_dir_acc'] = float(np.mean(np.sign(preds) == np.sign(y_val)))
        return model, metrics

    @staticmethod
    def fit_classifier(X: np.ndarray, y: np.ndarray, fee_pct: float = 0.05,
                       val_frac: float = 0.15):
        """Fit an ensemble of XGBClassifier + LGBMClassifier for binary direction (Up vs Down).

        Returns (model, metrics, label_encoder).
        """
        import xgboost as xgb
        from sklearn.metrics import log_loss, accuracy_score, roc_auc_score
        from sklearn.preprocessing import LabelEncoder

        # Binary direction for Kalshi contracts: 1 = Up (return > 0), 0 = Down (return <= 0)
        y_bin = (y > 0).astype(int)
        le = LabelEncoder()
        y_enc = le.fit_transform(y_bin)

        n = len(X)
        split_idx = int(n * (1 - val_frac))
        X_train, y_train = X[:split_idx], y_enc[:split_idx]
        X_val, y_val = X[split_idx:], y_enc[split_idx:]

        # Weight higher-magnitude moves more heavily during training
        sample_weight = np.maximum(np.abs(y[:split_idx]) * 100, 0.1)

        # 1. XGBoost Binary Classifier
        xgb_m = xgb.XGBClassifier(
            n_estimators=350,
            max_depth=4,
            learning_rate=0.025,
            subsample=0.85,
            colsample_bytree=0.85,
            min_child_weight=15,
            reg_lambda=3.0,
            objective='binary:logistic',
            eval_metric='logloss',
            n_jobs=2,
            random_state=42,
            early_stopping_rounds=30,
        )
        eval_set = [(X_val, y_val)] if len(y_val) > 0 else None
        xgb_m.fit(X_train, y_train, sample_weight=sample_weight,
                  eval_set=eval_set, verbose=False)

        # 2. LightGBM Binary Classifier
        lgb_m = None
        try:
            import lightgbm as lgb
            lgb_m = lgb.LGBMClassifier(
                n_estimators=350,
                max_depth=4,
                num_leaves=15,
                learning_rate=0.025,
                subsample=0.85,
                colsample_bytree=0.85,
                min_child_samples=20,
                reg_lambda=3.0,
                objective='binary',
                random_state=42,
                verbose=-1,
                n_jobs=2,
            )
            eval_lgb = [(X_val, y_val)] if len(y_val) > 0 else None
            cbs = [lgb.early_stopping(30, verbose=False)] if eval_lgb else None
            lgb_m.fit(X_train, y_train, sample_weight=sample_weight,
                      eval_set=eval_lgb, callbacks=cbs)
        except Exception as e:
            logger.debug(f"LightGBM classifier skipped: {e}")

        model = EnsembleBinaryClassifier(xgb_m, lgb_m, classes=le.classes_.tolist())

        metrics = {'val_logloss': None, 'val_acc': float('nan'), 'val_auc': float('nan'),
                   'n_trees': 0, 'classes': le.classes_.tolist()}
        try:
            metrics['n_trees'] = int(xgb_m.get_booster().num_boosted_rounds())
        except Exception:
            pass
        if len(X_val) > 0:
            proba = model.predict_proba(X_val)
            metrics['val_logloss'] = float(log_loss(y_val, proba))
            preds = model.predict(X_val)
            metrics['val_acc'] = float(accuracy_score(y_val, preds))
            try:
                metrics['val_auc'] = float(roc_auc_score(y_val, proba[:, 1]))
            except Exception:
                pass
        return model, metrics, le

    def load(self, horizon: int) -> Optional[Tuple]:
        """Load the model for a horizon, retraining if stale or mismatched."""
        if horizon in self.models:
            return self.models[horizon]

        path = self._model_path(horizon)
        if not os.path.exists(path):
            logger.info(f"[{self.symbol}:{horizon}m] No model found, training...")
            if self.train(horizon, force=True):
                return self.models.get(horizon)
            return None

        try:
            model, feature_names = joblib.load(path)
            self.models[horizon] = {
                'model': model,
                'feature_names': feature_names,
                'path': path,
                'feature_count': len(feature_names),
            }
            logger.info(
                f"[{self.symbol}:{horizon}m] Loaded model "
                f"({len(feature_names)} features) from {path}"
            )

            # Quick feature shape check against current feature engineering
            _, current_features = self.feature_engine.get_current_features(
                horizon=horizon
            )
            if current_features is not None and \
               len(current_features) != len(feature_names):
                logger.warning(
                    f"[{self.symbol}:{horizon}m] Feature mismatch "
                    f"(saved={len(feature_names)}, current={len(current_features)}). "
                    f"Retraining..."
                )
                return None if not self.train(horizon, force=True) \
                    else self.models[horizon]

            return self.models[horizon]
        except Exception as e:
            logger.error(f"[{self.symbol}:{horizon}m] Load failed: {e}")
            return None

    def load_classifier(self, horizon: int) -> Optional[Tuple]:
        """Load the classifier for a horizon, retraining if missing/mismatched."""
        if horizon in self.classifiers:
            return self.classifiers[horizon]

        path = self._clf_path(horizon)
        if not os.path.exists(path):
            logger.info(f"[{self.symbol}:{horizon}m] No classifier found, training...")
            if self.train_classifier(horizon, force=True):
                return self.classifiers.get(horizon)
            return None

        try:
            model, feature_names, le = joblib.load(path)
            self.classifiers[horizon] = {
                'model': model,
                'feature_names': feature_names,
                'le': le,
                'path': path,
                'feature_count': len(feature_names),
            }
            logger.info(
                f"[{self.symbol}:{horizon}m] Loaded classifier "
                f"({len(feature_names)} features) from {path}"
            )

            _, current_features = self.feature_engine.get_current_features(
                horizon=horizon
            )
            if current_features is not None and \
               len(current_features) != len(feature_names):
                logger.warning(
                    f"[{self.symbol}:{horizon}m] Classifier feature mismatch "
                    f"(saved={len(feature_names)}, current={len(current_features)}). "
                    f"Retraining..."
                )
                return None if not self.train_classifier(horizon, force=True) \
                    else self.classifiers[horizon]

            return self.classifiers[horizon]
        except Exception as e:
            logger.error(f"[{self.symbol}:{horizon}m] Classifier load failed: {e}")
            return None
