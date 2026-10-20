"""Scoreboard used by the Batch-1 cases.

Public benchmark: SPY total return.
Optional benchmark: the author's private conservative portfolio. Supply a CSV
at data/private/author_benchmark.csv with columns ``date`` and ``nav``.
The file is gitignored. Without it, author columns are skipped.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from cases._shared.config import AUTHOR_BENCHMARK, DATA


def _monthly_returns_from_nav(nav: pd.Series) -> pd.Series:
    nav = nav.dropna().sort_index()
    me = nav.groupby(nav.index.to_period("M")).last()
    return me.pct_change().dropna()


def load_spy_monthly() -> pd.Series:
    """Month-end simple returns for SPY. Cache preferred; yfinance is the fallback."""
    cached = DATA / "benchmarks" / "spy_daily.csv"
    if cached.exists():
        df = pd.read_csv(cached, parse_dates=["date"]).set_index("date").sort_index()
        col = "adj_close" if "adj_close" in df.columns else df.columns[0]
        s = _monthly_returns_from_nav(df[col])
        s.name = "SPY"
        return s
    try:
        import yfinance as yf
    except ImportError as exc:
        raise SystemExit(
            "No data/benchmarks/spy_daily.csv and yfinance is not installed.\n"
            "See docs/data.md."
        ) from exc
    px = yf.download("SPY", start="1993-01-01", auto_adjust=True, progress=False)
    close = px["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close.index = pd.to_datetime(close.index)
    s = _monthly_returns_from_nav(close)
    s.name = "SPY"
    return s


def load_author_monthly():
    """Optional private benchmark. Returns None when the file is absent."""
    path = AUTHOR_BENCHMARK
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    if "nav" not in df.columns:
        raise SystemExit(f"{path} needs columns date, nav")
    s = _monthly_returns_from_nav(df.set_index("date")["nav"])
    s.name = "author"
    return s


def bench() -> pd.DataFrame:
    df = pd.DataFrame({"SPY": load_spy_monthly()})
    author = load_author_monthly()
    if author is not None:
        df = df.join(author, how="outer")
    return df


def st(r: pd.Series):
    r = r.dropna()
    if len(r) < 2:
        return np.nan, np.nan, np.nan
    w = (1 + r).cumprod()
    n = len(r) / 12
    c = w.iloc[-1] ** (1 / n) - 1
    d = (w / np.maximum(w.cummax(), 1) - 1).min()
    k = c / abs(d) if d < 0 else np.nan
    return c, d, k


def yr(r: pd.Series) -> pd.Series:
    return (1 + r).groupby(r.index.year).prod() - 1


def judge(r: pd.Series, B: pd.DataFrame, start2: str = "2010-01") -> dict:
    """Calmar scoreboard. Author columns appear only when that series was loaded."""
    out = {}
    c, d, k = st(r)
    out["CAGR"], out["MDD"], out["Calmar"] = c, d, k
    names = [b for b in ("SPY", "author") if b in B.columns and B[b].notna().any()]
    for b in names:
        bb = B[b].reindex(r.index)
        bc, bd, bk = st(bb)
        tag = "SPY" if b == "SPY" else "author"
        out[f"{tag}_CAGR"], out[f"{tag}_MDD"], out[f"{tag}_Calmar"] = bc, bd, bk
        out[f"dCal_{tag}"] = k - bk
        out[f"dMDDpp_{tag}"] = (d - bd) * 100
        ex = yr(r) - yr(bb)
        drop = ex.nlargest(3).index
        keep = ~r.index.year.isin(drop)
        out[f"dCal_drop3_{tag}"] = st(r[keep])[2] - st(bb[keep])[2]
        out[f"best3_{tag}"] = ",".join(map(str, drop))
        s2 = r.index >= pd.Period(start2, "M")
        out[f"dCal_s2_{tag}"] = st(r[s2])[2] - st(bb[s2])[2]
        out[f"PASS_{tag}"] = bool(
            out[f"dCal_{tag}"] >= 0.05
            and out[f"dMDDpp_{tag}"] >= -5
            and out[f"dCal_drop3_{tag}"] > 0
            and out[f"dCal_s2_{tag}"] >= 0.05
        )
    return out
