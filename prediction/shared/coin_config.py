#!/usr/bin/env python3
"""
Central configuration for all supported prediction coins.
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _parse_binance_price(data: dict) -> float:
    return float(data.get('price', 0))


def _parse_coinbase_price(data: dict) -> float:
    return float(data['data']['amount'])


def _parse_kraken_xxbtzusd(data: dict) -> float:
    return float(data['result']['XXBTZUSD']['c'][0])


def _parse_kraken_bnbusd(data: dict) -> float:
    return float(data['result']['BNBUSD']['c'][0])


def _parse_coingecko_hype(data: dict) -> float:
    return float(data['hyperliquid']['usd'])


@dataclass
class CoinConfig:
    """Configuration for a single coin."""
    symbol: str
    display_name: str
    db_name: str
    price_sources: List[Dict[str, Any]] = field(default_factory=list)
    min_price: float = 0.0
    max_price: float = 1e12
    collection_interval: int = 5
    prediction_horizons: List[int] = field(default_factory=lambda: [5, 10, 15])
    min_train_bars: int = 60
    retrain_min_bars: int = 30
    prediction_threshold_pct: float = 1.0
    api_port: int = 5000

    @property
    def db_path(self) -> str:
        return os.path.join(BASE_DIR, self.db_name, f"{self.db_name}_prices.db")

    @property
    def model_dir(self) -> str:
        return os.path.join(BASE_DIR, self.db_name, "models")

    def ensure_dirs(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)


def _btc_sources() -> List[Dict[str, Any]]:
    return [
        {
            'name': 'Coinbase',
            'url': 'https://api.coinbase.com/v2/prices/BTC-USD/spot',
            'parser': _parse_coinbase_price,
            'timeout': 10,
            'cooldown': 6,
            'weight': 1,
        },
        {
            'name': 'Kraken',
            'url': 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD',
            'parser': _parse_kraken_xxbtzusd,
            'timeout': 10,
            'cooldown': 6,
            'weight': 2,
        },
        {
            'name': 'Binance',
            'url': 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT',
            'parser': _parse_binance_price,
            'timeout': 10,
            'cooldown': 6,
            'weight': 5,
        },
    ]


def _bnb_sources() -> List[Dict[str, Any]]:
    return [
        {
            'name': 'Binance',
            'url': 'https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT',
            'parser': _parse_binance_price,
            'timeout': 10,
            'cooldown': 6,
            'weight': 1,
        },
        {
            'name': 'Coinbase',
            'url': 'https://api.coinbase.com/v2/prices/BNB-USD/spot',
            'parser': _parse_coinbase_price,
            'timeout': 10,
            'cooldown': 6,
            'weight': 2,
        },
        {
            'name': 'Kraken',
            'url': 'https://api.kraken.com/0/public/Ticker?pair=BNBUSD',
            'parser': _parse_kraken_bnbusd,
            'timeout': 10,
            'cooldown': 6,
            'weight': 3,
        },
    ]


def _hype_sources() -> List[Dict[str, Any]]:
    return [
        {
            'name': 'CoinGecko',
            'url': 'https://api.coingecko.com/api/v3/simple/price?ids=hyperliquid&vs_currencies=usd',
            'parser': _parse_coingecko_hype,
            'timeout': 15,
            'cooldown': 8,
            'weight': 1,
        },
    ]


COINS: Dict[str, CoinConfig] = {
    'btc': CoinConfig(
        symbol='BTC',
        display_name='Bitcoin',
        db_name='bitcoin',
        price_sources=_btc_sources(),
        min_price=1000.0,
        max_price=1_000_000.0,
        collection_interval=5,
        prediction_horizons=[5, 10, 15],
        min_train_bars=120,
        retrain_min_bars=60,
        prediction_threshold_pct=1.0,
    ),
    'bnb': CoinConfig(
        symbol='BNB',
        display_name='BNB',
        db_name='bnb',
        price_sources=_bnb_sources(),
        min_price=10.0,
        max_price=100_000.0,
        collection_interval=5,
        prediction_horizons=[5, 10, 15],
        min_train_bars=120,
        retrain_min_bars=60,
        prediction_threshold_pct=1.0,
    ),
    'hype': CoinConfig(
        symbol='HYPE',
        display_name='HYPE',
        db_name='hype',
        price_sources=_hype_sources(),
        min_price=0.01,
        max_price=1_000_000.0,
        collection_interval=6,
        prediction_horizons=[5, 10, 15],
        min_train_bars=60,
        retrain_min_bars=30,
        prediction_threshold_pct=2.0,
    ),
}


def get_coin_config(coin_id: str) -> CoinConfig:
    """Return configuration for a coin id (case-insensitive)."""
    key = coin_id.lower()
    if key not in COINS:
        raise ValueError(f"Unknown coin: {coin_id}. Supported: {list(COINS.keys())}")
    cfg = COINS[key]
    cfg.ensure_dirs()
    return cfg


def list_coins() -> List[str]:
    return list(COINS.keys())
