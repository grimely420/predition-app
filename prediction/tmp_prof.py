import time, sys
sys.path.insert(0, '.')
from shared.api import get_components, _round_series_payload
from shared.news_engine import get_news_engine
from shared.kalshi_engine import KalshiRoundTracker
for cid in ['btc','hype','bnb']:
    cfg, ds, fe, mm, pred, val, *rest = get_components(cid)
    t=time.time(); last=ds.last_price(); t_last=time.time()-t
    t=time.time()
    for h in cfg.prediction_horizons: r=pred.predict(h, current_price=last[0])
    t_pred=time.time()-t
    t=time.time(); nf=get_news_engine().get_features(cfg.symbol); t_news=time.time()-t
    t=time.time(); cp=pred.get_contract_prob(); t_cp=time.time()-t
    t=time.time()
    kt = rest[0] if rest else KalshiRoundTracker(ds, cfg.symbol)
    pr={h:0.001 for h in cfg.prediction_horizons}; cpr={h:{'up':.4,'down':.4,'flat':.2} for h in cfg.prediction_horizons}
    an=kt.analyze_round(last[0], pr, cpr, nf, contract_prob=cp)
    t_an=time.time()-t
    t=time.time(); rs=_round_series_payload(ds, an); t_rs=time.time()-t
    print(f'{cid}: last={t_last:.2f}s predict={t_pred:.2f}s news={t_news:.2f}s contract={t_cp:.2f}s analyze={t_an:.2f}s series={t_rs:.2f}s', flush=True)
