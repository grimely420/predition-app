import json,urllib.request,urllib.parse
d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=60))
print(f'{"coin":6s} {"our_price":>12s} {"our_strike":>12s} {"k_strike":>12s} {"k_yesask":>9s} {"k_noask":>9s}')
for cid,v in d.items():
    pr=(v.get('pricing') or {})
    m=v.get('market') or {}
    # kalshi official strike for the same round
    t=v['timing']['current_round']
    import datetime as dt
    url='https://api.elections.kalshi.com/trade-api/v2/markets?'+urllib.parse.urlencode({'series_ticker':v.get('series'),'status':'open','limit':5})
    try:
        mk=json.load(urllib.request.urlopen(url,timeout=10)).get('markets',[])
        ks=next((x.get('floor_strike') for x in mk if x.get('open_time','')[:16]==t['start_time'][:16]),None)
    except Exception as e:
        ks='ERR'
    print(f'{cid:6s} {str(pr.get("current_price")):>12s} {str(pr.get("round_open_price")):>12s} {str(ks):>12s} {str(m.get("yes_ask")):>9s} {str(m.get("no_ask")):>9s}')
