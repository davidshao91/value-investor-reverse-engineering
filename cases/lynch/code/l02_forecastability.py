"""Trailing 3-year growth versus the next 3 years. Run after the caches in docs/data.md exist.

    python cases/lynch/code/l02_forecastability.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

import l01_backtest as m


def main():
    m.load()
    NI, REV = m.NI, m.REV
    rows = []
    for univ in ["SPX", "BROAD"]:
        for y in range(2011, 2022):
            d = m.frame(y, univ).copy()
            for var, S in [("NI", NI), ("REV", REV)]:
                a, b, c = d.index.map(S[y - 3]), d.index.map(S[y]), d.index.map(S[y + 3])
                x = pd.DataFrame({"a": a, "b": b, "c": c, "sic2": (d.sic // 100).values, "stable": d.stable.values}, index=d.index)
                x = x[(x.a > 0) & (x.b > 0) & (x.c > 0)]
                x["gp"] = np.log(x.b / x.a) / 3
                x["gf"] = np.log(x.c / x.b) / 3
                subsets = [("all", x), ("stable", x[x.stable])] if var == "NI" else [("all", x)]
                for sub, z in subsets:
                    if len(z) < 20:
                        continue
                    rho = z.gp.rank().corr(z.gf.rank())
                    q = z.gp >= z.gp.quantile(0.8)
                    hit = (z.gf[q] > z.gf.median()).mean()
                    ind = z.groupby("sic2").gp.transform("median")
                    mae_own = (z.gf - z.gp).abs().mean()
                    mae_ind = (z.gf - ind).abs().mean()
                    mae_mkt = (z.gf - z.gp.median()).abs().mean()
                    beta = np.polyfit(z.gp, z.gf, 1)[0]
                    rows.append(dict(univ=univ, var=var, sub=sub, fy=y, n=len(z), rho=rho, top20_hit=hit,
                                     mae_own=mae_own, mae_ind=mae_ind, mae_mkt=mae_mkt, slope=beta))
    R = pd.DataFrame(rows)
    out = Path(m.OUT)
    R.to_csv(out / "forecastability_by_year.csv", index=False)
    S = R.groupby(["univ", "var", "sub"]).agg(
        years=("fy", "count"), n_med=("n", "median"), rho_mean=("rho", "mean"),
        rho_pos_share=("rho", lambda s: (s > 0).mean()), top20_hit=("top20_hit", "mean"),
        mae_own=("mae_own", "mean"), mae_ind=("mae_ind", "mean"), mae_mkt=("mae_mkt", "mean"),
        slope=("slope", "median")).reset_index()
    S["verdict"] = np.where((S.rho_mean >= 0.10) & (S.rho_pos_share >= 0.70) & (S.top20_hit >= 0.55), "弱可预测", "不可预测→弱代理")
    S.to_csv(out / "forecastability_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(S.round(3).to_string())


if __name__ == "__main__":
    main()
