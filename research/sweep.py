"""
Structured F8 sensitivity and subperiod harness for the FOREX
research runner.

Local sensitivity discipline (repo AGENTS.md §5-6, roadmap §71):

- exactly ONE parameter is swept at a time;
- the grid must be declared BEFORE running (no selection
  after the fact);
- results are compared as stability regions, not maxima;
- every run is a full auditable report produced by
  research/runner.py run_single().

Subperiod analysis (roadmap §73) runs the same strategy over
the four standard F8 windows.

Usage:

    # Local sensitivity over lookback (start:end:step)
    python -m research.sweep --strategy time_series_momentum \
        --range lookback=96:192:32 --cost explicit

    # Explicit value list
    python -m research.sweep --strategy mean_reversion \
        --values lookback=32,48,64

    # Fixed parameters stay fixed during the sweep
    python -m research.sweep --strategy time_series_momentum \
        --range lookback=96:192:32 --param entry_threshold=0.002

    # Standard F8 subperiods
    python -m research.sweep --strategy ema_trend --subperiods --cost explicit

    # Pre-registered Dev/Val/OOS periods (roadmap §74, §78)
    python -m research.sweep --strategy ema_trend --period dev --cost explicit
    python -m research.sweep --strategy ema_trend --period val --cost explicit

    # OOS is a lockbox: refuses to run without --allow-oos
    python -m research.sweep --strategy ema_trend --period oos

    # Stability analysis: development vs validation, never touches OOS
    python -m research.sweep --strategy ema_trend --stability --cost explicit
"""

from __future__ import annotations

import argparse
import json
from dataclasses import fields
from pathlib import Path
from typing import Any

from research.periods import (
    OOS_LOCKBOX_LABEL,
    PERIOD_ORDER,
    RESEARCH_PERIODS,
    ResearchPeriod,
    require_oos_allowed,
    resolve_period,
)
from research.runner import (
    REPO_ROOT,
    INSTRUMENT_REGISTRY,
    STRATEGY_REGISTRY,
    coerce_strategy_params,
    discover_strategy_class,
    parse_params,
    run_single,
)

REPORTS_DIR = REPO_ROOT / "research" / "reports"

# Period roles defined in research/periods.py (roadmap §74, §78):
#   dev -> 2015-2020, val -> 2021-2023, oos (lockbox) -> 2024-2026
PERIOD_ROLES = {label: period.role for label, period in RESEARCH_PERIODS.items()}


# ---------------------------------------------------------------------------
# Period comparison (stability analysis)
# ---------------------------------------------------------------------------


def compare_period_rows(
    dev_row: dict[str, Any],
    val_row: dict[str, Any],
) -> dict[str, Any]:
    """
    Structured stability comparison between development and validation
    rows (roadmap §78 stability analysis).

    Returns a dict with the delta of key metrics plus a signal
    consistency verdict: the sign of the net result must not flip
    between dev and val for the spec to be considered stable.
    """
    dev_return = dev_row["return_pct"]
    val_return = val_row["return_pct"]

    dev_pf = dev_row["profit_factor"]
    val_pf = val_row["profit_factor"]

    def _sign(value: float) -> str:
        if value > 1e-9:
            return "+"
        if value < -1e-9:
            return "-"
        return "0"

    consistent_sign = _sign(dev_return) == _sign(val_return)

    return {
        "period": "dev-vs-val",
        "dev_return_pct": dev_return,
        "val_return_pct": val_return,
        "return_delta_pct": round(val_return - dev_return, 4),
        "dev_net_profit": dev_row["net_profit"],
        "val_net_profit": val_row["net_profit"],
        "net_profit_delta": round(
            val_row["net_profit"] - dev_row["net_profit"],
            2,
        ),
        "dev_max_dd_pct": dev_row["max_dd_pct"],
        "val_max_dd_pct": val_row["max_dd_pct"],
        "max_dd_delta_pct": round(
            val_row["max_dd_pct"] - dev_row["max_dd_pct"],
            4,
        ),
        "dev_win_rate": dev_row["win_rate"],
        "val_win_rate": val_row["win_rate"],
        "dev_profit_factor": dev_pf,
        "val_profit_factor": val_pf,
        "profit_factor_delta": round(
            val_pf - dev_pf,
            6,
        ),
        "signal_consistent": consistent_sign,
    }

STANDARD_SUBPERIODS: tuple[tuple[str, str, str], ...] = (
    ("2015-2017", "2015-01-01", "2018-01-01"),
    ("2018-2020", "2018-01-01", "2021-01-01"),
    ("2021-2023", "2021-01-01", "2024-01-01"),
    ("2024-2026", "2024-01-01", "2027-01-01"),
)


