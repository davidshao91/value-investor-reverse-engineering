"""Lynch-style GARP proxies.

Run from the repo root:

    python cases/lynch/code/l01_backtest.py

Inputs are documented in docs/data.md. Nothing is fetched at import time.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import json, glob, os, time, warnings
import numpy as np
import pandas as pd
import requests

from cases._shared.config import lynch_paths, edgar_headers, require

warnings.filterwarnings("ignore")

P = NI = REV = FLT = T2C = C2T = SIC = C = A = S = HIST = OUT = SICF = SX = UA = F = None

def frame_series(tag, per):
    fn = F / f"{tag}_{per}.json"
    if not fn.exists():
        return pd.Series(dtype=float)
    d = pd.DataFrame(json.loads(fn.read_text()))
    if d.empty:
        return pd.Series(dtype=float)
    return d.sort_values("end").drop_duplicates("cik", keep="last").set_index("cik")["val"].astype(float)

def first(*ss):
    o = None
    for s in ss:
        o = s if o is None else o.combine_first(s)
    return o

def load():
    global P, NI, REV, FLT, T2C, C2T, SIC, C, A, S, HIST, OUT, SICF, SX, UA, F
    paths = lynch_paths()
    OUT = str(paths["out"]) + "/"
    os.makedirs(paths["out"], exist_ok=True)
    F = require(paths["frames"], "Download SEC XBRL frames into data/xbrl/frames/.")
    P = pd.read_pickle(require(paths["panel"], "Build data/xbrl/panel_fund.pkl."))
    tm = pd.read_csv(require(paths["tickers"], "Need data/xbrl/tickers_map.csv with columns cik, yf."))
    tm = tm.drop_duplicates("cik")
    T2C = dict(zip(tm.yf, tm.cik)); C2T = dict(zip(tm.cik, tm.yf))
    sic = json.loads(require(paths["sic"], "Need data/xbrl/sic.json.").read_text())
    SIC = {int(k): pd.to_numeric(v, errors="coerce") for k, v in sic.items()}
    px_files = sorted(glob.glob(paths["prices_glob"]))
    if not px_files:
        raise SystemExit(f"No monthly price pickles at {paths['prices_glob']}. See docs/data.md.")
    px = pd.concat([pd.read_pickle(f) for f in px_files], axis=1, sort=True)
    C, A = px["Close"], px["Adj Close"]
    S = px["Stock Splits"].fillna(0)
    for X in (C, A, S):
        X.index = pd.to_datetime(X.index).to_period("M")
    S = S.groupby(level=0).sum()
    C = C[~C.index.duplicated(keep="last")]
    A = A[~A.index.duplicated(keep="last")]
    HIST = pd.read_csv(require(paths["spx_hist"], "Need data/spx/hist.csv."), parse_dates=["date"]).sort_values("date")
    float_dir = paths["float_dir"]
    FLT = {}
    for y in range(2012, 2026):
        fp = float_dir / f"float_CY{y}Q2I.json"
        if not fp.exists():
            raise SystemExit(f"Missing {fp}. See docs/data.md.")
        FLT[y] = pd.DataFrame(json.loads(fp.read_text())["data"]).drop_duplicates("cik", keep="last").set_index("cik")["val"].astype(float)
    NI = {y: frame_series("NetIncomeLoss", f"CY{y}") for y in range(2008, 2025)}
    REV = {y: first(frame_series("Revenues", f"CY{y}"), frame_series("RevenueFromContractWithCustomerExcludingAssessedTax", f"CY{y}"), frame_series("SalesRevenueNet", f"CY{y}")) for y in range(2008, 2025)}
    UA = edgar_headers()
    SICF = paths["sic_extra"]
    SX = json.loads(SICF.read_text()) if SICF.exists() else {}

def members(dt):
    row = HIST[HIST.date <= dt].iloc[-1]
    return set(x.strip().upper().replace(".", "-") for x in row.tickers.split(","))

def sf(t, after):
    s = S[t][S.index > after]
    s = s[s > 0]
    return float(np.prod(s.values)) if len(s) else 1.0

def get_sic(c):
    if c in SIC and not np.isnan(SIC[c]): return SIC[c]
    k=str(c)
    if k not in SX:
        try:
            j=requests.get(f"https://data.sec.gov/submissions/CIK{c:010d}.json",headers=UA,timeout=30).json(); SX[k]=j.get("sic") or ""
        except Exception: SX[k]=""
        time.sleep(0.12)
    return pd.to_numeric(SX[k],errors="coerce")

_FC={}
def frame(y,univ):
    k=(y,univ)
    if k not in _FC: _FC[k]=_frame(y,univ)
    return _FC[k]
def _frame(y,univ):
    f0=pd.Period(f"{y+1}-06","M")
    d=P[P.fy==y][["cik","eq","debt","shares"]].copy()
    d["ni"]=d.cik.map(NI[y]); d["ni3"]=d.cik.map(NI[y-3]); d["rev"]=d.cik.map(REV[y]); d["rev3"]=d.cik.map(REV[y-3])
    d["yf"]=d.cik.map(C2T)
    if univ=="ALL":
        d["mcap"]=d.cik.map(FLT[y+1]); d=d[d.mcap>=1e9]
        d["priced"]=d.yf.isin(C.columns)&d.yf.map(lambda t: t in C.columns and pd.notna(C.at[f0,t]) if isinstance(t,str) else False)
    else:
        d=d[d.yf.isin(C.columns)].copy(); d["p"]=[C.at[f0,t] for t in d.yf]; d=d[d.p.notna()&d.shares.gt(0)]
        d["mcap"]=d.p*d.shares*[sf(t,pd.Period(f"{y}-12","M")) for t in d.yf]; d["priced"]=True
        if univ=="SPX":
            m=members(pd.Timestamp(f"{y+1}-06-30")); d=d[d.yf.isin(m)]
        else: d=d[d.mcap>=1e9]
    d["sic"]=[SIC.get(c,np.nan) if univ!="ALL" else np.nan for c in d.cik]
    if univ!="ALL": d=d[d.sic.notna()&~d.sic.between(6000,6799)]
    d["pe"]=np.where(d.ni>0,d.mcap/d.ni,np.nan)
    d["g"]=np.where((d.ni>0)&(d.ni3>0),(d.ni/d.ni3)**(1/3)-1,np.nan)
    d["gr"]=np.where((d.rev>0)&(d.rev3>0),(d.rev/d.rev3)**(1/3)-1,np.nan)
    gy=[np.log(d.cik.map(NI[y-i])/d.cik.map(NI[y-i-1])) for i in range(3)]
    G=pd.concat(gy,axis=1); allpos=(G>0).all(axis=1); sd=G.std(axis=1)
    elig=d.g.between(0.10,0.50)&allpos
    d["stable"]=allpos&(sd<=sd[elig].median())
    d["peg"]=d.pe/(100*d.g); d["de"]=np.where(d["eq"]>0,d["debt"]/d["eq"],np.nan)
    return d.set_index("cik")

def finfilter_all(d,ciks):
    return [c for c in ciks if not (6000<=get_sic(c)<=6799) and not np.isnan(get_sic(c))]

def select(rule,d,prev,univ):
    ok_de=d.de<1; N=50
    def fin(ix):  # ALL universe: lazily drop financials / unknown SIC among candidates
        return finfilter_all(d,list(ix)) if univ=="ALL" else list(ix)
    if rule=="L-PEG":
        keep=d[(d.index.isin(prev))&(d.peg<1.5)&d.g.between(0.10,0.50)&(d.de<1)]
        keep=fin(keep.index)[:N]
        cand=d[(d.peg<1)&d.g.between(0.10,0.50)&ok_de&~d.index.isin(keep)].sort_values("peg")
        add=[]; 
        for c in cand.index:
            if len(keep)+len(add)>=N: break
            if fin([c]): add.append(c)
        return keep+add
    if rule=="L-PEG-STABLE":
        keep=d[(d.index.isin(prev))&(d.peg<1.5)&d.g.between(0.10,0.50)&(d.de<1)&d.stable]
        keep=fin(keep.index)[:N]
        cand=d[(d.peg<1)&d.g.between(0.10,0.50)&ok_de&d.stable&~d.index.isin(keep)].sort_values("peg")
        add=[]
        for c in cand.index:
            if len(keep)+len(add)>=N: break
            if fin([c]): add.append(c)
        return keep+add
    if rule=="L-FG":
        cand=d[(d.gr>=0.20)&(d.g>=0.20)&(d.pe<=40)&ok_de].sort_values("gr",ascending=False)
    elif rule=="A_lowPE": cand=d[d.pe>0].sort_values("pe")
    elif rule=="B_highG": cand=d[d.g.between(0.10,0.50)].sort_values("g",ascending=False)
    elif rule=="EW": return fin(d.index)
    out=[]
    for c in cand.index:
        if len(out)>=N: break
        if fin([c]): out.append(c)
    return out

RULES=["L-PEG","L-PEG-STABLE","L-FG","A_lowPE","B_highG","EW"]
def run(univ, cost_bp, dead="cash", cap=True):
    navs={}; logs=[]
    for rule in RULES:
        prev=[]; wold=pd.Series(dtype=float); rets=[]
        for y in range(2011,2025):
            f0=pd.Period(f"{y+1}-06","M"); f1=pd.Period(f"{y+2}-06","M")
            if f0>A.index[-1]: break
            d=frame(y,univ); sel=select(rule,d,prev,univ); prev=sel
            n=len(sel); N=(50 if rule!="EW" else max(n,1)) if cap else max(n,1)
            w=pd.Series(1.0/N,index=sel) if n else pd.Series(dtype=float)
            allix=w.index.union(wold.index); to=(w.reindex(allix).fillna(0)-wold.reindex(allix).fillna(0)).abs().sum()
            to+=abs((1-w.sum())-(1-wold.sum())) if len(wold) else abs(1-w.sum())
            cost=cost_bp/1e4*to
            end=min(f1,A.index[-1]); rng=A.loc[f0:end]
            rel={}
            for c in sel:
                t=C2T.get(c)
                if isinstance(t,str) and t in rng.columns and pd.notna(rng[t].iloc[0]):
                    s=rng[t]/rng[t].iloc[0]
                    if dead=="zero" and s.notna().sum()<len(s): s=s.where(s.index<=s.last_valid_index(),0.0)
                    rel[c]=s.ffill()
                else:
                    rel[c]=pd.Series(0.0 if dead=="zero" else 1.0,index=rng.index); rel[c].iloc[0]=1.0
            Rl=pd.DataFrame(rel) if rel else pd.DataFrame(index=rng.index)
            v=(Rl.mul(w.reindex(Rl.columns),axis=1).sum(axis=1)+(1-w.sum()))
            r=(v/v.shift(1)-1).iloc[1:]; r.iloc[0]=(1+r.iloc[0])*(1-cost)-1
            rets.append(r)
            wold=(Rl.iloc[-1]*w.reindex(Rl.columns)) ; tot=wold.sum()+(1-w.sum()); wold=wold/tot if tot>0 else wold
            unp=sum(1 for c in sel if not (isinstance(C2T.get(c),str) and C2T.get(c) in A.columns and pd.notna(A.at[f0,C2T.get(c)])))
            logs.append(dict(univ=univ,rule=rule,form=str(f0),n_univ=len(d),n_sel=n,unpriced=unp,turnover=round(to,3),
                med_pe=float(d.loc[sel,"pe"].median()) if n else np.nan,med_g=float(d.loc[sel,"g"].median()) if n else np.nan,
                names=",".join(str(C2T.get(c,c)) for c in sel[:12])))
        navs[rule]=pd.concat(rets)
    json.dump(SX, open(SICF, "w"))
    return pd.DataFrame(navs),pd.DataFrame(logs)

def main():
    load()

    allr=[]; alll=[]
    for univ in ["SPX","BROAD","ALL"]:
        for cost in [10,30]:
            for dead in (["cash","zero"] if univ=="ALL" else ["cash"]):
                r,l=run(univ,cost,dead); r.columns=[f"{univ}|{cost}|{dead}|{c}" for c in r.columns]; allr.append(r)
                if cost==10: alll.append(l.assign(dead=dead))
                print(univ,cost,dead,"done",flush=True)
    pd.concat(allr,axis=1).to_csv(OUT+"monthly_returns.csv"); pd.concat(alll).to_csv(OUT+"selection_log.csv",index=False)

if __name__ == "__main__":
    main()
