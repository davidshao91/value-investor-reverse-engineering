"""Filter cached HKEX headlines down to privatisation-like titles.

    python cases/hk-privatization/code/h02_events.py

Reads data/hk_privatization/hkex_titles/*.json. Writes titles_filtered.pkl
in that cache. Does not write a price or benchmark series.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import html
import json
import re

import pandas as pd

from cases._shared.config import hk_paths, require

KEY = re.compile(
    r"PRIVATI[SZ]|SCHEME OF ARRANGEMENT|WITHDRAWAL OF (THE )?LISTING|"
    r"MERGER BY (WAY OF )?ABSORPTION|TAKE[- ]PRIVATE|"
    r"VOLUNTARY (GENERAL|CONDITIONAL|UNCONDITIONAL)"
)
BAD = re.compile(
    r"WARRANT|CBBC|DERIVATIVE|NOTES DUE|BONDS? DUE|CALLABLE BULL|"
    r"RIGHTS ISSUE|SHARE OPTION SCHEME|SHARE AWARD|REIT|UNITS"
)


def main():
    paths = hk_paths()
    folder = require(
        paths["hkex_titles"],
        "Run h01_titles.py first. HKEX JSON is not shipped with the repo.",
    )
    files = sorted(folder.glob("*.json"))
    if not files:
        raise SystemExit(f"No JSON in {folder}. Run h01_titles.py. See docs/data.md.")
    rows = []
    for path in files:
        rows.extend(json.loads(path.read_text()))
    df = pd.DataFrame(rows).drop_duplicates("NEWS_ID")
    df["title"] = df.TITLE.map(lambda s: html.unescape(s).replace("\n", " ").upper())
    df["dt"] = pd.to_datetime(df.DATE_TIME, format="%d/%m/%Y %H:%M")
    df = df[df.title.str.contains(KEY)]
    df = df[~df.title.str.contains(BAD)]
    dest = paths["titles_filtered"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    df[["NEWS_ID", "dt", "STOCK_CODE", "STOCK_NAME", "title", "FILE_LINK", "_mk"]].to_pickle(dest)
    print(len(df))
    print(df.dt.dt.year.value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main()
