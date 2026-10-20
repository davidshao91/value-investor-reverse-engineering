"""Daily-nav scoreboard for the Schloss case. Author benchmark is optional."""
import numpy as np
import pandas as pd

from cases._shared.config import AUTHOR_BENCHMARK, require, schloss_paths


def st(s):
    s = s.dropna()
    r = s.pct_change().dropna()
    w = (1 + r).cumprod()
    n = len(r) / 252
    c = w.iloc[-1] ** (1 / n) - 1
    m = (w / np.maximum(w.cummax(), 1) - 1).min()
    return c, m, c / abs(m)


def yr(s):
    r = s.pct_change().dropna()
    return (1 + r).groupby(r.index.year).prod() - 1


def cmp(s, bm):
    s = s.dropna()
    bm = bm.reindex(s.index).ffill()
    c, m, k = st(s)
    bc, bmd, bk = st(bm)
    rs = s.pct_change().dropna()
    ex = yr(s) - yr(bm)
    drop = ex.nlargest(3).index
    keep = ~rs.index.year.isin(drop)
    rb = bm.pct_change().reindex(rs.index)
    k2 = st((1 + rs[keep]).cumprod())[2] - st((1 + rb[keep]).cumprod())[2]
    return dict(dCal=k - bk, dMDDpp=(m - bmd) * 100, drop3=k2, best3=list(drop))


def benchmarks():
    """SPY from the price-cache bench file, plus the optional author nav."""
    paths = schloss_paths()
    b = pd.read_pickle(require(paths["yf_bench"], "Need data/schloss/yf_bench.pkl with SPY and ^IRX."))
    out = {"SPY": b["SPY"].dropna()}
    if AUTHOR_BENCHMARK.exists():
        df = pd.read_csv(AUTHOR_BENCHMARK, parse_dates=["date"]).set_index("date").sort_index()
        out["author"] = df["nav"].dropna()
    return out
