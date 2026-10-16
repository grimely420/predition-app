import json,urllib.request
d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=30))
for k,v in list(d.items())[:5]:
    print(k, v.get('prob_yes_up'), v.get('recommendation'))