def parse_range(
    raw: str,
) -> list[str]:
    """
    Parse start:end:step into raw string values.

    The end value is inclusive. Float-safe iteration is used.
    """
    parts = raw.split(":")

    if len(parts) != 3:
        raise ValueError(
            "--range must use key=start:end:step syntax, "
            f"got {raw!r}"
        )

    start_text, end_text, step_text = (
        part.strip() for part in parts
    )

    start = float(start_text)
    end = float(end_text)
    step = float(step_text)

    if not (start <= end):
        raise ValueError(
            "range start must be <= end"
        )

    if step <= 0:
        raise ValueError(
            "range step must be positive"
        )

    values: list[str] = []
    current = start

    while current <= end + (step * 1e-9):
        values.append(
            format(current, "g")
        )
        current += step

    return values


def parse_values(
    raw: str,
) -> list[str]:
    """Parse key=v1,v2,v3 into raw string values."""
    parts = [
        part.strip()
        for part in raw.split(",")
    ]

    if not parts or any(not part for part in parts):
        raise ValueError(
            "--values must use key=v1,v2,v3 syntax, "
            f"got {raw!r}"
        )

    return parts


def parse_sweep_spec(
    raw: str,
    *,
    mode: str,
) -> tuple[str, list[str]]:
    """Split key=spec and parse the value list for the mode."""
    if "=" not in raw:
        raise ValueError(
            f"--{mode} must use key=... syntax, got {raw!r}"
        )

    key, spec = raw.split("=", 1)
    key = key.strip()

    if not key:
        raise ValueError(
            f"--{mode} key cannot be empty"
        )

    if mode == "range":
        values = parse_range(spec)
    elif mode == "values":
        values = parse_values(spec)
    else:
        raise ValueError(f"unsupported sweep mode: {mode!r}")

    return key, values


def validate_sweep_key(
    strategy_class: type,
    key: str,
) -> None:
    """The swept key must be a parameter of the strategy."""
    dataclass_names = {
        field.name for field in fields(strategy_class)
    }

    if key not in dataclass_names:
        raise ValueError(
            f"unknown parameter {key!r} for "
            f"{strategy_class.__name__}; valid params: "
            + ", ".join(sorted(dataclass_names))
        )


# ---------------------------------------------------------------------------
# Sweep execution
# ---------------------------------------------------------------------------


def run_sweep(
    *,
    strategy_key: str,
    sweep_key: str,
    sweep_values: list[str],
    fixed_params: dict[str, str],
    symbol: str,
    timeframe: str,
    date_from: str | None,
    date_to: str | None,
    initial_capital: float,
    fixed_quantity: float,
    cost_mode: str,
    cost_params: dict[str, float],
    cost_multiplier: float,
    out_dir: Path,
    write_equity: bool,
) -> list[dict[str, Any]]:
    """Run one strategy over one parameter grid (local sensitivity)."""
    strategy_class = discover_strategy_class(
        STRATEGY_REGISTRY[strategy_key]
    )
    strategy_module = STRATEGY_REGISTRY[strategy_key]

    validate_sweep_key(
        strategy_class,
        sweep_key,
    )

    rows: list[dict[str, Any]] = []

    for raw_value in sweep_values:
        strategy_params = coerce_strategy_params(
            strategy_class,
            {
                **fixed_params,
                sweep_key: raw_value,
            },
        )

        report_path = run_single(
            symbol=symbol,
            timeframe=timeframe,
            strategy_class=strategy_class,
            strategy_module=strategy_module,
            tag=f"sweep-{sweep_key}={raw_value}",
            strategy_params=strategy_params,
            date_from=date_from,
            date_to=date_to,
            initial_capital=initial_capital,
            fixed_quantity=fixed_quantity,
            cost_mode=cost_mode,
            cost_params=cost_params,
            cost_multiplier=cost_multiplier,
            out_dir=out_dir,
            write_equity=write_equity,
        )

        rows.append(
            extract_row(report_path)
        )

        rows[-1]["param_key"] = sweep_key
        rows[-1]["param_value"] = raw_value

    return rows


