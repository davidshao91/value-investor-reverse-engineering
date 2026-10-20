"""Metrics for the price-to-book variant, plus the cash-matched scale diagnostic.

    python cases/schloss/code/s10_metrics2.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pickle

import pandas as pd

from cases._shared.config import require, schloss_paths
import engine
from navmetrics import benchmarks, cmp, st, yr


def main():
    paths = schloss_paths()
    with open(require(paths["runs_v2"], "Run s09_v2.py first."), "rb") as fh:
        o2 = pickle.load(fh)
    nav = benchmarks()
    ew = pd.read_csv(require(paths["ew_nav"], "Run s05_ew.py first."), index_col=0, parse_dates=True).iloc[:, 0]
    rows = []
    for bn, b in {**nav, "EW": ew}.items():
        c, m, k = st(b.loc["2014-12-31":])
        rows.append(dict(spec=bn + "@2015", CAGR=c, MDD=m, Calmar=k, y2022=yr(b.loc["2014-12-31":]).get(2022)))
    for k, (s, i) in o2.items():
        c, m, kk = st(s)
        row = dict(spec=k, CAGR=c, MDD=m, Calmar=kk, y2022=yr(s).get(2022), avg_pos=i["avg_pos"], avg_cash=i["avg_cash"])
        for bn, b in nav.items():
            d = cmp(s, b)
            row.update({f"{a}_{bn}": v for a, v in d.items() if a != "best3"})
        rows.append(row)
    T = pd.DataFrame(rows)
    paths["out"].mkdir(parents=True, exist_ok=True)
    T.to_csv(paths["out"] / "metrics_v2.csv", index=False)
    print(T.round(3).to_string())
    with open(paths["runs_v1"], "rb") as fh:
        o1 = pickle.load(fh)
    engine.load()
    L, il = o1["v1|lump|tgt|D0|10"]
    S, is_ = o1["v1|scale|tgt|D0|10"]
    x = (is_["avg_cash"] - il["avg_cash"]) / (1 - il["avg_cash"])
    rl = L.pct_change().fillna(0)
    rb = (1 - x) * rl + x * engine.IRX.reindex(L.index).fillna(0)
    B = (1 + rb).cumprod()
    print("scale diagnostic: extra cash share", round(x, 3), "lump", [round(v, 3) for v in st(L)], "lump+cash", [round(v, 3) for v in st(B)], "scale", [round(v, 3) for v in st(S)])
    Yr = pd.DataFrame({k: yr(o1[k][0]) for k in ["v1|lump|tgt|D0|10", "v1|scale|tgt|D0|10", "C3L|lump|tgt|D0|10", "v1|lump|tgt|D1|10"]})
    Yr["SPY"] = yr(nav["SPY"].loc["1999-12-31":])
    if "author" in nav:
        Yr["author"] = yr(nav["author"].loc["1999-12-31":])
    Yr["EW"] = yr(ew)
    Yr.round(3).to_csv(paths["out"] / "calendar_years.csv")
    print(Yr.round(3).to_string())


if __name__ == "__main__":
    main()
