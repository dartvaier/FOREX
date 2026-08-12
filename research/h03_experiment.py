"""
H03 experiment — stage 1 (docs/26 §10): conditional prediction, NO trade.

Compares three models on EURUSD M15:

    1. no filter (baseline: every closed candle)
    2. traditional rolling-ATR filter  (true_range / mean(TR, 60) >= 1.5)
    3. H03 intraday-clock volatility surprise (>= 1.5)

Output: forward-return conditional stats (1/2/4/8 candles), per year
and overall, written as JSON + printed summary.

Causal: only already-closed candles feed the features; the current
candle never contributes to its own denominator.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from research.features import volatility_surprise

THRESHOLD = 1.50
ATR_WINDOW = 60
HORIZONS = (1, 2, 4, 8)


def _true_range_series(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    return pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _rolling_atr_filter(df: pd.DataFrame) -> pd.Series:
    tr = _true_range_series(df)
    # rolling mean of PRIOR true ranges (shift 1 -> causal)
    baseline = tr.shift(1).rolling(ATR_WINDOW).mean()
    signal = (tr / baseline) >= THRESHOLD
    return signal.fillna(False)


def _surprise_filter(df: pd.DataFrame, lookback: int) -> pd.Series:
    surprises = volatility_surprise(
        highs=df["high"].tolist(),
        lows=df["low"].tolist(),
        closes=df["close"].tolist(),
        timestamps=[ts.to_pydatetime() for ts in df["time"]],
        lookback_slots=lookback,
    )
    return pd.Series(
        [s is not None and s >= THRESHOLD for s in surprises],
        index=df.index,
    )


def _fwd_returns(df: pd.DataFrame, horizon: int) -> pd.Series:
    return df["close"].shift(-horizon) / df["close"] - 1.0


def _stats(fwd: pd.Series, mask: pd.Series, years: pd.Series) -> dict:
    rows: dict[str, dict] = {"overall": {}}

    selected = fwd[mask].dropna()

    if len(selected) == 0:
        return {"overall": {"events": 0}, "by_year": {}}

    rows["overall"] = {
        "events": int(len(selected)),
        "mean_fwd_return": float(selected.mean()),
        "positive_rate": float((selected > 0).mean()),
        "median_fwd_return": float(selected.median()),
    }

    by_year: dict[str, dict] = {}
    for year, group in selected.groupby(years[mask]):
        by_year[str(year)] = {
            "events": int(len(group)),
            "mean_fwd_return": float(group.mean()),
            "positive_rate": float((group > 0).mean()),
        }
    rows["by_year"] = by_year
    return rows


def run(
    parquet_path: Path,
    *,
    lookback: int = 60,
    out_path: Path,
) -> dict:
    df = pd.read_parquet(parquet_path)
    df = df.sort_values("time").reset_index(drop=True)

    years = df["time"].dt.year

    surprise = _surprise_filter(df, lookback)
    atr = _rolling_atr_filter(df)
    no_filter = pd.Series(True, index=df.index)

    models = {
        "no_filter": no_filter,
        "rolling_atr": atr,
        "volatility_surprise": surprise,
    }

    report: dict = {
        "hypothesis": "H03",
        "stage": 1,
        "threshold": THRESHOLD,
        "atr_window": ATR_WINDOW,
        "lookback_slots": lookback,
        "dataset": str(parquet_path),
        "rows": int(len(df)),
        "models": {},
    }

    for name, mask in models.items():
        report["models"][name] = {}
        for horizon in HORIZONS:
            fwd = _fwd_returns(df, horizon)
            report["models"][name][f"h{horizon}"] = _stats(
                fwd, mask, years
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)

    return report


def _fmt(value: float | None) -> str:
    if value is None:
        return "     -"
    return f"{value * 100:>7.3f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description="H03 stage-1 experiment")
    parser.add_argument(
        "--parquet",
        default="data/raw/EURUSD/M15.parquet",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=60,
        help="trading days of same-slot history (40/60/80 sensitivity)",
    )
    parser.add_argument(
        "--out",
        default="research/reports/h03_experiment.json",
    )
    args = parser.parse_args()

    report = run(
        Path(args.parquet),
        lookback=args.lookback,
        out_path=Path(args.out),
    )

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write(f"H03 stage-1 | threshold={report['threshold']} | "
              f"lookback={report['lookback_slots']} | rows={report['rows']}\n")
    out.write(f"{'model':<22} {'h':<3} {'events':>7} {'mean':>9} "
              f"{'pos%':>7} {'med':>9}\n")
    for name, horizons in report["models"].items():
        for h in HORIZONS:
            stats = horizons[f"h{h}"]["overall"]
            events = stats.get("events", 0)
            out.write(
                f"{name:<22} {h:<3} {events:>7} "
                f"{_fmt(stats.get('mean_fwd_return'))} "
                f"{_fmt(stats.get('positive_rate'))} "
                f"{_fmt(stats.get('median_fwd_return'))}\n"
            )
    out.write(f"report: {args.out}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
