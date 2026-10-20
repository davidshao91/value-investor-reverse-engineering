"""Pull SEC submissions for each 10-12B filer.

    python cases/greenblatt/code/g02_subs.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import json
import time

import pandas as pd
import requests

from cases._shared.config import edgar_headers, greenblatt_paths


def main():
    headers = edgar_headers()
    paths = greenblatt_paths()
    rows = []
    for f in sorted(paths["idx"].glob("*.tsv")):
        for line in f.read_text().splitlines():
            p = line.split("\t")
            if len(p) == 4:
                rows.append(p)
    if not rows:
        raise SystemExit(f"No index rows in {paths['idx']}. Run g01_idx.py first.")
    E = pd.DataFrame(rows, columns=["form", "company", "cik", "date"])
    E["date"] = pd.to_datetime(E["date"])
    F = E.sort_values("date").groupby("cik").agg(company=("company", "first"), first12b=("date", "min"), n12b=("date", "size")).reset_index()
    paths["cache"].mkdir(parents=True, exist_ok=True)
    F.to_csv(paths["events_raw"], index=False)
    print("unique CIK", len(F), flush=True)
    subs = paths["subs"]
    subs.mkdir(parents=True, exist_ok=True)
    for i, c in enumerate(F.cik):
        fn = subs / f"{c}.json"
        if fn.exists():
            continue
        url = f"https://data.sec.gov/submissions/CIK{int(c):010d}.json"
        r = None
        for t in range(5):
            try:
                r = requests.get(url, headers=headers, timeout=30)
                if r.status_code in (200, 404):
                    break
            except Exception:
                pass
            time.sleep(2 + 2 * t)
        try:
            if r is not None and r.status_code == 200:
                j = r.json()
                rec = j["filings"]["recent"]
                forms = list(rec["form"])
                dates = list(rec["filingDate"])
                for extra in j["filings"].get("files", []):
                    try:
                        r2 = requests.get("https://data.sec.gov/submissions/" + extra["name"], headers=headers, timeout=30).json()
                        forms += r2["form"]
                        dates += r2["filingDate"]
                        time.sleep(0.15)
                    except Exception:
                        pass
                fn.write_text(json.dumps({
                    "tickers": j.get("tickers", []), "exchanges": j.get("exchanges", []),
                    "name": j.get("name"), "sic": j.get("sic"),
                    "former": j.get("formerNames", []), "forms": forms, "dates": dates,
                }))
            else:
                status = r.status_code if r is not None else "err"
                fn.write_text(json.dumps({"status": status}))
        except Exception as e:
            print("err", c, e)
        if i % 100 == 0:
            print(i, flush=True)
        time.sleep(0.15)


if __name__ == "__main__":
    main()
