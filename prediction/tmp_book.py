
import sys, os, json, urllib.request
sys.path.insert(0, os.getcwd())
from datetime import datetime, timezone, timedelta
from shared.kalshi_markets import get_kalshi_markets
from shared.coin_config import COINS
cfg = COINS['btc']
print('kalshi_series attr:', getattr(cfg, 'kalshi_series', None))
km = get_kalshi_markets()
now = datetime.now(timezone.utc)
st = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
en = st + timedelta(minutes=15)
series = getattr(cfg, 'kalshi_series', None) or 'KXBTC15M'
print('series used:', series)
m = km._find_market(series, st, en)
print('market found:', bool(m), m.get('ticker') if m else None)
b = km.get_book_snapshot(series, st, en)
print('book:', b)
