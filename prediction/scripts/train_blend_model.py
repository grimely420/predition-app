#!/usr/bin/env python3
"""Train a per-coin blend layer: logistic combination of contract-model
probability and live market mid, learned from resolved contract signals.

Motivation (from the ledger audit): the fixed 70/30 model+market anchor is
a guess, and the data shows the right weight depends on situation — when
the model disagrees strongly with the book it is usually wrong (edge>3c
calls won only 59%). Instead of a hand-tuned weight we fit

    p_blend = sigmoid(a*logit(p_model) + b*logit(p_mkt) + c*mins_remaining + d)

on the signal ledger's own resolved rows — the layer learns exactly when
to trust the model vs the crowd, including phase/position-in-round via
mins_remaining and disagreement via the two logits' interaction.

Protocol (same falsification discipline as recalibrate_phases.py):
  - rows are ordered by call_time; fit on OLDEST 60%, validate on newest 40%
  - artifact written ONLY if blend Brier beats ALL of: raw model prob,
    pure market mid, and the fixed 0.70/0.30 blend — out-of-sample
  - <coin>/blend_lr.json absent => engine keeps the fixed anchor
    (deleting the file reverts; no code change needed)

Run from prediction/:
    .venv/bin/python scripts/train_blend_model.py
"""

import glob
import json
import os
import sqlite3
import numpy as np

MIN_FIT = 300   # need real sample size for a 4-param logistic
FIT_FRAC = 0.60


def logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def brier(p, y):
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


def design(p_model, p_mkt, mins_rem):
    """[logit_model, logit_mkt, mins_remaining] design matrix."""
    return np.column_stack([logit(p_model), logit(p_mkt),
                            np.asarray(mins_rem, dtype=float)])


def main():
    from sklearn.linear_model import LogisticRegression

    report = {}
    for db in sorted(glob.glob('*/*_prices.db')):
        coin_dir = os.path.dirname(db)
        coin = os.path.basename(db).replace('_prices.db', '')
        coin = 'btc' if coin == 'bitcoin' else coin
        con = sqlite3.connect(db)
        rows = con.execute(
            "SELECT prob_yes, mid_yes, mins_remaining, outcome "
            "FROM contract_signals "
            "WHERE resolved = 1 AND outcome IS NOT NULL "
            "  AND mid_yes IS NOT NULL AND bias IN ('UP','DOWN') "
            "ORDER BY call_time ASC").fetchall()
        con.close()
        if len(rows) < MIN_FIT + 50:
            continue

        pm = np.array([r[0] for r in rows], dtype=float)
        mk = np.array([r[1] / 100.0 for r in rows], dtype=float)
        mr = np.array([r[2] if r[2] is not None else 7.5 for r in rows],
                      dtype=float)
        y = np.array([r[3] for r in rows], dtype=float)

        k = int(len(rows) * FIT_FRAC)
        Xf, Xo = design(pm[:k], mk[:k], mr[:k]), design(pm[k:], mk[k:], mr[k:])
        yf, yo = y[:k], y[k:]
        if len(yo) < 100:
            continue

        lr = LogisticRegression(C=1.0, solver='lbfgs', max_iter=1000)
        lr.fit(Xf, yf)
        p_blend = lr.predict_proba(Xo)[:, 1]  # already a probability

        p_raw = pm[k:]
        p_mkt = mk[k:]
        p_fixed = 0.70 * p_raw + 0.30 * p_mkt

        b_raw = brier(p_raw, yo)
        b_mkt = brier(p_mkt, yo)
        b_fix = brier(p_fixed, yo)
        b_bln = brier(p_blend, yo)
        beats_all = b_bln < min(b_raw, b_mkt, b_fix)

        st = {
            'n_fit': int(k), 'n_oos': int(len(yo)),
            'brier_raw': round(b_raw, 4), 'brier_mkt': round(b_mkt, 4),
            'brier_fixed': round(b_fix, 4), 'brier_blend': round(b_bln, 4),
            'coef': [round(float(c), 6) for c in lr.coef_[0]],
            'intercept': round(float(lr.intercept_[0]), 6),
            'applied': bool(beats_all),
        }
        report[coin] = st
        if beats_all:
            with open(os.path.join(coin_dir, 'blend_lr.json'), 'w') as f:
                json.dump({'coin': coin,
                           'coef': st['coef'], 'intercept': st['intercept'],
                           'n_fit': st['n_fit']}, f, indent=2)

    for coin, s in report.items():
        flag = 'APPLIED' if s['applied'] else 'rejected'
        print(f"{coin:5s} fit={s['n_fit']:5d} oos={s['n_oos']:5d} "
              f"brier raw={s['brier_raw']:.4f} mkt={s['brier_mkt']:.4f} "
              f"fixed={s['brier_fixed']:.4f} blend={s['brier_blend']:.4f} "
              f"[{flag}] coef={s['coef']} b={s['intercept']}")


if __name__ == '__main__':
    main()
