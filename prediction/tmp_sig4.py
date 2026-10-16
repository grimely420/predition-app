
import sqlite3, glob, os
print('=== coverage last 40 min ===')
for db in sorted(glob.glob('*/*_prices.db')):
    coin = os.path.basename(db).replace('_prices.db','')
    con = sqlite3.connect(db)
    tot = con.execute("SELECT COUNT(*) FROM contract_signals WHERE call_time > datetime('now','-40 minutes')").fetchone()[0]
    wb = con.execute("SELECT COUNT(*) FROM contract_signals WHERE call_time > datetime('now','-40 minutes') AND yes_ask IS NOT NULL").fetchone()[0]
    we = con.execute("SELECT COUNT(*) FROM contract_signals WHERE call_time > datetime('now','-40 minutes') AND edge_cents IS NOT NULL").fetchone()[0]
    print(f'{coin:8s} signals:{tot:4d} book:{wb:3d} edge:{we:3d}')
    con.close()
print()
print('=== edge samples (favored side only) ===')
for db in sorted(glob.glob('*/*_prices.db')):
    coin = os.path.basename(db).replace('_prices.db','')
    con = sqlite3.connect(db)
    rows = con.execute("SELECT phase, prob_yes, bias, yes_ask, no_ask, edge_cents, is_correct FROM contract_signals WHERE edge_cents IS NOT NULL AND call_time > datetime('now','-40 minutes') ORDER BY call_time DESC LIMIT 6").fetchall()
    for r in rows: print(coin, r)
    con.close()
