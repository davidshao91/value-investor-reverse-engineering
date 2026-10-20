"""Join parsed consideration with completion / termination dates.

    python cases/greenblatt/code/arb/a05_events.py
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
    paths = arb_paths()
    O = pd.read_csv(require(paths["parsed"], "Run a03_parse.py first."), dtype={"cik": str})
    O["date"] = pd.to_datetime(O.date)
    C = O[O.fetched & O.cash.notna() & ~O.stock.astype(bool) & ~O.spac.astype(bool)].copy()
    nse = {}
    for f in paths["idx"].glob("*.tsv"):
        for line in f.read_text().splitlines():
            p = line.split("\t")
            if len(p) == 5 and p[0] == "25-NSE":
                nse.setdefault(str(int(p[2])), []).append(pd.Timestamp(p[3]))
    rows = []
    for _, e in C.iterrows():
        fn = paths["subs"] / f"{e.cik}.json"
        j = json.loads(fn.read_text()) if fn.exists() else {}
        forms = j.get("form", [])
        dates = pd.to_datetime(pd.Series(j.get("filingDate", []), dtype=str), errors="coerce")
        items = j.get("items", [""] * len(forms))
        lim = e.date + pd.DateOffset(months=24)
        comp = [d for f, d in zip(forms, dates) if f in DONE and e.date < d <= lim]
        comp += [d for d in nse.get(str(int(e.cik)), []) if e.date < d <= lim]
        comp += [d for f, d, it in zip(forms, dates, items) if f == "8-K" and "5.01" in str(it) and e.date < d <= lim]
        term = [d for f, d, it in zip(forms, dates, items) if f == "8-K" and "1.02" in str(it) and e.date < d <= lim]
        t = (j.get("tickers") or [None])[0]
        ok_px = pd.notna(e.px_pd) and 0.5 <= e.px_pd / e.cash <= 1.5
        rows.append(dict(
            cik=e.cik, company=e.company, date=e.date, cash=e.cash, cvr=e.cvr,
            px_pd=e.px_pd if ok_px else np.nan, px_pd_raw=e.px_pd, px_un=e.px_un,
            subs=bool(j), completed=bool(comp), done_date=min(comp) if comp else pd.NaT,
            term_date=min(term) if term else pd.NaT, ticker=t,
        ))
    E = pd.DataFrame(rows)
    E["spread"] = E.cash / E.px_pd - 1
    E.to_csv(paths["events_cash"], index=False)
    print(len(E), "entry ok", E.px_pd.notna().sum(), "completed", E.completed.sum(), "broken", (~E.completed).sum())


if __name__ == "__main__":
    main()
