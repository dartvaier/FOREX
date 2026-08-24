from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any

import pandas as pd

from research.alpha_diagnostic_matrix import write_variant_configs
from research.runner import REPORTS_DIR
from research.scalping_pullback_study import (
    SCALPING_REPORTS_DIR,
    build_m15_direction_states,
    build_pullback_events,
    load_m15_frame,
    load_m5_frame,
)

SESSION_GROUPS = {
    "all": (),
    "liquid": ("london_morning", "london_ny_overlap"),
    "london_morning": ("london_morning",),
    "london_ny_overlap": ("london_ny_overlap",),
}

DIRECTION_GROUPS = {
    "all": None,
    "long": 1,
    "short": -1,
}

DEFAULT_HORIZONS = (3, 6)
DEFAULT_SPREAD_PERCENTILES = (0.50, 0.60)
DEFAULT_REGIME_STRENGTHS = (0.35, 0.50, 0.65)
DEFAULT_PULLBACK_MINS = (2.0, 3.0, 4.0)

SWEEP_COLUMNS = [
    "symbol",
    "session_group",
    "direction_group",
    "horizon_bars",
    "max_spread_slot_percentile",
    "min_regime_strength",
    "min_pullback_pips",
    "events",
    "mean_gross_pips",
    "median_gross_pips",
    "hit_rate",
    "mean_net_pips",
    "median_entry_spread_pips",
    "mean_entry_spread_pips",
]


