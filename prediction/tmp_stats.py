import sqlite3, math, os, statistics
base='/home/chain-deaction/local_prediction/predition-app/prediction'
dirs={'btc':'bitcoin','bnb':'bnb','eth':'eth','sol':'sol','xrp':'xrp','doge':'doge','hype':'hype','near':'near','zec':'zec'}
rows=[]
for cid,d in dirs.items():
    db=f'{base}/{d}/{d}_prices.db'
    try:
        c=sqlite3.connect(f'file:{db}?mode=ro',uri=True,timeout=8)
        r=c.execute('select phase,prob_yes,bias,outcome,is_correct,yes_ask,no_ask,edge_cents,call_time from contract_signals where resolved=1').fetchall()
        for x in r: rows.append((cid,)+x)
    except Exception as e: print(f'{cid}: ERR {e}')
print('resolved total:', len(rows))
for ph in ('entry','mid','late'):
    sel=[r for r in rows if r[1]==ph]
    wins=sum(1 for r in sel if r[5]==1)
    pnls=[]
    for r in sel:
        bias=(r[3] or '').upper(); out=r[4]; ya,na=r[6],r[7]
        if out not in (0,1) or bias not in ('UP','DOWN'): continue
        ask=ya if bias=='UP' else na
        if ask is None: continue
        pnls.append((100.0-ask) if ((out==1)==(bias=='UP')) else -ask)
    probs=[r[2] for r in sel if r[2] is not None]
    yesr=sum(1 for r in sel if r[4]==1)/len(sel)
    line=f'{ph:5s} n={len(sel):5d} win%={100*wins/len(sel):.1f} | mean_prob_yes={statistics.mean(probs):.3f} actual_yes={yesr:.3f}'
    if pnls:
        w=sum(1 for p in pnls if p>0); m=statistics.mean(pnls)
        sd=statistics.stdev(pnls) if len(pnls)>1 else 1
        t=m/(sd/math.sqrt(len(pnls))) if sd>0 else 0
        line+=f' | book n={len(pnls)} pnl={m:+.2f}c t={t:+.2f} win%={100*w/len(pnls):.0f}'
    print(line)
# late edge>3 subset (4 days of books)
late3=[]; late_any=[]
for r in rows:
    if r[1]!='late': continue
    bias=(r[3] or '').upper(); out=r[4]; ya,na=r[6],r[7]; ec=r[8]
    if out not in (0,1) or bias not in ('UP','DOWN'): continue
    ask=ya if bias=='UP' else na
    if ask is None: continue
    p=(100.0-ask) if ((out==1)==(bias=='UP')) else -ask
    late_any.append(p)
    if ec is not None and ec>3: late3.append(p)
for nm,arr in (('late all-book',late_any),('late edge>3c',late3)):
    if arr:
        m=statistics.mean(arr); sd=statistics.stdev(arr) if len(arr)>1 else 1
        t=m/(sd/math.sqrt(len(arr))) if sd else 0
        print(f'{nm}: n={len(arr)} mean={m:+.2f}c t={t:+.2f} win%={100*sum(1 for p in arr if p>0)/len(arr):.0f}')
