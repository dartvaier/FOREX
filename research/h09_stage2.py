"""
H09 stage 2 — full trade simulation (docs/26 §36).

    signal    = compressed Asian range (p30, 60d causal) + CLV >= 0.80
    direction = SHORT (reversion)
    entry     = close of last Asian M15 bar
    TP        = midpoint of Asian range
    SL        = high + 0.10 * range
    timeout   = 16 M15 bars (4h), market exit at close
    cost      = measured entry spread + 0.40 exit + 1.0 slippage
                + 0.7 commission (pips), PIP_SIZE = 0.0001
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pandas as pd

from research.h02_experiment import CANDLES_PER_HOUR, add_features, asian_sessions
from research.h09_experiment import CLV_HIGH, P_LOW
from research.rare_events import leave_one_year_out

EXIT_SPREAD_PIPS = 0.40
SLIPPAGE_PIPS = 1.0
COMMISSION_PIPS = 0.7
PIP_SIZE = 0.0001
TIMEOUT_BARS = 4 * CANDLES_PER_HOUR  # 16
SL_BUFFER = 0.10


def simulate_short(entry: float, tp: float, sl: float, bars: list[dict]) -> dict:
    """Simulate one short trade on M15 bars after entry (SL-first).

    bars: sequence of {open, high, low, close} AFTER the entry bar.
    Returns pnl in price units (entry - exit), exit_reason,
    bars_held, exit_price.
    """
    for k, b in enumerate(bars, start=1):
        # gap at open
        if b["open"] >= sl:
            return {"pnl": entry - b["open"], "exit_reason": "sl", "bars_held": k, "exit_price": b["open"]}
        if b["open"] <= tp:
            return {"pnl": entry - b["open"], "exit_reason": "tp", "bars_held": k, "exit_price": b["open"]}
        # SL-first within the bar
        if b["high"] >= sl:
            return {"pnl": entry - sl, "exit_reason": "sl", "bars_held": k, "exit_price": sl}
        if b["low"] <= tp:
            return {"pnl": entry - tp, "exit_reason": "tp", "bars_held": k, "exit_price": tp}
        if k == TIMEOUT_BARS:
            return {"pnl": entry - b["close"], "exit_reason": "timeout", "bars_held": k, "exit_price": b["close"]}
    raise ValueError("no exit reached (bars exhausted before timeout)")


def build_trades(m15_path: Path) -> list[dict]:
    m15 = pd.read_parquet(m15_path)
    sessions = add_features(asian_sessions(m15))

    ts = m15["time"].reset_index(drop=True)
    opens = m15["open"].astype(float).reset_index(drop=True)
    highs = m15["high"].astype(float).reset_index(drop=True)
    lows = m15["low"].astype(float).reset_index(drop=True)
    closes = m15["close"].astype(float).reset_index(drop=True)
    spreads = (m15["spread"].astype(float) / 10.0).reset_index(drop=True)

    trades: list[dict] = []
    for _, row in sessions.iterrows():
        rp = row["range_pct"]
        clv = row["clv"]
        if rp is None or clv is None or pd.isna(clv):
            continue
        if not (rp < P_LOW and clv >= CLV_HIGH):
            continue
        match = ts[ts == row["last_ts"]]
        if match.empty:
            continue
        i = int(match.index[0])
        if i + TIMEOUT_BARS >= len(closes):
            continue

        entry = float(closes.iloc[i])
        rng = float(row["high"] - row["low"])
        if rng <= 0:
            continue
        tp = float((row["high"] + row["low"]) / 2.0)
        sl = float(row["high"] + SL_BUFFER * rng)
        if tp >= entry or sl <= entry:
            continue  # structural guard (should not trigger with CLV 0.80)

        bars = [
            {
                "open": float(opens.iloc[j]),
                "high": float(highs.iloc[j]),
                "low": float(lows.iloc[j]),
                "close": float(closes.iloc[j]),
            }
            for j in range(i + 1, i + 1 + TIMEOUT_BARS)
        ]
        sim = simulate_short(entry, tp, sl, bars)
        cost = (float(spreads.iloc[i]) + EXIT_SPREAD_PIPS + SLIPPAGE_PIPS + COMMISSION_PIPS) * PIP_SIZE
        trades.append(
            {
                "day": row["day"],
                "entry": entry,
                "tp": tp,
                "sl": sl,
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
    }


def run(m15_path: Path, *, out_path: Path) -> dict:
    trades = build_trades(m15_path)

    by_year: dict[str, list[float]] = {}
    for t in trades:
        by_year.setdefault(str(t["day"])[:4], []).append(t["net_pips"])

    blocks: dict[str, list[float]] = {}
    for t in trades:
        y = int(str(t["day"])[:4])
        block = f"{y - (y % 2)}-{y - (y % 2) + 1}"
        blocks.setdefault(block, []).append(t["net_pips"])

    def mean_of(vals: list[float]) -> float:
        return sum(vals) / len(vals)

    report = {
        "hypothesis": "H09",
        "stage": 2,
        "dataset": str(m15_path),
        "prereg": "docs/26 §36",
        "trade": {
            "direction": "short",
            "tp": "midpoint",
            "sl": "high + 0.10*range",
            "timeout_bars": TIMEOUT_BARS,
        },
        "aggregate": aggregate(trades),
        "by_year": {y: mean_of(v) for y, v in sorted(by_year.items())},
        "by_year_n": {y: len(v) for y, v in sorted(by_year.items())},
        "leave_one_year_out": leave_one_year_out(by_year),
        "blocks_2y": {b: mean_of(v) for b, v in sorted(blocks.items())},
        "blocks_2y_n": {b: len(v) for b, v in sorted(blocks.items())},
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="H09 stage-2 experiment")
    parser.add_argument("--m15", default="data/raw/EURUSD/M15.parquet")
    parser.add_argument("--out", default="research/reports/h09_stage2.json")
    args = parser.parse_args()

    report = run(Path(args.m15), out_path=Path(args.out))

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    a = report["aggregate"]
    out.write(f"H09 stage-2 | n={a['n']}\n")
    out.write(
        f"net medio: {a['net_mean_pips']:+.2f} pips | bruto: "
        f"{a['gross_mean_pips']:+.2f} pips\n"
    )
    out.write(
        f"hit TP: {a['hit_rate']*100:.1f}% | stop: {a['stop_rate']*100:.1f}% | "
        f"timeout: {a['timeout_rate']*100:.1f}%\n"
    )
    out.write(f"payoff: {a['payoff'] if a['payoff'] is not None else float('nan'):.2f} | "
              f"bars held: {a['mean_bars_held']:.1f}\n")
    for y, v in sorted(report["by_year"].items()):
        out.write(f"  {y}: {v:+.2f} pips (n={report['by_year_n'][y]})\n")
    out.write(f"report: {args.out}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
