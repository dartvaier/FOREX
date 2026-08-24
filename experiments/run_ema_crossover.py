"""Minimal H1 EURUSD EMA crossover experiment runner."""

import argparse
import json
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

import pandas as pd

from backtest.costs import FixedCostModel
from backtest.engine import BacktestEngine
from backtest.execution import SimulatedExecution
from backtest.feed import HistoricalBarFeed
from backtest.models import BacktestConfig, Timeframe
from backtest.performance import PerformanceAnalytics, PerformanceReport
from backtest.portfolio import Portfolio
from backtest.risk import FixedSizeRiskModel, RiskLimits
from strategies.ema_crossover import EmaCrossoverStrategy


def run_ema_crossover_experiment(
    dataset_path: str | Path,
    *,
    initial_capital: float = 10_000.0,
    fast_period: int = 20,
    slow_period: int = 50,
    quantity: float = 1.0,
    spread: float = 0.0,
    slippage: float = 0.0,
    commission_per_unit: float = 0.0,
    periods_per_year: int | None = None,
) -> PerformanceReport:
    """Run one fixed-parameter EURUSD/H1 experiment and return its report.

    This deliberately offers no parameter search or optimization facility.
    """

    path = Path(dataset_path)
    if not path.is_file():
        raise FileNotFoundError(f"dataset not found: {path}")
    frame = pd.read_parquet(path).copy()
    if "time" not in frame:
        raise ValueError("dataset must contain a time column")
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    if frame.empty:
        raise ValueError("dataset must not be empty")
    date_from = frame["time"].iloc[0].to_pydatetime()
    date_to = frame["time"].iloc[-1].to_pydatetime() + timedelta(hours=1)
    config = BacktestConfig("EURUSD", Timeframe.H1, date_from, date_to, initial_capital)
    feed = HistoricalBarFeed(frame, config)
    strategy = EmaCrossoverStrategy("EURUSD", fast_period, slow_period)
    risk = FixedSizeRiskModel(RiskLimits("EURUSD"), quantity)
    costs = FixedCostModel(spread, slippage, commission_per_unit)
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        risk_model=risk,
        execution=SimulatedExecution(costs),
        portfolio=Portfolio(symbol="EURUSD", initial_cash=initial_capital),
        context_closed_bar_limit=slow_period + 1,
    )
    return PerformanceAnalytics(periods_per_year=periods_per_year).analyze(engine.run())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one fixed-parameter EURUSD H1 EMA crossover experiment.")
    parser.add_argument("dataset", type=Path, help="Path to the H1 EURUSD Parquet dataset")
    parser.add_argument("--fast-period", type=int, default=20)
    parser.add_argument("--slow-period", type=int, default=50)
    parser.add_argument("--quantity", type=float, default=1.0)
    parser.add_argument("--initial-capital", type=float, default=10_000.0)
    parser.add_argument("--spread", type=float, default=0.0)
    parser.add_argument("--slippage", type=float, default=0.0)
    parser.add_argument("--commission-per-unit", type=float, default=0.0)
    parser.add_argument("--periods-per-year", type=int)
    parser.add_argument("--output", type=Path, help="Optional JSON PerformanceReport output path")
    args = parser.parse_args()
    report = run_ema_crossover_experiment(
        args.dataset, initial_capital=args.initial_capital, fast_period=args.fast_period,
        slow_period=args.slow_period, quantity=args.quantity, spread=args.spread,
        slippage=args.slippage, commission_per_unit=args.commission_per_unit,
        periods_per_year=args.periods_per_year,
    )
    serialized = json.dumps(asdict(report), default=str, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
