from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any

import pandas as pd

from backtest.clock import SimulationClock
from backtest.context import BacktestContextBuilder
from backtest.feed import HistoricalBarFeed
from backtest.instruments import instrument_specification
from backtest.models import BacktestConfig, Timeframe
from backtest.models.enums import SimulationPhase
from research.alpha_diagnostic_matrix import write_variant_configs
from research.features import slot_percentile
from research.runner import REPORTS_DIR
from research.scalping_spread_profile import session_label
from strategy import DeclarativeEnsembleStrategy

SCALPING_REPORTS_DIR = REPORTS_DIR / "scalping"

DEFAULT_HORIZONS = (1, 2, 3, 6)

SUMMARY_COLUMNS = [
    "symbol",
    "session",
    "direction",
    "horizon_bars",
    "events",
    "mean_gross_pips",
    "median_gross_pips",
    "hit_rate",
    "mean_net_pips",
    "median_entry_spread_pips",
    "mean_entry_spread_pips",
]


def load_m15_frame(
    *,
    symbol: str,
    base_path: Path = Path("data/raw"),
) -> pd.DataFrame:
    path = base_path / symbol / "M15.parquet"

    if not path.exists():
        raise FileNotFoundError(path)

    return pd.read_parquet(path).sort_values("time").reset_index(drop=True)


def load_m5_frame(
    *,
    symbol: str,
    base_path: Path = Path("data/scalping/processed"),
) -> pd.DataFrame:
    path = base_path / symbol / "M5.parquet"

    if not path.exists():
        raise FileNotFoundError(path)

    frame = pd.read_parquet(path).sort_values("time").reset_index(drop=True)

    if "complete" in frame.columns:
        frame = frame[frame["complete"]].copy()

    return frame.reset_index(drop=True)


def build_m15_direction_states(
    m15: pd.DataFrame,
    *,
    symbol: str,
    config_path: Path,
) -> pd.DataFrame:
    if m15.empty:
        raise ValueError("m15 cannot be empty")

    date_from = m15["time"].iloc[0].to_pydatetime()
    date_to = (
        m15["time"].iloc[-1] + pd.Timedelta(minutes=15)
    ).to_pydatetime()

    config = BacktestConfig(
        symbol=symbol,
        timeframe=Timeframe.M15,
        date_from=date_from,
        date_to=date_to,
        initial_capital=10000.0,
    )
    feed = HistoricalBarFeed(m15, config)
    clock = SimulationClock(feed.bar_starts, Timeframe.M15)
    strategy = DeclarativeEnsembleStrategy(
        symbol=symbol,
        config_path=str(config_path),
    )
    builder = BacktestContextBuilder(feed, clock)

    rows = []

    for event in clock.events():
        if event.phase != SimulationPhase.BAR_CLOSE:
            continue

        context = builder.build(
            event,
            closed_bar_limit=strategy.closed_bar_limit,
        )
        signal = strategy.on_bar(context)
        metadata = signal.metadata
        value = float(metadata["blended_value"])
        abstained = bool(metadata["blended_abstained"])

        if abstained:
            direction = 0
        elif value >= float(metadata["enter_long"]):
            direction = 1
        elif value <= float(metadata["enter_short"]):
            direction = -1
        else:
            direction = 0

        rows.append(
            {
                "state_time": event.timestamp,
                "blended_value": value,
                "direction": direction,
                "contributors": len(metadata["contributors"]),
                "abstained": abstained,
            }
        )

    return pd.DataFrame(rows)


