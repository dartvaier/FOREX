"""
H02 experiment — stage 1 (docs/26 §16): conditional prediction, NO trade.

Asia-London handoff conditioned on session shape (EURUSD M15):

    Asian session = M15 bars with Europe/London hour in [00:00, 07:00)
    asian_return   = close(last bar) / open(first bar) - 1
    asian_range    = high - low of the session
    range_pct      = empirical percentile vs prior 60 trading days
    CLV            = (close - low) / (high - low) of last Asian bar

    Groups (mutually exclusive):
      range < p30 & CLV >= 0.80 -> continuation up   (signed = +fwd)
      range < p30 & CLV <= 0.20 -> continuation down (signed = -fwd)
      range > p70 & CLV >= 0.80 -> reversal down     (signed = -fwd)
      range > p70 & CLV <= 0.20 -> reversal up       (signed = +fwd)

Forward returns measured 1/2/4 hours after 07:00 London (from the
close of the last Asian bar). Causal percentiles only.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from collections import deque
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

LONDON = ZoneInfo("Europe/London")
HOUR_HORIZONS = (1, 2, 4)
CANDLES_PER_HOUR = 4
LOOKBACK = 60
P_LOW = 0.30
P_HIGH = 0.70
CLV_HIGH = 0.80
CLV_LOW = 0.20


def asian_sessions(m15: pd.DataFrame) -> pd.DataFrame:
    """Per-London-day Asian session summary (causal features)."""
    london_hour = m15["time"].dt.tz_convert(LONDON).dt.hour
    london_day = m15["time"].dt.tz_convert(LONDON).dt.date

    asian = m15[(london_hour >= 0) & (london_hour < 7)].copy()
    asian["day"] = london_day

    sessions = []
    for day, group in asian.sort_values("time").groupby("day"):
        sessions.append(
            {
                "day": day,
                "open": float(group["open"].iloc[0]),
                "high": float(group["high"].max()),
                "low": float(group["low"].min()),
                "close": float(group["close"].iloc[-1]),
                "tick_volume": float(group["tick_volume"].sum()),
                "last_ts": group["time"].iloc[-1],
            }
        )
    return pd.DataFrame(sessions)


def add_features(sessions: pd.DataFrame) -> pd.DataFrame:
    s = sessions.sort_values("day").reset_index(drop=True)
    s["asian_return"] = s["close"] / s["open"] - 1.0
    s["asian_range"] = s["high"] - s["low"]

    ranges = s["asian_range"].tolist()
    pcts: list[float | None] = []
    hist: deque[float] = deque(maxlen=LOOKBACK)
    for r in ranges:
        if not hist:
            pcts.append(None)
        else:
            pcts.append(sum(1 for prior in hist if prior <= r) / len(hist))
        hist.append(r)

    vol_hist: deque[float] = deque(maxlen=LOOKBACK)
    rel_vol: list[float | None] = []
    for v in s["tick_volume"].tolist():
        if not vol_hist:
            rel_vol.append(None)
        else:
            rel_vol.append(v / (sum(vol_hist) / len(vol_hist)))
        vol_hist.append(v)

    s["range_pct"] = pcts
    s["relative_tick_volume"] = rel_vol

    rng = (s["high"] - s["low"]).replace(0, float("nan"))
    s["clv"] = (s["close"] - s["low"]) / rng
    s["distance_to_high"] = (s["high"] - s["close"]) / rng
    s["distance_to_low"] = (s["close"] - s["low"]) / rng
    return s


def group_of(row: pd.Series) -> str | None:
    rp = row["range_pct"]
    clv = row["clv"]
    if rp is None or clv is None or pd.isna(clv):
        return None
    if rp < P_LOW:
        if clv >= CLV_HIGH:
            return "continuation_up"
        if clv <= CLV_LOW:
            return "continuation_down"
    elif rp > P_HIGH:
        if clv >= CLV_HIGH:
            return "reversal_down"
        if clv <= CLV_LOW:
            return "reversal_up"
    return None


def _signed(fwd: float, group: str) -> float:
    if group in ("continuation_up", "reversal_up"):
        return fwd
    return -fwd


def run(m15_path: Path, *, out_path: Path) -> dict:
    m15 = pd.read_parquet(m15_path)
    sessions = add_features(asian_sessions(m15))

    closes = m15["close"].reset_index(drop=True)
    ts = m15["time"].reset_index(drop=True)

    groups: dict[str, dict] = {}
    for g in (
        "continuation_up",
        "continuation_down",
        "reversal_down",
        "reversal_up",
    ):
        groups[g] = {h: [] for h in HOUR_HORIZONS}

    for _, row in sessions.iterrows():
        g = group_of(row)
        if g is None:
            continue
        last_idx = ts[ts == row["last_ts"]]
        if last_idx.empty:
            continue
        i = int(last_idx.index[0])
        for h in HOUR_HORIZONS:
            j = i + h * CANDLES_PER_HOUR
            if j < len(closes):
                fwd = closes[j] / closes[i] - 1.0
                groups[g][h].append(_signed(fwd, g))

    report: dict = {
        "hypothesis": "H02",
        "stage": 1,
        "dataset": str(m15_path),
        "p_low": P_LOW,
        "p_high": P_HIGH,
        "clv_high": CLV_HIGH,
        "clv_low": CLV_LOW,
        "lookback": LOOKBACK,
        "sessions": int(len(sessions)),
        "groups": {},
    }

    for g, horizons in groups.items():
        report["groups"][g] = {}
        for h, vals in horizons.items():
            report["groups"][g][f"h{h}"] = {
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
    parser = argparse.ArgumentParser(description="H02 stage-1 experiment")
    parser.add_argument("--m15", default="data/raw/EURUSD/M15.parquet")
    parser.add_argument("--out", default="research/reports/h02_experiment.json")
    args = parser.parse_args()

    report = run(Path(args.m15), out_path=Path(args.out))

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write(
        f"H02 stage-1 | sessions={report['sessions']} | "
        f"p{int(report['p_low']*100)}/p{int(report['p_high']*100)} "
        f"CLV {report['clv_low']}/{report['clv_high']}\n"
    )
    out.write(f"{'group':<20} {'h':<3} {'n':>7} {'signed%':>9} {'pos%':>7}\n")
    for g, horizons in report["groups"].items():
        for h in HOUR_HORIZONS:
            s = horizons[f"h{h}"]
            n = s["n"]
            mean = s["mean_signed_return"]
            pos = s["positive_rate"]
            out.write(
                f"{g:<20} {h:<3} {n:>7} "
                f"{(mean*100 if mean is not None else float('nan')):>9.3f} "
                f"{(pos*100 if pos is not None else float('nan')):>6.2f}%\n"
            )
    out.write(f"report: {args.out}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
