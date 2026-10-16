import json,urllib.request,time
for i in range(5):
    d=json.load(urllib.request.urlopen('http://localhost:5000/kalshi',timeout=30))
    line=[]
    for k,v in sorted(d.items()):
        if isinstance(v,dict):
            dg=v.get('diagnostics') or {}
            line.append(f'{k}:{"S" if v.get("_stale") else "ok"}@{dg.get("data_age_s")}')
    print(i, ' '.join(line), flush=True)
    time.sleep(12)
