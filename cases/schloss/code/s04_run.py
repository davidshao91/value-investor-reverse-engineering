"""Run the locked M2 / M3 / M4 variants.

    python cases/schloss/code/s04_run.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pickle
import time

from cases._shared.config import schloss_paths
from engine import run


def main():
    specs = {}
    for e in ["v1", "v1b", "C3L"]:
        for dl in ["D0", "D2", "D1", "D1b"]:
            specs[f"{e}|lump|tgt|{dl}|10"] = dict(entry=e, delist=dl)
        specs[f"{e}|lump|tgt|D0|30"] = dict(entry=e, cost=0.003)
    for dl in ["D0", "D2", "D1", "D1b"]:
        specs[f"v1|scale|tgt|{dl}|10"] = dict(entry="v1", scale=True, delist=dl)
    specs["v1|scale|tgt|D0|30"] = dict(entry="v1", scale=True, cost=0.003)
    for x in ["X1", "X2", "X3"]:
        for dl in ["D0", "D1"]:
            specs[f"v1|lump|{x}|{dl}|10"] = dict(entry="v1", exit_=x, delist=dl)
        specs[f"v1|lump|{x}|D0|30"] = dict(entry="v1", exit_=x, cost=0.003)
    out = {}
    for k, sp in specs.items():
        t = time.time()
        s, info = run(**sp)
        out[k] = (s, info)
        print(k, round(time.time() - t, 1), {a: round(b, 3) for a, b in info.items()}, flush=True)
    paths = schloss_paths()
    paths["cache"].mkdir(parents=True, exist_ok=True)
    with open(paths["runs_v1"], "wb") as fh:
        pickle.dump(out, fh)


if __name__ == "__main__":
    main()
