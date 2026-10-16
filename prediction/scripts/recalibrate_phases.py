#!/usr/bin/env python3
"""Fit per-phase Platt calibration on resolved contract signals.

The contract model is one model for all round minutes; empirically it is
miscalibrated by phase (entry ~50% win on ~65c confidence). A single global
Platt fit cannot fix phase-dependent bias, so we fit one per phase:

    p_cal = sigmoid(a_phase * logit(p_raw) + b_phase)

Fit on the OLDEST 60% of each phase's signals (time-ordered — no shuffle,
no leakage), validated on the newest 40% (out-of-sample). A phase's map is
only written when it IMPROVES OOS Brier score — otherwise raw model probs
are kept for that phase (identity). Artifacts land in
<coin>/phase_platt.json next to the coin DB; predictor_core applies them at
inference when present. Deleting the file reverts to raw probabilities.

Run from prediction/:
    .venv/bin/python scripts/recalibrate_phases.py
"""

import glob
import json
import os
import sqlite3
import numpy as np

MIN_FIT = 120   # per-phase rows needed before fitting
FIT_FRAC = 0.60


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def brier(p, y):
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


def fit_platt(p, y):
    from sklearn.linear_model import LogisticRegression
    p = np.clip(np.asarray(p, dtype=float), 1e-4, 1 - 1e-4)
    logit = np.log(p / (1 - p)).reshape(-1, 1)
    lr = LogisticRegression(C=1e10, solver='lbfgs', max_iter=500)
    lr.fit(logit, np.asarray(y, dtype=float))
    return float(lr.coef_[0][0]), float(lr.intercept_[0])


def main():
    report = {}
    for db in sorted(glob.glob('*/*_prices.db')):
        coin_dir = os.path.dirname(db)
        coin = os.path.basename(db).replace('_prices.db', '')
        coin = 'btc' if coin == 'bitcoin' else coin
        con = sqlite3.connect(db)
        rows = con.execute(
            "SELECT phase, prob_yes, outcome FROM contract_signals "
            "WHERE resolved = 1 AND outcome IS NOT NULL "
            "ORDER BY call_time ASC").fetchall()
        con.close()
        if not rows:
            continue

        cal_map = {}
        stats = {}
        for phase in ('entry', 'mid', 'late'):
            sub = [(float(p), int(o)) for ph, p, o in rows if ph == phase]
            if len(sub) < MIN_FIT:
                continue
            p_all = np.array([s[0] for s in sub])
            y_all = np.array([s[1] for s in sub])
            k = int(len(sub) * FIT_FRAC)
            p_fit, y_fit = p_all[:k], y_all[:k]
            p_oos, y_oos = p_all[k:], y_all[k:]
            if len(p_oos) < 30:
                continue
            a, b = fit_platt(p_fit, y_fit)
            p_cal = sigmoid(a * np.log(np.clip(p_oos, 1e-4, 1 - 1e-4)
                                       / (1 - np.clip(p_oos, 1e-4, 1 - 1e-4))) + b)
            br, bc = brier(p_oos, y_oos), brier(p_cal, y_oos)
            improved = bc < br
            stats[phase] = {
                'n_fit': len(p_fit), 'n_oos': len(p_oos),
                'brier_raw': round(br, 4), 'brier_cal': round(bc, 4),
                'a': round(a, 4), 'b': round(b, 4),
                'applied': improved,
            }
            # Only ship phases that beat raw OOS — falsification discipline:
            # a fit that doesn't validate out-of-sample is not applied.
            if improved:
                cal_map[phase] = [round(a, 6), round(b, 6)]

        out_path = os.path.join(coin_dir, 'phase_platt.json')
        with open(out_path, 'w') as f:
            json.dump({'coin': coin, 'platt': cal_map}, f, indent=2)
        if stats:
            report[coin] = stats

    for coin, st in report.items():
        print(f'=== {coin.upper()} ===')
        for ph, s in st.items():
            delta = s['brier_raw'] - s['brier_cal']
            flag = 'APPLIED' if s['applied'] else 'rejected'
            print(f"  {ph:5s} fit={s['n_fit']:4d} oos={s['n_oos']:4d} "
                  f"brier {s['brier_raw']:.4f} -> {s['brier_cal']:.4f} "
                  f"({flag} {delta:+.4f}) a={s['a']} b={s['b']}")


if __name__ == '__main__':
    main()
