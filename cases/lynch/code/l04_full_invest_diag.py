"""Unregistered diagnostic: invest the signal fully (no cash residual). Not a pass/fail run.

    python cases/lynch/code/l04_full_invest_diag.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

import l01_backtest as m


def main():
    m.load()
    out = []
    for univ in ["SPX", "BROAD"]:
        r, _l = m.run(univ, 10, "cash", cap=False)
        r.columns = [f"{univ}|10|full|{c}" for c in r.columns]
        out.append(r)
        print(univ, "done", flush=True)
    pd.concat(out, axis=1).to_csv(m.OUT + "monthly_returns_fullinvest_diag.csv")
    cov = []
    for y in range(2011, 2025):
        mem = m.members(pd.Timestamp(f"{y + 1}-06-30"))
        d = m.frame(y, "SPX")
        cov.append(dict(form=y + 1, members=len(mem), in_universe_nonfin=len(d)))
    pd.DataFrame(cov).to_csv(m.OUT + "spx_coverage.csv", index=False)
    print(pd.DataFrame(cov).to_string())


if __name__ == "__main__":
    main()
