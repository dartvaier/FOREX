"""
H01 experiment — stage 1 (docs/26 §14): conditional prediction, NO trade.

Asian-range false-breakout events on EURUSD M15:

    1. Asian range = M15 bars with Europe/London hour in [00:00, 07:00)
    2. ATR(H1,14) from the 14 H1 bars closed before 07:00 London (causal)
    3. breakout after 07:00 London: high > range_high + buffer*ATR
       (upper) or low < range_low - buffer*ATR (lower)
    4. confirmation: first candle in {N, N+1, N+2} closing INSIDE
       the Asian range
    5. expected: upper false breakout -> negative forward return;
       lower -> positive (reversion toward the midpoint)

Stage 1 metrics: signed forward return (1/2/4/8), midpoint-touch
rate within 8 bars, return toward the opposite edge, by year, by
subgroups (range size percentile, duration outside, side).
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from research.features import true_range

LONDON = ZoneInfo("Europe/London")
HORIZONS = (1, 2, 4, 8)


def _atr_h1_14(h1: pd.DataFrame, before_ts: datetime) -> float | None:
    """ATR(H1,14): mean TR of the 14 H1 bars closed strictly before
    `before_ts` (causal). Wilder TR; first bar in the window uses
    high - low (no prior close)."""
    prior = h1[h1["time"] < before_ts].tail(14)
    if len(prior) < 14:
        return None

    highs = prior["high"].tolist()
    lows = prior["low"].tolist()
    closes = prior["close"].tolist()

    trs: list[float] = []
    for i in range(len(prior)):
        if i == 0:
            trs.append(highs[i] - lows[i])
        else:
            trs.append(
                max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1]),
                )
            )
    return sum(trs) / len(trs)


def detect_events(
    m15: pd.DataFrame,
    h1: pd.DataFrame,
    *,
    buffer: float,
    max_confirm: int = 2,
) -> list[dict]:
    """Detect H01 false-breakout events. Returns a list of event
    dicts with the confirmation bar index and side."""
    m15 = m15.sort_values("time").reset_index(drop=True)
    london_hour = m15["time"].dt.tz_convert(LONDON).dt.hour
    london_day = m15["time"].dt.tz_convert(LONDON).dt.date

    events: list[dict] = []

    # group bars by London day for the Asian window
    asian = m15[(london_hour >= 0) & (london_hour < 7)]
    for day, group in asian.groupby(london_day):
        group = group.sort_values("time")
        range_high = float(group["high"].max())
        range_low = float(group["low"].min())
        mid = (range_high + range_low) / 2.0

        # ATR from H1 closed before 07:00 London of this day
        day_start = group["time"].iloc[0]
        seven_london = day_start.astimezone(LONDON).replace(
            hour=7, minute=0, second=0, microsecond=0
        ).astimezone(m15["time"].dt.tz)
        atr = _atr_h1_14(h1, seven_london)
        if atr is None or atr <= 0:
            continue

        # post-Asian bars of the same London day
        post = m15[
            (london_day == day) & (m15["time"] >= seven_london)
        ]
        if post.empty:
            continue

        used_sides: set[str] = set()

        for idx in post.index:
            row = m15.loc[idx]
            side = None
            if row["high"] > range_high + buffer * atr:
                side = "upper"
            elif row["low"] < range_low - buffer * atr:
                side = "lower"

            if side is None:
                continue

            if side in used_sides:
                continue

            # confirmation within {idx, idx+1, idx+2}
            confirmed_idx = None
            for offset in range(max_confirm + 1):
                j = idx + offset
                if j >= len(m15):
                    break
                c = m15.loc[j, "close"]
                if range_low < c < range_high:
                    confirmed_idx = j
                    break

            if confirmed_idx is None:
                continue

            used_sides.add(side)
            events.append(
                {
                    "day": str(day),
                    "side": side,
                    "breakout_idx": int(idx),
                    "confirm_idx": int(confirmed_idx),
                    "duration_out": int(confirmed_idx - idx),
                    "range_high": range_high,
                    "range_low": range_low,
                    "mid": mid,
                    "atr": atr,
                }
            )

    return events


def run(
    m15_path: Path,
    h1_path: Path,
    *,
    buffer: float,
    out_path: Path,
) -> dict:
    m15 = pd.read_parquet(m15_path)
    h1 = pd.read_parquet(h1_path)

    events = detect_events(m15, h1, buffer=buffer)

    # forward returns from the confirmation close
    closes = m15["close"].reset_index(drop=True)
    signed_all: dict[int, list[float]] = {h: [] for h in HORIZONS}
    touch_mid: list[bool] = []
    signed_year: dict[str, list[float]] = {}
    signed_side: dict[str, list[float]] = {"upper": [], "lower": []}

    for ev in events:
        i = ev["confirm_idx"]
        side_sign = -1.0 if ev["side"] == "upper" else 1.0
        for h in HORIZONS:
            j = i + h
            if j < len(closes):
                fwd = closes[j] / closes[i] - 1.0
                signed_all[h].append(side_sign * fwd)

        h8_fwd = None
        j8 = i + 8
        if j8 < len(closes):
            h8_fwd = side_sign * (closes[j8] / closes[i] - 1.0)
            year = str(ev["day"][:4])
            signed_year.setdefault(year, []).append(h8_fwd)
            signed_side[ev["side"]].append(h8_fwd)

        # midpoint touch within 8 bars after confirmation
        end = min(i + 8, len(m15) - 1)
        window = m15["high"].iloc[i + 1 : end + 1]
        window_low = m15["low"].iloc[i + 1 : end + 1]
        touched = bool(
            (window >= ev["mid"]).any() or (window_low <= ev["mid"]).any()
        )
        touch_mid.append(touched)

    report: dict = {
        "hypothesis": "H01",
        "stage": 1,
        "buffer": buffer,
        "dataset_m15": str(m15_path),
        "dataset_h1": str(h1_path),
        "events": len(events),
        "horizons": {},
        "midpoint_touch_rate_8": (
            sum(touch_mid) / len(touch_mid) if touch_mid else None
        ),
        "by_year": {
            year: {
                "n": len(vals),
                "mean_signed_return_h8": (
                    sum(vals) / len(vals) if vals else None
                ),
            }
            for year, vals in sorted(signed_year.items())
        },
        "by_side": {
            side: {
                "n": len(vals),
                "mean_signed_return_h8": (
                    sum(vals) / len(vals) if vals else None
                ),
            }
            for side, vals in signed_side.items()
        },
    }

    for h in HORIZONS:
        vals = signed_all[h]
        report["horizons"][f"h{h}"] = {
            "n": len(vals),
            "mean_signed_return": (
                sum(vals) / len(vals) if vals else None
            ),
            "positive_rate": (
                sum(1 for v in vals if v > 0) / len(vals) if vals else None
            ),
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="H01 stage-1 experiment")
    parser.add_argument("--m15", default="data/raw/EURUSD/M15.parquet")
    parser.add_argument("--h1", default="data/processed/EURUSD/H1.parquet")
    parser.add_argument(
        "--buffer", type=float, default=0.15, help="breakout buffer x ATR"
    )
    parser.add_argument("--out", default="research/reports/h01_experiment.json")
    args = parser.parse_args()

    report = run(
        Path(args.m15),
        Path(args.h1),
        buffer=args.buffer,
        out_path=Path(args.out),
    )

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write(f"H01 stage-1 | buffer={report['buffer']} | events={report['events']}\n")
    out.write(
        f"midpoint touch rate (8 bars): "
        f"{report['midpoint_touch_rate_8']}\n"
    )
    out.write(f"{'h':<3} {'n':>7} {'signed%':>9} {'pos%':>7}\n")
    for h in HORIZONS:
        s = report["horizons"][f"h{h}"]
        n = s["n"]
        mean = s["mean_signed_return"]
        pos = s["positive_rate"]
        out.write(
            f"{h:<3} {n:>7} "
            f"{(mean*100 if mean is not None else float('nan')):>9.3f} "
            f"{(pos*100 if pos is not None else float('nan')):>6.2f}%\n"
        )
    out.write(f"report: {args.out}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
