"""
H04 experiment — stage 1 (docs/26 §18): conditional prediction, NO trade.

Compression + price/activity shock with mandatory ablation:

    realized_range_16 = max(high)-min(low) of last 16 M15 bars
    compression      = slot_percentile(realized_range_16) < p25 (60 slots)
    range shock      = slot_percentile(true_range) >= p90 (60 slots)
    activity shock   = slot_percentile(tick_volume) >= p80 (60 slots)
    CLV              = (close - low) / (high - low)

    Models (signed forward return 1/2/4/8, direction = signal side):
      A1 = compression only
      A2 = compression + range shock
      A3 = compression + range + activity
      A4 = full (compression + range + activity + CLV confirmation)
      CTRL = simple breakout (range shock without compression)

Causal: percentiles use only prior same-slot observations.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pandas as pd

from research.features import directional_efficiency, slot_percentile, true_range

HORIZONS = (1, 2, 4, 8)
LOOKBACK = 60
P_COMP = 0.25
P_SHOCK = 0.90
P_ACT = 0.80
CLV_LONG = 0.75
CLV_SHORT = 0.25
WINDOW = 16


def build_signals(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return per-model boolean masks + direction + CLV."""
    timestamps = [ts.to_pydatetime() for ts in df["time"]]

    # realized range of the last WINDOW bars (evaluated on close of bar i)
    rr = pd.Series(
        [
            float(df["high"].iloc[max(0, i - WINDOW + 1) : i + 1].max()
                  - df["low"].iloc[max(0, i - WINDOW + 1) : i + 1].min())
            for i in range(len(df))
        ],
        index=df.index,
    )

    prev_close = df["close"].shift(1)
    tr = pd.Series(
        [
            true_range(h, l, pc)
            for h, l, pc in zip(df["high"], df["low"], prev_close)
        ],
        index=df.index,
    )

    rr_pct = slot_percentile(
        values=[float(v) for v in rr],
        timestamps=timestamps,
        lookback_slots=LOOKBACK,
    )
    tr_pct = slot_percentile(
        values=[float(v) if v is not None else float("nan") for v in tr],
        timestamps=timestamps,
        lookback_slots=LOOKBACK,
    )
    tv_pct = slot_percentile(
        values=df["tick_volume"].astype(float).tolist(),
        timestamps=timestamps,
        lookback_slots=LOOKBACK,
    )

    rng = df["high"] - df["low"]
    clv = (df["close"] - df["low"]) / rng.replace(0, float("nan"))

    def pct_ge(col: list, threshold: float) -> pd.Series:
        return pd.Series(
            [p is not None and p >= threshold for p in col], index=df.index
        )

    def pct_lt(col: list, threshold: float) -> pd.Series:
        return pd.Series(
            [p is not None and p < threshold for p in col], index=df.index
        )

    comp = pct_lt(rr_pct, P_COMP)
    shock = pct_ge(tr_pct, P_SHOCK)
    act = pct_ge(tv_pct, P_ACT)
    clv_long = clv >= CLV_LONG
    clv_short = clv <= CLV_SHORT
    clv_dir = clv_long | clv_short

    # signal direction: candle direction (+1 close>open, -1 close<open,
    # 0 doji -> no signal). Used by all ablation models; A4 additionally
    # requires the CLV confirmation via its mask.
    direction = pd.Series(0, index=df.index, dtype=int)
    direction[df["close"] > df["open"]] = 1
    direction[df["close"] < df["open"]] = -1

    # for A4, only keep directions consistent with CLV side
    direction_full = direction.copy()
    direction_full[~clv_dir] = 0

    models: dict[str, pd.Series] = {
        "A1_compression_only": comp,
        "A2_compression_range": comp & shock,
        "A3_compression_range_activity": comp & shock & act,
        "A4_full": comp & shock & act & clv_dir,
        "CTRL_simple_breakout": shock & ~comp,
    }
    return {
        "models": models,
        "direction": direction,
        "direction_full": direction_full,
        "clv_dir": clv_dir,
    }


def run(parquet_path: Path, *, out_path: Path) -> dict:
    df = pd.read_parquet(parquet_path).sort_values("time").reset_index(drop=True)
    built = build_signals(df)
    models = built["models"]
    direction = built["direction"]
    direction_full = built["direction_full"]

    closes = df["close"]
    years = df["time"].dt.year
    hours = df["time"].dt.hour

    report: dict = {
        "hypothesis": "H04",
        "stage": 1,
        "dataset": str(parquet_path),
        "rows": int(len(df)),
        "p_comp": P_COMP,
        "p_shock": P_SHOCK,
        "p_act": P_ACT,
        "clv_long": CLV_LONG,
        "clv_short": CLV_SHORT,
        "models": {},
    }

    for name, mask in models.items():
        m = report["models"][name] = {}
        use_dir = direction_full if name == "A4_full" else direction
        for horizon in HORIZONS:
            fwd = closes.shift(-horizon) / closes - 1.0
            signed = fwd * use_dir
            selected = signed[mask].dropna()

            m[f"h{horizon}"] = {
                "n": int(len(selected)),
                "mean_signed_return": (
                    float(selected.mean()) if len(selected) else None
                ),
                "positive_rate": (
                    float((selected > 0).mean()) if len(selected) else None
                ),
            }

        # by-year summary at h8 for stability check
        m["by_year_h8"] = {}
        mask_s = pd.Series(mask, index=df.index)
        h8_signed_all = (signed.where(mask_s)).dropna()
        for year in sorted(set(years)):
            sel = h8_signed_all[years[h8_signed_all.index] == year]
            if len(sel):
                m["by_year_h8"][str(year)] = {
                    "n": int(len(sel)),
                    "mean_signed_return": float(sel.mean()),
                }

        # hourly distribution at h8 (rejection: effect only from hour filter)
        m["hourly_h8"] = {}
        for hour, group in h8_signed_all.groupby(hours[h8_signed_all.index]):
            if len(group):
                m["hourly_h8"][str(int(hour))] = {
                    "n": int(len(group)),
                    "mean_signed_return": float(group.mean()),
                }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="H04 stage-1 experiment")
    parser.add_argument("--parquet", default="data/raw/EURUSD/M15.parquet")
    parser.add_argument("--out", default="research/reports/h04_experiment.json")
    args = parser.parse_args()

    report = run(Path(args.parquet), out_path=Path(args.out))

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write(f"H04 stage-1 | rows={report['rows']}\n")
    out.write(f"{'model':<32} {'h':<3} {'n':>8} {'signed%':>9} {'pos%':>7}\n")
    for name, m in report["models"].items():
        for h in HORIZONS:
            s = m[f"h{h}"]
            mean = s["mean_signed_return"]
            pos = s["positive_rate"]
            out.write(
                f"{name:<32} {h:<3} {s['n']:>8} "
                f"{(mean*100 if mean is not None else float('nan')):>9.3f} "
                f"{(pos*100 if pos is not None else float('nan')):>6.2f}%\n"
            )
    out.write(f"report: {args.out}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
