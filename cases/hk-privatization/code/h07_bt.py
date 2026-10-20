"""Diagnostic backtest of announced HK privatizations, 2019-01-02 to 2026-09-30.

    python cases/hk-privatization/code/h07_bt.py

Public benchmark is 2800.HK adjusted close (data/hk_privatization/px_2800.csv).
The author's private conservative portfolio is optional: a CSV with columns
date, nav at data/private/author_benchmark.csv (or VIRE_AUTHOR_BENCH).
Only summary scoreboard rows are written for that series. Its level is
never written to out/.

This window is a diagnostic. The preregistered coverage bar already failed,
so these numbers are not a pass.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import json

import numpy as np
import pandas as pd

from cases._shared.config import AUTHOR_BENCHMARK, hk_paths, require

W0 = pd.Timestamp("2019-01-02")
W1 = pd.Timestamp("2026-09-30")


def _prices(px_dir, code):
    path = px_dir / f"{code}.csv"
    if not path.exists():
        raise SystemExit(f"Missing {path}\nSee docs/data.md.")
    series = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index().close
    return series[series > 0]


def _load_2800(paths):
    frame = pd.read_csv(require(paths["px_2800"], "Save 2800.HK adjusted close as data/hk_privatization/px_2800.csv."))
    if "Date" in frame.columns:
        frame = frame.set_index("Date")
    frame.index = pd.to_datetime(frame.index.astype(str).str[:10])
    col = "Adj Close" if "Adj Close" in frame.columns else frame.columns[0]
    return frame[col].sort_index()


def _load_author():
    """Optional. Returns None when the file is absent. Never persisted."""
    path = AUTHOR_BENCHMARK
    if not path.exists():
        print("optional author benchmark absent; author rows skipped")
        return None
    frame = pd.read_csv(path, parse_dates=["date"])
    if "nav" not in frame.columns:
        raise SystemExit(f"{path} needs columns date, nav")
    series = frame.set_index("date")["nav"].sort_index()
    series.index = pd.to_datetime(series.index, utc=True).tz_localize(None)
    series.name = "author"
    return series


def _raw(nav):
    nav = nav.dropna()
    nav = nav / nav.iloc[0]
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    cagr = float(nav.iloc[-1] ** (1 / years) - 1)
    mdd = float((nav / nav.cummax() - 1).min())
    calmar = cagr / abs(mdd) if mdd < 0 else np.nan
    return cagr, mdd, calmar


def _stats(nav):
    cagr, mdd, calmar = _raw(nav)
    return dict(CAGR=round(cagr, 4), MDD=round(mdd, 4), Calmar=round(calmar, 3))


def _yearly(nav):
    year_end = nav.resample("YE").last()
    year_end = pd.concat([pd.Series([nav.iloc[0]], index=[nav.index[0] - pd.Timedelta(days=1)]), year_end])
    return year_end.pct_change().dropna()


def main():
    paths = hk_paths()
    px_dir = require(paths["px_sina"], "Need data/hk_privatization/px_sina/.")
    table = pd.read_csv(
        require(paths["out"] / "event_table.csv", "Need out/event_table.csv. See the shipped table or rerun h06."),
        parse_dates=["t0", "exit_date", "last_trade"],
        dtype={"code": str},
    )
    table["code"] = table.code.str.zfill(5)
    bench_2800 = _load_2800(paths)
    author = _load_author()
    days = bench_2800[(bench_2800.index >= W0) & (bench_2800.index <= W1)].index
    ok = table[table.status == "ok"].copy()
    ok_completed = ok[ok.outcome == "completed"]
    ok_failed = ok[ok.outcome == "failed"]
    med_c = ok_completed.ret.median()
    med_f = ok_failed.ret.median()
    med_days = int(ok_completed.days.median())
    all_completed = table[
        (table.outcome == "completed")
        & (table.last_trade >= W0 + pd.Timedelta(days=med_days))
        & (table.last_trade <= W1)
    ].copy()
    all_failed = table[table.outcome == "failed"].copy()
    missing = all_completed[all_completed.status != "ok"].copy()
    missing["t0"] = missing.last_trade - pd.Timedelta(days=med_days - 14)
    missing["exit_date"] = missing.last_trade
    universe = pd.concat(
        [all_completed[all_completed.status == "ok"], missing, all_failed[all_failed.status == "ok"]]
    )
    universe = universe[(universe.t0 >= W0) & (universe.t0 <= W1 - pd.Timedelta(days=30))]
    fail_rate = len(ok_failed[ok_failed.t0 >= W0]) / (len(ok_failed[ok_failed.t0 >= W0]) + len(all_completed))
    coverage = (universe.status == "ok").mean()

    def path_of(event, mode):
        if event.status == "ok":
            series = _prices(px_dir, event.code)
            segment = series[(series.index >= event.t0) & (series.index <= event.exit_date)]
            if len(segment) == 0:
                return None, None
            values = (segment / segment.iloc[0]).copy()
            if event.outcome == "completed":
                values.iloc[-1] = event.exit / event.entry
            end = event.exit_date + pd.Timedelta(days=14) if event.outcome == "completed" else event.exit_date
            return values, end
        idx = days[(days >= event.t0) & (days <= event.exit_date)]
        if len(idx) == 0:
            return None, None
        if mode == "neutral":
            values = bench_2800.reindex(idx).ffill()
            values = values / values.iloc[0]
        elif mode == "zero":
            values = pd.Series(1.0, index=idx)
        else:
            total = (1 - fail_rate) * med_c + fail_rate * med_f
            values = pd.Series(np.linspace(1, 1 + total, len(idx)), index=idx)
        return values, event.exit_date + pd.Timedelta(days=14)

    def simulate(events, mode="neutral", cost_in=0.003, cost_out_c=0.003, cost_out_f=0.003, slot=0.10, maxpos=10):
        ordered = events[events.t0 >= W0].sort_values("t0")
        cash = 1.0
        positions = []
        nav = []
        queue = list(ordered.itertuples())
        cursor = 0
        for day in days:
            kept = []
            for pos in positions:
                if day in pos["v"].index:
                    pos["val"] = pos["amt"] * pos["v"].loc[day]
                if day >= pos["end"]:
                    cash += pos["val"] * (1 - pos["cout"])
                else:
                    kept.append(pos)
            positions = kept
            nav_today = cash + sum(pos["val"] for pos in positions)
            while cursor < len(queue) and queue[cursor].t0 <= day:
                event = queue[cursor]
                cursor += 1
                if len(positions) >= maxpos:
                    continue
                values, end = path_of(event, mode)
                if values is None or len(values) == 0:
                    continue
                amount = min(slot * nav_today, cash)
                if amount <= 0:
                    continue
                cash -= amount
                amount_net = amount * (1 - cost_in)
                cost_out = cost_out_c if event.outcome == "completed" else cost_out_f
                positions.append(
                    dict(v=values, amt=amount_net / values.iloc[0], val=amount_net, end=end, cout=cost_out)
                )
            nav.append(cash + sum(pos["val"] for pos in positions))
        return pd.Series(nav, index=days)

    benches = {"2800": bench_2800[(bench_2800.index >= W0) & (bench_2800.index <= W1)]}
    if author is not None:
        benches["author"] = author[(author.index >= W0) & (author.index <= W1)]

    summary = {name: _stats(series) for name, series in benches.items()}
    runs = {}
    costs = {"30bp": (0.003, 0.003, 0.003), "real": (0.0017, 0.0, 0.0017)}
    for mode in ("neutral", "zero", "obsmix"):
        for cost_name, (cost_in, cost_c, cost_f) in costs.items():
            nav = simulate(universe, mode, cost_in, cost_c, cost_f)
            runs[(mode, cost_name)] = nav
            summary[f"P1_X0_{mode}_{cost_name}"] = _stats(nav)
    priced = simulate(universe[universe.status == "ok"], "neutral")
    runs[("pricedonly", "30bp")] = priced
    summary["P1_X0_pricedonly_30bp"] = _stats(priced)
    wide = universe[
        (universe.status != "ok")
        | (universe.outcome == "failed")
        | ((universe.exit / universe.entry - 1) >= 0.05)
    ]
    lookahead = simulate(wide, "neutral")
    runs[("X5_lookahead", "30bp")] = lookahead
    summary["P1_X5_LOOKAHEAD_neutral_30bp"] = _stats(lookahead)
    slot25 = simulate(universe, "neutral", slot=0.25, maxpos=4)
    runs[("slot25", "30bp")] = slot25
    summary["P1_X0_neutral_30bp_slot25"] = _stats(slot25)

    top3 = universe[universe.status == "ok"].sort_values("ret", ascending=False).head(3)
    dropped_events = simulate(universe.drop(top3.index), "neutral")
    summary["P1_X0_neutral_30bp_dropbest3events"] = _stats(dropped_events)
    print("drop best3 events", top3[["code", "name", "ret"]].values.tolist(), _stats(dropped_events))

    def aligned_raw(left, right):
        idx = left.dropna().index.intersection(right.dropna().index)
        return _raw(left.reindex(idx)), _raw(right.reindex(idx))

    def drop3(left, right):
        """Zero out the three calendar years with the largest excess, then rescore.

        The window length stays the original span, matching the published bars.
        """
        idx = left.dropna().index.intersection(right.dropna().index)
        a = left.reindex(idx).dropna()
        b = right.reindex(idx).dropna()
        yearly = pd.DataFrame({"P": _yearly(a), "B": _yearly(b)}).dropna()
        excess = (yearly.P - yearly.B).sort_values(ascending=False)
        dropped = list(excess.index[:3])
        years = {stamp.year for stamp in dropped}

        def flat(nav):
            rets = nav.pct_change()
            rets.iloc[0] = 0.0
            rets = rets.copy()
            rets.loc[rets.index.year.isin(years)] = 0.0
            return (1 + rets.fillna(0)).cumprod()

        return round(_raw(flat(a))[2] - _raw(flat(b))[2], 3), [stamp.year for stamp in dropped]

    published = [
        (("neutral", "30bp"), "neutral_30bp"),
        (("neutral", "real"), "neutral_real"),
        (("zero", "30bp"), "zero_30bp"),
        (("obsmix", "30bp"), "obsmix_30bp"),
        (("X5_lookahead", "30bp"), "X5_lookahead_30bp"),
        (("slot25", "30bp"), "slot25_30bp"),
    ]
    bar_rows = []
    for key, label in published:
        nav = runs[key]
        for bench_name, bench in benches.items():
            got, base = aligned_raw(nav, bench)
            delta3, dropped_years = drop3(nav, bench)
            bar_rows.append(
                dict(
                    variant=label,
                    bench=bench_name,
                    CAGR=round(got[0], 4),
                    MDD=round(got[1], 4),
                    Calmar=round(got[2], 3),
                    bCalmar=round(base[2], 3),
                    dCalmar=round(got[2] - base[2], 3),
                    dMDD_pp=round((got[1] - base[1]) * 100, 1),
                    dCalmar_drop3=delta3,
                    dropped=json.dumps(dropped_years),
                )
            )
            print(label, bench_name, "dCalmar", round(got[2] - base[2], 3), "drop3", delta3, dropped_years)

    out = paths["out"]
    out.mkdir(parents=True, exist_ok=True)
    # Strategy paths only. Benchmark levels stay out of this file.
    pd.DataFrame({f"{a}_{b}": series for (a, b), series in runs.items()}).to_csv(out / "p1_navs.csv")
    (out / "p1_metrics.json").write_text(json.dumps(summary, indent=1))
    pd.DataFrame(bar_rows).to_csv(out / "p1_bars.csv", index=False)
    print(
        "coverage(window U)",
        round(float(coverage), 3),
        "n_events",
        len(universe),
        "completed",
        int((universe.outcome == "completed").sum()),
        "failed",
        int((universe.outcome == "failed").sum()),
        "pf_est",
        round(float(fail_rate), 3),
        "med_c",
        round(float(med_c), 3),
        "med_f",
        round(float(med_f), 3),
        "med_days",
        med_days,
    )


if __name__ == "__main__":
    main()
