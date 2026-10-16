import json, urllib.request, sqlite3
def get(u):
    req=urllib.request.Request(u, headers={'User-Agent':'x/1'})
    return json.load(urllib.request.urlopen(req, timeout=10))
d=get('https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXBTC15M&status=open&limit=10')
for m in d.get('markets',[]):
    print(json.dumps({k:m.get(k) for k in ['ticker','open_time','close_time','floor_strike','cap_strike','functional_strike','price_level_structure','settlement_timer_seconds','result','yes_bid','yes_ask','last_price','index_price','underlying_price','expiration_value']}))
# our strike for same round
c=sqlite3.connect('/home/chain-deaction/local_prediction/predition-app/prediction/bitcoin/bitcoin_prices.db',timeout=5)
print('our latest signal strike/price:', c.execute('select round_start, strike_price, current_price from contract_signals order by id desc limit 1').fetchone())
