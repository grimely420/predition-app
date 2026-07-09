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


class ModelManager:
    """Trains/loads XGBoost models per horizon and handles feature mismatch."""

    def __init__(self, coin_cfg, data_store, feature_engine):
        self.cfg = coin_cfg
        self.symbol = coin_cfg.symbol
        self.data_store = data_store
        self.feature_engine = feature_engine
        self.models: Dict[int, Dict[str, Any]] = {}
        self.model_dir = coin_cfg.model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        self.last_train_counts = self._load_counts()
        self.last_train_times: Dict[int, float] = {}

    def _model_path(self, horizon: int) -> str:
        return os.path.join(self.model_dir, f"xgb_{horizon}min_latest.pkl")

    def _counts_path(self) -> str:
        return os.path.join(self.model_dir, ".last_train_counts.json")

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
            limit=2000
        )
        if X is None or len(X) < 30:
            logger.warning(
                f"[{self.symbol}:{horizon}m] Not enough data to train "
                f"(got {0 if X is None else len(X)} samples)"
            )
            return False

        try:
            import xgboost as xgb
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import mean_absolute_error

            # Time-based split: use last 20% as validation
            n = len(X)
            split_idx = int(n * 0.85)
            X_train, y_train = X[:split_idx], y[:split_idx]
            X_val, y_val = X[split_idx:], y[split_idx:]

            model = xgb.XGBRegressor(
                n_estimators=120,
                max_depth=4,
                learning_rate=0.08,
                subsample=0.85,
                colsample_bytree=0.85,
                objective='reg:squarederror',
                eval_metric='mae',
                n_jobs=2,
                random_state=42,
                early_stopping_rounds=15,
            )

            eval_set = [(X_train, y_train), (X_val, y_val)] if len(X_val) > 0 else None
            model.fit(
                X_train, y_train,
                eval_set=eval_set,
                verbose=False
            )

            # Compute out-of-sample MAE on validation set
            val_mae = None
            if len(X_val) > 0:
                preds = model.predict(X_val)
                val_mae = mean_absolute_error(y_val, preds)

            path = self._model_path(horizon)
            joblib.dump((model, feature_names), path)

            self.models[horizon] = {
                'model': model,
                'feature_names': feature_names,
                'path': path,
                'val_mae': val_mae,
                'feature_count': len(feature_names),
            }

            count = self.data_store.count_prices()
            self.last_train_counts[str(horizon)] = count
            self.last_train_times[horizon] = time.time()
            self._save_counts()

            logger.info(
                f"[{self.symbol}:{horizon}m] Trained model "
                f"({len(feature_names)} features, {len(X)} samples, "
                f"val_mae={val_mae:.6f}) -> {path}"
            )
            return True
        except Exception as e:
            logger.error(f"[{self.symbol}:{horizon}m] Training failed: {e}")
            return False

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
                horizon=horizon,
                limit=2000
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
