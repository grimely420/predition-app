
import sqlite3, json, urllib.request
con = sqlite3.connect('bitcoin/bitcoin_prices.db')
for r in con.execute("SELECT phase, prob_yes, bias, yes_ask, no_ask, mid_yes, edge_cents, call_time FROM contract_signals WHERE call_time > datetime('now','-30 minutes') ORDER BY call_time DESC LIMIT 8"):
    print('SIG', r)
con.close()
d = json.load(urllib.request.urlopen('http://localhost:5000/kalshi', timeout=30))
for k, v in list(d.items())[:8]:
    print('API', k, '|', v.get('decision'), '| p:', round(v.get('prob_yes', 0), 3))
