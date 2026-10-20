"""Metrics for the full-investment diagnostic.

    python cases/lynch/code/l05_metrics_diag.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l03_metrics import score


def main():
    score("monthly_returns_fullinvest_diag.csv", "metrics_fullinvest_diag.csv", "calendar_years_fullinvest_diag.csv")


if __name__ == "__main__":
    main()
