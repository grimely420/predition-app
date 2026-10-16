import json,urllib.request
d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=60))
print(f'{"coin":6s} {"contract":>9s} {"bs_prior":>9s} {"blend":>7s} {"mkt_mid":>8s} {"src":>15s}')
for cid,v in d.items():
    cm=v.get('contract_model') or {}
    dec=v.get('decision') or {}
    m=v.get('market') or {}
    stl=v.get('settlement') or {}
    print(f'{cid:6s} {str(cm.get("p_up"))[:8]:>9s} {str(v.get("bs_prob_up"))[:8]:>9s} {str(dec.get("prob_yes_up"))[:6]:>7s} {str(m.get("mid_yes"))[:8]:>8s} {dec.get("prob_source")}')
