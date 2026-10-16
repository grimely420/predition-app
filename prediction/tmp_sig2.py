
import sqlite3
for coin, db in [('btc','bitcoin/bitcoin_prices.db'), ('bnb','bnb/bnb_prices.db'), ('hype','hype/hype_prices.db'), ('eth','eth/eth_prices.db')]:
    con = sqlite3.connect(db)
    tot = con.execute("SELECT COUNT(*) FROM contract_signals WHERE call_time > datetime('now','-60 minutes')").fetchone()[0]
    wb  = con.execute("SELECT COUNT(*) FROM contract_signals WHERE call_time > datetime('now','-60 minutes') AND yes_ask IS NOT NULL").fetchone()[0]
    print(coin, 'signals:', tot, 'with book:', wb)
    for r in con.execute("SELECT phase, prob_yes, bias, yes_ask, no_ask, edge_cents FROM contract_signals WHERE call_time > datetime('now','-60 minutes') AND yes_ask IS NOT NULL ORDER BY call_time DESC LIMIT 4"):
        print('  ', r)
    con.close()
