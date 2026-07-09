#!/usr/bin/env python3
"""
Feature engineering shared by all coins and prediction horizons.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Tuple, Optional, List, Dict, Any

from .utils import setup_logging

logger = setup_logging("FeatureEngine")


def to_dataframe(records: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
    """Convert raw price records into a DataFrame."""
    if not records:
        return None
    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.sort_values('timestamp').set_index('timestamp')
    df = df[~df.index.duplicated(keep='last')]
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df = df.dropna(subset=['price'])
    return df


def resample_ohlc(df: pd.DataFrame, freq: str = '1min') -> Optional[pd.DataFrame]:
    """Resample tick price data into OHLC bars."""
    if df is None or len(df) < 2:
        return None
    try:
        ohlc = df.resample(freq, closed='left', label='left').agg({
            'price': ['first', 'max', 'min', 'last']
        })
        ohlc.columns = ['open', 'high', 'low', 'close']
        return ohlc.dropna()
    except Exception as e:
        logger.error(f"resample error: {e}")
        return None


class FeatureEngine:
    """Compute a stable feature set for any coin / horizon."""

    def __init__(self, data_store, symbol: str):
        self.data_store = data_store
        self.symbol = symbol

    def _build_features(self, bars: pd.DataFrame, horizon: int) -> pd.DataFrame:
        close = bars['close']
        high = bars['high']
        low = bars['low']
        returns = close.pct_change()

        feats = pd.DataFrame(index=bars.index)
        feats['return_1'] = returns

        for w in [3, 5, 10, 15]:
            feats[f'return_{w}'] = close.pct_change(w)

        for w in [3, 5, 10]:
            feats[f'momentum_{w}'] = close - close.shift(w)

        for w in [5, 10, 20]:
            feats[f'volatility_{w}'] = returns.rolling(w, min_periods=3).std()

        for w in [5, 10, 20]:
            ma = close.rolling(w, min_periods=3).mean()
            feats[f'ma_dist_{w}'] = (close - ma) / (ma + 1e-10)

        feats['hl_range_pct'] = (high - low) / (close + 1e-10)
        feats['price_position'] = (close - low) / (high - low + 1e-10)

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14, min_periods=5).mean()
        loss = (-delta.clip(upper=0)).rolling(14, min_periods=5).mean()
        rs = gain / (loss + 1e-10)
        feats['rsi_14'] = 100 - 100 / (1 + rs)

        feats['target'] = (close.shift(-horizon) - close) / (close + 1e-10)
        return feats

    def get_training_data(self, horizon: int, limit: int = 2000):
        records = self.data_store.get_prices(limit=limit)
        df = to_dataframe(records)
        bars = resample_ohlc(df, freq='1min')
        if bars is None or len(bars) < max(20, horizon) + 5:
            return None, None, None

        feats = self._build_features(bars, horizon)
        feature_cols = [c for c in feats.columns if c != 'target']
        feats = feats.dropna(subset=feature_cols)
        train = feats.dropna(subset=['target'])
        if len(train) < 30:
            return None, None, None

        X = train[feature_cols].values
        y = train['target'].values
        return X, y, feature_cols

    def get_current_features(self, horizon: int, limit: int = 2000):
        records = self.data_store.get_prices(limit=limit)
        df = to_dataframe(records)
        bars = resample_ohlc(df, freq='1min')
        if bars is None or len(bars) < max(20, horizon) + 5:
            return None, None

        feats = self._build_features(bars, horizon)
        feature_cols = [c for c in feats.columns if c != 'target']
        feats = feats.dropna(subset=feature_cols)
        if len(feats) == 0:
            return None, None
        return feats.iloc[-1][feature_cols].values, feature_cols
