"""
H09 experiment — stage 1 (docs/26 §28): reversion after a COMPRESSED
Asian range closing at the extreme (the anti-H02 pattern, now
pre-registered). NET of measured per-event costs.

    compression   = asian_range_percentile < p30 (60d causal)
    CLV high/low  = last Asian bar closes at extreme (0.80 / 0.20)
    expected      = compressed + close at high  -> fwd NEGATIVE (reversion)
                    compressed + close at low   -> fwd POSITIVE
    signed        = -fwd (high) / +fwd (low)
    cost          = entry spread (last Asian bar, measured) + 0.40
                    (exit +1h) + 1.0 slippage + 0.7 commission

Acceptance (pre-registered): net mean > 0, stable leave-one-year-out,
robust to frontier variations (p25/p35, CLV 0.75/0.85, 0.15/0.25).
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pandas as pd

from research.h02_experiment import (
    CANDLES_PER_HOUR,
    HOUR_HORIZONS,
    add_features,
    asian_sessions,
)
from research.rare_events import leave_one_year_out, summarize

P_LOW = 0.30
CLV_HIGH = 0.80
CLV_LOW = 0.20
EXIT_SPREAD_PIPS = 0.40
SLIPPAGE_PIPS = 1.0
COMMISSION_PIPS = 0.7
PIP_SIZE = 0.0001


def run(m15_path: Path, *, out_path: Path) -> dict:
    m15 = pd.read_parquet(m15_path)
    sessions = add_features(asian_sessions(m15))

    closes = m15["close"].reset_index(drop=True)
    opens = m15["open"].reset_index(drop=True)
    spreads = m15["spread"].astype(float).reset_index(drop=True) / 10.0
    ts = m15["time"].reset_index(drop=True)

    report: dict = {
        "hypothesis": "H09",
        "stage": 1,
        "dataset": str(m15_path),
        "sessions": int(len(sessions)),
        "groups": {},
    }

    for label, rp_cond, clv_cond, sign_mult in (
        ("compressed_close_high", lambda r: r < P_LOW, lambda c: c >= CLV_HIGH, -1.0),
        ("compressed_close_low", lambda r: r < P_LOW, lambda c: c <= CLV_LOW, +1.0),
    ):
        nets: dict[int, list] = {h: [] for h in HOUR_HORIZONS}
        nets_years: dict[int, dict[str, list]] = {
            h: {} for h in HOUR_HORIZONS
        }
        entry_spreads: list[float] = []

        for _, row in sessions.iterrows():
            rp = row["range_pct"]
            clv = row["clv"]
            if rp is None or clv is None or pd.isna(clv):
                continue
            if not (rp_cond(rp) and clv_cond(clv)):
                continue
            last_idx = ts[ts == row["last_ts"]]
            if last_idx.empty:
                continue
            i = int(last_idx.index[0])
            if i + 1 >= len(closes):
                continue
            entry_spread = float(spreads.iloc[i])
            entry_spreads.append(entry_spread)
            cost_pips = entry_spread + EXIT_SPREAD_PIPS + SLIPPAGE_PIPS + COMMISSION_PIPS
            year = str(row["day"])[:4]
            for h in HOUR_HORIZONS:
                j = i + h * CANDLES_PER_HOUR
                if j >= len(closes):
                    continue
                fwd = closes[j] / closes[i] - 1.0
                signed = sign_mult * fwd
                nets[h].append(signed - cost_pips * PIP_SIZE)
                nets_years[h].setdefault(year, []).append(
                    signed - cost_pips * PIP_SIZE
                )

        g = report["groups"][label] = {}
        for h in HOUR_HORIZONS:
            g[f"h{h}"] = {
                **summarize(nets[h]),
                "mean_entry_spread": (
                    sum(entry_spreads) / len(entry_spreads)
                    if entry_spreads
                    else None
                ),
                "by_year": {
                    y: summarize(v) for y, v in sorted(nets_years[h].items())
                },
                "leave_one_year_out": leave_one_year_out(nets_years[h]),
            }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="H09 stage-1 experiment")
    parser.add_argument("--m15", default="data/raw/EURUSD/M15.parquet")
    parser.add_argument("--out", default="research/reports/h09_experiment.json")
    args = parser.parse_args()

    report = run(Path(args.m15), out_path=Path(args.out))

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write(f"H09 stage-1 | sessions={report['sessions']}\n")
    out.write(f"{'grupo':<24} {'h':<3} {'n':>5} {'net%':>9} {'pos%':>7} "
              f"{'custo ent':>9}\n")
    for label, g in report["groups"].items():
        for h in HOUR_HORIZONS:
            s = g[f"h{h}"]
            net = s["mean"]
            pos = s["positive_rate"]
            esp = s["mean_entry_spread"]
            out.write(
                f"{label:<24} {h:<3} {s['n']:>5} "
                f"{(net*100 if net is not None else float('nan')):>9.3f} "
                f"{(pos*100 if pos is not None else float('nan')):>6.2f}% "
                f"{(esp if esp is not None else float('nan')):>9.3f}\n"
            )
    out.write(f"report: {args.out}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
