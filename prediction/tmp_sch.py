import sqlite3
c=sqlite3.connect('/home/chain-deaction/local_prediction/predition-app/prediction/bitcoin/bitcoin_prices.db',timeout=10)
print('outcome:', c.execute('select outcome, count(*) from contract_signals group by outcome').fetchall())
print('bias:', c.execute('select bias, count(*) from contract_signals group by bias').fetchall())
print('resolved+book:', c.execute('select count(*) from contract_signals where resolved=1 and yes_ask is not null').fetchone())
print('sample:', c.execute('select phase,bias,outcome,is_correct,yes_ask,no_ask from contract_signals where resolved=1 and yes_ask is not null order by id desc limit 3').fetchall())
