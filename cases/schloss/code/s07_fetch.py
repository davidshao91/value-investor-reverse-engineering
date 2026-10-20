"""Download quarterly XBRL frames used by the price-to-book variant.

    python cases/schloss/code/s07_fetch.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import time

import requests

from cases._shared.config import edgar_headers, schloss_paths


def main():
    headers = edgar_headers()
    paths = schloss_paths()
    paths["frames"].mkdir(parents=True, exist_ok=True)
    cons = [
        ("us-gaap", "StockholdersEquity", "USD"),
        ("us-gaap", "LongTermDebt", "USD"),
        ("us-gaap", "LongTermDebtNoncurrent", "USD"),
        ("us-gaap", "LongTermDebtCurrent", "USD"),
        ("us-gaap", "Liabilities", "USD"),
        ("us-gaap", "CommonStockSharesOutstanding", "shares"),
        ("dei", "EntityCommonStockSharesOutstanding", "shares"),
    ]
    per = [f"CY{y}Q{q}I" for y in range(2009, 2027) for q in range(1, 5)][:70]
    miss = []
    for tx, c, u in cons:
        for p in per:
            fn = paths["frames"] / f"{c}_{p}.json"
            if fn.exists():
                continue
            r = requests.get(f"https://data.sec.gov/api/xbrl/frames/{tx}/{c}/{u}/{p}.json", headers=headers, timeout=60)
            if r.status_code == 200:
                fn.write_text(r.text)
            else:
                miss.append((c, p, r.status_code))
            time.sleep(0.12)
    r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers, timeout=60)
    paths["company_tickers"].write_text(r.text)
    print(len(miss), miss[:20])


if __name__ == "__main__":
    main()
