"""Placebo: replace priced spin-offs with a random same-month stock. Not size-matched.

    python cases/greenblatt/code/g05_placebo.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import glob
import re

import numpy as np
import pandas as pd

from cases._shared.config import greenblatt_paths
import g04_backtest as g


def main():
    g.prepare()
    paths = greenblatt_paths()
    files = sorted(glob.glob(paths["prices_glob"]))
    if not files:
        raise SystemExit(f"No price pickles at {paths['prices_glob']}. See docs/data.md.")
    P = [pd.read_pickle(f) for f in files]
    level = P[0].columns.get_level_values(0)
    A = pd.concat([p["Close"] if "Adj Close" not in level else p["Adj Close"] for p in P], axis=1)
    A = A.loc[:, ~A.columns.duplicated()]
    A = A[[c for c in A.columns if re.fullmatch(r"[A-Z]{1,5}", str(c)) and not (len(c) == 5 and c[-1] in "WUR")]]
    A.index = A.index.to_period("M")
    A = A.groupby(level=0).last()
    PR = A.pct_change(fill_method=None).clip(-0.95, 5)
    print("placebo panel", A.shape)
    S0 = pd.Period("2009-07", "M")
    EVp = g.EV[g.EV.entryP >= S0].copy()

    def run_real(dead):
        r = g.sim(EVp, 12, 20, dead, 10 / 1e4)
        return r[r.index >= S0 + 1]

    real = {d: run_real(d) for d in ("drop", "spy")}

    def mk_placebo(seed, mode):
        rng = np.random.default_rng(seed)

        def f(ev, H):
            ms = [m for m in pd.period_range(ev.entryP + 1, ev.entryP + H, freq="M") if m <= g.W1]
            if ev.status != "priced" and mode == "spy":
                return ms, g.spy.reindex(ms).fillna(0).values.copy()
            ok = A.columns[A.loc[ev.entryP].notna().values & (A.loc[ev.entryP].values >= 3)] if ev.entryP in A.index else []
            t = rng.choice(ok)
            return ms, PR[t].reindex(ms).fillna(0).values.copy()

        return f

    out = []
    for mode, dead in (("drop", "drop"), ("spy", "spy")):
        stats = []
        for s in range(50):
            r = g.sim(EVp, 12, 20, dead, 10 / 1e4, placebo_ret=mk_placebo(s, mode))
            r = r[r.index >= S0 + 1]
            stats.append(g.st(r))
        S = np.array(stats)
        rc = g.st(real[dead])
        out.append(dict(
            mode=dead, real_CAGR=rc[0], real_MDD=rc[1], real_Calmar=rc[2],
            plc_CAGR_med=np.median(S[:, 0]), plc_Calmar_med=np.median(S[:, 2]),
            plc_Calmar_p90=np.percentile(S[:, 2], 90), plc_CAGR_p90=np.percentile(S[:, 0], 90),
            real_Calmar_pctile=(S[:, 2] < rc[2]).mean(),
        ))
    O = pd.DataFrame(out)
    print(O.round(3).to_string())
    O.to_csv(paths["out"] / "placebo_2009.csv", index=False)


if __name__ == "__main__":
    main()
