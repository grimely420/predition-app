import sqlite3, json, urllib.request, time
c=sqlite3.connect('/home/chain-deaction/local_prediction/predition-app/prediction/bitcoin/bitcoin_prices.db',timeout=10)
print('--- source distribution (last 2000 ticks) ---')
for r in c.execute('select source, count(*), avg(price) from (select * from prices order by id desc limit 2000) group by source').fetchall():
    print(r)
print('--- last 5 ticks ---')
for r in c.execute('select timestamp, price, source from prices order by id desc limit 5').fetchall():
    print(r)
print('--- our /feed/btc ---')
try:
    d=json.load(urllib.request.urlopen('http://localhost:5000/feed/btc',timeout=10))
    print(json.dumps(d)[:400])
except Exception as e: print('feed err', e)
