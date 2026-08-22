"""
Run one registered strategy across multiple symbols.

This module is only orchestration around research.runner.run_single.
Backtest semantics, costs, risk and execution remain owned by the
existing runner and engine.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any, Callable

from backtest.instruments import INSTRUMENT_REGISTRY, MAJOR_SYMBOLS
from research.runner import (
    DEFAULT_EXPLICIT_COSTS,
    REPORTS_DIR,
    STRATEGY_REGISTRY,
    coerce_strategy_params,
    dataset_path,
    discover_strategy_class,
    parse_params,
    run_single,
    validate_cost_multiplier,
)
from strategy.declarative import load_strategy_config

DEFAULT_CONFIG_PATH = (
    "config/strategies/ensemble_low_turnover_multi_symbol_v1.yaml"
)

SUMMARY_COLUMNS = [
    "symbol",
    "strategy",
    "tf",
    "cost",
    "cost_multiplier",
    "tag",
    "from",
    "to",
    "trades",
    "net_profit",
    "return_pct",
    "max_dd_pct",
    "win_rate",
    "profit_factor",
    "expectancy",
    "round_trip_cost_pips",
    "report_path",
]

RunSingleFn = Callable[..., Path]


def missing_dataset_paths(
    symbols: tuple[str, ...],
    *,
    timeframe: str,
) -> dict[str, Path]:
    missing = {}

    for symbol in symbols:
        path = dataset_path(
            symbol,
            timeframe,
        )

        if not path.exists():
            missing[symbol] = path

    return missing


def available_symbols(
    symbols: tuple[str, ...],
    *,
    timeframe: str,
) -> tuple[str, ...]:
    missing = missing_dataset_paths(
        symbols,
        timeframe=timeframe,
    )

    return tuple(
        symbol
        for symbol in symbols
        if symbol not in missing
    )


def dataset_preflight_message(
    missing: dict[str, Path],
) -> str:
    lines = [
        "missing datasets for multi-symbol run:",
    ]

    for symbol, path in sorted(missing.items()):
        lines.append(
            f"- {symbol}: {path}"
        )

    lines.extend(
        [
            "To prepare M15 data for a symbol:",
            "  python collect_history.py --symbol <SYMBOL>",
            "  python build_timeframes.py --symbol <SYMBOL>",
        ]
    )

    return "\n".join(lines)


def assert_datasets_available(
    symbols: tuple[str, ...],
    *,
    timeframe: str,
) -> None:
    missing = missing_dataset_paths(
        symbols,
        timeframe=timeframe,
    )

    if missing:
        raise FileNotFoundError(
            dataset_preflight_message(missing)
        )


def parse_symbols(
    raw_symbols: str | None,
    *,
    config_path: str | Path | None = None,
) -> tuple[str, ...]:
    if raw_symbols is not None:
        symbols = tuple(
            item.strip().upper()
            for item in raw_symbols.split(",")
            if item.strip()
        )
    elif config_path is not None:
        config = load_strategy_config(config_path)

        if config.symbols is not None:
            symbols = config.symbols
        elif config.symbol is not None:
            symbols = (config.symbol,)
        else:
            symbols = MAJOR_SYMBOLS
    else:
        symbols = MAJOR_SYMBOLS

    if not symbols:
        raise ValueError(
            "symbols must not be empty"
        )

    if len(set(symbols)) != len(symbols):
        raise ValueError(
            "symbols must not contain duplicates"
        )

    unknown = tuple(
        symbol
        for symbol in symbols
        if symbol not in INSTRUMENT_REGISTRY
    )

    if unknown:
        raise ValueError(
            "unknown symbols: "
            + ", ".join(unknown)
        )

    return tuple(symbols)


def cost_modes(
    cost: str,
) -> tuple[str, ...]:
    if cost == "both":
        return ("zero", "explicit")

    if cost in ("zero", "explicit"):
        return (cost,)

    raise ValueError(
        "cost must be one of zero, explicit, both"
    )


def symbol_tag(
    tag: str | None,
    symbol: str,
) -> str:
    suffix = symbol.lower()

    if tag is None or not tag.strip():
        return suffix

    return f"{tag.strip()}-{suffix}"


def extract_summary_row(
    report_path: Path,
) -> dict[str, Any]:
    report = json.loads(
        report_path.read_text(encoding="utf-8")
    )
    config = report["config"]
    performance = report["performance"]
    cost_analysis = report["cost_analysis"]

    return {
        "symbol": config["symbol"],
        "strategy": config["strategy_id"],
        "tf": config["timeframe"],
        "cost": config["cost_model"],
        "cost_multiplier": config.get(
            "cost_multiplier",
            1.0,
        ),
        "tag": config.get("tag") or "",
        "from": config["date_from"][:10],
        "to": config["date_to"][:10],
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
        "expectancy": round(
            performance["expectancy"],
            4,
        ),
        "round_trip_cost_pips": round(
            cost_analysis["round_trip_cost_pips"],
            6,
        ),
        "report_path": str(report_path),
    }


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


def write_summary_files(
    rows: list[dict[str, Any]],
    *,
    out_dir: Path,
    stem: str,
) -> tuple[Path, Path]:
    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = out_dir / f"{stem}.json"
    csv_path = out_dir / f"{stem}.csv"

    json_path.write_text(
        json.dumps(
            {
                "schema_version": "multi-symbol-summary/0.1.0",
                "rows": rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    csv_path.write_text(
        render_csv(rows),
        encoding="utf-8",
    )

    return json_path, csv_path


def run_multi_symbol(
    *,
    symbols: tuple[str, ...],
    strategy_key: str,
    strategy_params: dict[str, Any],
    timeframe: str,
    date_from: str | None,
    date_to: str | None,
    initial_capital: float,
    fixed_quantity: float,
    cost: str,
    cost_params: dict[str, float],
    cost_multiplier: float,
    out_dir: Path,
    tag: str | None,
    write_equity: bool,
    skip_missing: bool = False,
    run_single_fn: RunSingleFn = run_single,
) -> list[dict[str, Any]]:
    if strategy_key not in STRATEGY_REGISTRY:
        raise ValueError(
            f"unknown strategy {strategy_key!r}"
        )

    validate_cost_multiplier(
        cost_multiplier
    )

    strategy_module = STRATEGY_REGISTRY[strategy_key]
    strategy_class = discover_strategy_class(
        strategy_module
    )

    if skip_missing:
        symbols = available_symbols(
            symbols,
            timeframe=timeframe,
        )
    else:
        assert_datasets_available(
            symbols,
            timeframe=timeframe,
        )

    if not symbols:
        raise FileNotFoundError(
            "no requested symbols have available datasets"
        )

    rows = []

    for symbol in symbols:
        if symbol not in INSTRUMENT_REGISTRY:
            raise ValueError(
                f"unknown symbol: {symbol}"
            )

        for mode in cost_modes(cost):
            report_path = run_single_fn(
                symbol=symbol,
                timeframe=timeframe,
                strategy_class=strategy_class,
                strategy_module=strategy_module,
                tag=symbol_tag(
                    tag,
                    symbol,
                ),
                strategy_params=dict(strategy_params),
                date_from=date_from,
                date_to=date_to,
                initial_capital=initial_capital,
                fixed_quantity=fixed_quantity,
                cost_mode=mode,
                cost_params=dict(cost_params),
                cost_multiplier=cost_multiplier,
                out_dir=out_dir,
                write_equity=write_equity,
            )
            rows.append(
                extract_summary_row(report_path)
            )

    rows.sort(
        key=lambda row: (
            row["symbol"],
            row["cost"],
        )
    )

    return rows


def summary_stem(
    *,
    strategy_key: str,
    timeframe: str,
    cost: str,
    tag: str | None,
) -> str:
    stem = f"multi_symbol_{strategy_key}_{timeframe}_{cost}"

    if tag is not None and tag.strip():
        stem += f"_{tag.strip()}"

    return stem


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one research strategy across multiple symbols and "
            "write an aggregate summary."
        )
    )
    parser.add_argument(
        "--strategy",
        default="declarative_ensemble",
        choices=sorted(STRATEGY_REGISTRY),
    )
    parser.add_argument(
        "--config-path",
        default=DEFAULT_CONFIG_PATH,
        help="declarative strategy YAML path",
    )
    parser.add_argument(
        "--symbols",
        default=None,
        help="comma-separated symbols; default comes from config",
    )
    parser.add_argument(
        "--timeframe",
        default="M15",
    )
    parser.add_argument(
        "--date-from",
        default=None,
    )
    parser.add_argument(
        "--date-to",
        default=None,
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
    )
    parser.add_argument(
        "--spread-pips",
        type=float,
        default=DEFAULT_EXPLICIT_COSTS["spread_pips"],
    )
    parser.add_argument(
        "--slippage-pips",
        type=float,
        default=DEFAULT_EXPLICIT_COSTS["slippage_pips"],
    )
    parser.add_argument(
        "--commission",
        type=float,
        default=DEFAULT_EXPLICIT_COSTS[
            "commission_per_lot_per_side"
        ],
    )
    parser.add_argument(
        "--cost-multiplier",
        type=float,
        default=1.0,
    )
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
    )
    parser.add_argument(
        "--tag",
        default=None,
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
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="run only symbols with available datasets",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raw_params = parse_params(args.param)

    if (
        args.strategy == "declarative_ensemble"
        and "config_path" not in raw_params
    ):
        raw_params["config_path"] = args.config_path

    strategy_class = discover_strategy_class(
        STRATEGY_REGISTRY[args.strategy]
    )
    strategy_params = coerce_strategy_params(
        strategy_class,
        raw_params,
    )
    symbols = parse_symbols(
        args.symbols,
        config_path=(
            strategy_params.get("config_path")
            if args.strategy == "declarative_ensemble"
            else None
        ),
    )

    try:
        rows = run_multi_symbol(
            symbols=symbols,
            strategy_key=args.strategy,
            strategy_params=strategy_params,
            timeframe=args.timeframe,
            date_from=args.date_from,
            date_to=args.date_to,
            initial_capital=args.initial_capital,
            fixed_quantity=args.fixed_quantity,
            cost=args.cost,
            cost_params={
                "spread_pips": args.spread_pips,
                "slippage_pips": args.slippage_pips,
                "commission_per_lot_per_side": args.commission,
            },
            cost_multiplier=args.cost_multiplier,
            out_dir=args.out_dir,
            tag=args.tag,
            write_equity=args.equity_csv,
            skip_missing=args.skip_missing,
        )
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    json_path, csv_path = write_summary_files(
        rows,
        out_dir=args.out_dir,
        stem=summary_stem(
            strategy_key=args.strategy,
            timeframe=args.timeframe,
            cost=args.cost,
            tag=args.tag,
        ),
    )

    print(f"Multi-symbol summary JSON: {json_path}")
    print(f"Multi-symbol summary CSV : {csv_path}")


if __name__ == "__main__":
    main()
