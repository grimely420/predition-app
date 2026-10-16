
import sqlite3, glob, os, time
for db in glob.glob('*/*hyperliquid*.db') + glob.glob('hype/*.db'):
    print(db, round(os.path.getsize(db)/1e6,1), 'MB')
    con = sqlite3.connect(db)
    for t in ('hl_snapshots','hl_trades','hl_candles_1m','hl_funding'):
        try:
            t0=time.time(); n=con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
            print(' ', t, n, 'rows', round(time.time()-t0,2),'s')
        except Exception as e: print(' ', t, 'ERR', e)
    for r in con.execute("SELECT name,tbl_name FROM sqlite_master WHERE type='index'"): print('  idx:', r)
    con.close()
