"""
Walk-Forward validation harness (roadmap §75, v0.5 scope).

Rolling train/validation windows select parameters on the TRAIN
segment by a pre-registered metric (expectancy, tiebreak profit
factor) and immediately evaluate them on the next VALIDATION
segment, under the same explicit costs as the rest of F8.

Lockbox discipline (roadmap §74): the OOS period (2024-01-01 ..)
is NEVER touched by the walk-forward windows. The final out-of-
sample consultation requires an explicit --allow-oos flag plus a
logged event, exactly like the F8 sweep harness.

Pre-registration (decided BEFORE looking at results):

    metric     : expectancy (max), tiebreak profit_factor
    windows    : train 2y / val 1y / step 1y, 2015-01-01 .. 2024-01-01
    grids      : the F8 grids (docs/15), reused verbatim
    acceptance : >= 5/7 val windows positive net profit AND
                 mean val expectancy > 0 AND same return sign in
                 >= 5/7 windows

Usage:

    python -m research.walkforward --strategy time_series_momentum \
        --cost explicit
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from research.periods import (
    OOS_DATE_FROM,
    require_oos_allowed,
)
from research.runner import (
    REPO_ROOT,
    INSTRUMENT_REGISTRY,
    STRATEGY_REGISTRY,
    coerce_strategy_params,
    discover_strategy_class,
    run_single,
)
from research.sweep import (
    extract_row,
    parse_params,
    parse_sweep_spec,
    run_sweep,
    write_summary_csv,
)

REPORTS_DIR = REPO_ROOT / "research" / "reports"

# ---------------------------------------------------------------------------
# Pre-registered grids (F8 grids from docs/15, reused verbatim)
# ---------------------------------------------------------------------------

PREREGISTERED_GRIDS: dict[str, dict[str, list[str]]] = {
    "time_series_momentum": {
        "lookback": ["64", "96", "128", "160", "192"],
    },
    "ema_trend": {
        "fast_period": ["10", "15", "20", "25", "30"],
    },
    "mean_reversion": {
        "lookback": ["8", "16", "24", "32"],
    },
}

# Fixed params per strategy (baseline configuration from F8)
PREREGISTERED_FIXED_PARAMS: dict[str, dict[str, str]] = {
    "time_series_momentum": {"entry_threshold": "0.001"},
    "ema_trend": {"slow_period": "50"},
    "mean_reversion": {"entry_threshold": "-0.001"},
}

SELECTION_METRIC = "expectancy"
TIEBREAK_METRIC = "profit_factor"

WINDOW_START = "2015-01-01"
WINDOW_END = "2024-01-01"  # exclusive; OOS lockbox starts here
TRAIN_YEARS = 2
VAL_YEARS = 1
STEP_YEARS = 1

ACCEPT_MIN_POSITIVE_WINDOWS = 5
ACCEPT_MIN_WINDOWS = 7


# ---------------------------------------------------------------------------
# Window construction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WalkForwardWindow:
    """One rolling train/validation pair (contiguous, causal)."""

    label: str
    train_from: str
    train_to: str
    val_from: str
    val_to: str


def _add_years(date_text: str, years: int) -> str:
    parsed = datetime.strptime(date_text, "%Y-%m-%d")
    shifted = parsed.replace(year=parsed.year + years)
    return shifted.strftime("%Y-%m-%d")


def build_wf_windows(
    *,
    start: str = WINDOW_START,
    end: str = WINDOW_END,
    train_years: int = TRAIN_YEARS,
    val_years: int = VAL_YEARS,
    step_years: int = STEP_YEARS,
) -> list[WalkForwardWindow]:
    """
    Build rolling train/val windows from `start` to `end`.

    Windows are contiguous: train_to == val_from and each window
    starts `step_years` after the previous one. The last window
    must end exactly at `end`; windows never extend past it.
    """
    if train_years <= 0 or val_years <= 0 or step_years <= 0:
        raise ValueError(
            "train_years, val_years and step_years must be positive"
        )

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")

    if end_dt <= start_dt:
        raise ValueError("end must be later than start")

    windows: list[WalkForwardWindow] = []
    cursor = start_dt
    index = 1

    while True:
        train_from = cursor
        train_to = train_from.replace(
            year=train_from.year + train_years
        )
        val_from = train_to
        val_to = val_from.replace(
            year=val_from.year + val_years
        )

        if val_to > end_dt:
            break

        windows.append(
            WalkForwardWindow(
                label=f"WF-{index:02d}",
                train_from=train_from.strftime("%Y-%m-%d"),
                train_to=train_to.strftime("%Y-%m-%d"),
                val_from=val_from.strftime("%Y-%m-%d"),
                val_to=val_to.strftime("%Y-%m-%d"),
            )
        )

        cursor = cursor.replace(
            year=cursor.year + step_years
        )
        index += 1

    return windows


def windows_touch_oos(
    windows: list[WalkForwardWindow],
    *,
    oos_from: str = OOS_DATE_FROM,
) -> bool:
    """True when any validation segment reaches the OOS lockbox."""
    oos_dt = datetime.strptime(oos_from, "%Y-%m-%d")

    for window in windows:
        val_to = datetime.strptime(
            window.val_to,
            "%Y-%m-%d",
        )

        if val_to > oos_dt:
            return True

    return False


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def select_best(
    rows: list[dict[str, Any]],
    *,
    metric: str = SELECTION_METRIC,
    tiebreak: str = TIEBREAK_METRIC,
) -> dict[str, Any]:
    """
    Select the best row by the pre-registered metric.

    Expectancy is maximized; ties are broken by profit factor.
    The metric must be present in the rows.
    """
    if not rows:
        raise ValueError("cannot select from an empty row list")

    if metric not in rows[0]:
        raise ValueError(
            f"selection metric {metric!r} not present in rows; "
            f"available: {sorted(rows[0])}"
        )

    if tiebreak not in rows[0]:
        raise ValueError(
            f"tiebreak metric {tiebreak!r} not present in rows"
        )

    def _key(row: dict[str, Any]) -> tuple[float, float]:
        return (
            float(row[metric]),
            float(row[tiebreak]),
        )

    return max(rows, key=_key)


# ---------------------------------------------------------------------------
# Walk-forward execution
# ---------------------------------------------------------------------------


def run_walk_forward(
    *,
    strategy_key: str,
    windows: list[WalkForwardWindow],
    symbol: str,
    timeframe: str,
    initial_capital: float,
    fixed_quantity: float,
    cost_mode: str,
    cost_params: dict[str, float],
    cost_multiplier: float,
    out_dir: Path,
    write_equity: bool,
) -> list[dict[str, Any]]:
    """Run one strategy over all windows (train sweep -> val run)."""
    if strategy_key not in PREREGISTERED_GRIDS:
        raise ValueError(
            f"strategy {strategy_key!r} has no pre-registered grid; "
            f"available: {sorted(PREREGISTERED_GRIDS)}"
        )

    strategy_class = discover_strategy_class(
        STRATEGY_REGISTRY[strategy_key]
    )
    strategy_module = STRATEGY_REGISTRY[strategy_key]

    grid_key, grid_values = next(
        iter(PREREGISTERED_GRIDS[strategy_key].items())
    )
    fixed_params = PREREGISTERED_FIXED_PARAMS[strategy_key]

    rows: list[dict[str, Any]] = []

    for window in windows:
        # Train: sweep the pre-registered grid on the train segment.
        train_rows = run_sweep(
            strategy_key=strategy_key,
            sweep_key=grid_key,
            sweep_values=grid_values,
            fixed_params=fixed_params,
            symbol=symbol,
            timeframe=timeframe,
            date_from=window.train_from,
            date_to=window.train_to,
            initial_capital=initial_capital,
            fixed_quantity=fixed_quantity,
            cost_mode=cost_mode,
            cost_params=cost_params,
            cost_multiplier=cost_multiplier,
            out_dir=out_dir,
            write_equity=write_equity,
        )

        best = select_best(train_rows)

        # Validation: run the selected parameters on the next segment.
        selected_params = {
            grid_key: best["param_value"],
            **fixed_params,
        }

        strategy_params = coerce_strategy_params(
            strategy_class,
            selected_params,
        )

        report_path = run_single(
            symbol=symbol,
            timeframe=timeframe,
            strategy_class=strategy_class,
            strategy_module=strategy_module,
            tag=f"wf-{window.label}-val",
            strategy_params=strategy_params,
            date_from=window.val_from,
            date_to=window.val_to,
            initial_capital=initial_capital,
            fixed_quantity=fixed_quantity,
            cost_mode=cost_mode,
            cost_params=cost_params,
            cost_multiplier=cost_multiplier,
            out_dir=out_dir,
            write_equity=write_equity,
        )

        val_row = extract_row(report_path)
        val_row["window"] = window.label
        val_row["train_from"] = window.train_from
        val_row["train_to"] = window.train_to
        val_row["val_from"] = window.val_from
        val_row["val_to"] = window.val_to
        val_row["selected_param_key"] = grid_key
        val_row["selected_param_value"] = best["param_value"]
        val_row["train_expectancy"] = best["expectancy"]
        val_row["train_profit_factor"] = best["profit_factor"]
        val_row["train_net_profit"] = best["net_profit"]

        rows.append(val_row)

    return rows


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def summarize_wf(
    rows: list[dict[str, Any]],
    *,
    min_positive: int = ACCEPT_MIN_POSITIVE_WINDOWS,
) -> dict[str, Any]:
    """Aggregate walk-forward validation rows into a verdict."""
    if not rows:
        raise ValueError("cannot summarize an empty window list")

    total = len(rows)
    positives = sum(
        1 for row in rows if row["net_profit"] > 0
    )
    negative = total - positives

    avg_return = sum(row["return_pct"] for row in rows) / total
    avg_net = sum(row["net_profit"] for row in rows) / total
    avg_expectancy = sum(
        row["expectancy"] for row in rows
    ) / total

    signs = [
        "+" if row["net_profit"] > 1e-9
        else ("-" if row["net_profit"] < -1e-9 else "0")
        for row in rows
    ]
    same_sign = signs.count("+") >= min_positive or (
        signs.count("-") >= min_positive
    )

    param_counts: dict[str, int] = {}

    for row in rows:
        value = str(row["selected_param_value"])
        param_counts[value] = param_counts.get(value, 0) + 1

    most_selected = max(
        param_counts,
        key=lambda key: (
            param_counts[key],
            # stable tiebreak: prefer the smallest value
            -float(key) if key.replace(".", "", 1).isdigit()
            else 0.0,
        ),
    )

    accepted = (
        positives >= min_positive
        and avg_expectancy > 0
        and same_sign
    )

    return {
        "windows_total": total,
        "windows_positive": positives,
        "windows_negative": negative,
        "positive_rate": round(positives / total, 4),
        "avg_val_return_pct": round(avg_return, 4),
        "avg_val_net_profit": round(avg_net, 2),
        "avg_val_expectancy": round(avg_expectancy, 4),
        "signal_consistent": same_sign,
        "param_most_selected": most_selected,
        "param_selection_count": param_counts[most_selected],
        "param_distinct_count": len(param_counts),
        "accepted": accepted,
    }


def print_wf_table(
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    headers = [
        "window",
        "val_range",
        "sel_param",
        "train_exp",
        "trades",
        "net_profit",
        "return_pct",
        "expectancy",
        "pf",
    ]

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["window"]),
                    f"{row['val_from'][2:]}->{row['val_to'][2:]}",
                    str(row["selected_param_value"]),
                    f"{row['train_expectancy']:.4f}",
                    str(row["trades"]),
                    f"{row['net_profit']:.2f}",
                    f"{row['return_pct']:.4f}",
                    f"{row['expectancy']:.4f}",
                    f"{row['profit_factor']:.4f}",
                ]
            )
            + " |"
        )

    print("\n".join(lines))

    print(
        "\n".join(
            [
                "",
                "--- WALK-FORWARD SUMMARY ---",
                f"windows        : "
                f"{summary['windows_positive']}/"
                f"{summary['windows_total']} positive",
                f"positive rate  : "
                f"{summary['positive_rate']:.0%}",
                f"avg val return : "
                f"{summary['avg_val_return_pct']:.4f}%",
                f"avg val net    : "
                f"{summary['avg_val_net_profit']:.2f} USD",
                f"avg expectancy : "
                f"{summary['avg_val_expectancy']:.4f}",
                f"signal         : "
                f"{'CONSISTENT' if summary['signal_consistent'] else 'MIXED'}",
                f"param selected : "
                f"{summary['param_most_selected']} "
                f"({summary['param_selection_count']}/"
                f"{summary['windows_total']}, "
                f"{summary['param_distinct_count']} distinct)",
                f"verdict        : "
                f"{'ACCEPT (edge transferable)' if summary['accepted'] else 'REJECT (no transferable edge)'}",
            ]
        )
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Walk-forward validation harness (roadmap §75): "
            "rolling train (2y) / val (1y) windows with "
            "pre-registered grids and expectancy selection."
        )
    )

    parser.add_argument(
        "--strategy",
        required=True,
        choices=sorted(PREREGISTERED_GRIDS),
        help="strategy key with a pre-registered walk-forward grid",
    )

    parser.add_argument(
        "--allow-oos",
        action="store_true",
        help=(
            "explicitly unlock the OOS lockbox for a final "
            "out-of-sample consultation (roadmap §74)"
        ),
    )

    parser.add_argument(
        "--symbol",
        default="EURUSD",
        choices=sorted(INSTRUMENT_REGISTRY),
    )

    parser.add_argument(
        "--timeframe",
        default="M15",
        choices=("M15", "H1", "H4"),
    )

    parser.add_argument(
        "--initial-capital",
        type=float,
        default=10000.0,
    )

    parser.add_argument(
        "--fixed-quantity",
        type=float,
        default=0.01,
    )

    parser.add_argument(
        "--cost",
        choices=("zero", "explicit"),
        default="explicit",
        help="cost model (default: explicit for F8 parity)",
    )

    parser.add_argument(
        "--cost-multiplier",
        type=float,
        default=1.0,
    )

    parser.add_argument(
        "--spread-pips",
        type=float,
        default=2.0,
    )

    parser.add_argument(
        "--slippage-pips",
        type=float,
        default=0.5,
    )

    parser.add_argument(
        "--commission",
        type=float,
        default=3.50,
    )

    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPORTS_DIR,
    )

    parser.add_argument(
        "--equity-csv",
        action="store_true",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()

    windows = build_wf_windows()

    if windows_touch_oos(windows):
        # The standard windows never touch OOS; this guard exists
        # for custom window configs or future redefinitions.
        require_oos_allowed(allow_oos=args.allow_oos)

    cost_params = {
        "spread_pips": args.spread_pips,
        "slippage_pips": args.slippage_pips,
        "commission_per_lot_per_side": args.commission,
    }

    rows = run_walk_forward(
        strategy_key=args.strategy,
        windows=windows,
        symbol=args.symbol,
        timeframe=args.timeframe,
        initial_capital=args.initial_capital,
        fixed_quantity=args.fixed_quantity,
        cost_mode=args.cost,
        cost_params=cost_params,
        cost_multiplier=args.cost_multiplier,
        out_dir=args.out_dir,
        write_equity=args.equity_csv,
    )

    for row in rows:
        row["cost"] = args.cost
        row["cost_multiplier"] = args.cost_multiplier

    summary = summarize_wf(rows)

    print(f"\n--- {args.cost.upper()} ---")
    print_wf_table(rows, summary)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = (
        args.out_dir
        / f"{args.strategy.upper()}_walkforward.csv"
    )

    write_summary_csv(rows, csv_path)

    print(f"\nSummary written: {csv_path}")
    print(
        f"Verdict: "
        f"{'ACCEPT' if summary['accepted'] else 'REJECT'}"
    )


if __name__ == "__main__":
    main()
