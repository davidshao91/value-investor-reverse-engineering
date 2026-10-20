"""Download EDGAR form.idx rows for spin-off registrations (Form 10-12B).

    python cases/greenblatt/code/g01_idx.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import re
import time

import requests

from cases._shared.config import edgar_headers, greenblatt_paths


def main():
    headers = edgar_headers()
    idx = greenblatt_paths()["idx"]
    idx.mkdir(parents=True, exist_ok=True)
    for y in range(2000, 2026):
        for q in range(1, 5):
            if y == 2025 and q > 3:
                break
            fn = idx / f"{y}Q{q}.tsv"
            if fn.exists():
                continue
            url = f"https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}/form.idx"
            txt = None
            for t in range(6):
                try:
                    r = requests.get(url, headers=headers, timeout=90)
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
                if line.startswith("10-12B"):
                    m = re.match(r"(\S+)\s+(.*?)\s+(\d+)\s+(\d{4}-\d{2}-\d{2})\s+", line)
                    if m and m.group(1) in ("10-12B", "10-12B/A"):
                        rows.append("\t".join(m.groups()))
            fn.write_text("\n".join(rows) + "\n")
            print(y, q, len(rows), flush=True)
            time.sleep(0.5)


if __name__ == "__main__":
    main()
