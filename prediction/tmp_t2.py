import json,urllib.request,time
from datetime import datetime,timezone
t0=time.time()
d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=60))
print('fetch took', round(time.time()-t0,1),'s | server utc now:', datetime.now(timezone.utc).strftime('%H:%M:%S'))
for k,v in list(d.items())[:4]:
    t=v['timing']['current_round']
    ph=v.get('phase',{})
    m=v.get('market') or {}
    print(k,'| round',t['start_time'][11:19],'->',t['end_time'][11:19],
          '| elapsed',t['elapsed_seconds'],'s remain',t['remaining_seconds'],'s',
          '| phase:',ph.get('label','?'),'| mkt_mid:',m.get('mid_yes'))
