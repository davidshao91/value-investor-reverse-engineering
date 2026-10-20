"""Download HKEX headline-search JSON, one file per month.

    python cases/hk-privatization/code/h01_titles.py 2000 2000

Caches land in data/hk_privatization/hkex_titles/. This search is the
still-listed issuer index. Delisted issuers' announcements are not in it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import datetime as dt
import json
import time
import urllib.parse
import urllib.request

from cases._shared.config import hk_paths

TERMS = [
    "privatisation",
    "privatization",
    "scheme of arrangement",
    "withdrawal of listing",
    "merger by absorption",
    "voluntary general offer",
    "voluntary conditional",
    "lapse",
    "not approved",
]


def _query(term, start, end, market):
    url = (
        "https://www1.hkexnews.hk/search/titleSearchServlet.do?"
        "sortDir=0&sortByOptions=DateTime&category=0&market=%s&stockId=-1"
        "&documentType=-1&fromDate=%s&toDate=%s&title=%s&searchType=0"
        "&t1code=-2&t2Gcode=-2&t2code=-2&rowRange=3000&lang=E"
    ) % (market, start, end, urllib.parse.quote(term))
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=60).read()
            return json.loads(raw)
        except Exception:
            time.sleep(3 + 5 * k)
    return None


def main(argv):
    if len(argv) != 3:
        raise SystemExit("Usage: python cases/hk-privatization/code/h01_titles.py YEAR0 YEAR1")
    out = hk_paths()["hkex_titles"]
    out.mkdir(parents=True, exist_ok=True)
    y0, y1 = int(argv[1]), int(argv[2])
    today = dt.date.today()
    for year in range(y0, y1 + 1):
        for month in range(1, 13):
            start = dt.date(year, month, 1)
            end = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
            if start > today:
                break
            dest = out / f"{year}{month:02d}.json"
            if dest.exists():
                continue
            rows = []
            for term in TERMS:
                for market in ("SEHK", "GEM"):
                    payload = _query(term, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), market)
                    if payload is None:
                        print("FAIL", year, month, term, market, flush=True)
                        continue
                    result = payload.get("result")
                    found = json.loads(result) if result not in ("null", None) else []
                    if payload.get("hasNextRow"):
                        print("TRUNC", year, month, term, market, flush=True)
                    for row in found:
                        row["_term"] = term
                        row["_mk"] = market
                    rows.extend(found)
                    time.sleep(0.3)
            dest.write_text(json.dumps(rows))
            print(year, month, len(rows), flush=True)


if __name__ == "__main__":
    main(sys.argv)
