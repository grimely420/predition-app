import json,urllib.request
d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=60))
for cid,v in list(d.items())[:5]:
    dg=v.get('diagnostics') or {}; dec=v.get('decision') or {}; m=v.get('market') or {}
    print(cid,'shown',dec.get('prob_yes_up'),'| data_age',dg.get('data_age_s'),'| model_age',dg.get('model_age_s'),'| mkt_mid',m.get('mid_yes'))
