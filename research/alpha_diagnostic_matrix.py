from __future__ import annotations

import argparse
import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from research.multi_symbol import (
    DEFAULT_CONFIG_PATH,
    parse_symbols,
    run_multi_symbol,
)
from research.runner import REPORTS_DIR


DIAGNOSTIC_DIR = REPORTS_DIR / "alpha_diagnostics"


@dataclass(frozen=True, slots=True)
class AlphaDiagnosticVariant:
    key: str
    strategy_id: str
    models: tuple[str, ...]
    min_active_models: int
    use_regime_gate: bool = False
    use_cost_gate: bool = False
    cost_estimate_pips: float = 3.7


VARIANTS = (
    AlphaDiagnosticVariant(
        key="tsmom_only",
        strategy_id="ALPHA-DIAG-TSMOM-ONLY",
        models=("time-series-momentum",),
        min_active_models=1,
    ),
    AlphaDiagnosticVariant(
        key="ema_only",
        strategy_id="ALPHA-DIAG-EMA-ONLY",
        models=("ema-trend",),
        min_active_models=1,
    ),
    AlphaDiagnosticVariant(
        key="ensemble_raw",
        strategy_id="ALPHA-DIAG-ENSEMBLE-RAW",
        models=("time-series-momentum", "ema-trend"),
        min_active_models=2,
    ),
    AlphaDiagnosticVariant(
        key="ensemble_cost_gate",
        strategy_id="ALPHA-DIAG-ENSEMBLE-COST-GATE",
        models=("time-series-momentum", "ema-trend"),
        min_active_models=2,
        use_cost_gate=True,
    ),
    AlphaDiagnosticVariant(
        key="ensemble_regime",
        strategy_id="ALPHA-DIAG-ENSEMBLE-REGIME",
        models=("time-series-momentum", "ema-trend"),
        min_active_models=2,
        use_regime_gate=True,
    ),
    AlphaDiagnosticVariant(
        key="ensemble_regime_cost",
        strategy_id="ALPHA-DIAG-ENSEMBLE-REGIME-COST",
        models=("time-series-momentum", "ema-trend"),
        min_active_models=2,
        use_regime_gate=True,
        use_cost_gate=True,
    ),
)

