"""Download unadjusted HK daily bars (akshare / Sina) for Webb codes.

    python cases/hk-privatization/code/h03_px.py
    python cases/hk-privatization/code/h03_px.py 00001 00700

A reused ticker only returns the current occupant's history. That gap is
the coverage failure in this case. Files: data/hk_privatization/px_sina/.
akshare is imported only when this script runs.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import time

import pandas as pd

from cases._shared.config import hk_paths, require


def main(argv):
    try:
        import akshare as ak
    except ImportError as exc:
        raise SystemExit(
            "h03_px.py needs akshare (pip install akshare). "
            "Reading the published tables does not. See docs/data.md."
        ) from exc
    paths = hk_paths()
    dest = paths["px_sina"]
    dest.mkdir(parents=True, exist_ok=True)
    if len(argv) > 1:
        codes = argv[1:]
    else:
        webb = require(paths["webb"], "The Webb list is shipped under cases/hk-privatization/ref/.")
        codes = sorted(set(pd.read_csv(webb, dtype=str).code))
    for code in codes:
        code5 = str(code).zfill(5)
        path = dest / f"{code5}.csv"
        if path.exists() or path.with_suffix(".csv.err").exists():
            continue
        for attempt in range(3):
            try:
                frame = ak.stock_hk_daily(symbol=code5, adjust="")
                frame.to_csv(path, index=False)
                break
            except Exception as exc:
                if attempt == 2:
                    path.with_suffix(".csv.err").write_text(repr(exc)[:300])
                time.sleep(2)
        time.sleep(0.3)


if __name__ == "__main__":
    main(sys.argv)
