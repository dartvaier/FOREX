"""
H10 experiment — stage 1 (docs/26 §29): London first-hour momentum.

    window     = M15 bars with Europe/London hour in [07:00, 08:00)
    day_return = close(08:00 London) / open(07:00 London) - 1
    fwd        = close(22:00 London) / close(08:00 London) - 1
    signed     = sign(day_return) * fwd   (momentum hypothesis)
    net        = signed - cost (entry spread measured + 0.40 exit
                 + 1.0 slippage + 0.7 commission)

Stage 1: signed mean, positive rate, by year, leave-one-year-out,
deciles by |day_return|.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from research.rare_events import leave_one_year_out, summarize

LONDON = ZoneInfo("Europe/London")
EXIT_SPREAD_PIPS = 0.40
SLIPPAGE_PIPS = 1.0
COMMISSION_PIPS = 0.7
PIP_SIZE = 0.0001


def run(m15_path: Path, *, out_path: Path) -> dict:
    m15 = pd.read_parquet(m15_path).sort_values("time").reset_index(drop=True)

    df = pd.DataFrame(
        {
            "ld": m15["time"].dt.tz_convert(LONDON).dt.date,
            "lh": m15["time"].dt.tz_convert(LONDON).dt.hour,
            "close": m15["close"].astype(float).values,
            "open": m15["open"].astype(float).values,
            "spread": (m15["spread"].astype(float) / 10.0).values,
        }
    )

    signed_list: list[float] = []
    by_year: dict[str, list] = {}
    decile_signed: dict[int, list] = {}
    entry_spreads: list[float] = []

    for day, g in df.groupby("ld"):
        win = g[(g["lh"] >= 7) & (g["lh"] < 8)]
        end = g[(g["lh"] >= 21) & (g["lh"] < 22)]
        if win.empty or end.empty:
            continue

        first_open = float(win.iloc[0]["open"])
        last_close = float(win.iloc[-1]["close"])
        entry_spread = float(win.iloc[-1]["spread"])
        end_close = float(end.iloc[-1]["close"])

        day_ret = last_close / first_open - 1.0
        fwd = end_close / last_close - 1.0
        signed = (1.0 if day_ret > 0 else -1.0) * fwd

        cost_pips = entry_spread + EXIT_SPREAD_PIPS + SLIPPAGE_PIPS + COMMISSION_PIPS
        net = signed - cost_pips * PIP_SIZE

        signed_list.append(net)
        entry_spreads.append(entry_spread)
        year = str(day)[:4]
        by_year.setdefault(year, []).append(net)

        dec = min(9, int(abs(day_ret) / (0.0015 + 1e-12)))
        decile_signed.setdefault(dec, []).append(net)

    report: dict = {
        "hypothesis": "H10",
        "stage": 1,
        "dataset": str(m15_path),
        "days": len(signed_list),
        "summary": summarize(signed_list),
        "mean_entry_spread": (
            sum(entry_spreads) / len(entry_spreads) if entry_spreads else None
        ),
        "by_year": {y: summarize(v) for y, v in sorted(by_year.items())},
        "leave_one_year_out": leave_one_year_out(by_year),
        "deciles": {
            str(k): summarize(v) for k, v in sorted(decile_signed.items())
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="H10 stage-1 experiment")
    parser.add_argument("--m15", default="data/raw/EURUSD/M15.parquet")
    parser.add_argument("--out", default="research/reports/h10_experiment.json")
    args = parser.parse_args()

    report = run(Path(args.m15), out_path=Path(args.out))

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    s = report["summary"]
    out.write(f"H10 stage-1 | days={report['days']}\n")
    out.write(
        f"net medio: {s['mean']*100 if s['mean'] is not None else float('nan'):.3f}% "
        f"pos: {s['positive_rate']*100 if s['positive_rate'] is not None else 0:.1f}% "
        f"n={s['n']}\n"
    )
    out.write(f"custo entrada medio: {report['mean_entry_spread']:.3f} pips\n")
    out.write(f"report: {args.out}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
