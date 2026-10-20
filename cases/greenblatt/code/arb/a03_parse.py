"""Regex parse of cash consideration and the proxy-date price. Importing does not read filings.

    python cases/greenblatt/code/arb/a03_parse.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

import gzip
import html
import re

import pandas as pd

from cases._shared.config import arb_paths, require

NUM = r"\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{1,4})?)"
CASH = [
    r"(?:right to receive|entitled to receive|will receive|would receive|to receive)\s+(?:an amount (?:in cash )?equal to\s+)?" + NUM + r"(?:\s+per share)?\s*(?:,\s*)?in cash",
    NUM + r"\s+per share in cash",
    NUM + r"\s+in cash(?:,)? (?:per share|for each)",
    r"cash consideration of " + NUM,
    r"merger consideration of " + NUM + r"(?:\s+per share)?(?:\s+in cash)",
]


def clean(b):
    t = b.decode("latin-1", errors="ignore")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = t.replace("\xa0", " ").replace("\u2019", "'")
    return re.sub(r"\s+", " ", t)


def num(s):
    return float(s.replace(",", ""))


def parse(t):
    head = t[:400000]
    cash = None
    ctx = ""
    for p in CASH:
        m = re.search(p, head, re.I)
        if m:
            v = num(m.group(1))
            if 0.05 <= v <= 5000:
                cash = v
                ctx = head[max(0, m.start() - 400):m.end() + 400]
                break
    stockflag = False
    cvr = False
    if cash is not None:
        stockflag = bool(re.search(r"exchange ratio|shares of (?:\w+\s){0,6}(?:common|class a|ordinary) (?:stock|shares)[^.]{0,80}(?:and|plus)|(?:and|plus) (?:\d|\w)+(?:\.\d+)? (?:of a )?shares? of|cash and stock|stock and cash|cash election|stock election|mixed election", ctx, re.I))
        cvr = bool(re.search(r"contingent value right|\bCVR\b", ctx, re.I))
    if len(re.findall(r"exchange ratio", head, re.I)) >= 5 or len(re.findall(r"proxy statement/prospectus", head, re.I)) >= 3:
        stockflag = True
    pp = None
    PDP = r"(?:most recent|latest|last) (?:reasonably )?practicable (?:trading )?(?:date|day)|(?:last|final) (?:full )?trading day (?:immediately )?(?:before|prior to|preceding) the (?:date of (?:this|the) (?:proxy|information|definitive)|(?:printing|mailing|filing) of (?:this|the))|(?:day|date) (?:immediately )?(?:before|prior to|preceding) the date of (?:this|the) (?:proxy|information)|the record date for the (?:special|annual) meeting"
    for m in re.finditer(PDP, t, re.I):
        if re.search(r"(?:expected|intend|anticipate|shall|will be)", t[max(0, m.start() - 60):m.start()], re.I):
            continue
        after = t[m.end():m.end() + 260]
        before = t[max(0, m.start() - 200):m.start()]
        x = re.search(NUM, after)
        if x and re.search(r"clos|sale", after[:x.start()] + before[-120:], re.I):
            v = num(x.group(1))
            if 0.05 <= v <= 5000:
                pp = v
                break
        y = list(re.finditer(NUM, before[-150:]))
        if y and re.search(r"clos|sale", before, re.I) and not re.search(r"announc|prior to the execution", before[-150:], re.I):
            v = num(y[-1].group(1))
            if 0.05 <= v <= 5000:
                pp = v
                break
    un = None
    UNP = r"(?:last|final) (?:full )?trading day (?:immediately )?(?:prior to|before|preceding) (?:the )?(?:\w+ ){0,4}(?:announc|execution|public)|(?:unaffected|undisturbed) (?:share |stock |closing )?price"
    for m in re.finditer(UNP, t, re.I):
        seg = t[max(0, m.start() - 260):m.end() + 300]
        cands = [(abs(x.start() - 260), num(x.group(1))) for x in re.finditer(NUM, seg)]
        cands = [c for c in cands if 0.05 <= c[1] <= 5000 and (cash is None or c[1] != cash)]
        if cands and re.search(r"clos", seg, re.I):
            un = min(cands)[1]
            break
    spac = len(re.findall(r"trust account", t[:300000], re.I)) >= 5 or bool(re.search(r"blank check", t[:50000], re.I))
    return cash, stockflag, cvr, pp, un, spac


def main():
    paths = arb_paths()
    D = pd.read_csv(require(paths["defm14a_events"], "Run a02_fetch.py first."), dtype={"cik": str})
    out = []
    prev_path = paths["parsed"]
    todo = None
    if prev_path.exists():
        prev = pd.read_csv(prev_path, dtype={"cik": str})
        todo = set(prev[prev.cash.notna()].path)
    for _, r in D.iterrows():
        if todo is not None and r.path not in todo:
            out.append(dict(cik=r.cik, company=r.company, date=r.date, path=r.path, fetched=True))
            continue
        fn = paths["docs"] / r.path.split("/")[-1].replace(".txt", ".gz")
        if not fn.exists():
            out.append(dict(cik=r.cik, date=r.date, fetched=False))
            continue
        with gzip.open(fn, "rb") as fh:
            t = clean(fh.read())
        c, s, v, p, u, sp = parse(t)
        out.append(dict(cik=r.cik, company=r.company, date=r.date, path=r.path, fetched=True, cash=c, stock=s, cvr=v, px_pd=p, px_un=u, spac=sp, nchar=len(t)))
    O = pd.DataFrame(out)
    O.to_csv(paths["parsed"], index=False)
    f = O[O.fetched]
    print("fetched", len(f), "cash found", f.cash.notna().sum())


if __name__ == "__main__":
    main()
