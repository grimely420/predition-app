import sqlite3, sys
try:
    c = sqlite3.connect('file:/home/chain-deaction/local_prediction/predition-app/prediction/btc/btc_prices.db?mode=ro', uri=True, timeout=5)
    rows = c.execute('select timestamp, price from prices order by timestamp desc limit 3').fetchall()
    print('btc last:', rows)
    print('integrity:', c.execute('pragma quick_check').fetchone())
except Exception as e:
    print('ERR', type(e).__name__, e)
