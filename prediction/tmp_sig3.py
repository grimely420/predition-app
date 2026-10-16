
import sqlite3, glob, os
for db in sorted(glob.glob('*/*_prices.db')):
    coin = os.path.basename(db).replace('_prices.db','')
    con = sqlite3.connect(db)
    tot = con.execute("SELECT COUNT(*) FROM contract_signals WHERE call_time > datetime('now','-75 minutes')").fetchone()[0]
    wb = con.execute("SELECT COUNT(*) FROM contract_signals WHERE call_time > datetime('now','-75 minutes') AND yes_ask IS NOT NULL").fetchone()[0]
    we = con.execute("SELECT COUNT(*) FROM contract_signals WHERE call_time > datetime('now','-75 minutes') AND edge_cents IS NOT NULL").fetchone()[0]
    print(coin, 'signals:', tot, '| book:', wb, '| edge:', we)
    con.close()
print('--- samples with edge ---')
con = sqlite3.connect('bitcoin/bitcoin_prices.db')
for r in con.execute("SELECT phase, prob_yes, bias, yes_ask, no_ask, edge_cents, resolved, is_correct FROM contract_signals WHERE edge_cents IS NOT NULL ORDER BY call_time DESC LIMIT 12"):
    print(r)
con.close()
