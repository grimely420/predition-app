import json,urllib.request,time
for i in range(6):
    d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=30))
    print(i, sorted(d.keys()), [k for k,v in d.items() if isinstance(v,dict) and v.get('_stale')])
    time.sleep(10)
