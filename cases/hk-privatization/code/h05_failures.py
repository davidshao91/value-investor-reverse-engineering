"""Turn filtered headlines into candidate episodes on still-listed codes.

    python cases/hk-privatization/code/h05_failures.py

Completed Webb names are excluded. Output pickle stays in the data cache.
The boolean mask is the one used for the published failure list.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import re

import pandas as pd

from cases._shared.config import hk_paths, require

INTENT = re.compile(
    r"(PRIVATI[SZ](?:ATION|E)|TAKE[- ]PRIVATE)\s+(?:OF\s+)?(.*?)(?:\s+BY\s+|\s+AND\s+|\(|$)"
)
FAIL = re.compile(
    r"LAPSE|NOT (?:BEEN )?APPROVED|NOT BE IMPLEMENTED|"
    r"WITHDRAWAL OF THE (?:PROPOSAL|SCHEME|OFFER)|NOT PROCEED"
)
FIRM = re.compile(
    r"PROPOS(?:AL|ED) (?:FOR THE )?(?:PRIVATI|TAKE)|PRIVATISATION BY WAY|"
    r"SCHEME DOCUMENT|COURT MEETING"
)


def main():
    paths = hk_paths()
    titles = pd.read_pickle(
        require(paths["titles_filtered"], "Run h02_events.py first.")
    ).rename(columns={"dt": "ts"})
    webb = pd.read_csv(require(paths["webb"], "Missing the shipped Webb list."), dtype=str)
    done = set(webb.code.str.zfill(5))
    rows = []
    for _, row in titles.iterrows():
        title = row.title
        if not re.search(r"PRIVATI[SZ]|TAKE[- ]PRIVATE|WITHDRAWAL OF (?:THE )?LISTING", title):
            continue
        match = INTENT.search(title)
        target = match.group(2) if match else ""
        codes = str(row.STOCK_CODE).split("<br/>")
        names = str(row.STOCK_NAME).split("<br/>")
        for code, name in zip(codes, names):
            words = re.sub(r"[^A-Z ]", "", name.upper()).split()
            words = [
                word
                for word in words
                if len(word) >= 3 and word not in ("HOLD", "HLDGS", "INTL", "GROUP", "LTD", "CHINA", "INT")
            ]
            is_target = (len(codes) == 1) or (bool(words) and words[0] in target) or ("THE COMPANY" in target)
            rows.append(
                dict(code=code, name=name, ts=row["ts"], title=title, tgt=target, is_target=is_target)
            )
    events = pd.DataFrame(rows)
    # Same mask as the run that produced the published list (AND binds before OR).
    main_mask = (
        events.is_target
        & ~events.code.isin(done)
        & events.code.str.len().eq(5)
        & ~events.code.str.startswith(("4", "8", "9"))
    )
    gem_mask = events.is_target & events.code.str.startswith("8") & ~events.code.isin(done)
    events = events[main_mask | gem_mask]
    episodes = []
    for code, group in events.sort_values("ts").groupby("code"):
        start = None
        current = None
        last = None
        for _, row in group.iterrows():
            if start is None or (row["ts"] - last).days > 300:
                if start is not None:
                    episodes.append(current)
                start = row["ts"]
                current = dict(
                    code=code,
                    name=row["name"],
                    t0=row["ts"],
                    tlast=row["ts"],
                    n=0,
                    first_title=row.title[:200],
                    has_fail=False,
                    titles=[],
                )
            current["tlast"] = row["ts"]
            current["n"] += 1
            current["titles"].append(row.title[:120])
            if FAIL.search(row.title):
                current["has_fail"] = True
            last = row["ts"]
        if start is not None:
            episodes.append(current)
    frame = pd.DataFrame(episodes)
    frame["firm"] = frame.titles.map(lambda titles: any(FIRM.search(text) for text in titles))
    dest = paths["listed_episodes"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    frame.to_pickle(dest)
    print(len(frame), int(frame.firm.sum()), int(frame.has_fail.sum()))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 110)
    print(frame[frame.firm][["code", "name", "t0", "tlast", "n", "has_fail", "first_title"]].to_string())


if __name__ == "__main__":
    main()
