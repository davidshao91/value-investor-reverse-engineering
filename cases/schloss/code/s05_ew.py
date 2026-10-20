"""Equal-weight covered S&P members. Gross of costs.

    python cases/schloss/code/s05_ew.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from cases._shared.config import schloss_paths
import engine


def main():
    engine.load()
    P, cal, ME, MEM, ci = engine.P, engine.cal, engine.ME, engine.MEM, engine.ci
    R = P.pct_change(fill_method=None)
    mes = sorted(d for d in ME if d >= pd.Timestamp("1999-12-31"))
    ret = []
    dates = cal[cal >= mes[0]]
    W = None
    for d in dates:
        if W is not None:
            r = R.loc[d, W.index].fillna(0)
            ret.append((d, (W * r).sum() / W.sum()))
            W = W * (1 + r)
        if d in ME:
            mem = MEM.get(d)
            ok = [n for n in mem if n in ci and pd.notna(P.at[d, n])]
            W = pd.Series(1.0 / len(ok), index=ok)
    s = pd.Series(dict(ret))
    nav = (1 + s).cumprod()
    paths = schloss_paths()
    paths["out"].mkdir(parents=True, exist_ok=True)
    nav.to_csv(paths["ew_nav"])
    print(nav.iloc[-1])


if __name__ == "__main__":
    main()
