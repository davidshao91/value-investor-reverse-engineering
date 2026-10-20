"""Slot simulation for cash merger spreads.

    python cases/greenblatt/code/arb/a07_sim.py
    python cases/greenblatt/code/arb/a07_sim.py _aud
    python cases/greenblatt/code/arb/a07_sim.py _501
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

import numpy as np
import pandas as pd

from cases._shared.config import arb_paths, require
from cases._shared.rea_metrics import bench, judge, yr


def main():
    suf = sys.argv[1] if len(sys.argv) > 1 else ""
    paths = arb_paths()
    events = paths["cache"] / f"events_final{suf}.csv"
    E = pd.read_csv(require(events, "Run a06_final.py first."))
    E["entry_m"] = pd.PeriodIndex(E.entry_m, freq="M")
    E["exit_m"] = pd.PeriodIndex(E.exit_m, freq="M")
    px = pd.read_pickle(require(paths["px_broken"], "Need data/greenblatt/arb/px_broken.pkl."))
    CL = px["Close"]
    CL.index = CL.index.to_period("M")
    CL = CL.groupby(level=0).last()
    B = bench()
    spy = B.SPY
    months = pd.period_range("2009-01", "2026-09", freq="M")

    def path(e, dead):
        x1 = max(e.exit_m, e.entry_m + 1)
        ms = list(pd.period_range(e.entry_m + 1, x1, freq="M"))
        if e.outcome == "broken_unpriced":
            if dead == "spy":
                return ms, [spy.get(m, 0.0) for m in ms]
            r = [0.0] * len(ms)
            if dead == "dead":
                r[-1] = -1.0
            return ms, r
        if e.outcome == "broken_priced" and isinstance(e.ticker, str) and e.ticker in CL.columns:
            lv = [e.px_pd]
            s = CL[e.ticker]
            for m in ms[:-1]:
                lv.append(s.get(m, np.nan))
            lv.append(e.exit_val)
            lv = pd.Series(lv).interpolate().tolist()
        else:
            g = (e.exit_val / e.px_pd) ** (1 / max(len(ms), 1))
            lv = [e.px_pd * g ** k for k in range(len(ms) + 1)]
        return ms, [lv[k + 1] / lv[k] - 1 for k in range(len(ms))]

    def sim(X, N, dead, cost):
        ev = E[(E.px_pd.notna()) & (E.px_pd >= 3) & (E.spread >= X) & ((E.outcome != "broken_unpriced") if dead == "drop" else True)]
        ev = ev[ev.covered | (ev.outcome == "broken_unpriced")].sort_values("date")
        by = {}
        for _, e in ev.iterrows():
            by.setdefault(e.entry_m, []).append(e)
        cash = 1.0
        pos = []
        out = {}
        ntr = 0
        nact = []
        for m in months:
            nv = cash + sum(p[0] for p in pos)
            for e in by.get(m - 1, []):
                if len(pos) >= N:
                    continue
                ms, r = path(e, dead)
                w = min(nv / N, cash)
                if w <= 1e-9:
                    continue
                cash -= w * (1 + cost)
                pos.append([w, ms, r, 0])
                ntr += 1
            v0 = cash + sum(p[0] for p in pos)
            keep = []
            for p in pos:
                p[0] *= 1 + p[2][p[3]]
                p[3] += 1
                if p[3] >= len(p[2]):
                    cash += p[0] * (1 - cost)
                else:
                    keep.append(p)
            pos = keep
            nact.append(len(pos))
            v1 = cash + sum(p[0] for p in pos)
            out[m] = v1 / v0 - 1
        return pd.Series(out), ntr, np.mean(nact) if nact else 0

    rows = []
    M = {}
    for X in (0.05, 0.02, 0.0):
        for dead in ("spy", "cash", "dead"):
            for c in (10, 30):
                r, n, a = sim(X, 20, dead, c / 1e4)
                k = f"X{int(X * 100)}|{dead}|{c}"
                M[k] = r
                j = judge(r, B, "2010-01")
                j.update(rule=k, n_trades=n, avg_pos=a)
                rows.append(j)
    paths["out"].mkdir(parents=True, exist_ok=True)
    T = pd.DataFrame(rows)
    tag = {"_aud": "_aud", "_501": "_501"}.get(suf, "")
    T.to_csv(paths["out"] / f"arb_metrics{tag}.csv", index=False)
    pd.DataFrame(M).to_csv(paths["out"] / f"arb_monthly{tag}.csv")
    R = pd.DataFrame(M)
    Y = pd.DataFrame({c: yr(R[c]) for c in R if str(c).endswith("|10")})
    Y["SPY"] = yr(spy.reindex(R.index))
    if "author" in B.columns:
        Y["author"] = yr(B.author.reindex(R.index))
    Y.to_csv(paths["out"] / f"arb_years{tag}.csv")
    print(T.round(3).to_string())


if __name__ == "__main__":
    main()
