import json,urllib.request,time,sys
try:
    t=time.time()
    d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=40))
    print(f'agg {time.time()-t:.1f}s keys={sorted(d.keys())}', flush=True)
    b=d.get('btc')
    print('btc entry:', 'MISSING' if b is None else json.dumps({k:b.get(k) for k in ['current_price','prob_yes_up','prob_source','phase']}), flush=True)
except Exception as e:
    print('agg ERR', e, flush=True)
for i in range(3):
    t=time.time()
    try:
        r=json.load(urllib.request.urlopen('http://localhost:5000/kalshi/btc',timeout=35))
        print(f'btc {i}: {time.time()-t:.1f}s ok prob={r.get("prob_yes_up")} src={r.get("prob_source")} mkt={r.get("market")}', flush=True)
    except Exception as e:
        print(f'btc {i}: {time.time()-t:.1f}s ERR {e}', flush=True)
