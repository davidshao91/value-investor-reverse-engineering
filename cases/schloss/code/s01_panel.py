"""Splice delisting-aware S&P prices with a later adjusted-close panel.

    python cases/schloss/code/s01_panel.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd

from cases._shared.config import require, schloss_paths

# Broken joins found while auditing the splice. Not a portfolio.
EXCLUDE = ["PBG", "SLR", "CBE", "FBF"]


def norm(s):
    return s.replace(".", "-").upper().strip()


def main():
    paths = schloss_paths()
    f = pd.read_pickle(require(paths["finsaber"], "Need data/schloss/finsaber_sp500.pkl. See docs/data.md."))
    f = f[~f.symbol.isin(EXCLUDE)]
    f["symbol"] = f.symbol.map(norm)
    f["date"] = pd.to_datetime(f.date)
    F = f.pivot_table(index="date", columns="symbol", values="adjusted_close", aggfunc="last")
    Y = pd.read_pickle(require(paths["yf_adj"], "Need data/schloss/yf_adj.pkl."))
    Y.columns = [norm(c) for c in Y.columns]
    Y = Y.loc[:, ~Y.columns.duplicated()]
    Y.index = pd.to_datetime(Y.index)
    idx = Y.index.union(F.index)
    cols = sorted(set(F.columns) | set(Y.columns))
    out = {}
    src = {}
    for c in cols:
        fs = F[c].dropna() if c in F else None
        ys = Y[c].dropna() if c in Y else None
        if fs is None or len(fs) == 0:
            out[c] = ys
            src[c] = "yf"
            continue
        if ys is None or len(ys) == 0:
            out[c] = fs
            src[c] = "fs"
            continue
        ov = fs.index.intersection(ys.index)
        if len(ov) < 20:
            out[c] = fs
            src[c] = "fs"
            continue
        r = pd.concat([fs.loc[ov].pct_change(), ys.loc[ov].pct_change()], axis=1).dropna()
        if r.corr().iloc[0, 1] < 0.9:
            out[c] = fs
            src[c] = "fs_only_mismatch"
            continue
        k = fs.index.min()
        pre = ys[ys.index < k]
        if len(pre):
            pre = pre * (fs.loc[k] / ys.loc[k]) if k in ys.index else pre * (fs.iloc[0] / pre.iloc[-1])
        e = fs.index.max()
        post = ys[ys.index > e]
        if len(post) and e in ys.index:
            post = post * (fs.loc[e] / ys.loc[e])
        elif len(post):
            post = post.iloc[0:0]
        out[c] = pd.concat([pre, fs, post])
        src[c] = "splice"
    P = pd.DataFrame(out).reindex(idx).sort_index()
    P = P[P.index <= "2026-10-16"]
    paths["cache"].mkdir(parents=True, exist_ok=True)
    P.to_pickle(paths["px"])
    pd.Series(src).to_csv(paths["px_src"])
    print(P.shape, pd.Series(src).value_counts())


if __name__ == "__main__":
    main()
