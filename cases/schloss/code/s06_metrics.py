"""Score the v1 runs. SPY is required; the author benchmark is optional.

    python cases/schloss/code/s06_metrics.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pickle

import pandas as pd

from cases._shared.config import require, schloss_paths
from engine import run
from navmetrics import benchmarks, cmp, st, yr


def main():
    paths = schloss_paths()
    with open(require(paths["runs_v1"], "Run s04_run.py first."), "rb") as fh:
        out = pickle.load(fh)
    nav = benchmarks()
    ew = pd.read_csv(require(paths["ew_nav"], "Run s05_ew.py first."), index_col=0, parse_dates=True).iloc[:, 0]
    series = dict(nav)
    series["EW"] = ew
    starts = {}
    for k in out:
        e, sc, x, dl, c = k.split("|")
        if dl in ("D0", "D2") or (dl == "D1" and c == "10"):
            starts[k] = dict(entry=e, scale=(sc == "scale"), exit_=x, delist=dl, cost=int(c) / 1e4)
    rows = []
    for k, (s, info) in out.items():
        cagr, m, kk = st(s)
        row = dict(spec=k, CAGR=cagr, MDD=m, Calmar=kk, **{a: info[a] for a in ["avg_pos", "avg_cash", "turnover", "entries", "delists", "zeroed"]})
        for bn, b in series.items():
            d = cmp(s, b)
            row.update({f"{a}_{bn}": v for a, v in d.items()})
        if k in starts:
            for st0 in ["2007-12-31", "2002-12-31"]:
                s8, _ = run(start=st0, **starts[k])
                tag = st0[:4]
                row[f"Cal_{tag}"] = st(s8)[2]
                for bn, b in nav.items():
                    row[f"dCal{tag}_{bn}"] = cmp(s8, b)["dCal"]
        y = yr(s)
        for Y in [2000, 2001, 2002, 2008, 2022]:
            row[f"y{Y}"] = y.get(Y)
        rows.append(row)
    bench_rows = []
    for bn, b in {**nav, "EW_cov(gross)": ew}.items():
        bb = b.loc["1999-12-31":]
        cagr, m, k = st(bb)
        y = yr(bb)
        r = dict(spec=bn, CAGR=cagr, MDD=m, Calmar=k, **{f"y{Y}": y.get(Y) for Y in [2000, 2001, 2002, 2008, 2022]})
        for st0 in ["2007-12-31", "2002-12-31"]:
            r[f"Cal_{st0[:4]}"] = st(b.loc[st0:])[2]
        bench_rows.append(r)
    T = pd.concat([pd.DataFrame(bench_rows), pd.DataFrame(rows)])
    paths["out"].mkdir(parents=True, exist_ok=True)
    T.to_csv(paths["out"] / "metrics_v1.csv", index=False)
    pd.set_option("display.width", 400)
    print(T.drop(columns=[c for c in T.columns if c.startswith("best3")]).round(3).to_string())


if __name__ == "__main__":
    main()