def run_filter_sweep_study(
    *,
    symbol: str,
    pullback_lookback: int = 3,
    base_pullback_min_pips: float = 2.0,
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
    events = build_pullback_events(
        m5,
        states,
        symbol=symbol,
        pullback_lookback=pullback_lookback,
        pullback_min_pips=base_pullback_min_pips,
        cost_overhead_pips=cost_overhead_pips,
        horizons=DEFAULT_HORIZONS,
    )
    rows = quality_filter_sweep(
        events,
        symbol=symbol,
    )

    return {
        "schema_version": "scalping-pullback-filter-sweep/0.1.0",
        "symbol": symbol,
        "m15_rows": int(len(m15)),
        "m5_rows": int(len(m5)),
        "state_rows": int(len(states)),
        "event_rows": int(len(events)),
        "pullback_lookback": pullback_lookback,
        "base_pullback_min_pips": base_pullback_min_pips,
        "cost_overhead_pips": cost_overhead_pips,
        "session_groups": SESSION_GROUPS,
        "direction_groups": DIRECTION_GROUPS,
        "spread_percentiles": DEFAULT_SPREAD_PERCENTILES,
        "regime_strengths": DEFAULT_REGIME_STRENGTHS,
        "pullback_mins": DEFAULT_PULLBACK_MINS,
        "summary": rows,
    }


def quality_filter_sweep(
    events: pd.DataFrame,
    *,
    symbol: str,
    session_groups: dict[str, tuple[str, ...]] = SESSION_GROUPS,
    direction_groups: dict[str, int | None] = DIRECTION_GROUPS,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    max_spread_slot_percentiles: tuple[float, ...] = (
        DEFAULT_SPREAD_PERCENTILES
    ),
    min_regime_strengths: tuple[float, ...] = DEFAULT_REGIME_STRENGTHS,
    min_pullback_pips: tuple[float, ...] = DEFAULT_PULLBACK_MINS,
) -> list[dict[str, Any]]:
    validate_events(events)

    rows: list[dict[str, Any]] = []

    for session_name, sessions in session_groups.items():
        session_mask = pd.Series(True, index=events.index)
        if sessions:
            session_mask = events["session"].isin(sessions)

        for direction_name, direction in direction_groups.items():
            direction_mask = pd.Series(True, index=events.index)
            if direction is not None:
                direction_mask = events["direction"] == direction

            for horizon in horizons:
                horizon_mask = events["horizon_bars"] == horizon

                for max_spread_pct in max_spread_slot_percentiles:
                    spread_mask = (
                        events["spread_slot_percentile"].notna()
                        & (
                            events["spread_slot_percentile"]
                            <= max_spread_pct
                        )
                    )

                    for min_strength in min_regime_strengths:
                        strength_mask = (
                            events["regime_strength"] >= min_strength
                        )

                        for min_pullback in min_pullback_pips:
                            pullback_mask = (
                                events["pullback_pips"].abs()
                                >= min_pullback
                            )
                            group = events[
                                session_mask
                                & direction_mask
                                & horizon_mask
                                & spread_mask
                                & strength_mask
                                & pullback_mask
                            ]
                            rows.append(
                                quality_filter_row(
                                    group,
                                    symbol=symbol,
                                    session_group=session_name,
                                    direction_group=direction_name,
                                    horizon_bars=horizon,
                                    max_spread_slot_percentile=(
                                        max_spread_pct
                                    ),
                                    min_regime_strength=min_strength,
                                    min_pullback_pips=min_pullback,
                                )
                            )

    rows.sort(
        key=lambda row: (
            row["session_group"],
            row["direction_group"],
            row["horizon_bars"],
            row["max_spread_slot_percentile"],
            row["min_regime_strength"],
            row["min_pullback_pips"],
        )
    )
    return rows


def quality_filter_row(
    group: pd.DataFrame,
    *,
    symbol: str,
    session_group: str,
    direction_group: str,
    horizon_bars: int,
    max_spread_slot_percentile: float,
    min_regime_strength: float,
    min_pullback_pips: float,
) -> dict[str, Any]:
    base = {
        "symbol": symbol,
        "session_group": session_group,
        "direction_group": direction_group,
        "horizon_bars": horizon_bars,
        "max_spread_slot_percentile": max_spread_slot_percentile,
        "min_regime_strength": min_regime_strength,
        "min_pullback_pips": min_pullback_pips,
        "events": int(len(group)),
        "mean_gross_pips": None,
        "median_gross_pips": None,
        "hit_rate": None,
        "mean_net_pips": None,
        "median_entry_spread_pips": None,
        "mean_entry_spread_pips": None,
    }

    if group.empty:
        return base

    gross = group["gross_pips"].astype(float)
    net = group["net_pips"].astype(float)
    spread = group["entry_spread_pips"].astype(float)

    return {
        **base,
        "mean_gross_pips": round(float(gross.mean()), 6),
        "median_gross_pips": round(float(gross.median()), 6),
        "hit_rate": round(float((gross > 0).mean()), 6),
        "mean_net_pips": round(float(net.mean()), 6),
        "median_entry_spread_pips": round(float(spread.median()), 6),
        "mean_entry_spread_pips": round(float(spread.mean()), 6),
    }


def validate_events(
    events: pd.DataFrame,
) -> None:
    if events.empty:
        raise ValueError("events cannot be empty")

    required = {
        "session",
        "direction",
        "horizon_bars",
        "spread_slot_percentile",
        "regime_strength",
        "pullback_pips",
        "gross_pips",
        "net_pips",
        "entry_spread_pips",
    }
    missing = required - set(events.columns)

    if missing:
        raise ValueError(f"events missing columns: {sorted(missing)}")


def write_filter_sweep(
    study: dict[str, Any],
    *,
    out_dir: Path = REPORTS_DIR / "scalping",
) -> tuple[Path, Path]:
    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    symbol = study["symbol"]
    stem = f"scalping_pullback_filter_sweep_{symbol}"
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
        fieldnames=SWEEP_COLUMNS,
    )
    writer.writeheader()

    for row in rows:
        writer.writerow(row)

    return buffer.getvalue()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "SC-01 diagnostic sweep: spread, regime strength, "
            "pullback size, session, side and horizon filters."
        )
    )
    parser.add_argument(
        "--symbol",
        default="USDJPY",
    )
    parser.add_argument(
        "--pullback-lookback",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--base-pullback-min-pips",
        type=float,
        default=2.0,
    )
    parser.add_argument(
        "--cost-overhead-pips",
        type=float,
        default=1.7,
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=SCALPING_REPORTS_DIR,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    study = run_filter_sweep_study(
        symbol=args.symbol,
        pullback_lookback=args.pullback_lookback,
        base_pullback_min_pips=args.base_pullback_min_pips,
        cost_overhead_pips=args.cost_overhead_pips,
        out_dir=args.out_dir,
    )
    json_path, csv_path = write_filter_sweep(
        study,
        out_dir=args.out_dir,
    )

    print(
        f"{args.symbol}: {len(study['summary'])} quality-filter rows "
        f"from {study['event_rows']} event-horizon rows"
    )
    print(f"SC-01 filter sweep JSON: {json_path}")
    print(f"SC-01 filter sweep CSV : {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
