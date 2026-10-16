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
        # ticker -> (fetched_at, book snapshot dict)
        self._book_cache: Dict[str, tuple] = {}
        # (series, round_start_iso) -> ticker — once a round's market is
        # discovered it never changes, so cache it permanently and skip the
        # market-list scans on every subsequent call.
        self._round_ticker: Dict[tuple, str] = {}

    def _find_market(self, series: str, round_start: datetime,
                     round_end: datetime) -> Optional[dict]:
        """Market dict for the round, matching open+close within 30s."""
        tkey = (series, round_start.isoformat())
        cached = self._round_ticker.get(tkey)
        if cached:
            return {'ticker': cached}
        for status in ('open', 'settled'):
            for m in self._fetch_markets(series, status=status):
                ot, ct = _parse_ts(m.get('open_time')), _parse_ts(m.get('close_time'))
                if ot and ct and \
                        abs((ot - round_start).total_seconds()) <= 30 and \
                        abs((ct - round_end).total_seconds()) <= 30:
                    if m.get('ticker'):
                        self._round_ticker[tkey] = m['ticker']
                    return m
        return None

    def get_book_snapshot(self, series: str, round_start: datetime,
                          round_end: datetime) -> Optional[Dict[str, Any]]:
        """Best bid/ask + mid for the live round's market, in cents.

        Kalshi's public orderbook returns resting *bids* in fixed-point
        dollars per side. Best asks are derived from the opposite side:
            yes_ask = 100 - best_no_bid,   no_ask = 100 - best_yes_bid.
        Returns None when the market/book is unavailable (thin books legit-
        imately return None on a side).
        """
        if round_start.tzinfo is None:
            round_start = round_start.replace(tzinfo=timezone.utc)
        if round_end.tzinfo is None:
            round_end = round_end.replace(tzinfo=timezone.utc)
        m = self._find_market(series, round_start, round_end)
        if not m or not m.get('ticker'):
            return None
        ticker = m['ticker']
        ent = self._book_cache.get(ticker)
        if ent and (time.time() - ent[0]) < 2.0:
            return ent[1]
        try:
            r = requests.get(f"{BASE_URL}/{ticker}/orderbook",
                             headers={'User-Agent': 'predition-app/1.0'},
                             timeout=8)
            r.raise_for_status()
            ob = (r.json().get('orderbook_fp')
                  or r.json().get('orderbook') or {})

            def best_bid(side):
                rows = ob.get(f'{side}_dollars') or []
                px = [float(p) for p, _q in rows]
                return max(px) * 100.0 if px else None  # cents

            yes_bid = best_bid('yes')
            no_bid = best_bid('no')
            yes_ask = 100.0 - no_bid if no_bid is not None else None
            no_ask = 100.0 - yes_bid if yes_bid is not None else None
            mid = None
            if yes_bid is not None and yes_ask is not None:
                mid = (yes_bid + yes_ask) / 2.0
            out = {'yes_bid': yes_bid, 'yes_ask': yes_ask,
                   'no_bid': no_bid, 'no_ask': no_ask,
                   'mid_yes': mid, 'ticker': ticker}
            self._book_cache[ticker] = (time.time(), out)
            return out
        except Exception as e:
            logger.debug(f"orderbook {ticker}: {e}")
            return ent[1] if ent else None

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
