from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any

import pandas as pd

from backtest.instruments import instrument_specification
from research.alpha_diagnostic_matrix import write_variant_configs
from research.features import slot_percentile
from research.scalping_pullback_study import (
    DEFAULT_HORIZONS,
    SCALPING_REPORTS_DIR,
    SUMMARY_COLUMNS,
    build_m15_direction_states,
    load_m15_frame,
    load_m5_frame,
    summarize_events,
)
from research.scalping_spread_profile import session_label


def build_breakout_events(
    m5: pd.DataFrame,
    states: pd.DataFrame,
    *,
    symbol: str,
    breakout_lookback: int = 6,
    min_breakout_pips: float = 0.5,
    min_body_pips: float = 0.5,
    cost_overhead_pips: float = 1.7,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
) -> pd.DataFrame:
    validate_inputs(
        m5,
        states,
        breakout_lookback=breakout_lookback,
        min_breakout_pips=min_breakout_pips,
        min_body_pips=min_body_pips,
        horizons=horizons,
    )

    spec = instrument_specification(symbol)
    points_per_pip = spec.pip_size / spec.point

    micro = m5.sort_values("time").copy()
    micro["event_time"] = micro["time"] + pd.Timedelta(minutes=5)

    states = states.sort_values("state_time").copy()
    merged = pd.merge_asof(
        micro,
        states,
        left_on="event_time",
        right_on="state_time",
        direction="backward",
    )
    merged["direction"] = merged["direction"].fillna(0).astype(int)
    merged["session"] = merged["event_time"].map(session_label)
    merged["entry_spread_pips"] = (
        merged["spread"].astype(float) / points_per_pip
    )
    merged["spread_slot_percentile"] = slot_percentile(
        values=list(merged["entry_spread_pips"].astype(float)),
        timestamps=[
            timestamp.to_pydatetime()
            for timestamp in merged["event_time"]
        ],
    )
    merged["regime_strength"] = merged["blended_value"].abs()

    merged["channel_high"] = (
        merged["high"]
        .shift(1)
        .rolling(
            breakout_lookback,
            min_periods=breakout_lookback,
        )
        .max()
    )
    merged["channel_low"] = (
        merged["low"]
        .shift(1)
        .rolling(
            breakout_lookback,
            min_periods=breakout_lookback,
        )
        .min()
    )

    long_breakout = (merged["close"] - merged["channel_high"]) / spec.pip_size
    short_breakout = (merged["channel_low"] - merged["close"]) / spec.pip_size
    merged["breakout_pips"] = long_breakout.where(
        merged["direction"] > 0,
        short_breakout.where(merged["direction"] < 0),
    )
    direction = merged["direction"].astype(float)
    merged["body_pips"] = (
        direction
        * (merged["close"] - merged["open"])
        / spec.pip_size
    )
    merged["qualifies"] = (
        (merged["direction"] != 0)
        & (merged["breakout_pips"] >= min_breakout_pips)
        & (merged["body_pips"] >= min_body_pips)
    )

    events = merged[merged["qualifies"]].copy()

    rows = []

    for horizon in horizons:
        future_close = merged["close"].shift(-horizon)
        gross_pips = (
            direction
            * (future_close - merged["close"])
            / spec.pip_size
        )

        selected = events.copy()
        selected["horizon_bars"] = horizon
        selected["gross_pips"] = gross_pips.loc[selected.index]
        selected = selected.dropna(subset=["gross_pips"])
        selected["net_pips"] = (
            selected["gross_pips"]
            - selected["entry_spread_pips"]
            - cost_overhead_pips
        )
        rows.append(
            selected[
                [
                    "event_time",
                    "session",
                    "direction",
                    "state_time",
                    "blended_value",
                    "regime_strength",
                    "channel_high",
                    "channel_low",
                    "breakout_pips",
                    "body_pips",
                    "entry_spread_pips",
                    "spread_slot_percentile",
                    "horizon_bars",
                    "gross_pips",
                    "net_pips",
                ]
            ]
        )

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True)


