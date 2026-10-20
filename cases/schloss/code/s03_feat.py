"""Rolling lows, highs, and jump filters used by the engine.

    python cases/schloss/code/s03_feat.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd

from cases._shared.config import require, schloss_paths


def main():
    paths = schloss_paths()
    P = pd.read_pickle(require(paths["px"], "Run s01_panel.py first."))
    P = P.loc["1995-01-01":]
    b = pd.read_pickle(require(paths["yf_bench"], "Need data/schloss/yf_bench.pkl with a SPY column."))
    cal = b["SPY"].dropna().index
    cal = cal[cal <= "2026-10-16"]
    P = P.reindex(cal)
    last = P.apply(lambda s: s.last_valid_index())
    Pf = P.ffill()
    Pf = Pf.where(Pf.index.values[:, None] <= last.values[None, :])
    r = P.pct_change(fill_method=None)
    bad = ((r > 1.5) | (r < -0.75)).astype(float).rolling(756, min_periods=1).max()
    lo3 = P.rolling(756, min_periods=700).min()
    hi5 = P.rolling(1260, min_periods=700).max()
    med3 = P.rolling(756, min_periods=700).median()
    hi1 = P.rolling(252, min_periods=1).max()
    n = P.notna().cumsum()
    pd.to_pickle(dict(P=P, Pf=Pf, last=last, bad=bad, lo3=lo3, hi5=hi5, med3=med3, hi1=hi1, n=n), paths["feat"])
    print(P.shape, int(bad.iloc[-1].sum()))


if __name__ == "__main__":
    main()
