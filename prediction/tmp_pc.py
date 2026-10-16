import sqlite3, os, statistics
base='/home/chain-deaction/local_prediction/predition-app/prediction'
dirs={'btc':'bitcoin','bnb':'bnb','eth':'eth','sol':'sol','xrp':'xrp','doge':'doge','hype':'hype','near':'near','zec':'zec'}
for cid,d in dirs.items():
    db=f'{base}/{d}/{d}_prices.db'
    try:
        c=sqlite3.connect(f'file:{db}?mode=ro',uri=True,timeout=8)
        r=c.execute("select is_correct, outcome, bias, yes_ask, no_ask from contract_signals where resolved=1 and phase='late'").fetchall()
        wins=sum(1 for x in r if x[0]==1)
        pnls=[]
        for ic,out,bias,ya,na in r:
            if out not in (0,1) or bias not in ('UP','DOWN'): continue
            ask=ya if bias=='UP' else na
            if ask is None: continue
            pnls.append((100.0-ask) if ((out==1)==(bias=='UP')) else -ask)
        s=f'{cid:4s} late n={len(r)} win%={100*wins/len(r):.0f}'
        if pnls: s+=f' | book pnl={statistics.mean(pnls):+.2f}c n={len(pnls)}'
        print(s)
    except Exception as e: print(f'{cid}: ERR {e}')
