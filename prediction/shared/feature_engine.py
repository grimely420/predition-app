#!/usr/bin/env python3
"""
Feature engineering shared by all coins and prediction horizons.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional, List, Dict, Any

from .utils import setup_logging

logger = setup_logging("FeatureEngine")


def to_dataframe(records: List[Dict[str, Any]],
                 single_source: bool = True) -> Optional[pd.DataFrame]:
    """Convert raw price records into a DataFrame.

    Different exchanges/aggregators quote slightly different prices and some
    lag others by a minute or more. Mixing them inside one bar series creates
    fake mean-reversion that a model will happily "learn" but that cannot be
    traded. With ``single_source`` we keep only the most frequent source in
    the window.
    """
    if not records:
        return None
    df = pd.DataFrame(records)
    if single_source and 'source' in df.columns and df['source'].notna().any():
        top = df['source'].value_counts().idxmax()
        df = df[df['source'] == top]
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, format='ISO8601')
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
        # Optional callable(bars) -> DataFrame aligned to bars.index with
        # extra feature columns (e.g. Hyperliquid market data). None = off.
        self.extras_fn = None

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

        for w in [30, 60]:
            feats[f'return_{w}'] = close.pct_change(w)
            feats[f'volatility_{w}'] = returns.rolling(w, min_periods=10).std()
        feats['vol_ratio_5_60'] = feats['volatility_5'] / (feats['volatility_60'] + 1e-10)

        for lag in [1, 5, 15]:
            feats[f'autocorr_{lag}'] = returns.rolling(60, min_periods=30).corr(returns.shift(lag))

        # Volatility regime flags using only past data (no future leak)
        vol_60 = feats['volatility_60']
        vol_high = vol_60.rolling(1000, min_periods=200).quantile(0.75)
        vol_low = vol_60.rolling(1000, min_periods=200).quantile(0.25)
        feats['regime_low'] = (vol_60 < vol_low).astype(float)
        feats['regime_high'] = (vol_60 > vol_high).astype(float)

        # Time cyclicals
        hour = bars.index.hour + bars.index.minute / 60.0
        feats['hour_sin'] = np.sin(2 * np.pi * hour / 24)
        feats['hour_cos'] = np.cos(2 * np.pi * hour / 24)
        dow = bars.index.dayofweek
        feats['dow_sin'] = np.sin(2 * np.pi * dow / 7)
        feats['dow_cos'] = np.cos(2 * np.pi * dow / 7)

        feats['target'] = (close.shift(-horizon) - close) / (close + 1e-10)
        return feats

    def build_bars(self, since: Optional[str] = None, until: Optional[str] = None,
                   limit: Optional[int] = None) -> Optional[pd.DataFrame]:
        """Fetch ticks in a window and resample to 1-minute OHLC bars."""
        records = self.data_store.get_prices(limit=limit, since=since, until=until)
        return resample_ohlc(to_dataframe(records), freq='1min')

    def features_from_bars(self, bars: pd.DataFrame, horizon: int):
        """Return (feature_frame, feature_cols) with NaN feature rows dropped."""
        feats = self._build_features(bars, horizon)
        if self.extras_fn is not None:
            try:
                extra = self.extras_fn(bars)
                if extra is not None and not extra.empty:
                    feats = feats.join(extra)
            except Exception as e:
                logger.warning(f"extras loader failed: {e}")
        feature_cols = [c for c in feats.columns if c != 'target']
        return feats.dropna(subset=feature_cols), feature_cols

    def get_training_data(self, horizon: int, lookback_hours: int = 168,
                          until: Optional[str] = None):
        end = datetime.fromisoformat(until) if until else datetime.now(timezone.utc)
        since = (end - timedelta(hours=lookback_hours)).isoformat()
        bars = self.build_bars(since=since, until=until)
        if bars is None or len(bars) < max(20, horizon) + 5:
            return None, None, None

        feats, feature_cols = self.features_from_bars(bars, horizon)
        train = feats.dropna(subset=['target'])
        if len(train) < 30:
            return None, None, None

        X = train[feature_cols].values
        y = train['target'].values
        return X, y, feature_cols

    def get_current_features(self, horizon: int, limit: int = 8000):
        bars = self.build_bars(limit=limit)
        if bars is None or len(bars) < max(20, horizon) + 5:
            return None, None

        feats, feature_cols = self.features_from_bars(bars, horizon)
        if len(feats) == 0:
            return None, None
        return feats.iloc[-1][feature_cols].values, feature_cols
