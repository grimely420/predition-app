import json,urllib.request
from datetime import datetime,timezone
print('SERVER NOW (UTC):', datetime.now(timezone.utc).isoformat())
d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=30))
v=d['btc']
t=v['timing']['current_round']
print('our round:', t['start_time'],'->',t['end_time'])
print('elapsed:',t['elapsed_seconds'],'s remaining:',t['remaining_seconds'],'s')
m=v.get('market') or {}
print('market:',m)
# also ask kalshi for the actual market times
from shared.kalshi_markets import KalshiMarketClient
import sys,os
