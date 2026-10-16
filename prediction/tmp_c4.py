import json,urllib.request
d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=30))
for k,v in list(d.items())[:4]:
    m=v.get('market') or {}
    dec=v.get('decision') or {}
    print(k,'FAIR',dec.get('yes_cents'),'/',dec.get('no_cents'),'| MKT yes_ask',m.get('yes_ask'),'no_ask',m.get('no_ask'),'mid',m.get('mid_yes'))
