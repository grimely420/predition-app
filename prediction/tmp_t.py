
import sqlite3, glob, os, math, statistics as st
pnl = {'entry':[], 'mid':[], 'late':[]}
late_only_pos_edge = []
for db in sorted(glob.glob('*/*_prices.db')):
    coin = os.path.basename(db).replace('_prices.db','')
    con = sqlite3.connect(db)
    rows = con.execute("SELECT phase,bias,prob_yes,yes_ask,no_ask,edge_cents,is_correct FROM contract_signals WHERE resolved=1 AND is_correct IS NOT NULL AND yes_ask IS NOT NULL AND bias<>'NEUTRAL'").fetchall()
    con.close()
    for ph,bias,p,ya,na,edge,corr in rows:
        fair = p*100 if bias=='UP' else (1-p)*100
        ask = ya if bias=='UP' else na
        if ask is None or ask<=0 or ask>=100: continue
        fee = 0.07*ask/100*(1-ask/100)*100
        x = (100-ask-fee) if corr==1 else (-ask-fee)
        pnl[ph].append(x)
        if ph=='late' and edge is not None and edge>2:
            late_only_pos_edge.append(x)
for ph,v in pnl.items():
    if len(v)<5: continue
    m=st.mean(v); sd=st.stdev(v); n=len(v); se=sd/math.sqrt(n); t=m/se
    print(f'{ph:5s} n={n:4d} meanPnL={m:+6.2f}c sd={sd:5.1f} t={t:+5.2f} total={sum(v):+7.1f}c')
if late_only_pos_edge:
    v=late_only_pos_edge; m=st.mean(v); sd=st.stdev(v); n=len(v); t=m/(sd/math.sqrt(n))
    print(f'late edge>2c: n={n} meanPnL={m:+.2f}c t={t:+.2f}')
