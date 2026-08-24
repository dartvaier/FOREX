"""
H05/H06 experiment — stage 1 (docs/26 §12): conditional prediction, NO trade.

6-cell matrix (range x tick volume x directional efficiency):

    range high + tick high + DE low  -> H05 (reversal vs prior move)
    range high + tick high + DE high -> H06 (continuation vs candle dir)
    other 4 cells                    -> controls

Signed forward returns (1/2/4/8 candles):
    H06-style:  signed = fwd * sign(close - open)
    H05-style:  signed = -fwd * sign(prior 4-bar return)

Causal: percentiles use only prior same-slot observations; the
current candle never contributes to its own distribution.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pandas as pd

from research.features import directional_efficiency, slot_percentile, true_range

P90 = 0.90
DE_LOW = 0.25
DE_HIGH = 0.70
CLV_HIGH = 0.90
CLV_LOW = 0.10
HORIZONS = (1, 2, 4, 8)
LOOKBACK = 60


def _tr_series(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    trs: list[float | None] = []
    for high, low, pc in zip(df["high"], df["low"], prev_close):
        trs.append(true_range(high, low, pc))
    return pd.Series(trs, index=df.index)


def build_cells(
    df: pd.DataFrame,
    *,
    p90: float = P90,
    de_low: float = DE_LOW,
    de_high: float = DE_HIGH,
) -> dict[str, pd.Series]:
    timestamps = [ts.to_pydatetime() for ts in df["time"]]

    tr = _tr_series(df)
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

    de = [
        directional_efficiency(o, h, l, c)
        for o, h, l, c in zip(df["open"], df["high"], df["low"], df["close"])
    ]

    rng = df["high"] - df["low"]
    clv = (df["close"] - df["low"]) / rng.replace(0, float("nan"))

    candle_dir = (df["close"] >= df["open"]).astype(int) * 2 - 1  # +1/-1
    prior_ret = (df["close"] / df["close"].shift(4) - 1.0).fillna(0.0)
    prior_sign = (prior_ret >= 0).astype(int) * 2 - 1

    tr_high = pd.Series(
        [p is not None and p >= p90 for p in tr_pct], index=df.index
    )
    tv_high = pd.Series(
        [p is not None and p >= p90 for p in tv_pct], index=df.index
    )
    tr_normal = pd.Series(
        [p is not None and p < p90 for p in tr_pct], index=df.index
    )
    tv_normal = pd.Series(
        [p is not None and p < p90 for p in tv_pct], index=df.index
    )
    de_series = pd.Series(de, index=df.index)
    de_low_mask = de_series.notna() & (de_series <= de_low)
    de_high_mask = de_series.notna() & (de_series >= de_high)

    h06_confirm = pd.Series(
        [
            (d is not None and d >= 0) and (c >= CLV_HIGH or c <= CLV_LOW)
            for d, c in zip(de, clv)
        ],
        index=df.index,
    )

    cells: dict[str, pd.Series] = {
        "H05_reversal": tr_high & tv_high & de_low_mask,
        "H06_continuation": tr_high & tv_high & de_high_mask & h06_confirm,
        "ctrl_range_high_tick_normal_de_low": tr_high & tv_normal & de_low_mask,
        "ctrl_range_high_tick_normal_de_high": tr_high & tv_normal & de_high_mask,
        "ctrl_range_normal_tick_high_de_low": tr_normal & tv_high & de_low_mask,
        "ctrl_range_normal_tick_high_de_high": tr_normal & tv_high & de_high_mask,
    }

    return {
        "cells": cells,
        "candle_dir": candle_dir,
        "prior_sign": prior_sign,
    }


def _signed_stats(
    fwd: pd.Series,
    mask: pd.Series,
    sign: pd.Series,
    years: pd.Series,
    invert: bool,
) -> dict:
    signed = fwd * sign
    if invert:
        signed = -signed
    selected = signed[mask].dropna()

    if len(selected) == 0:
        return {"events": 0, "by_year": {}}

    rows: dict[str, dict] = {
        "events": int(len(selected)),
        "mean_signed_return": float(selected.mean()),
        "positive_rate": float((selected > 0).mean()),
        "median_signed_return": float(selected.median()),
    }
    by_year: dict[str, dict] = {}
    for year, group in selected.groupby(years[mask]):
        by_year[str(year)] = {
            "events": int(len(group)),
            "mean_signed_return": float(group.mean()),
        }
    rows["by_year"] = by_year
    return rows


def run(parquet_path: Path, *, out_path: Path, p90: float = P90) -> dict:
    df = pd.read_parquet(parquet_path).sort_values("time").reset_index(drop=True)
    years = df["time"].dt.year

    built = build_cells(df, p90=p90)
    cells = built["cells"]
    candle_dir = built["candle_dir"]
    prior_sign = built["prior_sign"]

    report: dict = {
        "hypothesis": "H05/H06",
        "stage": 1,
        "p90": p90,
        "de_low": DE_LOW,
        "de_high": DE_HIGH,
        "dataset": str(parquet_path),
        "rows": int(len(df)),
        "cells": {},
    }

    for name, mask in cells.items():
        invert = name.startswith("H05")
        report["cells"][name] = {}
        for horizon in HORIZONS:
            fwd = df["close"].shift(-horizon) / df["close"] - 1.0
            report["cells"][name][f"h{horizon}"] = _signed_stats(
                fwd,
                mask,
                prior_sign if invert else candle_dir,
                years,
                invert,
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="H05/H06 stage-1 experiment")
    parser.add_argument("--parquet", default="data/raw/EURUSD/M15.parquet")
    parser.add_argument(
        "--p90", type=float, default=P90, help="percentile threshold (p85/p90/p95)"
    )
    parser.add_argument(
        "--out", default="research/reports/h0506_experiment.json"
    )
    args = parser.parse_args()

    report = run(Path(args.parquet), out_path=Path(args.out), p90=args.p90)

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write(
        f"H05/H06 stage-1 | p{int(args.p90*100)} | rows={report['rows']}\n"
    )
    out.write(f"{'cell':<36} {'h':<3} {'events':>7} {'signed%':>9} "
              f"{'pos%':>7} {'med%':>8}\n")
    for name, horizons in report["cells"].items():
        for h in HORIZONS:
            stats = horizons[f"h{h}"]
            events = stats.get("events", 0)
            mean = stats.get("mean_signed_return")
            pos = stats.get("positive_rate")
            med = stats.get("median_signed_return")
            out.write(
                f"{name:<36} {h:<3} {events:>7} "
                f"{(mean*100 if mean is not None else float('nan')):>9.3f} "
                f"{(pos*100 if pos is not None else float('nan')):>6.2f}% "
                f"{(med*100 if med is not None else float('nan')):>7.3f}\n"
            )
    out.write(f"report: {args.out}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
