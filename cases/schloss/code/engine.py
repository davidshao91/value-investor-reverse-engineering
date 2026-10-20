"""Schloss fallen-blue-chip engine. Importing this module does not read data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import pandas as pd, numpy as np
from cases._shared.config import require, schloss_paths

_LOADED = False
F = MEM = P = cal = SPY = IRX = A = cols = ci = last = lastpos = ME = None
DATAEND = pd.Timestamp("2024-12-27")

def load():
    global _LOADED, F, MEM, P, cal, SPY, IRX, A, cols, ci, last, lastpos, ME
    if _LOADED:
        return
    paths = schloss_paths()
    F = pd.read_pickle(require(paths["feat"], "Run s03_feat.py after the price caches exist."))
    MEM = pd.read_pickle(require(paths["members"], "Run s02_members.py first."))
    b = pd.read_pickle(require(paths["yf_bench"], "Place SPY and ^IRX in data/schloss/yf_bench.pkl. See docs/data.md."))
    P = F["P"]; cal = P.index
    SPY = b["SPY"].reindex(cal).ffill(); IRX = b["^IRX"].reindex(cal).ffill() / 100 / 252
    A = {k: F[k].values for k in ["P", "lo3", "hi5", "med3", "bad", "hi1", "n"]}
    cols = list(P.columns); ci = {c: i for i, c in enumerate(cols)}
    last = F["last"]; lastpos = np.array([cal.get_loc(x) if pd.notna(x) else -1 for x in last])
    ME = set(cal.to_series().groupby(cal.to_period("M")).last().values)
    _LOADED = True

def months(d0,d1): return (d1.year-d0.year)*12+(d1.month-d0.month)+(d1.day>=d0.day)-1
def run(entry='v1',exit_='tgt',scale=False,delist='D0',cost=0.001,start='1999-12-31',end='2026-10-16',slots=30,extra_filter=None,pb_exit=None):
    load()
    i0=cal.get_loc(cal[cal>=start][0]); i1=cal.get_loc(cal[cal<=end][-1])
    cash=1.0; pos={}; parks=[]; pend_buy=[]; pend_sell=[]; pend_add=[]; ban={}
    LOG=[]; nav=[]; trades=0.0; npos=[]; cashw=[]; nent=0; ndel=0; nzero=0
    Pm=A['P']
    for i in range(i0,i1+1):
        d=cal[i]
        cash*=1+IRX.iat[i-1] if i>0 else 1
        # delist handling
        for nm in list(pos):
            j=ci[nm]
            if lastpos[j]<i:
                p=pos.pop(nm); lp=Pm[lastpos[j],j]; val=p['sh']*lp; ndel+=1; LOG.append((nm,p['t0'],cal[lastpos[j]],p['cost'],val,'delist'))
                dataend=cal[lastpos[j]]>=DATAEND
                zero=(delist=='D1' and not dataend) or (delist=='D1b' and not dataend and lp<0.3*A['hi1'][lastpos[j],j])
                if zero: val=0; nzero+=1
                else: val*=1-cost; trades+=val
                cash+=p['res']
                if delist=='D2' and not zero and not dataend:
                    parks.append([val/SPY.iat[i],p['t0']+pd.DateOffset(months=48)])
                else: cash+=val
                ban[nm]=d
        for pk in list(parks):
            if d>=pk[1]: v=pk[0]*SPY.iat[i]*(1-cost); cash+=v; trades+=v; parks.remove(pk)
        # execute pending
        for nm,frac in pend_sell:
            if nm not in pos: continue
            j=ci[nm]; px=Pm[i,j]
            if np.isnan(px): continue
            p=pos[nm]; sh=p['sh']*frac; v=sh*px*(1-cost); cash+=v; trades+=sh*px; p['sh']-=sh
            p.setdefault('proc',0); p['proc']+=sh*px
            if frac>=0.999: pos.pop(nm); ban[nm]=d; LOG.append((nm,p['t0'],d,p['cost'],p['proc'],'sell'))
        pend_sell=[]
        for nm in pend_add:
            if nm not in pos: continue
            j=ci[nm]; px=Pm[i,j]; p=pos[nm]
            if np.isnan(px) or p['res']<=1e-12: continue
            amt=min(p['tranche'],p['res']); p['res']-=amt; cash-=amt
            sh=amt*(1-cost)/px; p['sh']+=sh; p['cost']+=amt; p['lastbuy']=px; p['nb']+=1; trades+=amt
        pend_add=[]
        if pend_buy:
            navnow=cash+sum(p['sh']*Pm[i,ci[n]] for n,p in pos.items() if not np.isnan(Pm[i,ci[n]]))+sum(pk[0]*SPY.iat[i] for pk in parks)
            free=cash-sum(p['res'] for p in pos.values())
            for nm,tgt in pend_buy:
                if len(pos)>=slots or nm in pos: continue
                j=ci[nm]; px=Pm[i,j]
                if np.isnan(px): continue
                budget=min(navnow/slots,free)
                if budget<=1e-6: break
                free-=budget
                first=budget/3 if scale else budget
                cash-=first; sh=first*(1-cost)/px; trades+=first; nent+=1
                pos[nm]=dict(sh=sh,cost=first,t0=d,tgt=tgt,lastbuy=px,nb=1,res=budget-first,tranche=budget/3,stage=0)
        pend_buy=[]
        # nav
        v=cash+sum(pk[0]*SPY.iat[i] for pk in parks)
        for n_,p in pos.items():
            px=Pm[i,ci[n_]]
            if np.isnan(px): px=Pm[lastpos[ci[n_]],ci[n_]] if lastpos[ci[n_]]<=i else np.nan
            if np.isnan(px):
                # gap: use last valid
                k=i
                while k>0 and np.isnan(Pm[k,ci[n_]]): k-=1
                px=Pm[k,ci[n_]]
            v+=p['sh']*px
        nav.append(v); npos.append(len(pos)); cashw.append((cash)/v if v>0 else 0)
        # signals on close
        for nm,p in pos.items():
            j=ci[nm]; px=Pm[i,j]
            if np.isnan(px): continue
            avg=p['cost']/max(p['sh'],1e-12)
            mo=months(p['t0'],d)
            if mo>=48: pend_sell.append((nm,1.0)); continue
            if exit_=='tgt':
                if p['tgt'] is not None and px>=p['tgt']: pend_sell.append((nm,1.0)); continue
            elif exit_=='X1':
                lv=[1.5,2,3]
                if p['stage']<3 and px>=lv[p['stage']]*p.get('avg0',avg):
                    p.setdefault('avg0',avg); p['stage']+=1
                    pend_sell.append((nm,1.0 if p['stage']==3 else 1/(4-p['stage']))); continue
            elif exit_=='X3':
                if px>=1.5*avg: pend_sell.append((nm,1.0)); continue
            elif exit_=='pb':
                if pb_exit is not None and pb_exit(nm,d,px,p): pend_sell.append((nm,1.0)); continue
            if scale and p['res']>1e-9 and px<=0.85*p['lastbuy']: pend_add.append(nm)
        if d in ME:
            mem=MEM.get(d) or MEM.get(max(k for k in MEM if k<=d))
            cand=[]
            for nm in mem:
                j=ci.get(nm)
                if j is None or nm in pos: continue
                if nm in ban and months(ban[nm],d)<6: continue
                px=Pm[i,j]
                if np.isnan(px) or A['n'][i,j]<756 or A['bad'][i,j]>0: continue
                lo,hi,md=A['lo3'][i,j],A['hi5'][i,j],A['med3'][i,j]
                near=px<=1.25*lo; fall=px<=0.60*hi
                if entry=='v1': ok=near and fall; key=px/hi
                elif entry=='v1b': ok=fall; key=px/hi
                elif entry=='C3L': ok=near; key=px/lo
                if ok and extra_filter is not None: ok=extra_filter(nm,d,px)
                if ok: cand.append((key,nm,md))
            cand.sort()
            pend_buy=[(nm,md) for _,nm,md in cand]
    s=pd.Series(nav,index=cal[i0:i1+1])
    run.log=LOG
    return s,dict(turnover=trades/ (s.mean()) / (len(s)/252), avg_pos=np.mean(npos), avg_cash=np.mean(cashw), entries=nent, delists=ndel, zeroed=nzero)
