#!/usr/bin/env python3
"""Single-coin, single-horizon prediction endpoint."""

import os
import numpy as np
from typing import Optional, Dict, Any

from .coin_config import CoinConfig
from .data_store import DataStore
from .feature_engine import FeatureEngine
from .model_manager import ModelManager
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
        features, feature_names = self.feature_engine.get_current_features(horizon=horizon, limit=2000)

        fallback = False
        model_used = 'xgboost'
        model_version = 'v1'
        val_mae = None
        predicted_return = 0.0

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
                    predicted_return = float(mdl.predict(X)[0])
                    model_version = str(int(os.path.getmtime(model_info['path'])))
            except Exception as e:
                logger.error(f"[{self.symbol}:{horizon}m] Prediction error: {e}")
                fallback = True
                model_used = 'fallback'

        if fallback:
            predicted_return = self._trend_fallback()

        predicted_return = float(np.clip(predicted_return, -0.05, 0.05))
        predicted_price = float(current_price * (1.0 + predicted_return))
        change_pct = round(predicted_return * 100, 4)

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
            'confidence_interval': [
                round(float(predicted_price - width), 4),
                round(float(predicted_price + width), 4)
            ],
            'model_used': model_used,
            'model_version': model_version,
            'threshold_pct': self.cfg.prediction_threshold_pct,
            'prediction_id': pred_id
        }