def run_study(
    *,
    symbol: str,
    breakout_lookback: int = 6,
    min_breakout_pips: float = 0.5,
    min_body_pips: float = 0.5,
    cost_overhead_pips: float = 1.7,
    out_dir: Path = SCALPING_REPORTS_DIR,
) -> dict[str, Any]:
    config_path = write_variant_configs(
        symbol=symbol,
        out_dir=out_dir,
    )["ensemble_regime_cost"]

    m15 = load_m15_frame(symbol=symbol)
    m5 = load_m5_frame(symbol=symbol)
    states = build_m15_direction_states(
        m15,
        symbol=symbol,
        config_path=config_path,
    )
    events = build_breakout_events(
        m5,
        states,
        symbol=symbol,
        breakout_lookback=breakout_lookback,
        min_breakout_pips=min_breakout_pips,
        min_body_pips=min_body_pips,
        cost_overhead_pips=cost_overhead_pips,
    )
    rows = summarize_events(
        events,
        symbol=symbol,
    )

    return {
        "schema_version": "scalping-breakout-study/0.1.0",
        "symbol": symbol,
        "m15_rows": int(len(m15)),
        "m5_rows": int(len(m5)),
        "state_rows": int(len(states)),
        "event_rows": int(len(events)),
        "breakout_lookback": breakout_lookback,
        "min_breakout_pips": min_breakout_pips,
        "min_body_pips": min_body_pips,
        "cost_overhead_pips": cost_overhead_pips,
        "summary": rows,
    }


def write_study(
    study: dict[str, Any],
    *,
    out_dir: Path = SCALPING_REPORTS_DIR,
) -> tuple[Path, Path]:
    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    symbol = study["symbol"]
    stem = f"scalping_breakout_study_{symbol}"
    json_path = out_dir / f"{stem}.json"
    csv_path = out_dir / f"{stem}.csv"

    json_path.write_text(
        json.dumps(
            study,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    csv_path.write_text(
        render_csv(study["summary"]),
        encoding="utf-8",
    )
    return json_path, csv_path


def render_csv(
    rows: list[dict[str, Any]],
) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=SUMMARY_COLUMNS,
    )
    writer.writeheader()

    for row in rows:
        writer.writerow(row)

    return buffer.getvalue()


def validate_inputs(
    m5: pd.DataFrame,
    states: pd.DataFrame,
    *,
    breakout_lookback: int,
    min_breakout_pips: float,
    min_body_pips: float,
    horizons: tuple[int, ...],
) -> None:
    if m5.empty:
        raise ValueError("m5 cannot be empty")

    if states.empty:
        raise ValueError("states cannot be empty")

    if breakout_lookback <= 0:
        raise ValueError("breakout_lookback must be positive")

    if min_breakout_pips < 0:
        raise ValueError("min_breakout_pips cannot be negative")

    if min_body_pips < 0:
        raise ValueError("min_body_pips cannot be negative")

    if not horizons or any(horizon <= 0 for horizon in horizons):
        raise ValueError("horizons must contain positive integers")

    for column in ["time", "open", "high", "low", "close", "spread"]:
        if column not in m5.columns:
            raise ValueError(f"m5 missing column: {column}")

    for column in ["state_time", "direction", "blended_value"]:
        if column not in states.columns:
            raise ValueError(f"states missing column: {column}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stage-1 SC-02 study: M5 breakouts in the direction of "
            "the M15 ensemble_regime_cost state."
        )
    )
    parser.add_argument(
        "--symbol",
        default="USDJPY",
    )
    parser.add_argument(
        "--breakout-lookback",
        type=int,
        default=6,
    )
    parser.add_argument(
        "--min-breakout-pips",
        type=float,
        default=0.5,
    )
    parser.add_argument(
        "--min-body-pips",
        type=float,
        default=0.5,
    )
    parser.add_argument(
        "--cost-overhead-pips",
        type=float,
        default=1.7,
        help="slippage + commission pips added to entry spread",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=SCALPING_REPORTS_DIR,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    study = run_study(
        symbol=args.symbol,
        breakout_lookback=args.breakout_lookback,
        min_breakout_pips=args.min_breakout_pips,
        min_body_pips=args.min_body_pips,
        cost_overhead_pips=args.cost_overhead_pips,
        out_dir=args.out_dir,
    )
    json_path, csv_path = write_study(
        study,
        out_dir=args.out_dir,
    )

    print(
        f"{args.symbol}: {study['event_rows']} event-horizon rows "
        f"from {study['m5_rows']} M5 candles"
    )
    print(f"SC-02 breakout JSON: {json_path}")
    print(f"SC-02 breakout CSV : {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
