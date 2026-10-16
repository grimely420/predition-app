import json,urllib.request
d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=30))
for k,v in d.items():
    cm=v.get('contract_model') or {}
    dec=v.get('decision') or {}
    print(k, 'p_up:',round(cm.get('p_up',-1),3),'| prob:',round(dec.get('prob_yes_up',-1),3),'|',dec.get('recommendation'))
