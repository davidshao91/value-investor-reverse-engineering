"""Spin-off slot backtest. Run from the repo root:

    python cases/greenblatt/code/g04_backtest.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np
import pandas as pd

from cases._shared.config import greenblatt_paths, require
from cases._shared.rea_metrics import bench as load_bench
from cases._shared.rea_metrics import st, yr

EV = RET = spy = BM = None
W0 = pd.Period("2000-01", "M")
W1 = pd.Period("2026-09", "M")
months = pd.period_range(W0, W1, freq="M")


def prepare():
    global EV, RET, spy, BM
    paths = greenblatt_paths()
    E = pd.read_csv(require(paths["events_flags"], "Run g03_events.py first."), parse_dates=["first12b", "first_periodic"])
    C = E[E.completed & ~E.pre10k].copy()
    px = pd.read_pickle(require(paths["px_events"], "Run g03_events.py first."))
    ADJ = px["Adj Close"]
    CL = px["Close"]
    ADJ.index = ADJ.index.to_period("M")
    CL.index = CL.index.to_period("M")
    ADJ = ADJ.groupby(level=0).last()
    CL = CL.groupby(level=0).last()
    RET = ADJ.pct_change(fill_method=None)
    spy = RET["SPY"]
    BM = load_bench()
    rows = []
    for _, e in C.iterrows():
        t = e.ticker
        status = "missing"
        first = None
        if isinstance(t, str) and t in ADJ.columns and ADJ[t].notna().any():
            first = ADJ[t].first_valid_index()
            fp = e.first_periodic.to_period("M")
            if first > fp + 9:
                status = "mismatch_late"
            elif first < e.first12b.to_period("M") - 3:
                status = "mismatch_early"
            else:
                status = "priced"
        if status == "priced":
            entry = first + 1
        else:
            entry = e.first_periodic.to_period("M") + 1
        px3 = None
        if status == "priced":
            px3 = CL[t].get(entry, np.nan)
            if not (px3 >= 3):
                status = "priced_lt3_or_nan"
        rows.append(dict(cik=e.cik, company=e.company, ticker=t, first12b=e.first12b.date(), entry=str(entry), status=status, entry_close=px3))
    EV = pd.DataFrame(rows)
    EV["entryP"] = pd.PeriodIndex(EV.entry, freq="M")
    paths["out"].mkdir(parents=True, exist_ok=True)
    EV.to_csv(paths["out"] / "event_panel.csv", index=False)
    print(EV.status.value_counts())


def path(ev, H, dead):
    ms = [m for m in pd.period_range(ev.entryP + 1, ev.entryP + H, freq="M") if m <= W1]
    if ev.status == "priced":
        r = RET[ev.ticker].reindex(ms).fillna(0.0).values.copy()
    elif dead == "spy":
        r = spy.reindex(ms).fillna(0.0).values.copy()
    else:
        r = np.zeros(len(ms))
        if dead == "dead" and len(ms) == H:
            r[-1] = -1.0
    return ms, r


def sim(evs, H, N, dead, cost, cap=True, placebo_ret=None):
    evs = evs.sort_values("entryP")
    by = {}
    for _, ev in evs.iterrows():
        by.setdefault(ev.entryP, []).append(ev)
    cash = 1.0
    pos = []
    out = {}
    for m in months:
        nv = cash + sum(p[0] for p in pos) if cap else 0
        for ev in by.get(m - 1, []):
            if ev.status not in ("priced", "missing", "mismatch_late", "mismatch_early"):
                continue
            if dead == "drop" and ev.status != "priced":
                continue
            if cap and len(pos) >= N:
                continue
            ms, r = path(ev, H, dead if ev.status != "priced" else None) if placebo_ret is None else placebo_ret(ev, H)
            if len(ms) == 0:
                continue
            if cap:
                w = min(nv / N, cash)
                if w <= 1e-9:
                    continue
                cash -= w
                cash -= w * cost
                pos.append([w, ms, r, 0])
            else:
                pos.append([None, ms, r, 0])
        if not cap:
            act = [p for p in pos]
            if act:
                rr = np.mean([p[2][p[3]] for p in act])
                for p in act:
                    p[3] += 1
                out[m] = rr
            else:
                out[m] = 0.0
            pos = [p for p in pos if p[3] < len(p[2])]
            continue
        v0 = cash + sum(p[0] for p in pos)
        for p in pos:
            p[0] *= 1 + p[2][p[3]]
            p[3] += 1
        keep = []
        for p in pos:
            if p[3] >= len(p[2]):
                cash += p[0] * (1 - cost)
            else:
                keep.append(p)
        pos = keep
        v1 = cash + sum(p[0] for p in pos)
        out[m] = v1 / v0 - 1
    return pd.Series(out)


def main():
    prepare()
    paths = greenblatt_paths()
    res = {}
    for H in (12, 24):
        for dead in ("spy", "cash", "dead", "drop"):
            for c in (10, 30, 100):
                res[f"G1-S{H}|{dead}|{c}"] = sim(EV, H, 20, dead, c / 1e4)
    for dead in ("spy", "cash", "dead", "drop"):
        res[f"G1-EW12|{dead}|0"] = sim(EV, 12, 20, dead, 0, cap=False)
    M = pd.DataFrame(res)
    M.index = M.index.astype(str)
    M.to_csv(paths["out"] / "monthly_returns.csv")
    M.index = pd.PeriodIndex(M.index, freq="M")
    B = BM.reindex(M.index)
    rows = []
    for col in M.columns:
        r = M[col]
        cagr, d, k = st(r)
        row = dict(rule=col, CAGR=cagr, MDD=d, Calmar=k)
        for bn, tag in (("SPY", "SPY"),) + ((("author", "author"),) if "author" in B.columns else ()):
            b = B[bn]
            _bc, bd, bk = st(b)
            row[f"dCal_{tag}"] = k - bk
            row[f"dMDDpp_{tag}"] = (d - bd) * 100
            ex = yr(r) - yr(b)
            drop = ex.nlargest(3).index
            keep = ~r.index.year.isin(drop)
            row[f"dCal_drop3_{tag}"] = st(r[keep])[2] - st(b[keep])[2]
            s08 = r.index >= pd.Period("2008-01", "M")
            row[f"dCal_from2008_{tag}"] = st(r[s08])[2] - st(b[s08])[2]
            row[f"best3_{tag}"] = ",".join(map(str, drop))
            row[f"PASS_{tag}"] = bool(
                (row[f"dCal_{tag}"] >= 0.05) and (row[f"dMDDpp_{tag}"] >= -5)
                and (row[f"dCal_drop3_{tag}"] > 0) and (row[f"dCal_from2008_{tag}"] >= 0.05)
            )
        rows.append(row)
    T = pd.DataFrame(rows)
    T.to_csv(paths["out"] / "metrics.csv", index=False)
    for bn in [c for c in ("SPY", "author") if c in B.columns]:
        print(bn, [round(x, 3) for x in st(B[bn])], "from2008", [round(x, 3) for x in st(B[bn][B.index >= pd.Period("2008-01", "M")])])
    pd.set_option("display.width", 300)
    pd.set_option("display.max_columns", 40)
    print(T.round(3).to_string())
    Y = pd.DataFrame({c: yr(M[c]) for c in M.columns if c.endswith("|10")})
    Y["SPY"] = yr(B["SPY"])
    if "author" in B.columns:
        Y["author"] = yr(B["author"])
    Y.to_csv(paths["out"] / "calendar_years.csv")
    print(Y.round(3)[["G1-S12|spy|10", "G1-S12|dead|10", "G1-S12|drop|10", "SPY"]].to_string())


if __name__ == "__main__":
    main()
