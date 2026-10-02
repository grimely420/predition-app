#!/usr/bin/env python3
"""Official Kalshi market data — the ground truth for strikes & settlements.

Our own tick-derived strike (nearest RTI tick after round open) and
settlement estimate (60s TWAP) systematically drift from Kalshi's official
values: the Kraken index_price we poll lags the published CF Benchmarks
print, and boundary grabs can land on the wrong tick. Kalshi's public REST
API exposes the authoritative `floor_strike` when a market opens and
`result` (yes/no) shortly after close — use those when available so the
dashboard shows exactly what the trading app shows.
"""

import time
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from .utils import setup_logging

logger = setup_logging("KalshiMarkets")

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"


def _parse_ts(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    except Exception:
        return None


class KalshiMarketClient:
    """Small cached client for Kalshi's public markets endpoint."""

    def __init__(self, cache_ttl: float = 3.0):
        self._cache_ttl = cache_ttl
        # series -> (fetched_at, [market dicts])
        self._markets_cache: Dict[str, tuple] = {}
        # (series, round_start_iso) -> strike float
        self._strike_cache: Dict[tuple, float] = {}
        # (series, round_end_iso) -> {'result': 'yes'/'no', 'settlement': float|None}
        self._result_cache: Dict[tuple, Dict[str, Any]] = {}

    def _fetch_markets(self, series: str,
                       status: Optional[str] = None) -> list:
        key = f"{series}:{status}"
        ent = self._markets_cache.get(key)
        if ent and (time.time() - ent[0]) < self._cache_ttl:
            return ent[1]
        params = {'series_ticker': series, 'limit': 50}
        if status:
            params['status'] = status
        try:
            r = requests.get(BASE_URL, params=params,
                             headers={'User-Agent': 'predition-app/1.0'},
                             timeout=8)
            r.raise_for_status()
            markets = r.json().get('markets', [])
            self._markets_cache[key] = (time.time(), markets)
            return markets
        except Exception as e:
            logger.debug(f"kalshi markets fetch {series}: {e}")
            return ent[1] if ent else []

    def get_official_strike(self, series: str,
                            round_start: datetime) -> Optional[float]:
        """floor_strike of the market whose open_time == round_start.

        Returns None until the market is listed (usually within seconds of
        round open) or if the API is unreachable.
        """
        if round_start.tzinfo is None:
            round_start = round_start.replace(tzinfo=timezone.utc)
        key = (series, round_start.isoformat())
        if key in self._strike_cache:
            return self._strike_cache[key]
        for m in self._fetch_markets(series, status='open') + \
                self._fetch_markets(series, status='settled'):
            ot = _parse_ts(m.get('open_time'))
            if ot and abs((ot - round_start).total_seconds()) <= 30:
                strike = m.get('floor_strike')
                if strike is not None:
                    try:
                        val = float(strike)
                        self._strike_cache[key] = val
                        return val
                    except (TypeError, ValueError):
                        pass
        return None

    def get_official_result(self, series: str,
                            round_start: datetime,
                            round_end: datetime) -> Optional[Dict[str, Any]]:
        """{'result': 'yes'|'no', 'settlement': float|None, 'ticker': str}
        for the market whose open/close bound the round, once Kalshi has
        settled it. None while pending or on API failure.
        """
        if round_start.tzinfo is None:
            round_start = round_start.replace(tzinfo=timezone.utc)
        if round_end.tzinfo is None:
            round_end = round_end.replace(tzinfo=timezone.utc)
        key = (series, round_end.isoformat())
        if key in self._result_cache:
            return self._result_cache[key]
        for m in self._fetch_markets(series, status='settled'):
            ot, ct = _parse_ts(m.get('open_time')), _parse_ts(m.get('close_time'))
            if not (ot and ct):
                continue
            if abs((ot - round_start).total_seconds()) <= 30 and \
               abs((ct - round_end).total_seconds()) <= 30:
                res = m.get('result')
                if res in ('yes', 'no'):
                    out = {
                        'result': res,
                        'settlement': m.get('settlement_value'),
                        'ticker': m.get('ticker'),
                        'strike': m.get('floor_strike'),
                    }
                    self._result_cache[key] = out
                    return out
                # market matched but not settled yet — keep polling
                return None
        return None


_client: Optional[KalshiMarketClient] = None


def get_kalshi_markets() -> KalshiMarketClient:
    global _client
    if _client is None:
        _client = KalshiMarketClient()
    return _client
