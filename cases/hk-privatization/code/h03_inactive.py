"""List HKEX inactive stock-code records into a local JSONL cache.

    python cases/hk-privatization/code/h03_inactive.py

Output: data/hk_privatization/inactive_stocks.jsonl. Not shipped.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from cases._shared.config import hk_paths


def _get(code):
    url = (
        "https://www1.hkexnews.hk/search/prefix.do?"
        f"callback=callback&lang=EN&type=I&name={code}&market=SEHK"
    )
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=40).read().decode()
            payload = json.loads(raw[raw.index("(") + 1 : raw.rindex(")")])
            return [row for row in payload.get("stockInfo", []) if row["code"] == code]
        except Exception:
            time.sleep(2 + 3 * k)
    return None


def main():
    dest = hk_paths()["inactive"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    codes = [f"{i:05d}" for i in list(range(1, 4000)) + list(range(6000, 7000)) + list(range(8000, 10000))]
    with ThreadPoolExecutor(8) as pool, dest.open("w") as handle:
        for code, res in zip(codes, pool.map(_get, codes)):
            handle.write(json.dumps({"q": code, "res": res}) + "\n")


if __name__ == "__main__":
    main()
