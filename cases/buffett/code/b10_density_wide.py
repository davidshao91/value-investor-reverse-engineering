"""Wide-universe density: cheap balance sheet intersected with buybacks or going-private filings.

    python cases/buffett/code/b10_density_wide.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import glob
import json

import numpy as np
import pandas as pd

from cases._shared.config import buffett_paths, require


def main():
    paths = buffett_paths()
    P = pd.read_pickle(require(paths["panel"], "Need data/xbrl/panel_fund.pkl."))
    P = P[(P.fy >= 2009) & (P.fy <= 2024)].copy()
    P["cik"] = P.cik.astype(int)
    fl = []
    files = glob.glob(paths["float_glob"])
    if not files:
        raise SystemExit(f"No float frames at {paths['float_glob']}. See docs/data.md.")
    for f in files:
        j = json.loads(Path(f).read_text())
        y = int(f.split("CY")[1][:4])
        for d in j["data"]:
            fl.append((int(d["cik"]), y, d["val"], d["end"]))
    FL = pd.DataFrame(fl, columns=["cik", "cy", "float", "end"]).sort_values("end").drop_duplicates(["cik", "cy"], keep="last")
    P["cy"] = P.fy + 1
    P = P.merge(FL[["cik", "cy", "float"]], on=["cik", "cy"], how="left")
    tm = pd.read_csv(require(paths["tickers"], "Need data/xbrl/tickers_map.csv."))
    px_files = sorted(glob.glob(paths["prices_glob"]))
    if not px_files:
        raise SystemExit(f"No monthly prices at {paths['prices_glob']}.")
    px = pd.concat([pd.read_pickle(f)["Close"] for f in px_files], axis=1)
    px = px.loc[:, ~px.columns.duplicated()]
    px.index = pd.to_datetime(px.index)
    jun = {y: px[px.index.to_period("M") == pd.Period(f"{y}-06", "M")].iloc[-1] for y in range(2010, 2026) if (px.index.to_period("M") == pd.Period(f"{y}-06", "M")).any()}
    t1 = tm.dropna(subset=["yf"]).drop_duplicates("cik").set_index("cik").yf

    def pmc(r):
        t = t1.get(r.cik)
        s = r.shares if pd.notna(r.shares) else r.sh_w
        if t is None or r.cy not in jun or pd.isna(s):
            return np.nan, np.nan
        p = jun[r.cy].get(t, np.nan)
        return p, p * s

    v = P.apply(pmc, axis=1, result_type="expand")
    P["px"] = v[0]
    P["mc_px"] = v[1]
    P["mc"] = P.mc_px.where(P.mc_px.notna(), P["float"])
    P["mc_src"] = np.where(P.mc_px.notna(), "px", np.where(P["float"].notna(), "float", "none"))
    sic = json.loads(require(paths["sic"], "Need data/xbrl/sic.json.").read_text())
    P["sic"] = P.cik.astype(str).map(sic)
    P["sicn"] = pd.to_numeric(P.sic, errors="coerce")
    fin = (P.sicn >= 6000) & (P.sicn <= 6799)
    classified = P.ca.notna() & P.cl.notna()
    P["nonfin"] = ~fin & (P.sicn.notna() | classified)
    BB = pd.read_csv(require(paths["buybacks"], "Need data/buffett/buyback_frames.csv."))
    P = P.merge(BB[["cik", "fy", "bb_amt"]], on=["cik", "fy"], how="left")
    P = P.sort_values(["cik", "fy"])
    s = P.shares.where(P.shares.notna(), P.sh_w)
    P["s"] = s
    P["s_prev"] = P.groupby("cik").s.shift(1)
    P["fy_prev"] = P.groupby("cik").fy.shift(1)
    P["sh_down"] = (P.fy_prev == P.fy - 1) & (P.s / P.s_prev - 1 <= -0.03)
    pz = []
    idx_files = list(paths["arb_idx"].glob("*.tsv"))
    if not idx_files:
        raise SystemExit(f"No EDGAR index at {paths['arb_idx']}. Run cases/greenblatt/code/arb/a01_idx.py.")
    for f in idx_files:
        for line in f.read_text().splitlines():
            p = line.split("\t")
            if len(p) == 5 and p[0] in ("SC 13E3", "SC TO-T"):
                pz.append((int(p[2]), p[3]))
    PZ = pd.DataFrame(pz, columns=["cik", "date"])
    PZ["date"] = pd.to_datetime(PZ.date)

    def haspz(r):
        b = pd.Timestamp(f"{r.cy}-06-30")
        d = PZ.date[PZ.cik == r.cik]
        return bool(((d > b - pd.DateOffset(months=12)) & (d <= b)).any())

    U = P[P.nonfin & (P.mc >= 5e7) & (P.mc <= 5e9) & ((P.px >= 3) | P.px.isna())].copy()
    U["nc_mkt"] = U.nc_cons / U.mc
    U["ncav"] = U.ca - U.liab
    U["p_ncav"] = U.mc / U.ncav
    U["bb"] = (U.bb_amt / U.mc >= 0.01) | U.sh_down
    U["ev"] = U.mc + U.debt.fillna(0) - U.cash.fillna(0) - U.sti.fillna(0)
    U["ev_ebit"] = U.ev / U.ebit
    U["cheap"] = (U.nc_mkt > 1) | ((U.ncav > 0) & (U.p_ncav < 2 / 3))
    cand = U[U.cheap].copy()
    cand["pz"] = cand.apply(haspz, axis=1)
    U = U.merge(cand[["cik", "fy", "pz"]], on=["cik", "fy"], how="left")
    U["pz"] = U.pz.fillna(False).astype(bool)
    U["b1"] = U.cheap & (U.bb | U.pz)
    U["b1ev"] = (U.ebit > 0) & (U.ev_ebit > 0) & (U.ev_ebit <= 5) & U.bb
    T = U.groupby("fy").agg(
        univ=("cik", "size"),
        univ_px=("mc_src", lambda x: (x == "px").sum()),
        univ_float=("mc_src", lambda x: (x == "float").sum()),
        cheap=("cheap", "sum"),
        nc_gt1=("nc_mkt", lambda x: (x > 1).sum()),
        b1=("b1", "sum"),
        pz=("pz", "sum"),
        b1ev=("b1ev", "sum"),
    )
    paths["cache"].mkdir(parents=True, exist_ok=True)
    T.to_csv(paths["density"])
    print(T.to_string())
    print("years b1>=5:", (T.b1 >= 5).sum(), "/", len(T), " b1ev>=5:", (T.b1ev >= 5).sum())
    cols = ["cik", "fy", "cy", "mc", "mc_src", "px", "nc_mkt", "p_ncav", "ev_ebit", "bb_amt", "sh_down", "pz", "b1", "b1ev"]
    U[U.b1 | U.b1ev][cols].to_csv(paths["candidates"], index=False)
    U.to_pickle(paths["universe"])


if __name__ == "__main__":
    main()
