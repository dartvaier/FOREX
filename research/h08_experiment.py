"""
H08 experiment — stage 1 (docs/26 §27): weekly-gap reversion with a
liquidity filter on the entry, NET of measured per-event costs.

    event           = normalized_gap >= 0.50 (same as H07)
    entry_spread    = spread of the first real bar of the week (pips)
    filter          = entry_spread <= threshold (1.2 / 1.0 / 0.8)
    cost_per_event  = entry_spread + 0.40 (exit at +1h, measured
                      median of hour 1 UTC) + 1.0 (slippage 2x0.5)
                      + 0.7 (commission)
    net_h1          = signed_h1 - cost_per_event   (signed = reversion)

Acceptance (pre-registered): net mean > 0 with n >= 50 per threshold,
robust to leave-one-year-out and without the 5 largest gaps.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pandas as pd

from research.h07_experiment import CANDLES_PER_HOUR, detect_gaps
from research.rare_events import (
    bootstrap_ci,
    leave_one_year_out,
    summarize,
    without_largest_n,
)

EXIT_SPREAD_PIPS = 0.40
SLIPPAGE_PIPS = 1.0
COMMISSION_PIPS = 0.7
PIP_SIZE = 0.0001
THRESHOLDS = (1.2, 1.0, 0.8)


def run(m15_path: Path, h1_path: Path, *, out_path: Path) -> dict:
    m15 = pd.read_parquet(m15_path)
    h1 = pd.read_parquet(h1_path)

    events = detect_gaps(m15, h1, threshold=0.50)

    closes = m15["close"].reset_index(drop=True)
    opens = m15["open"].reset_index(drop=True)
    spreads = m15["spread"].astype(float).reset_index(drop=True) / 10.0

    report: dict = {
        "hypothesis": "H08",
        "stage": 1,
        "dataset_m15": str(m15_path),
        "dataset_h1": str(h1_path),
        "events_total": len(events),
        "exit_spread_pips": EXIT_SPREAD_PIPS,
        "slippage_pips": SLIPPAGE_PIPS,
        "commission_pips": COMMISSION_PIPS,
        "thresholds": {},
    }

    for threshold in THRESHOLDS:
        nets: list[float] = []
        signed_list: list[float] = []
        mags: list[float] = []
        years: list[str] = []

        for ev in events:
            i = ev["first_idx"]
            entry_spread = float(spreads.iloc[i])
            if entry_spread > threshold:
                continue
            j = i + CANDLES_PER_HOUR  # +1h
            if j >= len(closes):
                continue
            sign = -1.0 if ev["gap"] > 0 else 1.0
            fwd = closes[j] / opens[i] - 1.0
            signed = sign * fwd
            cost_pips = (
                entry_spread + EXIT_SPREAD_PIPS + SLIPPAGE_PIPS + COMMISSION_PIPS
            )
            nets.append(signed - cost_pips * PIP_SIZE)
            signed_list.append(signed)
            mags.append(abs(ev["gap"]))
            years.append(str(ev["week"][:4]))

        by_year: dict[str, list] = {}
        for y, v in zip(years, nets):
            by_year.setdefault(y, []).append(v)

        entry = report["thresholds"][str(threshold)] = {
            "n": len(nets),
            "net_mean": sum(nets) / len(nets) if nets else None,
            "net_positive_rate": (
                sum(1 for v in nets if v > 0) / len(nets) if nets else None
            ),
            "gross_signed_mean": (
                sum(signed_list) / len(signed_list) if signed_list else None
            ),
            "mean_entry_spread": (
                sum(float(spreads.iloc[ev["first_idx"]]) for ev in events[:0])
                if False
                else None
            ),
            "by_year": {y: summarize(v) for y, v in sorted(by_year.items())},
            "leave_one_year_out": leave_one_year_out(by_year),
            "without_top5": summarize(without_largest_n(nets, mags, n=5)),
            "bootstrap_ci_95": bootstrap_ci(nets),
        }

        # mean entry spread actually used
        used = [
            float(spreads.iloc[ev["first_idx"]])
            for ev in events
            if float(spreads.iloc[ev["first_idx"]]) <= threshold
        ]
        entry["mean_entry_spread"] = (
            sum(used) / len(used) if used else None
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="H08 stage-1 experiment")
    parser.add_argument("--m15", default="data/raw/EURUSD/M15.parquet")
    parser.add_argument("--h1", default="data/processed/EURUSD/H1.parquet")
    parser.add_argument("--out", default="research/reports/h08_experiment.json")
    args = parser.parse_args()

    report = run(Path(args.m15), Path(args.h1), out_path=Path(args.out))

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write(f"H08 stage-1 | events total={report['events_total']}\n")
    out.write(
        f"{'limiar':<7} {'n':>5} {'net%':>9} {'net pos%':>9} "
        f"{'bruto%':>8} {'custo ent':>9} {'CI lo%':>8} {'CI hi%':>8}\n"
    )
    for th in THRESHOLDS:
        s = report["thresholds"][str(th)]
        net = s["net_mean"]
        pos = s["net_positive_rate"]
        gross = s["gross_signed_mean"]
        esp = s["mean_entry_spread"]
        ci = s["bootstrap_ci_95"]
        lo = ci["lo"] if ci else None
        hi = ci["hi"] if ci else None
        out.write(
            f"{th:<7.1f} {s['n']:>5} "
            f"{(net*100 if net is not None else float('nan')):>9.3f} "
            f"{(pos*100 if pos is not None else float('nan')):>8.2f}% "
            f"{(gross*100 if gross is not None else float('nan')):>8.3f} "
            f"{(esp if esp is not None else float('nan')):>9.3f} "
            f"{(lo*100 if lo is not None else float('nan')):>8.3f} "
            f"{(hi*100 if hi is not None else float('nan')):>8.3f}\n"
        )
    out.write(f"report: {args.out}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
