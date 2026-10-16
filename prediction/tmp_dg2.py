import json,urllib.request
d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=60))
for cid,v in d.items():
    cm=v.get('contract_model') or {}; dg=v.get('diagnostics') or {}
    dec=v.get('decision') or {}; m=v.get('market') or {}
    print(f'{cid:5s} contract={str(cm.get("p_up")):>7s} w={str(dg.get("w_contract")):>5s} shown={dec.get("prob_yes_up")} mkt_mid={m.get("mid_yes")}')