def run_subperiods(
    *,
    strategy_key: str,
    fixed_params: dict[str, str],
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
    """Run one strategy over the four standard F8 subperiods."""
    strategy_class = discover_strategy_class(
        STRATEGY_REGISTRY[strategy_key]
    )
    strategy_module = STRATEGY_REGISTRY[strategy_key]

    strategy_params = coerce_strategy_params(
        strategy_class,
        fixed_params,
    )

    rows: list[dict[str, Any]] = []

    for label, date_from, date_to in STANDARD_SUBPERIODS:
        report_path = run_single(
            symbol=symbol,
            timeframe=timeframe,
            strategy_class=strategy_class,
            strategy_module=strategy_module,
            tag=f"sub-{label}",
            strategy_params=strategy_params,
            date_from=date_from,
            date_to=date_to,
            initial_capital=initial_capital,
            fixed_quantity=fixed_quantity,
            cost_mode=cost_mode,
            cost_params=cost_params,
            cost_multiplier=cost_multiplier,
            out_dir=out_dir,
            write_equity=write_equity,
        )

        row = extract_row(report_path)
        row["period"] = label
        rows.append(row)

    return rows


def run_period(
    *,
    strategy_key: str,
    period: ResearchPeriod,
    fixed_params: dict[str, str],
    symbol: str,
    timeframe: str,
    initial_capital: float,
    fixed_quantity: float,
    cost_mode: str,
    cost_params: dict[str, float],
    cost_multiplier: float,
    out_dir: Path,
    write_equity: bool,
) -> dict[str, Any]:
    """Run one strategy over a pre-registered Dev/Val/OOS period."""
    strategy_class = discover_strategy_class(
        STRATEGY_REGISTRY[strategy_key]
    )
    strategy_module = STRATEGY_REGISTRY[strategy_key]

    strategy_params = coerce_strategy_params(
        strategy_class,
        fixed_params,
    )

    report_path = run_single(
        symbol=symbol,
        timeframe=timeframe,
        strategy_class=strategy_class,
        strategy_module=strategy_module,
        tag=f"period-{period.label}",
        strategy_params=strategy_params,
        date_from=period.date_from,
        date_to=period.date_to,
        initial_capital=initial_capital,
        fixed_quantity=fixed_quantity,
        cost_mode=cost_mode,
        cost_params=cost_params,
        cost_multiplier=cost_multiplier,
        out_dir=out_dir,
        write_equity=write_equity,
    )

    row = extract_row(report_path)
    row["period"] = period.label
    return row


def run_stability(
    *,
    strategy_key: str,
    fixed_params: dict[str, str],
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
    """
    Stability analysis: run development + validation with identical
    configuration and compare the two rows (roadmap §78).

    The OOS lockbox is never touched here.
    """
    dev_row = run_period(
        strategy_key=strategy_key,
        period=RESEARCH_PERIODS["dev"],
        fixed_params=fixed_params,
        symbol=symbol,
        timeframe=timeframe,
        initial_capital=initial_capital,
        fixed_quantity=fixed_quantity,
        cost_mode=cost_mode,
        cost_params=cost_params,
        cost_multiplier=cost_multiplier,
        out_dir=out_dir,
        write_equity=write_equity,
    )

    val_row = run_period(
        strategy_key=strategy_key,
        period=RESEARCH_PERIODS["val"],
        fixed_params=fixed_params,
        symbol=symbol,
        timeframe=timeframe,
        initial_capital=initial_capital,
        fixed_quantity=fixed_quantity,
        cost_mode=cost_mode,
        cost_params=cost_params,
        cost_multiplier=cost_multiplier,
        out_dir=out_dir,
        write_equity=write_equity,
    )

    comparison = compare_period_rows(
        dev_row,
        val_row,
    )

    return [dev_row, val_row, comparison]


def extract_row(
    report_path: Path,
) -> dict[str, Any]:
    """Extract the comparison row from a runner report JSON."""
    report = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    config = report["config"]
    performance = report["performance"]

    return {
        "strategy": config["strategy_id"],
        "param_key": None,
        "param_value": None,
        "period": None,
        "tag": config.get("tag") or "",
        "date_from": config["date_from"][:10],
        "date_to": config["date_to"][:10],
        "trades": performance["trades"],
        "net_profit": round(
            performance["net_profit"],
            2,
        ),
        "return_pct": round(
            performance["total_return_pct"],
            4,
        ),
        "max_dd_pct": round(
            performance["max_drawdown_pct"],
            4,
        ),
        "win_rate": round(
            performance["win_rate"],
            2,
        ),
        "profit_factor": round(
            performance["profit_factor"],
            6,
        ),
        "avg_trade": round(
            performance["average_trade"],
            4,
        ),
        "expectancy": round(
            performance["expectancy"],
            4,
        ),
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_summary_csv(
    rows: list[dict[str, Any]],
    path: Path,
) -> None:
    import csv

    fieldnames = [
        "strategy",
        "param_key",
        "param_value",
        "period",
        "tag",
        "date_from",
        "date_to",
        "trades",
        "net_profit",
        "return_pct",
        "max_dd_pct",
        "win_rate",
        "profit_factor",
        "avg_trade",
        "expectancy",
        "cost",
        "cost_multiplier",
        "signal_consistent",
        "dev_return_pct",
        "val_return_pct",
        "return_delta_pct",
        "dev_net_profit",
        "val_net_profit",
        "net_profit_delta",
        "dev_max_dd_pct",
        "val_max_dd_pct",
        "max_dd_delta_pct",
        "dev_win_rate",
        "val_win_rate",
        "dev_profit_factor",
        "val_profit_factor",
        "profit_factor_delta",
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in rows:
            row["signal_consistent"] = (
                row.get("signal_consistent")
                if row.get("period") == "dev-vs-val"
                else ""
            )

            writer.writerow(row)


def print_table(
    rows: list[dict[str, Any]],
    *,
    value_label: str,
) -> None:
    if value_label == "period":
        headers = [
            "period",
            "trades",
            "net_profit",
            "return_pct",
            "max_dd_pct",
            "win_rate",
            "profit_factor",
            "expectancy",
        ]
    else:
        headers = [
            value_label,
            "period",
            "trades",
            "net_profit",
            "return_pct",
            "max_dd_pct",
            "win_rate",
            "profit_factor",
            "expectancy",
        ]

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for row in rows:
        cells = [str(row.get("period") or "")]

        if value_label != "period":
            cells.insert(
                0,
                str(row.get("param_value") or ""),
            )

        cells.extend(
            [
                str(row["trades"]),
                str(row["net_profit"]),
                str(row["return_pct"]),
                str(row["max_dd_pct"]),
                str(row["win_rate"]),
                str(row["profit_factor"]),
                str(row["expectancy"]),
            ]
        )

        lines.append(
            "| " + " | ".join(cells) + " |"
        )

    print("\n".join(lines))


def print_stability_table(
    rows: list[dict[str, Any]],
) -> None:
    """Print the dev/val/comparison stability table."""
    headers = [
        "period",
        "return_pct",
        "net_profit",
        "max_dd_pct",
        "win_rate",
        "profit_factor",
        "signal",
    ]

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for row in rows:
        if row["period"] == "dev-vs-val":
            cells = [
                "dev-vs-val",
                f"{row['dev_return_pct']} -> {row['val_return_pct']}"
                f" (d {row['return_delta_pct']})",
                f"{row['dev_net_profit']} -> {row['val_net_profit']}"
                f" (d {row['net_profit_delta']})",
                f"{row['dev_max_dd_pct']} -> {row['val_max_dd_pct']}"
                f" (d {row['max_dd_delta_pct']})",
                f"{row['dev_win_rate']} -> {row['val_win_rate']}",
                f"{row['dev_profit_factor']} -> {row['val_profit_factor']}"
                f" (d {row['profit_factor_delta']})",
                "CONSISTENT" if row["signal_consistent"] else "FLIPPED",
            ]
        else:
            cells = [
                str(row["period"]),
                str(row["return_pct"]),
                str(row["net_profit"]),
                str(row["max_dd_pct"]),
                str(row["win_rate"]),
                str(row["profit_factor"]),
                "",
            ]

        lines.append("| " + " | ".join(cells) + " |")

    print("\n".join(lines))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "F8 sensitivity / subperiod harness over "
            "research/runner.py"
        )
    )

    parser.add_argument(
        "--strategy",
        required=True,
        choices=sorted(STRATEGY_REGISTRY),
    )

    parser.add_argument(
        "--range",
        default=None,
        help=(
            "sweep one parameter: key=start:end:step "
            "(end inclusive)"
        ),
    )

    parser.add_argument(
        "--values",
        default=None,
        help="sweep one parameter: key=v1,v2,v3",
    )

    parser.add_argument(
        "--subperiods",
        action="store_true",
        help="run the four standard F8 subperiods",
    )

    parser.add_argument(
        "--period",
        default=None,
        choices=PERIOD_ORDER,
        help=(
            "run a pre-registered research period: "
            "dev (2015-2020), val (2021-2023), "
            "oos (lockbox, requires --allow-oos)"
        ),
    )

    parser.add_argument(
        "--stability",
        action="store_true",
        help=(
            "run development + validation and print the "
            "structured comparison (never touches OOS)"
        ),
    )

    parser.add_argument(
        "--allow-oos",
        action="store_true",
        help="explicitly unlock the OOS lockbox (roadmap §74)",
    )

    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="fixed strategy parameter (repeatable)",
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
        "--date-from",
        default=None,
        help="inclusive start, UTC",
    )

    parser.add_argument(
        "--date-to",
        default=None,
        help="exclusive end, UTC",
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
        choices=("zero", "explicit", "both"),
        default="explicit",
        help="cost model (default: explicit for F8)",
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

    modes = [
        args.range is not None,
        args.values is not None,
        args.subperiods,
        args.period is not None,
        args.stability,
    ]

    if sum(modes) != 1:
        raise ValueError(
            "exactly one of --range, --values, --subperiods, "
            "--period or --stability is required"
        )

    if args.period == OOS_LOCKBOX_LABEL:
        require_oos_allowed(
            allow_oos=args.allow_oos,
        )

    fixed_params = parse_params(args.param)

    cost_params = {
        "spread_pips": args.spread_pips,
        "slippage_pips": args.slippage_pips,
        "commission_per_lot_per_side": args.commission,
    }

    cost_modes = (
        ("zero", "explicit")
        if args.cost == "both"
        else (args.cost,)
    )

    all_rows: list[dict[str, Any]] = []
    value_label = "param_value"

    for cost_mode in cost_modes:
        if args.period is not None:
            period = resolve_period(args.period)
            rows = [
                run_period(
                    strategy_key=args.strategy,
                    period=period,
                    fixed_params=fixed_params,
                    symbol=args.symbol,
                    timeframe=args.timeframe,
                    initial_capital=args.initial_capital,
                    fixed_quantity=args.fixed_quantity,
                    cost_mode=cost_mode,
                    cost_params=cost_params,
                    cost_multiplier=args.cost_multiplier,
                    out_dir=args.out_dir,
                    write_equity=args.equity_csv,
                )
            ]
            value_label = "period"

        elif args.stability:
            rows = run_stability(
                strategy_key=args.strategy,
                fixed_params=fixed_params,
                symbol=args.symbol,
                timeframe=args.timeframe,
                initial_capital=args.initial_capital,
                fixed_quantity=args.fixed_quantity,
                cost_mode=cost_mode,
                cost_params=cost_params,
                cost_multiplier=args.cost_multiplier,
                out_dir=args.out_dir,
                write_equity=args.equity_csv,
            )
            value_label = "period"

        elif args.subperiods:
            rows = run_subperiods(
                strategy_key=args.strategy,
                fixed_params=fixed_params,
                symbol=args.symbol,
                timeframe=args.timeframe,
                initial_capital=args.initial_capital,
                fixed_quantity=args.fixed_quantity,
                cost_mode=cost_mode,
                cost_params=cost_params,
                cost_multiplier=args.cost_multiplier,
                out_dir=args.out_dir,
                write_equity=args.equity_csv,
            )
            value_label = "period"

        else:
            spec = args.range if args.range is not None else args.values
            mode = "range" if args.range is not None else "values"

            sweep_key, sweep_values = parse_sweep_spec(
                spec,
                mode=mode,
            )

            rows = run_sweep(
                strategy_key=args.strategy,
                sweep_key=sweep_key,
                sweep_values=sweep_values,
                fixed_params=fixed_params,
                symbol=args.symbol,
                timeframe=args.timeframe,
                date_from=args.date_from,
                date_to=args.date_to,
                initial_capital=args.initial_capital,
                fixed_quantity=args.fixed_quantity,
                cost_mode=cost_mode,
                cost_params=cost_params,
                cost_multiplier=args.cost_multiplier,
                out_dir=args.out_dir,
                write_equity=args.equity_csv,
            )

        for row in rows:
            row["cost"] = cost_mode
            row["cost_multiplier"] = args.cost_multiplier

        all_rows.extend(rows)

        print(f"\n--- {cost_mode.upper()} ---")

        if args.stability:
            print_stability_table(rows)
        else:
            print_table(
                rows,
                value_label=value_label,
            )

    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.period is not None:
        stem = f"{args.strategy.upper()}_period_{args.period}"
    elif args.stability:
        stem = f"{args.strategy.upper()}_stability"
    elif args.subperiods:
        stem = f"{args.strategy.upper()}_subperiods"
    else:
        stem = (
            f"{args.strategy.upper()}_sweep_"
            f"{args.range.split('=', 1)[0] if args.range else args.values.split('=', 1)[0]}"
        )

    csv_path = args.out_dir / (stem + ".csv")

    write_summary_csv(
        all_rows,
        csv_path,
    )

    print(f"\nSummary written: {csv_path}")


if __name__ == "__main__":
    main()