SUMMARY_COLUMNS = [
    "variant",
    "symbol",
    "cost",
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

RunMultiSymbolFn = Callable[..., list[dict[str, Any]]]


def render_variant_config(
    variant: AlphaDiagnosticVariant,
    *,
    symbol: str,
) -> str:
    lines = [
        f"name: alpha-diagnostic-{symbol.lower()}-{variant.key}",
        f"strategy_id: {variant.strategy_id}",
        f"symbol: {symbol}",
        "",
        "models:",
    ]

    for model in variant.models:
        lines.extend(_model_config_lines(model))

    lines.extend(
        [
            "",
            "blend:",
            "  method: weighted_mean",
            f"  min_active_models: {variant.min_active_models}",
            "  min_conviction: 0.0",
            "",
            "signal_policy:",
            "  enter_long: 0.40",
            "  enter_short: -0.40",
            "  exit_long_below: 0.05",
            "  exit_short_above: -0.05",
        ]
    )

    if variant.use_regime_gate:
        lines.extend(
            [
                "",
                "regime_gate:",
                "  trend_lookback: 96",
                "  volatility_lookback: 96",
                "  trend_threshold: 0.0025",
                "  max_volatility: 0.00055",
                "  allowed_regimes: [trending_up, trending_down]",
            ]
        )

    if variant.use_cost_gate:
        lines.extend(
            [
                "",
                "cost_gate:",
                f"  cost_estimate_pips: {variant.cost_estimate_pips}",
                "  safety_factor: 1.0",
            ]
        )

    return "\n".join(lines) + "\n"


def write_variant_configs(
    *,
    symbol: str,
    out_dir: Path = DIAGNOSTIC_DIR,
    variants: tuple[AlphaDiagnosticVariant, ...] = VARIANTS,
) -> dict[str, Path]:
    config_dir = out_dir / "configs" / symbol
    config_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    paths = {}

    for variant in variants:
        path = config_dir / f"{variant.key}.yaml"
        path.write_text(
            render_variant_config(
                variant,
                symbol=symbol,
            ),
            encoding="utf-8",
        )
        paths[variant.key] = path

    return paths


def run_alpha_diagnostic_matrix(
    *,
    symbol: str,
    cost: str,
    date_from: str | None,
    date_to: str | None,
    calibrated_spread: bool,
    calibration_path: Path | None,
    out_dir: Path = DIAGNOSTIC_DIR,
    run_multi_symbol_fn: RunMultiSymbolFn = run_multi_symbol,
) -> list[dict[str, Any]]:
    config_paths = write_variant_configs(
        symbol=symbol,
        out_dir=out_dir,
    )

    rows: list[dict[str, Any]] = []

    for variant in VARIANTS:
        variant_rows = run_multi_symbol_fn(
            symbols=(symbol,),
            strategy_key="declarative_ensemble",
            strategy_params={
                "config_path": str(config_paths[variant.key]),
            },
            timeframe="M15",
            date_from=date_from,
            date_to=date_to,
            initial_capital=10000.0,
            fixed_quantity=0.01,
            cost=cost,
            cost_params={
                "spread_pips": None,
                "slippage_pips": 0.5,
                "commission_per_lot_per_side": 3.50,
            },
            cost_multiplier=1.0,
            out_dir=out_dir,
            tag=f"alpha-diagnostic-{variant.key}",
            write_equity=False,
            calibrated_spread=calibrated_spread,
            calibration_path=calibration_path,
        )

        for row in variant_rows:
            rows.append(
                {
                    "variant": variant.key,
                    "symbol": row["symbol"],
                    "cost": row["cost"],
                    "trades": row["trades"],
                    "net_profit": row["net_profit"],
                    "return_pct": row["return_pct"],
                    "max_dd_pct": row["max_dd_pct"],
                    "win_rate": row["win_rate"],
                    "profit_factor": row["profit_factor"],
                    "expectancy": row["expectancy"],
                    "round_trip_cost_pips": row[
                        "round_trip_cost_pips"
                    ],
                    "report_path": row["report_path"],
                }
            )

    rows.sort(
        key=lambda row: (
            row["variant"],
            row["cost"],
        )
    )

    return rows


def write_summary_files(
    rows: list[dict[str, Any]],
    *,
    symbol: str,
    cost: str,
    out_dir: Path = DIAGNOSTIC_DIR,
) -> tuple[Path, Path]:
    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stem = f"alpha_diagnostic_matrix_{symbol}_{cost}"
    json_path = out_dir / f"{stem}.json"
    csv_path = out_dir / f"{stem}.csv"

    json_path.write_text(
        json.dumps(
            {
                "schema_version": "alpha-diagnostic-matrix/0.1.0",
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run alpha diagnostic variants for one symbol."
        )
    )
    parser.add_argument(
        "--symbol",
        default="USDJPY",
        help="single symbol to diagnose (default: USDJPY)",
    )
    parser.add_argument(
        "--cost",
        choices=("zero", "explicit", "both"),
        default="both",
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
        "--calibrated-spread",
        action="store_true",
    )
    parser.add_argument(
        "--calibration-path",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DIAGNOSTIC_DIR,
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    symbol = parse_symbols(
        args.symbol,
        config_path=DEFAULT_CONFIG_PATH,
    )[0]

    rows = run_alpha_diagnostic_matrix(
        symbol=symbol,
        cost=args.cost,
        date_from=args.date_from,
        date_to=args.date_to,
        calibrated_spread=args.calibrated_spread,
        calibration_path=args.calibration_path,
        out_dir=args.out_dir,
    )
    json_path, csv_path = write_summary_files(
        rows,
        symbol=symbol,
        cost=args.cost,
        out_dir=args.out_dir,
    )

    print(f"Alpha diagnostic JSON: {json_path}")
    print(f"Alpha diagnostic CSV : {csv_path}")


def _model_config_lines(
    model: str,
) -> list[str]:
    if model == "time-series-momentum":
        return [
            "  - id: time-series-momentum",
            "    weight: 1.0",
            "    params:",
            "      lookback: 96",
            "      score_scale: 0.01",
            "      pip_size: auto",
        ]

    if model == "ema-trend":
        return [
            "  - id: ema-trend",
            "    weight: 1.0",
            "    params:",
            "      fast_period: 20",
            "      slow_period: 50",
            "      score_scale: 0.0010",
            "      pip_size: auto",
        ]

    raise ValueError(
        f"unknown diagnostic model: {model}"
    )


if __name__ == "__main__":
    main()
