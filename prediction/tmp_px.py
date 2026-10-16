import sqlite3, glob, os
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
print('NOW UTC:', now.strftime('%H:%M:%S'))
for db in sorted(glob.glob('*/*_prices.db')):
    coin = os.path.basename(db).replace('_prices.db','')
    con = sqlite3.connect(db)
    rows = con.execute('SELECT timestamp, price, source FROM prices ORDER BY timestamp DESC LIMIT 6').fetchall()
    con.close()
    print('===', coin)
    for ts, px, src in rows[:4]:
        print('   ', ts[:19], px, src)
