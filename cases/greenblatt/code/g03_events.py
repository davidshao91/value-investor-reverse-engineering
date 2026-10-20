"""Mark completed spin-offs and download monthly prices.

    python cases/greenblatt/code/g03_events.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import json

import pandas as pd

from cases._shared.config import greenblatt_paths, require


def main():
    import yfinance as yf
    paths = greenblatt_paths()
    F = pd.read_csv(require(paths["events_raw"], "Run g02_subs.py first."), dtype={"cik": str})
    F["first12b"] = pd.to_datetime(F.first12b)
    PER = ("10-K", "10-Q", "10-K405", "10-KT", "10-KSB", "10-QSB")
    out = []
    for _, e in F.iterrows():
        fn = paths["subs"] / f"{e.cik}.json"
        j = json.loads(fn.read_text()) if fn.exists() else {}
        forms = j.get("forms", [])
        dates = pd.to_datetime(pd.Series(j.get("dates", []), dtype=str), errors="coerce")
        per = [d for f, d in zip(forms, dates) if f in PER]
        pre10k = any((f in ("10-K", "10-K405", "10-KSB")) and d < e.first12b for f, d in zip(forms, dates))
        post = [d for d in per if e.first12b < d <= e.first12b + pd.DateOffset(months=24)]
        out.append(dict(
            cik=e.cik, company=e.company, first12b=e.first12b, pre10k=pre10k, completed=len(post) > 0,
            first_periodic=min(post) if post else pd.NaT, ticker=(j.get("tickers") or [None])[0],
            exch=(j.get("exchanges") or [None])[0], sic=j.get("sic"), subs_ok="forms" in j,
        ))
    E = pd.DataFrame(out)
    print("all", len(E), "subs_ok", E.subs_ok.sum(), "pre10k", E.pre10k.sum(), "completed(no pre10k)", (E.completed & ~E.pre10k).sum())
    E.to_csv(paths["events_flags"], index=False)
    C = E[E.completed & ~E.pre10k].copy()
    tk = sorted(set(C.ticker.dropna()))
    print("completed with current ticker", C.ticker.notna().sum(), "unique", len(tk))
    px = yf.download(tk + ["SPY"], start="1999-01-01", interval="1mo", auto_adjust=False, progress=False, threads=True)
    paths["cache"].mkdir(parents=True, exist_ok=True)
    px.to_pickle(paths["px_events"])
    print(px.shape)


if __name__ == "__main__":
    main()
