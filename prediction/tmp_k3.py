import json,urllib.request,time
d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=30))
print('coins:',sorted(d.keys()))
for k,v in d.items():
    if isinstance(v,dict):
        dg=v.get('diagnostics') or {}
        print(f'{k:5s} stale={v.get("_stale",False)} shown={ (v.get("decision") or {}).get("prob_yes_up") } tick_age={dg.get("data_age_s")}')
