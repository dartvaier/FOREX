from datetime import datetime, timedelta, timezone

import pandas as pd

from backtest.context import BacktestContext
from backtest.costs import FixedCostModel
from backtest.engine import BacktestEngine
from backtest.execution import SimulatedExecution
from backtest.feed import HistoricalBarFeed
from backtest.models import BacktestConfig, MarketBar, SimulationPhase, Timeframe
from backtest.performance import PerformanceAnalytics
from backtest.portfolio import Portfolio
from backtest.risk import FixedSizeRiskModel, RiskLimits
from domain.signal import SignalAction
from experiments.run_ema_crossover import run_ema_crossover_experiment
from strategies.ema_crossover import EmaCrossoverStrategy


def at(hour): return datetime(2026, 8, 24, hour, tzinfo=timezone.utc)


def context(closes, *, phase=SimulationPhase.BAR_CLOSE):
    bars = tuple(MarketBar(at(index), close, close, close, close, 1) for index, close in enumerate(closes))
    index = len(bars) - 1
    return BacktestContext(at(index + 1) if phase is SimulationPhase.BAR_CLOSE else at(index), phase, index, bars[-1] if phase is SimulationPhase.BAR_CLOSE else None, bars if phase is SimulationPhase.BAR_CLOSE else bars[:-1])


def test_bullish_and_bearish_crossovers_generate_directional_signals():
    strategy = EmaCrossoverStrategy(fast_period=2, slow_period=3)
    bullish = strategy.on_bar(context((10, 9, 8, 12)))
    bearish = strategy.on_bar(context((8, 9, 10, 6)))
    assert bullish.action is SignalAction.ENTER_LONG
    assert bearish.action is SignalAction.ENTER_SHORT
    assert bullish.timestamp == at(4) and bearish.timestamp == at(4)


def test_warm_up_and_non_crossover_return_hold_without_portfolio_knowledge():
    strategy = EmaCrossoverStrategy(fast_period=2, slow_period=3)
    assert strategy.on_bar(context((10, 9, 8))).action is SignalAction.HOLD
    assert "warm-up" in strategy.on_bar(context((10, 9, 8))).reason
    assert strategy.on_bar(context((8, 9, 10, 11))).action is SignalAction.HOLD
    assert strategy.on_bar(context((8, 9, 10, 11), phase=SimulationPhase.BAR_OPEN)).action is SignalAction.HOLD


def test_long_and_short_signals_are_deterministic_from_the_same_closed_context():
    strategy = EmaCrossoverStrategy(fast_period=2, slow_period=3)
    long_context, short_context = context((10, 9, 8, 12)), context((8, 9, 10, 6))
    assert strategy.on_bar(long_context) == strategy.on_bar(long_context)
    assert strategy.on_bar(short_context) == strategy.on_bar(short_context)
    assert {strategy.on_bar(long_context).action, strategy.on_bar(short_context).action} == {SignalAction.ENTER_LONG, SignalAction.ENTER_SHORT}


def test_future_prices_cannot_change_already_emitted_ema_signals():
    source = (10, 9, 8, 12, 13, 12, 11, 14, 15, 10)
    mutated = source[:6] + (10_000, 0.01, 8_000, 0.02)
    strategy = EmaCrossoverStrategy(fast_period=2, slow_period=3)
    original = tuple(strategy.on_bar(context(source[:index])).action for index in range(1, 7))
    changed = tuple(strategy.on_bar(context(mutated[:index])).action for index in range(1, 7))
    assert original == changed


def h1_frame(closes):
    return pd.DataFrame({"time": [at(index) for index in range(len(closes))], "open": closes, "high": closes, "low": closes, "close": closes, "tick_volume": [1] * len(closes)})


def test_end_to_end_ema_uses_engine_risk_costs_execution_portfolio_and_analytics():
    frame = h1_frame((10, 9, 8, 12, 13))
    feed = HistoricalBarFeed(frame, BacktestConfig("EURUSD", Timeframe.H1, at(0), at(5), 1_000))
    engine = BacktestEngine(
        feed=feed,
        strategy=EmaCrossoverStrategy(fast_period=2, slow_period=3),
        risk_model=FixedSizeRiskModel(RiskLimits("EURUSD"), 1),
        execution=SimulatedExecution(FixedCostModel(spread=0.2, slippage=0.1, commission_per_unit=0.5)),
        portfolio=Portfolio(symbol="EURUSD", initial_cash=1_000),
        context_closed_bar_limit=4,
    )
    result = engine.run()
    report = PerformanceAnalytics().analyze(result)
    assert [signal.action for signal in result.signals] == [SignalAction.HOLD, SignalAction.HOLD, SignalAction.HOLD, SignalAction.ENTER_LONG, SignalAction.HOLD]
    assert len(result.fills) == 1 and result.fills[0].execution_price == 13.2
    assert max(len(item.closed_bars) for item in result.contexts) == 4
    assert report.total_commissions == 0.5 and report.trade_count == 0
    assert report.final_equity == 999.3


def test_experiment_runner_loads_a_h1_parquet_dataset_and_returns_a_report(tmp_path):
    path = tmp_path / "EURUSD_H1.parquet"
    h1_frame((10, 9, 8, 12, 13)).to_parquet(path)
    report = run_ema_crossover_experiment(path, fast_period=2, slow_period=3, quantity=1)
    assert report.initial_equity == 10_000 and report.final_equity == 10_000
