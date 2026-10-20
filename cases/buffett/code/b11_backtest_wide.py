"""Backtest the cheap-plus-catalyst basket. Author benchmark is optional.

    python cases/buffett/code/b11_backtest_wide.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import glob

import numpy as np
import pandas as pd

from cases._shared.config import buffett_paths, require
from cases._shared.rea_metrics import bench, judge, yr


def main():
    paths = buffett_paths()
    U = pd.read_pickle(require(paths["universe"], "Run b10_density_wide.py first."))
    U["b3"] = U.cheap & ~U.bb & ~U.pz
    tm = pd.read_csv(require(paths["tickers"], "Need data/xbrl/tickers_map.csv.")).dropna(subset=["yf"]).drop_duplicates("cik").set_index("cik").yf
    px_files = sorted(glob.glob(paths["prices_glob"]))
    if not px_files:
        raise SystemExit(f"No monthly prices at {paths['prices_glob']}.")
    px = pd.concat([pd.read_pickle(f)["Adj Close"] for f in px_files], axis=1, sort=True)
    px = px.loc[:, ~px.columns.duplicated()]
    px.index = pd.to_datetime(px.index).to_period("M")
    px = px.groupby(level=0).last()
    RET = px.pct_change(fill_method=None)
    B = bench()
    spy = B.SPY
    months = pd.period_range("2010-07", "2026-09", freq="M")

    def run(flag, dead, cost):
        held = {}
        w = {}
        out = {}
        ncov = [0, 0]
        tc = 0.0
        for m in months:
            if m.month == 7:
                cy = m.year
                cur = U[U.cy == cy]
                sel = set(cur[cur[flag]].cik)
                keep = set()
                for c, s in held.items():
                    if cy - s < 2 and c not in sel:
                        r = cur[cur.cik == c]
                        if len(r) == 0 or not (r.nc_mkt.iloc[0] < 0.5):
                            keep.add(c)
                newheld = {c: held.get(c, cy) for c in sel | keep}
                held = {c: (cy if c in sel else s) for c, s in newheld.items()}
                n = len(held)
                wt = min(0.05, 1 / n) if n else 0
                nw = {c: wt for c in held}
                turn = sum(abs(nw.get(c, 0) - w.get(c, 0)) for c in set(nw) | set(w))
                tc = turn * cost
                w = nw
                for c in sel:
                    ncov[1] += 1
                    t = tm.get(c)
                    if t in RET.columns and RET[t].loc[m:m + 11].notna().sum() >= 6:
                        ncov[0] += 1
            r = -tc if m.month == 7 else 0.0
            nw = {}
            for c, wc in w.items():
                t = tm.get(c)
                x = np.nan
                if t in RET.columns:
                    x = RET[t].get(m, np.nan)
                if pd.isna(x):
                    x = spy.get(m, 0.0) if dead == "spy" else 0.0
                    if dead == "dead" and m.month == 6 and not (t in RET.columns and RET[t].loc[m - 11:m].notna().any()):
                        x = -1.0
                if pd.isna(x):
                    x = 0.0
                r += wc * x
                nw[c] = wc * (1 + x)
            tot = 1 + r
            w = {c: v / tot for c, v in nw.items()}
            out[m] = r
        return pd.Series(out), ncov

    rows = []
    M = {}
    for flag in ("b1", "b3", "b1ev"):
        for dead in ("spy", "cash", "dead"):
            for cost in (10, 30):
                r, cov = run(flag, dead, cost / 1e4)
                M[f"{flag}|{dead}|{cost}"] = r
                j = judge(r, B, "2011-01")
                j.update(rule=f"{flag}|{dead}|{cost}", coverage=cov[0] / max(cov[1], 1), n_sel=cov[1])
                rows.append(j)
    paths["out"].mkdir(parents=True, exist_ok=True)
    T = pd.DataFrame(rows)
    T.to_csv(paths["out"] / "wide_metrics.csv", index=False)
    pd.DataFrame(M).to_csv(paths["out"] / "wide_monthly.csv")
    print(T.round(3).to_string())
    R = pd.DataFrame(M)
    Y = pd.DataFrame({c: yr(R[c]) for c in R if str(c).endswith("|10")})
    Y["SPY"] = yr(B.SPY.reindex(R.index))
    if "author" in B.columns:
        Y["author"] = yr(B.author.reindex(R.index))
    Y.to_csv(paths["out"] / "wide_years.csv")


if __name__ == "__main__":
    main()
