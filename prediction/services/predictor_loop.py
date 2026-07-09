#!/usr/bin/env python3
"""Run predictions, validation, and periodic retraining for one coin."""

import os
import sys
import time
import signal
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.coin_config import get_coin_config
from shared.data_store import DataStore
from shared.feature_engine import FeatureEngine
from shared.model_manager import ModelManager
from shared.predictor_core import Predictor
from shared.validator import Validator
from shared.utils import setup_logging

logger = setup_logging("PredictorLoop")


class PredictorLoop:
    def __init__(self, coin_id: str):
        self.cfg = get_coin_config(coin_id)
        self.ds = DataStore(self.cfg.db_path, self.cfg.symbol)
        self.fe = FeatureEngine(self.ds, self.cfg.symbol)
        self.mm = ModelManager(self.cfg, self.ds, self.fe)
        self.predictor = Predictor(self.cfg, self.ds, self.fe, self.mm)
        self.validator = Validator(self.cfg, self.ds)
        self.running = True
        self._setup_signals()

    def _setup_signals(self):
        def handler(signum, frame):
            self.running = False
            logger.info("Shutdown signal received")
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def _predict_all(self):
        for h in self.cfg.prediction_horizons:
            try:
                result = self.predictor.predict(h)
                if result:
                    logger.info(
                        f"[{self.cfg.symbol}:{h}m] Predicted {result['predicted_price']} "
                        f"(change {result['change_percent']}% model={result['model_used']})"
                    )
            except Exception as e:
                logger.error(f"[{self.cfg.symbol}:{h}m] Prediction failed: {e}")

    def _validate(self):
        try:
            n = self.validator.validate()
            if n:
                logger.info(f"[{self.cfg.symbol}] Validated {n} predictions")
        except Exception as e:
            logger.error(f"[{self.cfg.symbol}] Validation failed: {e}")

    def _maybe_retrain(self):
        try:
            for h in self.cfg.prediction_horizons:
                if self.mm.should_train(h):
                    logger.info(f"[{self.cfg.symbol}:{h}m] Retraining model")
                    self.mm.train(h, force=False)
        except Exception as e:
            logger.error(f"[{self.cfg.symbol}] Retraining failed: {e}")

    def run(self):
        logger.info(f"{self.cfg.symbol} predictor loop started")
        last_predict = 0
        last_validate = 0
        last_retrain = 0
        while self.running:
            now = time.time()
            if now - last_validate >= 60:
                self._validate()
                last_validate = now
            if now - last_predict >= 300:
                self._predict_all()
                last_predict = now
            if now - last_retrain >= 3600:
                self._maybe_retrain()
                last_retrain = now
            time.sleep(5)
        logger.info(f"{self.cfg.symbol} predictor loop stopped")


def main():
    coin_id = sys.argv[1] if len(sys.argv) > 1 else 'btc'
    loop = PredictorLoop(coin_id)
    loop.run()


if __name__ == '__main__':
    main()
