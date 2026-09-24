#!/usr/bin/env python3
"""Single-coin, single-horizon prediction endpoint."""

import os
import numpy as np
from typing import Optional, Dict, Any

from .coin_config import CoinConfig
from .data_store import DataStore
from .feature_engine import FeatureEngine
from .model_manager import ModelManager
from .news_engine import get_news_engine
from .utils import setup_logging

logger = setup_logging("PredictorCore")


class Predictor:
    """Generate and log a price prediction for one coin and one horizon."""

    def __init__(self, coin_cfg: CoinConfig, data_store: DataStore,
                 feature_engine: FeatureEngine, model_manager: ModelManager):
        self.cfg = coin_cfg
        self.symbol = coin_cfg.symbol
        self.data_store = data_store
        self.feature_engine = feature_engine
        self.model_manager = model_manager

    def _current_price(self) -> Optional[float]:
        last = self.data_store.last_price()
        if last is not None:
            return float(last[0])
        return None

    def _trend_fallback(self) -> float:
        try:
            records = self.data_store.get_prices(limit=60)
            if not records or len(records) < 5:
                return 0.0
            prices = np.array([float(r['price']) for r in records])
            x = np.arange(len(prices))
            slope = np.polyfit(x, prices, 1)[0]
            if prices[-1]:
                return float(slope / prices[-1])
        except Exception as e:
            logger.debug(f"[{self.symbol}] trend fallback error: {e}")
        return 0.0

    def predict(self, horizon: int, current_price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        if current_price is None:
            current_price = self._current_price()
        if current_price is None:
            logger.error(f"[{self.symbol}:{horizon}m] No current price")
            return None

        if current_price < self.cfg.min_price or current_price > self.cfg.max_price:
            logger.warning(f"[{self.symbol}:{horizon}m] Price {current_price} outside sanity range")

        model_info = self.model_manager.load(horizon)
        clf_info = self.model_manager.load_classifier(horizon)
        features, feature_names = self.feature_engine.get_current_features(horizon=horizon)

        fallback = False
        model_used = 'xgboost'
        model_version = 'v1'
        val_mae = None
        raw_return = 0.0
        predicted_return = 0.0
        signal_strength = 1.0
        probs = {'up': 1/3, 'down': 1/3, 'flat': 1/3}
        expected_pnl_pct = -0.05

        if model_info is None or features is None:
            fallback = True
            model_used = 'fallback'
        else:
            try:
                mdl = model_info['model']
                fnames = model_info.get('feature_names') or feature_names
                val_mae = model_info.get('val_mae')

                if len(features) != len(fnames):
                    logger.warning(f"[{self.symbol}:{horizon}m] Feature mismatch, retraining")
                    if self.model_manager.train(horizon, force=True):
                        model_info = self.model_manager.load(horizon)
                    if model_info is None:
                        fallback = True
                        model_used = 'fallback'
                    else:
                        mdl = model_info['model']
                        fnames = model_info.get('feature_names') or feature_names
                        val_mae = model_info.get('val_mae')

                if not fallback:
                    X = np.array(features).reshape(1, -1)
                    raw_return = float(mdl.predict(X)[0])
                    model_version = str(int(os.path.getmtime(model_info['path'])))

                    # Blend with classifier probability
                    if clf_info is not None:
                        clf = clf_info['model']
                        le = clf_info['le']
                        prob = clf.predict_proba(X)[0]
                        class_to_prob = {int(c): float(p) for c, p in zip(le.classes_, prob)}
                        probs = {
                            'up': class_to_prob.get(1, 0.0),
                            'down': class_to_prob.get(-1, 0.0),
                            'flat': class_to_prob.get(0, 0.0),
                        }
                        signal_strength = probs['up'] - probs['down']
                        # Correct directional consensus (NEVER invert negative * negative):
                        reg_dir = 1.0 if raw_return > 0 else (-1.0 if raw_return < 0 else 0.0)
                        clf_dir = 1.0 if signal_strength > 0.04 else (-1.0 if signal_strength < -0.04 else 0.0)

                        if clf_dir != 0.0:
                            # If classifier has directional conviction, sign follows classifier
                            final_sign = clf_dir
                            # If regressor agrees, amplify magnitude; if it disagrees, dampen
                            mult = (1.0 + abs(signal_strength)) if reg_dir == clf_dir else max(0.2, 1.0 - abs(signal_strength))
                            mag = max(abs(raw_return), abs(signal_strength) * 0.003) * mult
                            predicted_return = float(np.clip(final_sign * mag, -0.05, 0.05))
                        else:
                            # Classifier is neutral, follow regressor with dampening
                            predicted_return = float(np.clip(raw_return * (1.0 - probs.get('flat', 0.3) * 0.5), -0.05, 0.05))
                    else:
                        predicted_return = float(np.clip(raw_return, -0.05, 0.05))
            except Exception as e:
                logger.error(f"[{self.symbol}:{horizon}m] Prediction error: {e}")
                fallback = True
                model_used = 'fallback'

        if fallback:
            predicted_return = self._trend_fallback()

        # Factor in real-time crypto news sentiment for short-horizon spans (5-17 mins)
        news_signal = 0.0
        try:
            news_feats = get_news_engine().get_features(self.symbol)
            news_signal = news_feats.get('news_compound_signal', 0.0)
            # 5-17 minute impact drift: up to ~0.15% (0.0015) based on news sentiment
            news_drift = news_signal * 0.0015 * (horizon / 15.0)
            predicted_return = float(np.clip(predicted_return + news_drift, -0.05, 0.05))
        except Exception as e:
            logger.debug(f"News drift calculation failed: {e}")

        fee_pct = getattr(self.cfg, 'fee_pct', 0.05)
        predicted_return = float(np.clip(predicted_return, -0.05, 0.05))
        predicted_price = float(current_price * (1.0 + predicted_return))
        change_pct = round(predicted_return * 100, 4)
        raw_change_pct = round(np.clip(raw_return, -0.05, 0.05) * 100, 4)
        expected_pnl_pct = round(predicted_return * 100 - fee_pct, 4)

        if val_mae is None or not np.isfinite(val_mae):
            val_mae = 0.002
        width = float(max(0.01, val_mae * current_price))

        pred_id = self.data_store.log_prediction(
            horizon_min=horizon,
            current_price=current_price,
            predicted_price=predicted_price,
            model_used=model_used,
            model_version=model_version
        )

        return {
            'success': True,
            'coin_id': self.cfg.db_name,
            'symbol': self.symbol,
            'horizon_minutes': horizon,
            'current_price': round(float(current_price), 4),
            'predicted_price': round(float(predicted_price), 4),
            'change_percent': float(change_pct),
            'raw_change_percent': float(raw_change_pct),
            'signal_strength': round(float(signal_strength), 4),
            'news_sentiment': round(float(news_signal), 4),
            'prob_up': round(float(probs['up']), 4),
            'prob_down': round(float(probs['down']), 4),
            'prob_flat': round(float(probs['flat']), 4),
            'expected_pnl_pct': float(expected_pnl_pct),
            'confidence_interval': [
                round(float(predicted_price - width), 4),
                round(float(predicted_price + width), 4)
            ],
            'model_used': model_used,
            'model_version': model_version,
            'threshold_pct': self.cfg.prediction_threshold_pct,
            'prediction_id': pred_id
        }
