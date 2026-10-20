"""SEC submissions for pure-cash merger targets.

    python cases/greenblatt/code/arb/a04_subs.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

import json
import time

import pandas as pd
import requests

from cases._shared.config import arb_paths, edgar_headers, require


def main():
    headers = edgar_headers()
    paths = arb_paths()
    O = pd.read_csv(require(paths["parsed"], "Run a03_parse.py first."), dtype={"cik": str})
    C = O[O.fetched & O.cash.notna() & ~O.stock.astype(bool) & ~O.spac.astype(bool)]
    paths["subs"].mkdir(parents=True, exist_ok=True)
    for i, c in enumerate(sorted(set(C.cik))):
        fn = paths["subs"] / f"{c}.json"
        if fn.exists():
            continue
        try:
            r = requests.get(f"https://data.sec.gov/submissions/CIK{int(c):010d}.json", headers=headers, timeout=30)
            if r.status_code != 200:
                fn.write_text(json.dumps({"status": r.status_code}))
                continue
            j = r.json()
            rec = j["filings"]["recent"]
            F = {k: list(rec.get(k, [])) for k in ("form", "filingDate", "items")}
            for ex in j["filings"].get("files", []):
                r2 = requests.get("https://data.sec.gov/submissions/" + ex["name"], headers=headers, timeout=30).json()
                time.sleep(0.12)
                for k in F:
                    F[k] += list(r2.get(k, []))
            fn.write_text(json.dumps({"tickers": j.get("tickers", []), "name": j.get("name"), "sic": j.get("sic"), **F}))
        except Exception as e:
            print("err", c, e, flush=True)
        time.sleep(0.12)
        if i % 100 == 0:
            print(i, flush=True)
    print("done")


if __name__ == "__main__":
    main()