def build_pullback_events(
    m5: pd.DataFrame,
    states: pd.DataFrame,
    *,
    symbol: str,
    pullback_lookback: int = 3,
    pullback_min_pips: float = 2.0,
    cost_overhead_pips: float = 1.7,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
) -> pd.DataFrame:
    validate_inputs(
        m5,
        states,
        pullback_lookback=pullback_lookback,
        pullback_min_pips=pullback_min_pips,
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

    previous_close = merged["close"].shift(pullback_lookback)
    direction = merged["direction"].astype(float)
    merged["pullback_pips"] = (
        direction
        * (merged["close"] - previous_close)
        / spec.pip_size
    )
    merged["body_pips"] = (
        direction
        * (merged["close"] - merged["open"])
        / spec.pip_size
    )
    merged["qualifies"] = (
        (merged["direction"] != 0)
        & (merged["pullback_pips"] <= -pullback_min_pips)
        & (merged["body_pips"] > 0)
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
                    "pullback_pips",
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


def summarize_events(
    events: pd.DataFrame,
    *,
    symbol: str,
) -> list[dict[str, Any]]:
    if events.empty:
        return []

    rows = []

    groupings = [
        ["session", "direction", "horizon_bars"],
        ["session", "horizon_bars"],
        ["horizon_bars"],
    ]

    for grouping in groupings:
        for key, group in events.groupby(grouping):
            if not isinstance(key, tuple):
                key = (key,)

            values = dict(zip(grouping, key))
            session = str(values.get("session", "all"))
            direction = values.get("direction", "all")
            rows.append(
                summary_row(
                    group,
                    symbol=symbol,
                    session=session,
                    direction=direction,
                    horizon_bars=int(values["horizon_bars"]),
                )
            )

    rows.sort(
        key=lambda row: (
            row["session"],
            str(row["direction"]),
            row["horizon_bars"],
        )
    )
    return rows


def summary_row(
    group: pd.DataFrame,
    *,
    symbol: str,
    session: str,
    direction: int | str,
    horizon_bars: int,
) -> dict[str, Any]:
    gross = group["gross_pips"].astype(float)
    net = group["net_pips"].astype(float)
    spread = group["entry_spread_pips"].astype(float)

    return {
        "symbol": symbol,
        "session": session,
        "direction": direction,
        "horizon_bars": horizon_bars,
        "events": int(len(group)),
        "mean_gross_pips": round(float(gross.mean()), 6),
        "median_gross_pips": round(float(gross.median()), 6),
        "hit_rate": round(float((gross > 0).mean()), 6),
        "mean_net_pips": round(float(net.mean()), 6),
        "median_entry_spread_pips": round(float(spread.median()), 6),
        "mean_entry_spread_pips": round(float(spread.mean()), 6),
    }


def run_study(
    *,
    symbol: str,
    pullback_lookback: int = 3,
    pullback_min_pips: float = 2.0,
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
        pullback_min_pips=pullback_min_pips,
        cost_overhead_pips=cost_overhead_pips,
    )
    rows = summarize_events(
        events,
        symbol=symbol,
    )

    return {
        "schema_version": "scalping-pullback-study/0.1.0",
        "symbol": symbol,
        "m15_rows": int(len(m15)),
        "m5_rows": int(len(m5)),
        "state_rows": int(len(states)),
        "event_rows": int(len(events)),
        "pullback_lookback": pullback_lookback,
        "pullback_min_pips": pullback_min_pips,
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
    stem = f"scalping_pullback_study_{symbol}"
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
    pullback_lookback: int,
    pullback_min_pips: float,
    horizons: tuple[int, ...],
) -> None:
    if m5.empty:
        raise ValueError("m5 cannot be empty")

    if states.empty:
        raise ValueError("states cannot be empty")

    if pullback_lookback <= 0:
        raise ValueError("pullback_lookback must be positive")

    if pullback_min_pips <= 0:
        raise ValueError("pullback_min_pips must be positive")

    if not horizons or any(horizon <= 0 for horizon in horizons):
        raise ValueError("horizons must contain positive integers")

    for column in ["time", "open", "close", "spread"]:
        if column not in m5.columns:
            raise ValueError(f"m5 missing column: {column}")

    for column in ["state_time", "direction", "blended_value"]:
        if column not in states.columns:
            raise ValueError(f"states missing column: {column}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stage-1 SC-01 study: M5 pullbacks conditioned on the "
            "M15 ensemble_regime_cost state."
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
        "--pullback-min-pips",
        type=float,
        default=2.0,
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
        pullback_lookback=args.pullback_lookback,
        pullback_min_pips=args.pullback_min_pips,
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
    print(f"SC-01 pullback JSON: {json_path}")
    print(f"SC-01 pullback CSV : {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
