"""Price-coverage table for completed Webb privatizations.

    python cases/hk-privatization/code/h04_cov.py

A code is "ok" only when the series still reaches the last trade date
(gap <= 7 days) and has at least 100 bars in the prior two years.
Anything else is a reused ticker, a stale gap, or a short history.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd

from cases._shared.config import hk_paths, require


def main():
    paths = hk_paths()
    webb = pd.read_csv(
        require(paths["webb"], "Missing the shipped Webb list under cases/hk-privatization/ref/."),
        dtype=str,
    )
    px_dir = require(
        paths["px_sina"],
        "Put Sina daily bars in data/hk_privatization/px_sina/.",
    )
    if not any(px_dir.glob("*.csv")):
        raise SystemExit(f"No daily bars in {px_dir}. Run h03_px.py or copy a local cache.")
    webb["ltd"] = pd.to_datetime(webb.last_trade)
    webb["y"] = webb.ltd.dt.year
    rows = []
    for _, row in webb.iterrows():
        path = px_dir / f"{str(row.code).zfill(5)}.csv"
        status, n_bars = "no_series", 0
        if path.exists():
            prices = pd.read_csv(path, parse_dates=["date"]).set_index("date")
            pre = prices[prices.index <= row.ltd + pd.Timedelta(days=3)]
            if len(pre) == 0:
                status = "reused_code_only"
            else:
                gap = (row.ltd - pre.index.max()).days
                n_bars = len(pre[pre.index >= row.ltd - pd.Timedelta(days=730)])
                if gap <= 7 and n_bars >= 100:
                    status = "ok"
                elif gap > 7:
                    status = f"stale_gap{gap}"
                else:
                    status = "short"
        rows.append(
            dict(
                code=row.code,
                name=row["name"],
                lt=row.ltd.date(),
                y=row.y,
                status=status,
                n2y=n_bars,
            )
        )
    covered = pd.DataFrame(rows)
    out = paths["out"]
    out.mkdir(parents=True, exist_ok=True)
    covered.to_csv(out / "coverage_completed.csv", index=False)
    print(covered.status.value_counts())
    covered["ok"] = covered.status.eq("ok")
    grouped = covered.groupby("y").ok.agg(["size", "sum"])
    grouped["cov"] = (grouped["sum"] / grouped["size"]).round(2)
    print(grouped.T.to_string())
    since_2008 = covered[covered.y >= 2008]
    print(
        "2008+ cov",
        round(since_2008.ok.mean(), 3),
        "n",
        int(since_2008.shape[0]),
        "| 2000+",
        round(covered.ok.mean(), 3),
    )


if __name__ == "__main__":
    main()
