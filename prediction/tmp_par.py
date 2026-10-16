import time, sys, threading
sys.path.insert(0, '.')
from shared.api import _analyze_kalshi_coin
from shared.coin_config import list_coins
res={}
def w(cid):
    t=time.time()
    try: _analyze_kalshi_coin(cid); res[cid]=round(time.time()-t,1)
    except Exception as e: res[cid]=('ERR',str(e)[:60])
t0=time.time()
ths=[threading.Thread(target=w,args=(c,)) for c in list_coins()]
for t in ths: t.start()
for t in ths: t.join()
print(f'wall={time.time()-t0:.1f}s per-coin={res}', flush=True)
# second run warm
res={}
t0=time.time()
ths=[threading.Thread(target=w,args=(c,)) for c in list_coins()]
for t in ths: t.start()
for t in ths: t.join()
print(f'warm wall={time.time()-t0:.1f}s per-coin={res}', flush=True)
