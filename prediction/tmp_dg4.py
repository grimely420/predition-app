import json,urllib.request
d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=60))
for cid,v in d.items():
    cm=v.get('contract_model') or {}; dec=v.get('decision') or {}; m=v.get('market') or {}
    print(f'{cid:5s} contract={str(cm.get("p_up")):>7s} shown={dec.get("prob_yes_up")} src={dec.get("prob_source")} mkt_mid={m.get("mid_yes")}')
