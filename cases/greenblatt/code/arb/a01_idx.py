"""EDGAR form index for merger proxies, tender offers, and delisting notices.

    python cases/greenblatt/code/arb/a01_idx.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

import re
import time

import requests

from cases._shared.config import arb_paths, edgar_headers

KEEP = {"DEFM14A", "SC TO-T", "SC 13E3", "25-NSE", "SC 14D9", "PREM14A"}


def main():
    headers = edgar_headers()
    idx = arb_paths()["idx"]
    idx.mkdir(parents=True, exist_ok=True)
    for y in range(2008, 2027):
        for q in range(1, 5):
            if (y, q) > (2026, 3):
                break
            fn = idx / f"{y}Q{q}.tsv"
            if fn.exists():
                continue
            url = f"https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}/form.idx"
            txt = None
            for t in range(6):
                try:
                    r = requests.get(url, headers=headers, timeout=120)
                    if r.status_code == 200:
                        txt = r.content.decode("latin-1")
                        break
                except Exception:
                    pass
                time.sleep(3 + 3 * t)
            if txt is None:
                print("FAIL", y, q, flush=True)
                continue
            rows = []
            for line in txt.splitlines():
                f = next((k for k in KEEP if line.startswith(k + "  ")), None)
                if f:
                    p = line[len(f):].split()
                    if len(p) >= 4 and re.match(r"\d{4}-\d{2}-\d{2}", p[-2]):
                        rows.append("\t".join([f, " ".join(p[:-3]), p[-3], p[-2], p[-1]]))
            fn.write_text("\n".join(rows) + "\n")
            print(y, q, len(rows), flush=True)
            time.sleep(0.3)


if __name__ == "__main__":
    main()
