import sqlite3, time
c=sqlite3.connect('/home/chain-deaction/local_prediction/predition-app/prediction/bitcoin/bitcoin_prices.db',timeout=10)
print('indexes:', c.execute("select name from sqlite_master where type='index'").fetchall())
t=time.time()
r=c.execute("select price from prices where timestamp>=? and timestamp<=? and source like 'CFBenchmarks%' order by timestamp asc limit 1",('2026-10-05T12:00:00+00:00','2026-10-05T12:01:30+00:00')).fetchone()
print(f'lookup {time.time()-t:.3f}s ->', r)
print('oldest tick:', c.execute('select min(timestamp) from prices').fetchone())
