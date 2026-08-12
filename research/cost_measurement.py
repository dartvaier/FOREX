"""
H07 re-evaluation — real execution-cost measurement (docs/27 §5 rec. 1-2).

Measures the real EURUSD M15 spread from the dataset (MT5 'spread'
column, in points; 5-digit EURUSD: 1 point = 0.1 pip) with focus on
the weekly-open bar (H07 entry point).

Reference round-trip cost = spread_pips + 2*slippage_pips +
commission_pips, where commission_pips = 7.0 USD/lot / 10 USD per
pip per lot = 0.7 pips (baseline: 2.0 + 1.0 + 0.7 = 3.7 pips, docs/21).

Outputs a JSON report under research/reports/.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pandas as pd

PIP_SIZE = 0.0001  # EURUSD 5-digit
POINTS_PER_PIP = 10
SLIPPAGE_PIPS = 0.5
COMMISSION_PIPS = 0.7  # 7.0 USD/lot round-trip / 10 USD per pip per lot


def points_to_pips(spread_points: float) -> float:
    return spread_points / POINTS_PER_PIP


def measure(m15_path: Path, *, out_path: Path) -> dict:
    m15 = pd.read_parquet(m15_path).sort_values("time").reset_index(drop=True)

    spread_pips = m15["spread"].astype(float) / POINTS_PER_PIP
    hours = m15["time"].dt.hour
    years = m15["time"].dt.year

    report: dict = {
        "dataset": str(m15_path),
        "rows": int(len(m15)),
        "pip_size": PIP_SIZE,
        "points_per_pip": POINTS_PER_PIP,
        "slippage_pips_per_fill": SLIPPAGE_PIPS,
        "commission_pips_round_trip": COMMISSION_PIPS,
        "spread_pips": {
            "mean": float(spread_pips.mean()),
            "median": float(spread_pips.median()),
            "p90": float(spread_pips.quantile(0.90)),
            "p95": float(spread_pips.quantile(0.95)),
        },
        "by_hour": {},
        "by_year": {},
    }

    for hour, group in spread_pips.groupby(hours):
        report["by_hour"][str(int(hour))] = {
            "n": int(len(group)),
            "mean": float(group.mean()),
            "median": float(group.median()),
            "p90": float(group.quantile(0.90)),
        }

    for year, group in spread_pips.groupby(years):
        report["by_year"][str(year)] = {
            "n": int(len(group)),
            "mean": float(group.mean()),
            "median": float(group.median()),
            "p90": float(group.quantile(0.90)),
        }

    # weekly-open bars: first bar of each ISO week
    iso = m15["time"].dt.isocalendar()
    week_key = iso["year"].astype(str) + "-W" + iso["week"].astype(str)
    first_of_week = m15.groupby(week_key).head(1)
    wk_spread = first_of_week["spread"].astype(float) / POINTS_PER_PIP
    report["weekly_open_spread_pips"] = {
        "n": int(len(wk_spread)),
        "mean": float(wk_spread.mean()),
        "median": float(wk_spread.median()),
        "p90": float(wk_spread.quantile(0.90)),
    }
    report["weekly_open_hour_utc"] = {
        "mean": float(first_of_week["time"].dt.hour.mean()),
        "median": float(first_of_week["time"].dt.hour.median()),
    }

    # reference round-trip costs
    for label, spread in (
        ("baseline_2.0", 2.0),
        ("median_weekly_open", float(wk_spread.median())),
        ("p90_weekly_open", float(wk_spread.quantile(0.90))),
        ("overall_median", float(spread_pips.median())),
    ):
        report[f"round_trip_{label}"] = {
            "spread_pips": spread,
            "total_pips": spread + 2 * SLIPPAGE_PIPS + COMMISSION_PIPS,
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Real cost measurement")
    parser.add_argument("--m15", default="data/raw/EURUSD/M15.parquet")
    parser.add_argument("--out", default="research/reports/cost_measurement.json")
    args = parser.parse_args()

    report = measure(Path(args.m15), out_path=Path(args.out))

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write(f"rows={report['rows']}\n")
    s = report["spread_pips"]
    out.write(
        f"spread pips overall: mean={s['mean']:.2f} median={s['median']:.2f} "
        f"p90={s['p90']:.2f} p95={s['p95']:.2f}\n"
    )
    w = report["weekly_open_spread_pips"]
    out.write(
        f"spread pips WEEKLY OPEN: n={w['n']} mean={w['mean']:.2f} "
        f"median={w['median']:.2f} p90={w['p90']:.2f} "
        f"(hora UTC mediana={report['weekly_open_hour_utc']['median']})\n"
    )
    for label in (
        "round_trip_baseline_2.0",
        "round_trip_median_weekly_open",
        "round_trip_p90_weekly_open",
        "round_trip_overall_median",
    ):
        r = report[label]
        out.write(
            f"{label}: spread {r['spread_pips']:.2f} + 1.7 = "
            f"{r['total_pips']:.2f} pips round-trip\n"
        )
    out.write(f"report: {args.out}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
