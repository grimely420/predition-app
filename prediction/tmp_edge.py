
import sqlite3, glob, os
import statistics as st
agg = {}
resolved_pnl = []
for db in sorted(glob.glob('*/*_prices.db')):
    con = sqlite3.connect(db)
    rows = con.execute("SELECT phase, bias, edge_cents, is_correct, resolved FROM contract_signals WHERE yes_ask IS NOT NULL ORDER BY call_time").fetchall()
    con.close()
    for ph, bias, edge, correct, res in rows:
        if bias == 'NEUTRAL' or edge is None:
            continue
        agg.setdefault(ph, []).append(edge)
        if res == 1 and correct is not None:
            ask = None  # realized pnl at the captured ask
            # edge = fair - ask => ask = fair - edge; win pays (100-ask)-fee, loss pays -ask-fee
            resolved_pnl.append((ph, edge, int(correct)))
print('EDGE BY PHASE (edge = model_fair - market_ask, cents):')
for ph, es in agg.items():
    print(f'  {ph:5s} n={len(es):3d} mean={st.mean(es):+6.1f}c med={st.median(es):+5.1f}c pos={sum(1 for e in es if e>0)}/{len(es)}')
print()
print('RESOLVED SIGNALS WITH BOOK (hypothetical fill at captured ask):')
for ph in ('entry','mid','late'):
    pnls = []
    for p, e, c in resolved_pnl:
        if p != ph: continue
        ask = None
        pnls.append((e, c))
    print(f'  {ph}: n={len(pnls)}', pnls)
