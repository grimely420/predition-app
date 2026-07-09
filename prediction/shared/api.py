#!/usr/bin/env python3
"""Unified Flask API for all coins and horizons."""

from flask import Flask, jsonify, request

from .coin_config import get_coin_config, list_coins
from .data_store import DataStore
from .feature_engine import FeatureEngine
from .model_manager import ModelManager
from .predictor_core import Predictor
from .validator import Validator
from .utils import setup_logging

logger = setup_logging("API")

_CACHE = {}


def get_components(coin_id: str):
    """Return cached components for a coin."""
    key = coin_id.lower()
    if key not in _CACHE:
        cfg = get_coin_config(key)
        ds = DataStore(cfg.db_path, cfg.symbol)
        fe = FeatureEngine(ds, cfg.symbol)
        mm = ModelManager(cfg, ds, fe)
        pred = Predictor(cfg, ds, fe, mm)
        val = Validator(cfg, ds)
        _CACHE[key] = (cfg, ds, fe, mm, pred, val)
    return _CACHE[key]


def create_app() -> Flask:
    app = Flask(__name__)
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

    @app.route('/predict/<coin_id>/<int:horizon>', methods=['GET'])
    def predict_one(coin_id, horizon):
        try:
            cfg, ds, fe, mm, pred, val = get_components(coin_id)
        except Exception as e:
            return jsonify(error=str(e)), 400
        if horizon not in cfg.prediction_horizons:
            return jsonify(error=f"Invalid horizon: {horizon}"), 400
        result = pred.predict(horizon)
        if result is None:
            return jsonify(error='Prediction failed'), 503
        return jsonify(result)

    @app.route('/predict/<coin_id>', methods=['GET'])
    def predict_all(coin_id):
        try:
            cfg, ds, fe, mm, pred, val = get_components(coin_id)
        except Exception as e:
            return jsonify(error=str(e)), 400
        results = []
        for h in cfg.prediction_horizons:
            r = pred.predict(h)
            if r:
                results.append(r)
        if not results:
            return jsonify(error='No predictions available'), 503
        return jsonify({'coin_id': coin_id, 'predictions': results})

    @app.route('/validate/<coin_id>', methods=['POST'])
    def validate_coin(coin_id):
        try:
            cfg, ds, fe, mm, pred, val = get_components(coin_id)
        except Exception as e:
            return jsonify(error=str(e)), 400
        n = val.validate()
        return jsonify({'coin_id': coin_id, 'validated': n})

    @app.route('/stats/<coin_id>', methods=['GET'])
    def stats(coin_id):
        try:
            cfg, ds, fe, mm, pred, val = get_components(coin_id)
        except Exception as e:
            return jsonify(error=str(e)), 400
        return jsonify({
            'coin_id': coin_id,
            'price_count': ds.count_prices(),
            'stats': {
                h: ds.get_prediction_stats(horizon=h)
                for h in cfg.prediction_horizons
            }
        })

    @app.route('/', methods=['GET'])
    def index():
        return jsonify({
            'service': 'Cryptocurrency Prediction API',
            'coins': list_coins(),
            'endpoints': {
                'GET /': 'This page',
                'GET /health': 'Health check',
                'GET /coins': 'List supported coins',
                'GET /predict/<coin>': 'Predictions for all horizons (5, 10, 15 min)',
                'GET /predict/<coin>/<horizon>': 'Single horizon prediction',
                'GET /stats/<coin>': 'Prediction accuracy stats',
                'POST /validate/<coin>': 'Validate past predictions',
            }
        })

    @app.route('/coins', methods=['GET'])
    def coins():
        return jsonify({'coins': list_coins()})

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok'})

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, threaded=True)
