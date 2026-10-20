"""Build a quarterly book-value panel from XBRL frames.

    python cases/schloss/code/s08_xbrl.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import json

import numpy as np
import pandas as pd

from cases._shared.config import require, schloss_paths


def norm(s):
    return s.replace(".", "-").upper().strip()


def main():
    paths = schloss_paths()
    rows = []
    files = list(paths["frames"].glob("*.json"))
    if not files:
        raise SystemExit(f"No frames in {paths['frames']}. Run s07_fetch.py first.")
    for fn in files:
        c = fn.name.split("_CY")[0]
        j = json.loads(fn.read_text())
        for d in j["data"]:
            rows.append((c, d["cik"], d["end"], d["val"]))
    X = pd.DataFrame(rows, columns=["c", "cik", "end", "val"])
    X["end"] = pd.to_datetime(X.end)
    W = X.pivot_table(index=["cik", "end"], columns="c", values="val", aggfunc="last").reset_index()
    W["sh"] = W["EntityCommonStockSharesOutstanding"].fillna(W["CommonStockSharesOutstanding"])
    W["debt"] = W["LongTermDebt"]
    alt = W[["LongTermDebtNoncurrent", "LongTermDebtCurrent"]].sum(axis=1, min_count=1)
    W["debt"] = W["debt"].fillna(alt)
    W["EQ"] = W["StockholdersEquity"]
    W["de_ok"] = np.where(W.debt.notna(), W.debt / W.EQ < 1, (W.Liabilities / W.EQ < 1))
    W.loc[~(W.EQ > 0), "de_ok"] = False
    W["bps"] = W.EQ / W.sh
    W["avail"] = W.end + pd.Timedelta(days=90)
    tk = json.loads(require(paths["company_tickers"], "Run s07_fetch.py to save company_tickers.json.").read_text())
    m = {}
    for v in tk.values():
        m.setdefault(v["cik_str"], []).append(norm(v["ticker"]))
    W["tickers"] = W.cik.map(m)
    W = W.dropna(subset=["tickers"]).explode("tickers").rename(columns={"tickers": "tk"})
    W = W[(W.sh > 0) & np.isfinite(W.bps)]
    W[["tk", "cik", "end", "avail", "EQ", "sh", "bps", "debt", "de_ok"]].to_pickle(paths["xbrl_q"])
    print(len(W), W.tk.nunique())
    f = pd.read_pickle(require(paths["finsaber"], "Need data/schloss/finsaber_sp500.pkl."))
    f["symbol"] = f.symbol.map(norm)
    f["date"] = pd.to_datetime(f.date)
    F = f.pivot_table(index="date", columns="symbol", values="close", aggfunc="last")
    Y = pd.read_pickle(require(paths["yf_close"], "Need data/schloss/yf_close.pkl."))
    Y.columns = [norm(c) for c in Y.columns]
    Y = Y.loc[:, ~Y.columns.duplicated()]
    Y.index = pd.to_datetime(Y.index)
    Y = Y[Y.index > "2024-12-31"]
    R = pd.concat([F, Y.reindex(columns=F.columns.union(Y.columns))]).groupby(level=0).last()
    R.to_pickle(paths["rawclose"])
    print(R.shape)


if __name__ == "__main__":
    main()
