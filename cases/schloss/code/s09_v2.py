"""Price-to-book variant. Coverage under 70% is a data blocker, not a pass.

    python cases/schloss/code/s09_v2.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pickle

import numpy as np
import pandas as pd

from cases._shared.config import require, schloss_paths
import engine
from engine import run


def main():
    engine.load()
    paths = schloss_paths()
    X = pd.read_pickle(require(paths["xbrl_q"], "Run s08_xbrl.py first."))
    RC = pd.read_pickle(require(paths["rawclose"], "Run s08_xbrl.py first.")).sort_index()
    X = X.sort_values(["tk", "end"]).drop_duplicates(["tk", "end"], keep="last")
    H = {}
    for tk, g in X.groupby("tk"):
        if tk not in RC.columns:
            continue
        rc = RC[tk].dropna()
        if len(rc) == 0:
            continue
        pos = rc.index.searchsorted(g.avail.values, side="right") - 1
        ok = pos >= 0
        pxq = np.where(ok, rc.values[np.clip(pos, 0, None)], np.nan)
        H[tk] = pd.DataFrame(dict(avail=g.avail.values, bps=g.bps.values, de=g.de_ok.values.astype(bool), pbq=pxq / g.bps.values))
    MED = {}

    def info(nm, d):
        h = H.get(nm)
        if h is None:
            return None
        h = h[h.avail <= d]
        if len(h) < 20:
            return None
        hh = h.iloc[-40:]
        rc = RC[nm].loc[:d].dropna()
        if len(rc) == 0:
            return None
        bps = hh.bps.iloc[-1]
        if not bps > 0:
            return None
        return rc.iloc[-1] / bps, hh.pbq.quantile(0.2), hh.pbq.median(), bool(hh.de.iloc[-1]), bps

    def filt(nm, d, px):
        r = info(nm, d)
        if r is None:
            return False
        pb, q20, med, de, bps = r
        if pb <= q20 and de:
            MED[nm] = med
            return True
        return False

    def pbx(nm, d, px, p):
        h = H.get(nm)
        med = p.setdefault("med", MED.get(nm))
        if h is None or med is None:
            return False
        hh = h[h.avail <= d]
        if len(hh) == 0:
            return False
        rc = RC[nm].loc[:d].dropna()
        return len(rc) > 0 and rc.iloc[-1] / hh.bps.iloc[-1] >= med

    cov = []
    for d in sorted(k for k in engine.MEM if k >= pd.Timestamp("2014-12-31")):
        mem = engine.MEM[d]
        n = sum(1 for nm in mem if info(nm, d) is not None)
        cov.append((d, len(mem), n))
    C = pd.DataFrame(cov, columns=["d", "mem", "mapped"])
    C["y"] = C.d.dt.year
    Y = C.groupby("y")[["mem", "mapped"]].mean()
    Y["cov"] = Y.mapped / Y.mem
    paths["out"].mkdir(parents=True, exist_ok=True)
    Y.round(3).to_csv(paths["out"] / "coverage_v2_xbrl.csv")
    print(Y.round(3))
    print("avg", C.mapped.sum() / C.mem.sum())
    out = {}
    S = "2014-12-31"
    jobs = {
        "v2|lump|pb|D0|10": dict(),
        "v2|lump|pb|D2|10": dict(delist="D2"),
        "v2|lump|pb|D1|10": dict(delist="D1"),
        "v2|lump|pb|D0|30": dict(cost=0.003),
        "v2|scale|pb|D0|10": dict(scale=True),
        "v1|lump|tgt|D0|10@2015": dict(entry="v1", exit_="tgt", extra=False),
        "C3L|lump|tgt|D0|10@2015": dict(entry="C3L", exit_="tgt", extra=False),
        "v2noPB_DEonly|lump|tgt|D0|10": dict(de_only=True),
    }
    for k, sp in jobs.items():
        MED.clear()
        if sp.pop("extra", True) is False:
            s, inf = run(start=S, **sp)
        elif sp.pop("de_only", False):
            s, inf = run(start=S, entry="v1", extra_filter=lambda nm, d, px: (info(nm, d) is not None and info(nm, d)[3]))
        else:
            s, inf = run(start=S, entry="v1", exit_="pb", extra_filter=filt, pb_exit=pbx, **sp)
        out[k] = (s, inf)
        print(k, {a: round(float(b), 3) for a, b in inf.items()}, flush=True)
    with open(paths["runs_v2"], "wb") as fh:
        pickle.dump(out, fh)


if __name__ == "__main__":
    main()
