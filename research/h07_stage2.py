"""
H07 stage 2 — full weekly-gap reversion trade (docs/26 §40).

    signal    = |weekly_gap| / ATR(H1,14) >= 0.50
    direction = against the gap: gap up -> SHORT, gap down -> LONG
    entry     = open of first M15 bar of the week
    TP        = entry + direction * 0.50 * |gap|   (half-fill)
    SL        = entry - direction * |gap|          (invalidation)
    timeout   = 32 M15 bars (8h), market exit at close
    cost      = measured entry spread + 0.40 + 1.0 + 0.7 pips
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pandas as pd

from research.h07_experiment import CANDLES_PER_HOUR, detect_gaps
from research.rare_events import leave_one_year_out, summarize

EXIT_SPREAD_PIPS = 0.40
SLIPPAGE_PIPS = 1.0
COMMISSION_PIPS = 0.7
PIP_SIZE = 0.0001
TIMEOUT_BARS = 8 * CANDLES_PER_HOUR  # 32
TP_FRACTION = 0.50
SL_FRACTION = 1.00
THRESHOLD = 0.50
MIN_TRADES = 100


def simulate_trade(
    entry: float, tp: float, sl: float, bars: list[dict], direction: int
) -> dict:
    """Simulate one trade on M15 bars after entry (SL-first).

    direction: +1 long (TP above, SL below), -1 short (TP below, SL above).
    Returns pnl (price units, sign-adjusted), exit_reason, bars_held,
    exit_price.
    """
    for k, b in enumerate(bars, start=1):
        if direction > 0:  # long
            if b["open"] <= sl:
                return {"pnl": b["open"] - entry, "exit_reason": "sl", "bars_held": k, "exit_price": b["open"]}
            if b["open"] >= tp:
                return {"pnl": b["open"] - entry, "exit_reason": "tp", "bars_held": k, "exit_price": b["open"]}
            if b["low"] <= sl:
                return {"pnl": sl - entry, "exit_reason": "sl", "bars_held": k, "exit_price": sl}
            if b["high"] >= tp:
                return {"pnl": tp - entry, "exit_reason": "tp", "bars_held": k, "exit_price": tp}
        else:  # short
            if b["open"] >= sl:
                return {"pnl": entry - b["open"], "exit_reason": "sl", "bars_held": k, "exit_price": b["open"]}
            if b["open"] <= tp:
                return {"pnl": entry - b["open"], "exit_reason": "tp", "bars_held": k, "exit_price": b["open"]}
            if b["high"] >= sl:
                return {"pnl": entry - sl, "exit_reason": "sl", "bars_held": k, "exit_price": sl}
            if b["low"] <= tp:
                return {"pnl": entry - tp, "exit_reason": "tp", "bars_held": k, "exit_price": tp}
        if k == TIMEOUT_BARS:
            exit_price = b["close"]
            pnl = (exit_price - entry) * direction
            return {"pnl": pnl, "exit_reason": "timeout", "bars_held": k, "exit_price": exit_price}
    raise ValueError("no exit reached (bars exhausted before timeout)")


def build_trades(m15_path: Path, h1_path: Path, *, threshold: float = THRESHOLD) -> list[dict]:
    m15 = pd.read_parquet(m15_path)
    h1 = pd.read_parquet(h1_path)
    events = detect_gaps(m15, h1, threshold=threshold)

    opens = m15["open"].astype(float).reset_index(drop=True)
    highs = m15["high"].astype(float).reset_index(drop=True)
    lows = m15["low"].astype(float).reset_index(drop=True)
    closes = m15["close"].astype(float).reset_index(drop=True)
    spreads = (m15["spread"].astype(float) / 10.0).reset_index(drop=True)

    trades: list[dict] = []
    for ev in events:
        i = int(ev["first_idx"])
        if i + TIMEOUT_BARS >= len(closes):
            continue
        entry = float(opens.iloc[i])
        gap_abs = abs(float(ev["gap"]))
        direction = -1.0 if ev["gap"] > 0 else 1.0  # against the gap
        tp = entry + direction * TP_FRACTION * gap_abs
        sl = entry - direction * SL_FRACTION * gap_abs

        bars = [
            {
                "open": float(opens.iloc[j]),
                "high": float(highs.iloc[j]),
                "low": float(lows.iloc[j]),
                "close": float(closes.iloc[j]),
            }
            for j in range(i + 1, i + 1 + TIMEOUT_BARS)
        ]
        sim = simulate_trade(entry, tp, sl, bars, int(direction))
        cost = (float(spreads.iloc[i]) + EXIT_SPREAD_PIPS + SLIPPAGE_PIPS + COMMISSION_PIPS) * PIP_SIZE
        trades.append(
            {
                "week": ev["week"],
                "direction": int(direction),
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "gap": float(ev["gap"]),
                "entry_spread": float(spreads.iloc[i]),
                **sim,
                "net": sim["pnl"] - cost,
                "net_pips": (sim["pnl"] - cost) / PIP_SIZE,
            }
        )
    return trades


def aggregate(trades: list[dict]) -> dict:
    n = len(trades)
    if n == 0:
        return {"n": 0}
    net = [t["net_pips"] for t in trades]
    wins = [t["net_pips"] for t in trades if t["net_pips"] > 0]
    losses = [t["net_pips"] for t in trades if t["net_pips"] <= 0]
    by_reason: dict[str, int] = {}
    for t in trades:
        by_reason[t["exit_reason"]] = by_reason.get(t["exit_reason"], 0) + 1
    return {
        "n": n,
        "net_mean_pips": sum(net) / n,
        "gross_mean_pips": sum(t["pnl"] for t in trades) / n / PIP_SIZE,
        "hit_rate": by_reason.get("tp", 0) / n,
        "stop_rate": by_reason.get("sl", 0) / n,
        "timeout_rate": by_reason.get("timeout", 0) / n,
        "payoff": (
            (sum(wins) / len(wins)) / abs(sum(losses) / len(losses))
            if wins and losses
            else None
        ),
        "mean_bars_held": sum(t["bars_held"] for t in trades) / n,
        "mean_entry_spread": sum(t["entry_spread"] for t in trades) / n,
        "exit_reasons": by_reason,
        "long_share": sum(1 for t in trades if t["direction"] > 0) / n,
    }


def run(m15_path: Path, h1_path: Path, *, out_path: Path) -> dict:
    trades = build_trades(m15_path, h1_path)

    by_year: dict[str, list[float]] = {}
    for t in trades:
        by_year.setdefault(str(t["week"])[:4], []).append(t["net_pips"])

    blocks: dict[str, list[float]] = {}
    for t in trades:
        y = int(str(t["week"])[:4])
        block = f"{y - (y % 2)}-{y - (y % 2) + 1}"
        blocks.setdefault(block, []).append(t["net_pips"])

    def mean_of(vals: list[float]) -> float:
        return sum(vals) / len(vals)

    report = {
        "hypothesis": "H07",
        "stage": 2,
        "dataset_m15": str(m15_path),
        "dataset_h1": str(h1_path),
        "prereg": "docs/26 §40",
        "trade": {
            "direction": "against gap (up->short, down->long)",
            "tp": "entry +/- 0.50*|gap|",
            "sl": "entry -/+ |gap|",
            "timeout_bars": TIMEOUT_BARS,
        },
        "aggregate": aggregate(trades),
        "by_year": {y: mean_of(v) for y, v in sorted(by_year.items())},
        "by_year_n": {y: len(v) for y, v in sorted(by_year.items())},
        "by_year_summary": {y: summarize(v) for y, v in sorted(by_year.items())},
        "leave_one_year_out": leave_one_year_out(by_year),
        "blocks_2y": {b: mean_of(v) for b, v in sorted(blocks.items())},
        "blocks_2y_n": {b: len(v) for b, v in sorted(blocks.items())},
        "passes": None,  # filled by caller
    }

    a = report["aggregate"]
    if a["n"] >= MIN_TRADES:
        annual_means = [mean_of(v) for v in by_year.values()]
        loyo_all = report["leave_one_year_out"].get("all_years", {}).get("metric", 0)
        pos_blocks = sum(1 for v in report["blocks_2y"].values() if v > 0)
        block_frac = pos_blocks / len(report["blocks_2y"]) if report["blocks_2y"] else 0
        report["passes"] = {
            "n_ok": a["n"] >= MIN_TRADES,
            "net_ok": a["net_mean_pips"] > 0,
            "loyo_ok": loyo_all > 0,
            "median_year_ok": (sorted(annual_means)[len(annual_means) // 2] > 0),
            "blocks_ok": block_frac >= 0.60,
            "hit_ok": a["hit_rate"] >= 0.20,
            "blocks_positive_fraction": block_frac,
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="H07 stage-2 AUDUSD/NZDUSD")
    parser.add_argument("--symbol", default="NZDUSD")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    m15 = Path("data/raw") / args.symbol / "M15.parquet"
    h1 = Path("data/processed") / args.symbol / "H1.parquet"
    out_path = Path(args.out) if args.out else Path("research/reports") / f"h07_stage2_{args.symbol}.json"
    report = run(m15, h1, out_path=out_path)

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    a = report["aggregate"]
    out.write(f"H07 stage-2 {args.symbol} | n={a['n']} | long {a['long_share']*100:.0f}%\n")
    out.write(f"net medio: {a['net_mean_pips']:+.2f} pips | bruto: {a['gross_mean_pips']:+.2f} pips\n")
    out.write(f"hit TP: {a['hit_rate']*100:.1f}% | stop: {a['stop_rate']*100:.1f}% | timeout: {a['timeout_rate']*100:.1f}%\n")
    out.write(f"payoff: {a['payoff'] if a['payoff'] is not None else float('nan'):.2f} | bars: {a['mean_bars_held']:.1f}\n")
    if report["passes"]:
        out.write(f"criteria: {report['passes']}\n")
    out.write(f"report: {out_path}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
