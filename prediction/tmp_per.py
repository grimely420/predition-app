import urllib.request,time
for c in ['btc','bnb','eth','sol','xrp','doge','hype','near','zec']:
    t0=time.time()
    try:
        r=urllib.request.urlopen(f'http://localhost:5000/kalshi/{c}',timeout=40)
        r.read(); print(c, r.status, round(time.time()-t0,1),'s')
    except Exception as e: print(c,'FAIL',round(time.time()-t0,1),'s',e)
