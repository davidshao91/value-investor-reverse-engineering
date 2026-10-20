"""Download the primary document of each DEFM14A (stop at the first </DOCUMENT>).

    python cases/greenblatt/code/arb/a02_fetch.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

import gzip
import time

import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor

from cases._shared.config import arb_paths, edgar_headers


def main():
    headers = edgar_headers()
    paths = arb_paths()
    rows = []
    for f in sorted(paths["idx"].glob("*.tsv")):
        for line in f.read_text().splitlines():
            p = line.split("\t")
            if len(p) == 5:
                rows.append(p)
    if not rows:
        raise SystemExit(f"No index in {paths['idx']}. Run a01_idx.py first.")
    E = pd.DataFrame(rows, columns=["form", "company", "cik", "date", "path"])
    E["date"] = pd.to_datetime(E.date)
    D = E[(E.form == "DEFM14A") & (E.date >= "2009-01-01") & (E.date <= "2025-09-30")].sort_values("date")
    keep = []
    last = {}
    for _, r in D.iterrows():
        if r.cik in last and (r.date - last[r.cik]).days < 548:
            continue
        last[r.cik] = r.date
        keep.append(r)
    D = pd.DataFrame(keep)
    paths["cache"].mkdir(parents=True, exist_ok=True)
    paths["docs"].mkdir(parents=True, exist_ok=True)
    D.to_csv(paths["defm14a_events"], index=False)
    print("events", len(D), flush=True)

    def get(path):
        fn = paths["docs"] / path.split("/")[-1].replace(".txt", ".gz")
        if fn.exists():
            return
        for t in range(4):
            try:
                r = requests.get("https://www.sec.gov/Archives/" + path, headers=headers, timeout=60, stream=True)
                if r.status_code != 200:
                    time.sleep(2 + t * 3)
                    continue
                buf = b""
                for ch in r.iter_content(65536):
                    buf += ch
                    if b"</DOCUMENT>" in buf or len(buf) > 6_000_000:
                        break
                r.close()
                i = buf.find(b"</DOCUMENT>")
                buf = buf[:i] if i > 0 else buf
                with gzip.open(fn, "wb") as fh:
                    fh.write(buf)
                return
            except Exception:
                time.sleep(2 + t * 3)

    t0 = time.time()
    with ThreadPoolExecutor(5) as ex:
        for i, _ in enumerate(ex.map(lambda p: (get(p), time.sleep(0.4)), list(D.path))):
            if i % 200 == 0:
                print(i, round(time.time() - t0), flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
