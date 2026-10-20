"""Extra guards: prospectus count, and per-share price sanity.

    python cases/greenblatt/code/arb/a05b_guards.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gzip
import re

import pandas as pd

from a03_parse import clean
from cases._shared.config import arb_paths, require


def main():
    paths = arb_paths()
    E = pd.read_csv(require(paths["events_cash"], "Run a05_events.py first."), dtype={"cik": str})
    O = pd.read_csv(paths["parsed"], dtype={"cik": str})
    E = E.merge(O[["cik", "date", "path"]], on=["cik", "date"], how="left")
    pros = []
    for p in E.path:
        fn = paths["docs"] / p.split("/")[-1].replace(".txt", ".gz")
        with gzip.open(fn, "rb") as fh:
            t = clean(fh.read())[:400000]
        pros.append(len(re.findall(r"prospectus", t, re.I)))
    E["n_prospectus"] = pros
    E["g_stock"] = E.n_prospectus >= 10
    E["g_pershare"] = (E.cash > 1000) | (E.px_un.notna() & ~((E.cash / E.px_un).between(0.3, 5)))
    E["in_universe"] = ~E.g_stock & ~E.g_pershare
    E.to_csv(paths["events_guarded"], index=False)
    U = E[E.in_universe]
    print("raw", len(E), "stock-guard", E.g_stock.sum(), "pershare-guard", (E.g_pershare & ~E.g_stock).sum(), "universe", len(U))
    print("entry ok", U.px_pd.notna().sum(), U.px_pd.notna().mean())


if __name__ == "__main__":
    main()
