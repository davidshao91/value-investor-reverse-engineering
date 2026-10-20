"""Score Lynch monthly returns against SPY and, if present, the optional author benchmark.

    python cases/lynch/code/l03_metrics.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd

from cases._shared.config import lynch_paths
from cases._shared.rea_metrics import bench, st, yr

def score(monthly_name, metrics_name, years_name):
    paths = lynch_paths()
    M = pd.read_csv(paths["out"] / monthly_name, index_col=0)
    M.index = pd.PeriodIndex(M.index, freq="M")
    B = bench().reindex(M.index)
    rows = []
    for col in M.columns:
        univ, cost, dead, rule = col.split("|")
        r = M[col]
        c, d, k = st(r)
        row = dict(univ=univ, cost=int(cost), dead=dead, rule=rule, CAGR=c, MDD=d, Calmar=k)
        for bn in [c for c in ("SPY", "author") if c in B.columns]:
            b = B[bn]
            bc, bd, bk = st(b)
            tag = "SPY" if bn == "SPY" else "author"
            row[f"dCalmar_{tag}"] = k - bk
            row[f"dMDDpp_{tag}"] = (d - bd) * 100
            ex = yr(r) - yr(b)
            drop = ex.nlargest(3).index
            keep = ~r.index.year.isin(drop)
            row[f"dCalmar_drop3_{tag}"] = st(r[keep])[2] - st(b[keep])[2]
            late = r.index >= pd.Period("2016-07", "M")
            row[f"dCalmar_from2016_{tag}"] = st(r[late])[2] - st(b[late])[2]
            row[f"pass_ex_start_{tag}"] = bool((k - bk >= 0.05) and ((d - bd) * 100 >= -5) and (row[f"dCalmar_drop3_{tag}"] > 0))
        rows.append(row)
    T = pd.DataFrame(rows)
    for bn in [c for c in ("SPY", "author") if c in B.columns]:
        cagr, mdd, cal = st(B[bn])
        print(bn, "same window", round(cagr, 4), round(mdd, 4), round(cal, 3))
    T.to_csv(paths["out"] / metrics_name, index=False)
    pd.set_option("display.width", 300)
    pd.set_option("display.max_columns", 30)
    print(T.round(3).to_string())
    keep_cols = [c for c in M.columns if "|10|" in c or monthly_name.endswith("diag.csv")]
    Y = pd.DataFrame({c: yr(M[c]) for c in keep_cols})
    Y["SPY"] = yr(B["SPY"])
    if "author" in B.columns:
        Y["author"] = yr(B["author"])
    Y.to_csv(paths["out"] / years_name)

def main():
    score("monthly_returns.csv", "metrics.csv", "calendar_years.csv")

if __name__ == "__main__":
    main()
