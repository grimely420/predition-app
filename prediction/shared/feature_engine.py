#!/usr/bin/env python3
"""
Feature engineering shared by all coins and prediction horizons.
"""

import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional, List, Dict, Any

from .utils import setup_logging

logger = setup_logging("FeatureEngine")


def to_dataframe(records: List[Dict[str, Any]],
                 single_source: bool = False) -> Optional[pd.DataFrame]:
    """Convert raw price records into a continuous DataFrame.
    Prioritizes official CF Benchmarks and primary feeds without dropping
    entire months of historical data from other sources.
    """
    if not records:
        return None
    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, format='ISO8601')
    if 'source' in df.columns:
        source_rank = {
            'CFBenchmarks-BRTI': 1,
            'CFBenchmarks-RTI': 1,
            'CFBenchmarks-BNB-RTI': 1,
            'CFBenchmarks-HYPE-RTI': 1,
            'CFBenchmarks': 2,
            'Alpaca': 3,
            'Coinbase': 4,
            'Kraken': 5,
            'Binance': 6,
            'MEXC': 7,
            'CoinGecko': 8
        }
        df['rank'] = df['source'].map(lambda s: source_rank.get(s, 10))
        df = df.sort_values(['timestamp', 'rank']).drop_duplicates(subset=['timestamp'], keep='first')
        df = df.drop(columns=['rank'])
    else:
        df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp'], keep='last')
    df = df.set_index('timestamp')
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
        self._bars_cache: Optional[pd.DataFrame] = None
        self._bars_cache_time: float = 0.0

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

        # Time cyclicals & Kalshi 15-minute round alignment
        hour = bars.index.hour + bars.index.minute / 60.0
        feats['hour_sin'] = np.sin(2 * np.pi * hour / 24)
        feats['hour_cos'] = np.cos(2 * np.pi * hour / 24)
        dow = bars.index.dayofweek
        feats['dow_sin'] = np.sin(2 * np.pi * dow / 7)
        feats['dow_cos'] = np.cos(2 * np.pi * dow / 7)

        # 15-minute Kalshi round cycle phase (0 to 14 minutes)
        min_in_15 = bars.index.minute % 15
        feats['round_15m_phase'] = min_in_15 / 15.0
        feats['round_15m_sin'] = np.sin(2 * np.pi * min_in_15 / 15.0)
        feats['round_15m_cos'] = np.cos(2 * np.pi * min_in_15 / 15.0)

        # Real-time News Sentiment signal feature
        try:
            from .news_engine import get_news_engine
            news_feats = get_news_engine().get_features(self.symbol)
            feats['news_sentiment'] = float(news_feats.get('news_compound_signal', 0.0))
        except Exception:
            feats['news_sentiment'] = 0.0

        feats['target'] = (close.shift(-horizon) - close) / (close + 1e-10)
        return feats

    def build_bars(self, since: Optional[str] = None, until: Optional[str] = None,
                   limit: Optional[int] = None) -> Optional[pd.DataFrame]:
        """Fetch ticks in a window and resample to 1-minute OHLC bars."""
        # Short cache for concurrent prediction requests without specific time range
        if since is None and until is None and (time.time() - self._bars_cache_time < 4.0) and self._bars_cache is not None:
            return self._bars_cache.copy()

        records = self.data_store.get_prices(limit=limit, since=since, until=until)
        bars = resample_ohlc(to_dataframe(records), freq='1min')
        if since is None and until is None and bars is not None:
            self._bars_cache = bars.copy()
            self._bars_cache_time = time.time()
        return bars

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
