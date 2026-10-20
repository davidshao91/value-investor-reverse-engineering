"""Build the event table: inferred entry for completed deals, headline entry for failures.

    python cases/hk-privatization/code/h06_events.py

Completed deals have no announcement date in the Webb list. The entry date
is inferred from the price path and the final price, so it uses the outcome.
That truncates wide-spread deals that still closed. Writes
out/event_table.csv and out/event_table_ok.csv.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np
import pandas as pd

from cases._shared.config import hk_paths, require

# Two failure episodes whose headline date was fixed by hand before the run.
MANUAL_WINDOW = {"00008": ("2008-11-04", "2009-04-22")}


def _prices(px_dir, code):
    path = px_dir / f"{str(code).zfill(5)}.csv"
    if not path.exists():
        return None
    frame = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
    return frame[frame.close > 0]


def _period(timestamp):
    year = pd.Timestamp(timestamp).year
    if year <= 2013:
        return "2008-13"
    if year <= 2018:
        return "2014-18"
    return "2019-25"


def main():
    paths = hk_paths()
    px_dir = require(paths["px_sina"], "Need data/hk_privatization/px_sina/.")
    webb = pd.read_csv(require(paths["webb"], "Missing the shipped Webb list."), dtype=str)
    covered_path = paths["out"] / "coverage_completed.csv"
    if not covered_path.exists():
        raise SystemExit("Run h04_cov.py first.")
    covered = pd.read_csv(covered_path, dtype=str)
    webb = webb.merge(
        covered[["code", "lt", "status"]],
        left_on=["code", "last_trade"],
        right_on=["code", "lt"],
        how="left",
    )
    rows = []
    for _, row in webb.iterrows():
        last_trade = pd.Timestamp(row.last_trade)
        record = dict(
            code=str(row.code).zfill(5),
            name=row["name"],
            outcome="completed",
            last_trade=last_trade,
            status=row.status,
        )
        if row.status != "ok":
            rows.append(record)
            continue
        prices = _prices(px_dir, row.code)
        prices = prices[prices.index <= last_trade]
        window = prices[prices.index >= last_trade - pd.Timedelta(days=730)]
        final = window.close.iloc[-1]
        deviation = (window.close / final - 1).abs()
        outside = np.where(deviation.values > 0.20)[0]
        start = int(outside.max()) + 1 if len(outside) else 0
        if start >= len(window) - 5 or start == 0:
            record["status"] = "no_lock"
            rows.append(record)
            continue
        log_ret = np.log(window.close).diff()
        cand = log_ret.iloc[max(1, start - 3) : min(len(window) - 5, start + 4)]
        if len(cand) == 0 or cand.max() < np.log(1.05):
            record["status"] = "no_jump_at_lock"
            rows.append(record)
            continue
        t0 = cand.idxmax()
        loc = window.index.get_loc(t0)
        pre = window.close.iloc[loc - 1]
        entry = window.close.iloc[loc]
        record.update(
            t0=t0,
            pre=pre,
            entry=entry,
            exit=final,
            exit_date=last_trade,
            premium=entry / pre - 1,
            ret=final / entry - 1,
            days=(last_trade - t0).days + 14,
            gap_days=(t0 - window.index[loc - 1]).days,
            status="ok",
        )
        rows.append(record)

    failed = pd.read_csv(require(paths["failed"], "Missing the shipped failure list."), dtype=str)
    episodes = pd.read_pickle(
        require(paths["listed_episodes"], "Run h05_failures.py first.")
    )
    episodes = episodes[episodes.firm]
    for _, row in failed.iterrows():
        record = dict(code=row.code, name=row["name"], outcome="failed", note=row.note)
        matched = episodes[episodes.code == row.code]
        if row.code in MANUAL_WINDOW:
            t0, t_last = map(pd.Timestamp, MANUAL_WINDOW[row.code])
        elif len(matched) == 0:
            record["status"] = "no_episode"
            rows.append(record)
            continue
        else:
            year = row.note[:4]
            years = {year, str(int(year) + 1), str(int(year) - 1)}
            narrowed = matched[matched.t0.dt.year.astype(str).isin(years)]
            narrowed = narrowed if len(narrowed) else matched
            t0 = narrowed.t0.iloc[0]
            t_last = narrowed.tlast.iloc[-1]
        prices = _prices(px_dir, row.code)
        if prices is None or len(prices[(prices.index >= t0 - pd.Timedelta(days=30)) & (prices.index <= t0)]) == 0:
            record["status"] = "no_px"
            rows.append(record)
            continue
        window = prices[prices.index >= t0 - pd.Timedelta(days=60)]
        if t0.hour >= 12 or t0.hour == 0:
            post = window[window.index > t0.normalize()]
        else:
            post = window[window.index >= t0.normalize()]
        pre_slice = window[window.index < t0.normalize()]
        pre = pre_slice.close.iloc[-1]
        entry = post.close.iloc[0]
        t_entry = post.index[0]
        after = prices[prices.index > t_last.normalize()]
        if len(after) == 0 or (prices.index.max() - t_last).days < 60:
            record["status"] = "no_post_or_ongoing"
            rows.append(record)
            continue
        exit_px = after.close.iloc[0]
        record.update(
            status="ok",
            t0=t_entry,
            pre=pre,
            entry=entry,
            exit=exit_px,
            exit_date=after.index[0],
            premium=entry / pre - 1,
            ret=exit_px / entry - 1,
            fail_vs_pre=exit_px / pre - 1,
            days=(after.index[0] - t_entry).days,
            trading_after_days=(prices.index.max() - t_last).days,
        )
        rows.append(record)

    table = pd.DataFrame(rows)
    out = paths["out"]
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "event_table.csv", index=False)
    ok = table[table.status == "ok"].copy()
    ok["per"] = ok.t0.map(_period)
    ok["ann"] = (1 + ok.ret) ** (365 / ok.days) - 1
    ok.to_csv(out / "event_table_ok.csv", index=False)
    print(table.groupby(["outcome", "status"]).size())
    pd.set_option("display.width", 220)
    print(
        ok[ok.outcome == "failed"][["code", "name", "t0", "premium", "ret", "fail_vs_pre", "days"]]
        .round(3)
        .to_string()
    )


if __name__ == "__main__":
    main()
