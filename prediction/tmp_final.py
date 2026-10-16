
import sqlite3, glob, os, statistics as st
agg = {}
res = []
for db in sorted(glob.glob('*/*_prices.db')):
    coin = os.path.basename(db).replace('_prices.db','')
    con = sqlite3.connect(db)
    rows = con.execute("SELECT phase, bias, prob_yes, yes_ask, no_ask, edge_cents, is_correct, resolved, call_time FROM contract_signals WHERE yes_ask IS NOT NULL").fetchall()
    con.close()
    for ph,bias,p,ya,na,edge,corr,r,ct in rows:
        agg.setdefault(ph, []).append((coin,bias,p,ya,na,edge,corr,r))
print('=== ALL SIGNALS WITH BOOK ===')
for ph in ('entry','mid','late'):
    rows = agg.get(ph,[])
    dir_rows = [r for r in rows if r[1]!='NEUTRAL' and r[5] is not None]
    es = [r[5] for r in dir_rows]
    wins = [r for r in dir_rows if r[7]==1]
    wint = sum(1 for r in wins if r[6]==1)
    print(f'{ph:5s} n_book={len(rows):4d} n_dir={len(dir_rows):4d} n_resolved={len(wins):4d} win={wint}/{len(wins)}')
    if es:
        print(f'       edge mean={st.mean(es):+6.1f}c med={st.median(es):+6.1f}c n>0:{sum(1 for e in es if e>0)}/{len(es)} n>2c:{sum(1 for e in es if e>2)}/{len(es)}')
    # resolved directional with book: net EV at captured ask (fee 0.07*p*(1-p)*100 cents)
    evs=[]
    for coin,bias,p,ya,na,edge,corr,r in wins:
        fair = p*100 if bias=='UP' else (1-p)*100
        ask = fair - edge
        fee = 0.07*ask/100*(1-ask/100)*100
        evs.append(((100-ask-fee) if corr==1 else (-ask-fee), edge))
    if evs:
        tot=[e[0] for e in evs]
        print(f'       REALIZED net EV if filled at captured ask: mean={st.mean(tot):+5.1f}c total={sum(tot):+6.1f}c n={len(tot)}')
