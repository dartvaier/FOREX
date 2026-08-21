"""
Reproducible research runner for the FOREX BacktestEngine.

Runs one strategy over one timeframe with the chosen cost
model and writes an audit bundle to research/reports/:

    <strategy_id>_<timeframe>_<cost>.json
    <strategy_id>_<timeframe>_<cost>.trades.csv

The runner is a thin orchestration layer. All simulation
semantics (bar-by-bar, no look-ahead, explicit costs,
worst-case protective exits, UTC, closed candles) belong to
the BacktestEngine and its components.

Examples:

    python -m research.runner --strategy ema_trend
    python -m research.runner --strategy asian_range_breakout --cost explicit
    python -m research.runner --strategy time_series_momentum --param lookback=192 --param entry_threshold=0.002
    python -m research.runner --strategy ema_trend --date-from 2015-01-01 --date-to 2020-12-31
    python -m research.runner --strategy mean_reversion --cost both --equity-csv

Cost stress (F8):

    python -m research.runner --strategy time_series_momentum --cost explicit --cost-multiplier 1.5 --tag cost1x5
    python -m research.runner --strategy time_series_momentum --cost explicit --cost-multiplier 2.0 --tag cost2x
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
from dataclasses import fields
from datetime import datetime, timedelta, timezone
from numbers import Real
from pathlib import Path
from typing import Any, get_type_hints

import pandas as pd

from backtest.costs import FixedCostModel, ZeroCostModel
from backtest.engine import BacktestEngine, BacktestResult
from backtest.models import (
    BacktestConfig,
    InstrumentSpecification,
    Timeframe,
)
from backtest.risk import FixedSizeRiskGate

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "research" / "reports"

TIMEFRAME_DELTA = {
    "M15": timedelta(minutes=15),
    "H1": timedelta(hours=1),
    "H4": timedelta(hours=4),
}

DEFAULT_EXPLICIT_COSTS = {
    "spread_pips": 2.0,
    "slippage_pips": 0.5,
    "commission_per_lot_per_side": 3.50,
}

STRATEGY_REGISTRY = {
    "ema_trend": "strategy.ema_trend",
    "volatility_breakout": "strategy.volatility_breakout",
    "time_series_momentum": "strategy.time_series_momentum",
    "ensemble_tsmom_ema": "strategy.ensemble_tsmom_ema",
    "ensemble_tsmom_ema_regime": (
        "strategy.ensemble_tsmom_ema_regime"
    ),
    "mean_reversion": "strategy.mean_reversion",
    "asian_range_breakout": "strategy.asian_range_breakout",
    "carry": "strategy.carry",
    "regime_detection": "strategy.regime_detection",
    "multi_timeframe_momentum": (
        "strategy.multi_timeframe_momentum"
    ),
}

EURUSD_INSTRUMENT = {
    "symbol": "EURUSD",
    "digits": 5,
    "point": 0.00001,
    "pip_size": 0.00010,
    "contract_size": 100000,
    "volume_min": 0.01,
    "volume_max": 500.0,
    "volume_step": 0.01,
    "tick_size": 0.00001,
    "tick_value": 1.0,
}

INSTRUMENT_REGISTRY = {
    "EURUSD": {
        "symbol": "EURUSD",
        "digits": 5,
        "point": 0.00001,
        "pip_size": 0.00010,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "base_currency": "USD",
        "quote_currency": "USD",
    },
    "GBPUSD": {
        "symbol": "GBPUSD",
        "digits": 5,
        "point": 0.00001,
        "pip_size": 0.00010,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "base_currency": "GBP",
        "quote_currency": "USD",
    },
    "USDJPY": {
        "symbol": "USDJPY",
        "digits": 3,
        "point": 0.001,
        "pip_size": 0.01,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.001,
        "tick_value": 100.0,
        "base_currency": "USD",
        "quote_currency": "JPY",
    },
    "USDCHF": {
        "symbol": "USDCHF",
        "digits": 5,
        "point": 0.00001,
        "pip_size": 0.00010,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "base_currency": "USD",
        "quote_currency": "CHF",
    },
    "AUDUSD": {
        "symbol": "AUDUSD",
        "digits": 5,
        "point": 0.00001,
        "pip_size": 0.00010,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "base_currency": "AUD",
        "quote_currency": "USD",
    },
    "USDCAD": {
        "symbol": "USDCAD",
        "digits": 5,
        "point": 0.00001,
        "pip_size": 0.00010,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "base_currency": "USD",
        "quote_currency": "CAD",
    },
    "NZDUSD": {
        "symbol": "NZDUSD",
        "digits": 5,
        "point": 0.00001,
        "pip_size": 0.00010,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "base_currency": "NZD",
        "quote_currency": "USD",
    },
}





# ---------------------------------------------------------------------------
# Strategy discovery and parameter coercion
# ---------------------------------------------------------------------------


def discover_strategy_class(module_name: str) -> type:
    """Return the strategy class defined in the given module."""
    module = importlib.import_module(module_name)

    candidates = [
        value
        for value in vars(module).values()
        if isinstance(value, type)
        and value.__module__ == module_name
        and "Strategy" in value.__name__
    ]

    if len(candidates) != 1:
        raise RuntimeError(
            "expected exactly one strategy class in "
            f"{module_name}, found {[c.__name__ for c in candidates]}"
        )

    return candidates[0]


def _parse_bool(raw: str) -> bool:
    lowered = raw.strip().lower()

    if lowered in ("true", "1", "yes"):
        return True

    if lowered in ("false", "0", "no"):
        return False

    raise ValueError(f"cannot parse bool from {raw!r}")


def validate_cost_multiplier(
    multiplier: float,
) -> float:
    """
    Validate a cost stress multiplier.

    The multiplier must be a finite non-negative number.
    1.0 reproduces the baseline explicit costs; 1.5 and 2.0
    are the standard F8 cost stress levels.
    """
    if (
        not isinstance(multiplier, Real)
        or isinstance(multiplier, bool)
        or not math.isfinite(multiplier)
        or multiplier < 0.0
    ):
        raise ValueError(
            "cost_multiplier must be a finite "
            "non-negative number"
        )

    return float(multiplier)


def scale_cost_params(
    cost_params: dict[str, float],
    multiplier: float,
) -> dict[str, float]:
    """
    Scale explicit cost parameters by a stress multiplier.

    Each of spread_pips, slippage_pips and
    commission_per_lot_per_side is multiplied by the same
    factor, preserving the relative structure of the baseline
    cost model while stressing its absolute magnitude.

    The base cost_params dict is never mutated.
    """
    if not isinstance(
        cost_params,
        dict,
    ):
        raise TypeError(
            "cost_params must be a dict"
        )

    multiplier = validate_cost_multiplier(
        multiplier
    )

    scaled = {
        key: value * multiplier
        for key, value in cost_params.items()
    }

    return scaled


def coerce_strategy_params(
    strategy_class: type,
    raw_params: dict[str, str],
) -> dict[str, Any]:
    """Convert --param key=value strings using dataclass annotations."""
    hints = get_type_hints(strategy_class)
    dataclass_names = {field.name for field in fields(strategy_class)}

    coerced: dict[str, Any] = {}

    for key, raw in raw_params.items():
        if key not in dataclass_names:
            raise ValueError(
                f"unknown parameter {key!r} for "
                f"{strategy_class.__name__}; valid params: "
                + ", ".join(sorted(dataclass_names))
            )

        hint = hints.get(key)

        if hint is bool:
            value: Any = _parse_bool(raw)
        elif hint is int:
            value = int(raw)
        elif hint is float:
            value = float(raw)
        else:
            value = raw

        coerced[key] = value

    return coerced


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def dataset_path(symbol: str, timeframe: str) -> Path:
    if timeframe == "M15":
        return REPO_ROOT / "data" / "raw" / symbol / "M15.parquet"

    return (
        REPO_ROOT
        / "data"
        / "processed"
        / symbol
        / f"{timeframe}.parquet"
    )


def load_dataframe(symbol: str, timeframe: str) -> pd.DataFrame:
    path = dataset_path(symbol, timeframe)

    if not path.exists():
        raise FileNotFoundError(
            f"dataset not found: {path} (run collect_history.py / "
            "build_timeframes.py first)"
        )

    return pd.read_parquet(path)


def load_higher_timeframe_dataframes(
    *,
    symbol: str,
    strategy: Any,
) -> dict[Timeframe, pd.DataFrame]:
    higher_timeframes = getattr(
        strategy,
        "higher_timeframes",
        (),
    )

    result = {}

    for timeframe in higher_timeframes:
        if not isinstance(
            timeframe,
            Timeframe,
        ):
            timeframe = Timeframe(timeframe)

        result[timeframe] = load_dataframe(
            symbol,
            timeframe.value,
        )

    return result


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()

    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)

    return digest.hexdigest().upper()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    if parsed.utcoffset() != timedelta(0):
        raise ValueError(f"{value!r} must use UTC")

    return parsed


def resolve_dates(
    dataframe: pd.DataFrame,
    timeframe: str,
    date_from: str | None,
    date_to: str | None,
) -> tuple[datetime, datetime]:
    first_bar = dataframe["time"].min().to_pydatetime()
    last_bar = dataframe["time"].max().to_pydatetime()

    start = (
        parse_utc(date_from)
        if date_from is not None
        else first_bar
    )

    end = (
        parse_utc(date_to)
        if date_to is not None
        else last_bar + TIMEFRAME_DELTA[timeframe]
    )

    if end <= start:
        raise ValueError("date_to must be later than date_from")

    return start, end


# ---------------------------------------------------------------------------
# Cost analysis helpers
# ---------------------------------------------------------------------------


def round_trip_cost_money(
    instrument: InstrumentSpecification,
    quantity: float,
    cost_params: dict[str, float],
    quote_to_account_rate: float = 1.0,
) -> float:
    """
    Total spread + slippage + commission of one round trip, in
    account currency (USD).

    The spread/slippage leg is expressed in quote currency and is
    converted to USD with quote_to_account_rate (causal: derived
    from an actual trade price by the caller). Commission is
    already USD.
    """
    price_distance = (
        cost_params["spread_pips"]
        + 2.0 * cost_params["slippage_pips"]
    ) * instrument.pip_size

    per_lot = (
        price_distance * instrument.contract_size
        * quote_to_account_rate
    )
    commission = (
        2.0 * cost_params["commission_per_lot_per_side"]
    )

    return (per_lot + commission) * quantity


def money_to_pips(
    money: float,
    instrument: InstrumentSpecification,
    quantity: float,
    quote_to_account_rate: float = 1.0,
) -> float:
    per_pip = (
        instrument.pip_size
        * instrument.contract_size
        * quantity
        * quote_to_account_rate
    )

    return money / per_pip


def effective_round_trip(
    *,
    cost_mode: str,
    instrument: InstrumentSpecification,
    fixed_quantity: float,
    cost_params: dict[str, float],
    quote_to_account_rate: float = 1.0,
) -> tuple[float, float]:
    """
    Effective round-trip cost for the report (docs/25 RA-04).

    With cost_mode == "zero" the effective costs are ZERO: the
    report must not present baseline explicit costs as if they had
    been paid. The baseline parameters are recorded separately as
    reference only.
    """
    if cost_mode == "zero":
        return 0.0, 0.0

    money = round_trip_cost_money(
        instrument,
        fixed_quantity,
        cost_params,
        quote_to_account_rate=quote_to_account_rate,
    )

    pips = money_to_pips(
        money,
        instrument,
        fixed_quantity,
        quote_to_account_rate=quote_to_account_rate,
    )

    return money, pips


# ---------------------------------------------------------------------------
# Report serialization
# ---------------------------------------------------------------------------


def _trade_row(trade: Any) -> dict[str, Any]:
    return {
        "trade_id": trade.trade_id,
        "position_id": trade.position_id,
        "strategy_id": trade.strategy_id,
        "symbol": trade.symbol,
        "side": str(trade.side),
        "entry_time": trade.entry_time.isoformat(),
        "exit_time": trade.exit_time.isoformat(),
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "quantity": trade.quantity,
        "gross_pnl": trade.gross_pnl,
        "net_pnl": trade.net_pnl,
        "spread_cost": trade.spread_cost,
        "slippage_cost": trade.slippage_cost,
        "commission": trade.commission,
        "swap": trade.swap,
        "bars_held": trade.bars_held,
        "exit_reason": str(trade.exit_reason),
    }


def _equity_row(point: Any) -> dict[str, Any]:
    return {
        "timestamp": point.timestamp.isoformat(),
        "bar_index": point.bar_index,
        "phase": str(point.phase),
        "cash": point.cash,
        "equity": point.equity,
        "realized_pnl": point.realized_pnl,
        "unrealized_pnl": point.unrealized_pnl,
    }


def build_report(
    result: BacktestResult,
    *,
    symbol: str,
    timeframe: str,
    cost_mode: str,
    cost_params: dict[str, float],
    effective_cost_params: dict[str, float],
    cost_multiplier: float,
    strategy_params: dict[str, Any],
    strategy_module: str,
    tag: str | None,
    dataset_path: Path,
    dataset_sha256: str,
    rows_loaded: int,
    round_trip_money: float,
    round_trip_pips: float,
) -> dict[str, Any]:
    performance = result.performance
    trade_metrics = performance.trade_metrics
    drawdown = performance.drawdown

    trades = list(result.trades)

    exit_reason_counts: dict[str, int] = {}
    side_counts: dict[str, int] = {}

    for trade in trades:
        reason = str(trade.exit_reason)
        exit_reason_counts[reason] = (
            exit_reason_counts.get(reason, 0) + 1
        )

        side = str(trade.side)
        side_counts[side] = side_counts.get(side, 0) + 1

    config = result.config

    return {
        "schema_version": "research-report/0.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner": "research/runner.py",
        "dataset": {
            "symbol": symbol,
            "timeframe": timeframe,
            "path": str(dataset_path),
            "rows_loaded": rows_loaded,
            "sha256": dataset_sha256,
        },
        "config": {
            "strategy_id": str(
                trades[0].strategy_id
                if trades
                else ""
            ),
            "strategy_module": strategy_module,
            "strategy_params": {
                key: value
                for key, value in strategy_params.items()
            },
            "tag": tag,
            "symbol": symbol,
            "timeframe": timeframe,
            "date_from": config.date_from.isoformat(),
            "date_to": config.date_to.isoformat(),
            "initial_capital": config.initial_capital,
            "fixed_quantity": _fixed_quantity_from(
                result
            ),
            "cost_model": cost_mode,
            "cost_params": dict(cost_params),
            "cost_multiplier": cost_multiplier,
            "ambiguous_bar_policy": str(
                config.ambiguous_bar_policy
            ),
            "end_of_backtest_policy": str(
                config.end_of_backtest_policy
            ),
            "allow_incomplete_bars": config.allow_incomplete_bars,
        },
        "performance": {
            "initial_capital": performance.initial_capital,
            "final_equity": performance.final_equity,
            "total_return": performance.total_return,
            "total_return_pct": performance.total_return_pct,
            "trades": trade_metrics.total_trades,
            "wins": trade_metrics.wins,
            "losses": trade_metrics.losses,
            "breakevens": trade_metrics.breakevens,
            "win_rate": trade_metrics.win_rate,
            "gross_profit": trade_metrics.gross_profit,
            "gross_loss": trade_metrics.gross_loss,
            "profit_factor": trade_metrics.profit_factor,
            "net_profit": trade_metrics.net_profit,
            "average_trade": trade_metrics.average_trade,
            "average_win": trade_metrics.average_win,
            "average_loss": trade_metrics.average_loss,
            "expectancy": trade_metrics.expectancy,
            "max_drawdown": drawdown.max_drawdown,
            "max_drawdown_pct": drawdown.max_drawdown_pct,
            "max_drawdown_peak_index": drawdown.peak_index,
            "max_drawdown_trough_index": drawdown.trough_index,
        },
        "trade_breakdown": {
            "exit_reason_counts": exit_reason_counts,
            "side_counts": side_counts,
        },
        "cost_analysis": {
            "cost_mode": cost_mode,
            "round_trip_cost_money": round_trip_money,
            "round_trip_cost_pips": round_trip_pips,
            "cost_multiplier": cost_multiplier,
            "baseline_cost_params": dict(cost_params),
            "effective_cost_params": dict(effective_cost_params),
            "trades_count": trade_metrics.total_trades,
            "total_cost_paid": sum(
                trade.spread_cost
                + trade.slippage_cost
                + trade.commission
                for trade in trades
            ),
        },
    }


def _fixed_quantity_from(result: BacktestResult) -> float:
    """Recover the fixed quantity from the last trade when present."""
    trades = list(result.trades)

    if not trades:
        return 0.0

    return trades[-1].quantity


def write_trades_csv(
    trades: list[Any],
    path: Path,
) -> None:
    pd.DataFrame(
        [_trade_row(trade) for trade in trades]
    ).to_csv(path, index=False)


def write_equity_csv(
    result: BacktestResult,
    path: Path,
) -> None:
    pd.DataFrame(
        [_equity_row(point) for point in result.equity.points]
    ).to_csv(path, index=False)


# ---------------------------------------------------------------------------
# Backtest execution
# ---------------------------------------------------------------------------


def run_single(
    *,
    symbol: str,
    timeframe: str,
    strategy_class: type,
    strategy_module: str,
    tag: str | None = None,
    strategy_params: dict[str, Any],
    date_from: str | None,
    date_to: str | None,
    initial_capital: float,
    fixed_quantity: float,
    cost_mode: str,
    cost_params: dict[str, float],
    cost_multiplier: float,
    out_dir: Path,
    write_equity: bool,
) -> Path:
    cost_multiplier = validate_cost_multiplier(
        cost_multiplier
    )

    dataframe = load_dataframe(symbol, timeframe)

    start, end = resolve_dates(
        dataframe,
        timeframe,
        date_from,
        date_to,
    )

    path = dataset_path(symbol, timeframe)
    dataset_sha256 = sha256_of(path)

    instrument = InstrumentSpecification(
        **INSTRUMENT_REGISTRY[symbol]
    )

    config = BacktestConfig(
        symbol=symbol,
        timeframe=Timeframe(timeframe),
        date_from=start,
        date_to=end,
        initial_capital=initial_capital,
    )

    if cost_mode == "zero":
        effective_cost_params = dict(cost_params)
        cost_model = ZeroCostModel(instrument)
    else:
        effective_cost_params = scale_cost_params(
            cost_params,
            cost_multiplier,
        )

        cost_model = FixedCostModel(
            instrument,
            **effective_cost_params,
        )

    risk_gate = FixedSizeRiskGate(
        instrument=instrument,
        fixed_quantity=fixed_quantity,
    )

    engine = BacktestEngine(
        config=config,
        instrument=instrument,
        cost_model=cost_model,
        risk_gate=risk_gate,
    )

    strategy_instance = strategy_class(
        symbol=symbol,
        **strategy_params,
    )

    higher_timeframe_dataframes = load_higher_timeframe_dataframes(
        symbol=symbol,
        strategy=strategy_instance,
    )

    result = engine.run(
        dataframe=dataframe,
        strategy=strategy_instance,
        higher_timeframe_dataframes=higher_timeframe_dataframes,
    )

    strategy_id = (
        result.trades.last_trade.strategy_id
        if result.trades.last_trade is not None
        else strategy_instance.strategy_id
    )

    trades = list(result.trades)

    # Causal quote->USD rate: derived from the average entry price
    # of the realized trades (available only after the simulation).
    if trades:
        avg_entry = sum(
            trade.entry_price for trade in trades
        ) / len(trades)
        quote_to_account_rate = (
            instrument.quote_to_account_rate(avg_entry)
        )
    else:
        quote_to_account_rate = 1.0

    round_trip_money, round_trip_pips = effective_round_trip(
        cost_mode=cost_mode,
        instrument=instrument,
        fixed_quantity=fixed_quantity,
        cost_params=effective_cost_params,
        quote_to_account_rate=quote_to_account_rate,
    )

    report = build_report(
        result,
        symbol=symbol,
        timeframe=timeframe,
        cost_mode=cost_mode,
        cost_params=cost_params,
        effective_cost_params=effective_cost_params,
        cost_multiplier=cost_multiplier,
        strategy_params=strategy_params,
        strategy_module=strategy_module,
        tag=tag,
        dataset_path=path,
        dataset_sha256=dataset_sha256,
        rows_loaded=len(dataframe),
        round_trip_money=round_trip_money,
        round_trip_pips=round_trip_pips,
    )

    out_dir.mkdir(parents=True, exist_ok=True)

    report_name = f"{strategy_id}_{timeframe}_{cost_mode}"

    if tag:
        report_name += f"_{tag}"

    report_path = out_dir / (report_name + ".json")
    trades_path = out_dir / (report_name + ".trades.csv")

    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    write_trades_csv(
        list(result.trades),
        trades_path,
    )

    if write_equity:
        write_equity_csv(
            result,
            out_dir / (report_name + ".equity.csv"),
        )

    print_summary(report)

    return report_path


def print_summary(report: dict[str, Any]) -> None:
    config = report["config"]
    performance = report["performance"]
    cost_analysis = report["cost_analysis"]

    print(
        "\n".join(
            [
                "",
                "--- BACKTEST SUMMARY ---",
                f"strategy      : {config['strategy_id']} "
                f"({config['strategy_module'] or 'research.runner'})",
                f"symbol/tf     : {config['symbol']} "
                f"{config['timeframe']}",
                f"period        : {config['date_from']} -> "
                f"{config['date_to']}",
                f"cost model    : {config['cost_model']} "
                f"{config['cost_params']}",
                f"trades        : {performance['trades']}",
                f"net profit    : {performance['net_profit']:.2f}",
                f"return        : {performance['total_return_pct']:.4f}%",
                f"max drawdown  : {performance['max_drawdown_pct']:.4f}%",
                f"win rate      : {performance['win_rate']:.2f}%",
                f"profit factor : {performance['profit_factor']:.6f}",
                f"avg trade     : {performance['average_trade']:.4f}",
                f"expectancy    : {performance['expectancy']:.4f}",
                f"final equity  : {performance['final_equity']:.2f}",
                f"round trip    : "
                f"{cost_analysis['round_trip_cost_money']:.2f} USD "
                f"({cost_analysis['round_trip_cost_pips']:.2f} pips)",
            ]
        )
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_params(raw: list[str] | None) -> dict[str, str]:
    params: dict[str, str] = {}

    for item in raw or []:
        if "=" not in item:
            raise ValueError(
                f"--param must use key=value syntax, got {item!r}"
            )

        key, value = item.split("=", 1)
        params[key.strip()] = value

    return params


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a reproducible BacktestEngine research backtest "
            "and write a JSON/CSV audit bundle."
        )
    )

    parser.add_argument(
        "--strategy",
        required=True,
        choices=sorted(STRATEGY_REGISTRY),
        help="strategy key from the research registry",
    )

    parser.add_argument(
        "--symbol",
        default="EURUSD",
        choices=sorted(INSTRUMENT_REGISTRY),
        help="instrument key (default: EURUSD)",
    )

    parser.add_argument(
        "--timeframe",
        default="M15",
        choices=sorted(TIMEFRAME_DELTA),
        help="timeframe (default: M15)",
    )

    parser.add_argument(
        "--date-from",
        default=None,
        help="inclusive start, UTC (YYYY-MM-DD or ISO-8601)",
    )

    parser.add_argument(
        "--date-to",
        default=None,
        help="exclusive end, UTC (YYYY-MM-DD or ISO-8601)",
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
        help="position size in lots (default: 0.01)",
    )

    parser.add_argument(
        "--cost",
        choices=("zero", "explicit", "both"),
        default="both",
        help="cost model (default: both)",
    )

    parser.add_argument(
        "--spread-pips",
        type=float,
        default=None,
        help=(
            "override spread in pips; default: baseline 2.0, or the "
            "measured median for the symbol with --calibrated-spread "
            "(docs/26 §25)"
        ),
    )

    parser.add_argument(
        "--calibrated-spread",
        action="store_true",
        help=(
            "use the measured median spread for the symbol from "
            "research/reports/cost_measurement_all.json (run "
            "python -m research.cost_measurement first)"
        ),
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
        help="commission per lot per side in USD",
    )

    parser.add_argument(
        "--cost-multiplier",
        type=float,
        default=1.0,
        help=(
            "cost stress multiplier applied to spread, "
            "slippage and commission (F8 cost stress; "
            "ignored for cost=zero)"
        ),
    )

    parser.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="strategy parameter override (repeatable)",
    )

    parser.add_argument(
        "--tag",
        default=None,
        help="suffix for report filenames to distinguish "
        "variations of the same strategy",
    )

    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPORTS_DIR,
    )

    parser.add_argument(
        "--equity-csv",
        action="store_true",
        help="also write the full equity curve CSV",
    )

    return parser


def load_calibrated_spread(
    symbol: str,
    calibration_path: Path | None = None,
) -> float:
    """
    Measured median spread (pips) for a symbol (docs/26 §25).

    Reads research/reports/cost_measurement_all.json, produced by
    ``python -m research.cost_measurement``. Raises ValueError when
    the calibration file is missing or the symbol was not measured.
    """
    path = calibration_path or Path(
        "research/reports/cost_measurement_all.json"
    )
    if not path.exists():
        raise ValueError(
            f"--calibrated-spread requires {path} "
            "(run: python -m research.cost_measurement)"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    symbols = payload.get("symbols", {})
    if symbol not in symbols:
        raise ValueError(
            f"--calibrated-spread: symbol {symbol} not found in "
            f"{path} (measured: {sorted(symbols)})"
        )
    return float(symbols[symbol]["spread_pips_median"])


def resolve_spread_pips(
    *,
    symbol: str,
    spread_pips: float | None,
    calibrated: bool,
    cost_mode: str,
    calibration_path: Path | None = None,
) -> float:
    """
    Effective spread (pips) for a run (docs/26 §25).

    Rules: --calibrated-spread + explicit --spread-pips is ambiguous
    (ValueError); calibrated loads the measured median for the symbol
    (ignored under zero costs); otherwise the baseline spread applies.
    """
    if calibrated and spread_pips is not None:
        raise ValueError(
            "use either --spread-pips or --calibrated-spread, not both"
        )
    if calibrated and cost_mode != "zero":
        return load_calibrated_spread(symbol, calibration_path)
    if spread_pips is None:
        return DEFAULT_EXPLICIT_COSTS["spread_pips"]
    return spread_pips


def main() -> None:
    args = build_parser().parse_args()

    if args.strategy not in STRATEGY_REGISTRY:
        raise ValueError(
            f"unknown strategy {args.strategy!r}; "
            f"available: {', '.join(sorted(STRATEGY_REGISTRY))}"
        )

    strategy_class = discover_strategy_class(
        STRATEGY_REGISTRY[args.strategy]
    )

    strategy_params = coerce_strategy_params(
        strategy_class,
        parse_params(args.param),
    )

    args.spread_pips = resolve_spread_pips(
        symbol=args.symbol,
        spread_pips=args.spread_pips,
        calibrated=args.calibrated_spread,
        cost_mode=args.cost,
    )

    cost_params = {
        "spread_pips": args.spread_pips,
        "slippage_pips": args.slippage_pips,
        "commission_per_lot_per_side": args.commission,
    }

    modes = (
        ("zero", "explicit")
        if args.cost == "both"
        else (args.cost,)
    )

    report_paths: list[Path] = []

    for mode in modes:
        report_paths.append(
            run_single(
                symbol=args.symbol,
                timeframe=args.timeframe,
                strategy_class=strategy_class,
                strategy_module=STRATEGY_REGISTRY[args.strategy],
                tag=args.tag,
                strategy_params=strategy_params,
                date_from=args.date_from,
                date_to=args.date_to,
                initial_capital=args.initial_capital,
                fixed_quantity=args.fixed_quantity,
                cost_mode=mode,
                cost_params=cost_params,
                cost_multiplier=args.cost_multiplier,
                out_dir=args.out_dir,
                write_equity=args.equity_csv,
            )
        )

    print("\nReports written:")
    for path in report_paths:
        print(f"  {path}")


if __name__ == "__main__":
    main()
