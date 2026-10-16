import sqlite3, json, urllib.request, time
c=sqlite3.connect('/home/chain-deaction/local_prediction/predition-app/prediction/bitcoin/bitcoin_prices.db',timeout=5)
def get(u):
    req=urllib.request.Request(u, headers={'User-Agent':'x/1'})
    return json.load(urllib.request.urlopen(req, timeout=10))
# sleep until ~23:16:30 (entry signal should be gated->official by then)
time.sleep(570)
for r in c.execute('select round_start, phase, strike_price, prob_yes, bias, call_time from contract_signals order by id desc limit 4').fetchall():
    print('signal:', r)
d=get('https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXBTC15M&status=open&limit=5')
for m in d.get('markets',[]):
    print('kalshi:', m['ticker'], m['open_time'], 'strike', m.get('floor_strike'))
