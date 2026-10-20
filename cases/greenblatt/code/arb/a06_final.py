"""Final event table: completion date and exit value.

    python cases/greenblatt/code/arb/a06_final.py
    python cases/greenblatt/code/arb/a06_final.py 501
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

import json

import numpy as np
import pandas as pd

from cases._shared.config import arb_paths, require

DONE = ("25-NSE", "25", "15-12B", "15-12G", "15-15D", "15-12B/A", "15-12G/A")


def main():
    use501 = len(sys.argv) > 1
    paths = arb_paths()
    E = pd.read_csv(require(paths["events_guarded"], "Run a05b_guards.py first."), dtype={"cik": str}, parse_dates=["date", "done_date", "term_date"])
    E = E[E.in_universe].copy()
    nse = {}
    for f in paths["idx"].glob("*.tsv"):
        for line in f.read_text().splitlines():
            p = line.split("\t")
            if len(p) == 5 and p[0] == "25-NSE":
                nse.setdefault(str(int(p[2])), []).append(pd.Timestamp(p[3]))
    dd = []
    for _, e in E.iterrows():
        j = json.loads((paths["subs"] / f"{e.cik}.json").read_text())
        forms = j.get("form", [])
        dates = pd.to_datetime(pd.Series(j.get("filingDate", []), dtype=str), errors="coerce")
        items = j.get("items", [""] * len(forms))
        lim = e.date + pd.DateOffset(months=24)
        cand = [d for f, d in zip(forms, dates) if f in DONE and e.date < d <= lim]
        cand += [d for d in nse.get(str(int(e.cik)), []) if e.date < d <= lim]
        if use501:
            cand += [d for f, d, it in zip(forms, dates, items) if f == "8-K" and "5.01" in str(it) and e.date < d <= lim]
        ok = sorted(cand)
        dd.append(ok[0] if ok else pd.NaT)
    E["done2"] = dd
    E["completed2"] = E.done2.notna()
    px = pd.read_pickle(require(paths["px_broken"], "Cache failed-deal prices at data/greenblatt/arb/px_broken.pkl."))
    CL = px["Close"]
    CL.index = CL.index.to_period("M")
    CL = CL.groupby(level=0).last()

    def exitpx(e):
        if e.completed2:
            return e.cash, e.done2.to_period("M"), "completed"
        ex = min([d for d in [e.term_date + pd.DateOffset(months=1) if pd.notna(e.term_date) else None, e.date + pd.DateOffset(months=12)] if d is not None])
        m = ex.to_period("M")
        if isinstance(e.ticker, str) and e.ticker in CL.columns and pd.notna(CL[e.ticker].get(m, np.nan)):
            return CL[e.ticker][m], m, "broken_priced"
        return np.nan, m, "broken_unpriced"

    r = E.apply(exitpx, axis=1, result_type="expand")
    E["exit_val"] = r[0]
    E["exit_m"] = r[1].astype(str)
    E["outcome"] = r[2]
    E["entry_m"] = E.date.dt.to_period("M").astype(str)
    E["covered"] = E.px_pd.notna() & E.exit_val.notna()
    name = "events_final_501.csv" if use501 else "events_final.csv"
    E.to_csv(paths["cache"] / name, index=False)
    print("universe", len(E))
    print(E.outcome.value_counts())
    print("coverage", E.covered.sum(), "/", len(E), "=", round(E.covered.mean(), 4))


if __name__ == "__main__":
    main()
