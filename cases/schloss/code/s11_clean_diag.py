"""Drop one-day -90% terminal prints, then rescore. Real zeros stay.

    python cases/schloss/code/s11_clean_diag.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

import engine as E
from navmetrics import benchmarks, cmp, st


def main():
    E.load()
    Pm = E.A["P"].copy()
    E.A["P"] = Pm
    fixed = []
    for j, c in enumerate(E.cols):
        lp = E.lastpos[j]
        if lp < 1:
            continue
        s = Pm[:lp + 1, j]
        v = np.where(~np.isnan(s))[0]
        tail = v[-20:]
        for a, b in zip(tail[:-1], tail[1:]):
            if s[b] < 0.1 * s[a]:
                Pm[b:, j] = np.nan
                E.lastpos[j] = a
                fixed.append((c, str(E.cal[a].date()), s[a], s[b]))
                break
    print(len(fixed), fixed)
    nav = benchmarks()
    res = []
    jobs = {
        "v1|lump|D0clean": dict(entry="v1"),
        "v1|scale|D0clean": dict(entry="v1", scale=True),
        "C3L|lump|D0clean": dict(entry="C3L"),
        "v1|lump|D1clean": dict(entry="v1", delist="D1"),
        "v1|lump|D0clean@2008": dict(entry="v1", start="2007-12-31"),
        "v1|lump|D0clean@2003": dict(entry="v1", start="2002-12-31"),
    }
    for k, sp in jobs.items():
        s, _i = E.run(**sp)
        c, m, kk = st(s)
        r = dict(spec=k, CAGR=c, MDD=m, Calmar=kk)
        for bn, b in nav.items():
            d = cmp(s, b)
            r.update({f"{a}_{bn}": v for a, v in d.items() if a != "best3"})
        res.append(r)
    T = pd.DataFrame(res)
    from cases._shared.config import schloss_paths
    paths = schloss_paths()
    paths["out"].mkdir(parents=True, exist_ok=True)
    T.to_csv(paths["out"] / "diag_terminal_clean.csv", index=False)
    print(T.round(3).to_string())


if __name__ == "__main__":
    main()
