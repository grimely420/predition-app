
import sqlite3
for coin, db in [('btc','bitcoin/bitcoin_prices.db'), ('bnb','bnb/bnb_prices.db'), ('hype','hype/hype_prices.db')]:
    con = sqlite3.connect(db)
    rows = con.execute("SELECT phase, prob_yes, bias, yes_ask, no_ask, edge_cents, call_time FROM contract_signals WHERE call_time > datetime('now','-20 minutes') ORDER BY call_time DESC LIMIT 5").fetchall()
    con.close()
    for r in rows: print(coin, r)
