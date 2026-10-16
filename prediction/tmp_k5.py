import json,urllib.request
d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=30))
for cid,v in sorted(d.items()):
    if isinstance(v,dict):
        dec=v.get('decision') or {}; m=v.get('market') or {}; dg=v.get('diagnostics') or {}
        print(f'{cid:5s} shown={dec.get("prob_yes_up")} src={dec.get("prob_source")} mid={m.get("mid_yes")} tick_age={dg.get("data_age_s")}')
