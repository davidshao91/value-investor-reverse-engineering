"""Point-in-time S&P membership and price coverage.

    python cases/schloss/code/s02_members.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd

from cases._shared.config import require, schloss_paths


def norm(s):
    return s.replace(".", "-").upper().strip()


def main():
    paths = schloss_paths()
    h = pd.read_csv(require(paths["spx_hist"], "Need data/spx/hist.csv."))
    h["date"] = pd.to_datetime(h.date)
    h = h.set_index("date").sort_index()
    P = pd.read_pickle(require(paths["px"], "Run s01_panel.py first."))
    me = P.index.to_series().groupby(P.index.to_period("M")).last()
    me = me[me >= "1999-12-01"]
    cnt = P.notna().cumsum()
    rows = []
    mem = {}
    for d in me:
        hh = h[h.index <= d]
        if len(hh) == 0:
            continue
        tk = [norm(x) for x in hh.iloc[-1].tickers.split(",")]
        mem[d] = tk
        has = [t for t in tk if t in P.columns and pd.notna(P.at[d, t])]
        hist3 = [t for t in has if cnt.at[d, t] >= 756]
        rows.append(dict(date=d, members=len(tk), has_px=len(has), has_3y=len(hist3)))
    C = pd.DataFrame(rows)
    C["year"] = C.date.dt.year
    Y = C.groupby("year")[["members", "has_px", "has_3y"]].mean()
    Y["cov_px"] = Y.has_px / Y.members
    Y["cov_3y"] = Y.has_3y / Y.members
    paths["out"].mkdir(parents=True, exist_ok=True)
    Y.round(3).to_csv(paths["out"] / "coverage_by_year.csv")
    print(Y.round(3).to_string())
    print("window avg cov_px", (C.has_px.sum() / C.members.sum()).round(3), "cov_3y", (C.has_3y.sum() / C.members.sum()).round(3))
    pd.to_pickle(mem, paths["members"])


if __name__ == "__main__":
    main()
