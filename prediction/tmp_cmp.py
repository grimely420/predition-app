import json, urllib.request, time
def get(u, hdrs=None):
    req=urllib.request.Request(u, headers=hdrs or {'User-Agent':'x/1'})
    return json.load(urllib.request.urlopen(req, timeout=8))
# our feed path (exact same URL/parser)
d=get('https://futures.kraken.com/derivatives/api/v3/tickers?symbol=PF_XBTUSD')
t=d['tickers'][0]
print('KRAKEN FUT indexPrice:', t.get('indexPrice'), '| markPrice:', t.get('markPrice'), '| last:', t.get('last'))
s=get('https://api.kraken.com/0/public/Ticker?pair=XBTUSD')
k=s['result']['XXBTZUSD']; print('KRAKEN SPOT last:', k['c'][0], '| bid/ask:', k['b'][0], k['a'][0])
try:
    cb=get('https://api.coinbase.com/v2/prices/BTC-USD/spot'); print('COINBASE spot:', cb['data']['amount'])
except Exception as e: print('coinbase err', e)
try:
    bn=get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT'); print('BINANCE spot:', bn['price'])
except Exception as e: print('binance err', e)
# kalshi market live book for current round
import sqlite3
c=sqlite3.connect('/home/chain-deaction/local_prediction/predition-app/prediction/bitcoin/bitcoin_prices.db',timeout=5)
print('OUR last 3 ticks:', c.execute('select timestamp, price from prices order by id desc limit 3').fetchall())
