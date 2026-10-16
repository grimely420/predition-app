#!/usr/bin/env python3
"""Empirical settlement-probability surface from REAL data only.

For every Kalshi 15m market that has already settled (official
floor_strike + result from the Kalshi API), we look up our own archived
CF Benchmarks RTI ticks at each minute-mark of the round and compute

    z = ln(price_t / floor_strike) / sqrt(mins_remaining)

— the normalized distance-to-strike that the digital-option formula says
should drive the outcome probability. The script then fits a monotone
isotonic map  z -> P(resolved YES)  per coin on the oldest 60% of
observations and validates on the newest 40%.

No invented parameters: every number comes from Kalshi settlements and
archived RTI ticks. Artifacts land in <coin>/settle_surface.json:
    {'z': [...knots...], 'p': [...empirical P(YES)...]}
The engine can linearly interpolate the surface at inference; deleting
the file reverts. Reported Brier is compared against the market mid where
book data exists so we know whether the empirical surface adds value.

Run from prediction/:
    .venv/bin/python scripts/build_settlement_surface.py
"""

import glob
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import requests

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"
SERIES = {
    'bitcoin': 'KXBTC15M', 'bnb': 'KXBNB15M', 'hype': 'KXHYPE15M',
    'eth': 'KXETH15M', 'sol': 'KXSOL15M', 'xrp': 'KXXRP15M',
    'doge': 'KXDOGE15M', 'near': 'KXNEAR15M', 'zec': 'KXZEC15M',
}
MAX_MARKETS = 4000          # per series (recent first)
SAMPLE_OFFSETS_MIN = list(range(1, 15))  # minutes before close to sample
FIT_FRAC = 0.60
UA = {'User-Agent': 'predition-app/1.0'}


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    except Exception:
        return None


def fetch_settled_markets(series):
    """All settled markets for a series, newest first, via cursor pages."""
    out, cursor = [], None
    while len(out) < MAX_MARKETS:
        params = {'series_ticker': series, 'status': 'settled', 'limit': 1000}
        if cursor:
            params['cursor'] = cursor
        try:
            r = requests.get(BASE_URL, params=params, headers=UA, timeout=15)
            r.raise_for_status()
            body = r.json()
        except Exception as e:
            print(f'  {series} fetch stopped: {e}')
            break
        out.extend(body.get('markets') or [])
        cursor = body.get('cursor')
        if not cursor:
            break
        time.sleep(0.25)
    return out


def price_at(con, iso_ts, window_s=90):
    """Nearest RTI tick at-or-after iso_ts (settlement-relevant feed only)."""
    end = (datetime.fromisoformat(iso_ts.replace('Z', '+00:00'))
           + timedelta(seconds=window_s)).isoformat()
    row = con.execute(
        "SELECT price FROM prices WHERE timestamp >= ? AND timestamp <= ? "
        "AND source LIKE 'CFBenchmarks%' ORDER BY timestamp ASC LIMIT 1",
        (iso_ts, end)).fetchone()
    return float(row[0]) if row else None


def main():
    try:
        from sklearn.isotonic import IsotonicRegression
    except ImportError:
        print('sklearn required'); sys.exit(1)

    for db in sorted(glob.glob('*/*_prices.db')):
        coin_dir = os.path.dirname(db)
        cname = os.path.basename(db).replace('_prices.db', '')
        series = SERIES.get(cname)
        if not series:
            continue
        print(f'=== {cname.upper()} ({series}) ===')
        markets = fetch_settled_markets(series)
        settled = [m for m in markets
                   if m.get('result') in ('yes', 'no')
                   and m.get('floor_strike') is not None
                   and parse_ts(m.get('close_time'))]
        print(f'  settled markets fetched: {len(settled)}')
        if len(settled) < 200:
            print('  not enough history, skipping')
            continue

        con = sqlite3.connect(db)
        zs, ys, ts = [], [], []
        for m in settled:
            close = parse_ts(m['close_time'])
            strike = float(m['floor_strike'])
            y = 1.0 if m['result'] == 'yes' else 0.0
            for t_rem in SAMPLE_OFFSETS_MIN:
                t_obs = (close - timedelta(minutes=t_rem)).isoformat()
                px = price_at(con, t_obs)
                if px and strike > 0:
                    zs.append(np.log(px / strike) / np.sqrt(t_rem))
                    ys.append(y)
                    ts.append(close.timestamp())
        con.close()
        zs, ys, ts = np.array(zs), np.array(ys), np.array(ts)
        print(f'  observations: {len(zs)}')
        if len(zs) < 1000:
            print('  too few obs, skipping')
            continue

        # time-ordered split — oldest 60% fit, newest 40% OOS
        order = np.argsort(ts)
        zs, ys, ts = zs[order], ys[order], ts[order]
        k = int(len(zs) * FIT_FRAC)
        iso = IsotonicRegression(out_of_bounds='clip', increasing=True)
        iso.fit(zs[:k], ys[:k])
        p_oos = np.clip(iso.predict(zs[k:]), 0.005, 0.995)
        b_surface = float(np.mean((p_oos - ys[k:]) ** 2))
        b_naive = float(np.mean((0.5 - ys[k:]) ** 2))
        # compare vs logged market mid on the overlapping signal rows
        con = sqlite3.connect(db)
        r = con.execute(
            "SELECT prob_yes, mid_yes, mins_remaining, strike_price, "
            "current_price, outcome FROM contract_signals "
            "WHERE resolved=1 AND outcome IS NOT NULL AND mid_yes IS NOT NULL "
            "AND strike_price>0 AND current_price>0").fetchall()
        con.close()
        cmp_txt = ''
        if r:
            zl = np.array([np.log(x[4] / x[3]) / np.sqrt(max(x[2], 0.05))
                           for x in r])
            pm, mk, yo = (np.array([x[0] for x in r]),
                          np.array([x[1] / 100 for x in r]),
                          np.array([x[5] for x in r], dtype=float))
            ps = np.clip(iso.predict(zl), 0.005, 0.995)
            b = lambda p: float(np.mean((p - yo) ** 2))
            cmp_txt = (f' | signal-rows brier: surface={b(ps):.4f} '
                       f'model={b(pm):.4f} mkt={b(mk):.4f}')
        print(f'  OOS brier: surface={b_surface:.4f} flat50={b_naive:.4f}{cmp_txt}')

        # knots for interpolation (subsample the isotonic curve)
        zg = np.linspace(np.percentile(zs[:k], 1),
                         np.percentile(zs[:k], 99), 121)
        pg = iso.predict(zg)
        with open(os.path.join(coin_dir, 'settle_surface.json'), 'w') as f:
            json.dump({'coin': cname, 'series': series,
                       'n_obs': int(len(zs)), 'oos_brier': round(b_surface, 4),
                       'z': [round(float(x), 6) for x in zg],
                       'p': [round(float(x), 5) for x in pg]}, f)


if __name__ == '__main__':
    main()
