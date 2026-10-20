"""Paths and SEC request settings.

Scripts are meant to be started from the repository root, for example:

    python cases/lynch/code/l01_backtest.py

Fetched caches live under ``data/`` (gitignored). See ``docs/data.md``.
"""
from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


ROOT = repo_root()
DATA = Path(os.environ.get("VIRE_DATA", ROOT / "data")).expanduser()

# Optional. Columns: date, nav. Not shipped with the repo.
AUTHOR_BENCHMARK = Path(
    os.environ.get("VIRE_AUTHOR_BENCH", DATA / "private" / "author_benchmark.csv")
).expanduser()


def edgar_user_agent() -> str:
    ua = os.environ.get("EDGAR_USER_AGENT", "").strip()
    if not ua or "example.com" in ua.lower():
        raise SystemExit(
            "Set EDGAR_USER_AGENT to a real contact string before calling SEC EDGAR.\n"
            "Example: export EDGAR_USER_AGENT='Your Name you@domain.com'"
        )
    return ua


def edgar_headers() -> dict:
    return {"User-Agent": edgar_user_agent(), "Accept-Encoding": "gzip, deflate"}


def _case(name: str) -> Path:
    return ROOT / "cases" / name


def lynch_paths() -> dict:
    case = _case("lynch")
    xbrl = DATA / "xbrl"
    return {
        "case": case,
        "out": case / "out",
        "xbrl": xbrl,
        "frames": xbrl / "frames",
        "panel": xbrl / "panel_fund.pkl",
        "tickers": xbrl / "tickers_map.csv",
        "sic": xbrl / "sic.json",
        "sic_extra": xbrl / "sic_extra.json",
        "float_dir": DATA / "lynch" / "float",
        "prices_glob": str(DATA / "prices" / "monthly" / "batch_*.pkl"),
        "spx_hist": DATA / "spx" / "hist.csv",
    }


def greenblatt_paths() -> dict:
    case = _case("greenblatt")
    cache = DATA / "greenblatt"
    return {
        "case": case,
        "out": case / "out",
        "cache": cache,
        "idx": cache / "idx",
        "subs": cache / "subs",
        "events_raw": cache / "events_raw.csv",
        "events_flags": cache / "events_flags.csv",
        "px_events": cache / "px_events.pkl",
        "prices_glob": str(DATA / "prices" / "monthly" / "batch_*.pkl"),
    }


def arb_paths() -> dict:
    """Cash-merger EDGAR cache. Code lives in cases/greenblatt/code/arb/."""
    cache = DATA / "greenblatt" / "arb"
    out = _case("greenblatt") / "out"
    return {
        "cache": cache,
        "idx": cache / "idx",
        "docs": cache / "docs",
        "subs": cache / "subs",
        "out": out,
        "defm14a_events": cache / "defm14a_events.csv",
        "parsed": cache / "parsed.csv",
        "events_cash": cache / "events_cash.csv",
        "events_guarded": cache / "events_cash_guarded.csv",
        "events_final": cache / "events_final.csv",
        "px_broken": cache / "px_broken.pkl",
    }


def buffett_paths() -> dict:
    case = _case("buffett")
    cache = DATA / "buffett"
    xbrl = DATA / "xbrl"
    return {
        "case": case,
        "out": case / "out",
        "cache": cache,
        "panel": xbrl / "panel_fund.pkl",
        "tickers": xbrl / "tickers_map.csv",
        "sic": xbrl / "sic.json",
        "prices_glob": str(DATA / "prices" / "monthly" / "*.pkl"),
        "float_glob": str(cache / "float" / "*Q2I.json"),
        "buybacks": cache / "buyback_frames.csv",
        "arb_idx": DATA / "greenblatt" / "arb" / "idx",
        "density": cache / "density_wide_2009plus.csv",
        "candidates": cache / "b1_candidates_wide.csv",
        "universe": cache / "U_wide.pkl",
    }


def schloss_paths() -> dict:
    case = _case("schloss")
    cache = DATA / "schloss"
    return {
        "case": case,
        "out": case / "out",
        "cache": cache,
        "frames": cache / "frames",
        "finsaber": cache / "finsaber_sp500.pkl",
        "yf_adj": cache / "yf_adj.pkl",
        "yf_close": cache / "yf_close.pkl",
        "yf_bench": cache / "yf_bench.pkl",
        "spx_hist": DATA / "spx" / "hist.csv",
        "px": cache / "px.pkl",
        "px_src": cache / "px_src.csv",
        "members": cache / "members_me.pkl",
        "feat": cache / "feat.pkl",
        "xbrl_q": cache / "xbrl_q.pkl",
        "rawclose": cache / "rawclose.pkl",
        "company_tickers": cache / "company_tickers.json",
        "runs_v1": cache / "runs_v1.pkl",
        "runs_v2": cache / "runs_v2.pkl",
        "ew_nav": case / "out" / "ew_covered_nav.csv",
    }


def require(path: Path, hint: str) -> Path:
    if not Path(path).exists():
        raise SystemExit(f"Missing {path}\n{hint}\nSee docs/data.md.")
    return Path(path)
