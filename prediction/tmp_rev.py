import sqlite3, glob, os, math, statistics as st
pnl={'entry':[],'mid':[],'late':[]}
agg={}
for db in sorted(glob.glob('*/*_prices.db')):
    con=sqlite3.connect(db)
    rows=con.execute("SELECT phase,bias,prob_yes,yes_ask,no_ask,edge_cents,is_correct FROM contract_signals WHERE resolved=1 AND is_correct IS NOT NULL AND yes_ask IS NOT NULL AND bias<>'NEUTRAL'").fetchall()
    allr=con.execute("SELECT phase,COUNT(*),AVG(is_correct) FROM contract_signals WHERE resolved=1 AND is_correct IS NOT NULL GROUP BY phase").fetchall()
    con.close()
    for ph,n,wr in allr:
        a=agg.setdefault(ph,[0,0]); a[0]+=n; a[1]+=wr*n
    for ph,bias,p,ya,na,edge,corr in rows:
        ask=ya if bias=='UP' else na
        if ask is None or ask<=0 or ask>=100: continue
        fee=0.07*ask/100*(1-ask/100)*100
        x=(100-ask-fee) if corr==1 else (-ask-fee)
        pnl.setdefault(ph,[]).append(x)
print('=== ACCURACY (all resolved directional, no book needed) ===')
for ph,(n,s) in agg.items(): print(f'  {ph:5s} n={n:5d} win={100*s/n:.1f}%')
print('=== NET EV AT CAPTURED ASK (real book data) ===')
for ph,v in pnl.items():
    if len(v)<5: continue
    m=st.mean(v); sd=st.stdev(v); n=len(v); t=m/(sd/math.sqrt(n))
    print(f'  {ph:5s} n={n:4d} mean={m:+6.2f}c sd={sd:5.1f} t={t:+5.2f} total={sum(v):+7.1f}c win_at_trade={sum(1 for x in v if x>0)}/{n}')
