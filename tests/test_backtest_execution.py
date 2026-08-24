from datetime import datetime, timezone

import pandas as pd
import pytest

from backtest.costs import FixedCostModel, ZeroCostModel
from backtest.execution import ExecutionResult, ExecutionStatus, SimulatedExecution
from backtest.feed import HistoricalBarFeed
from backtest.models import BacktestConfig, Timeframe
from domain.fill import Fill
from domain.order_intent import OrderIntent, OrderSide, OrderType


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 24, hour, minute, tzinfo=timezone.utc)


def feed(starts: list[datetime] | None = None, *, symbol: str = "EURUSD") -> HistoricalBarFeed:
    times = starts or [at(10), at(10, 15), at(10, 30)]
    frame = pd.DataFrame({"time": times, "open": [1.10 + index / 100 for index in range(len(times))], "high": [1.11 + index / 100 for index in range(len(times))], "low": [1.09 + index / 100 for index in range(len(times))], "close": [1.105 + index / 100 for index in range(len(times))], "tick_volume": [100] * len(times)})
    return HistoricalBarFeed(frame, BacktestConfig(symbol, Timeframe.M15, at(9), at(12), 10_000))


def order(side: OrderSide = OrderSide.BUY, *, created_at: datetime = at(10, 15), identifier: str = "one", symbol: str = "EURUSD") -> OrderIntent:
    return OrderIntent(identifier, "signal", symbol, side, 2.0, OrderType.MARKET, created_at)


def test_buy_and_sell_fill_at_next_open_with_zero_cost():
    execution = SimulatedExecution(ZeroCostModel())
    buy = execution.execute(order(OrderSide.BUY), feed=feed())
    sell = execution.execute(order(OrderSide.SELL, identifier="sell"), feed=feed())

    assert buy.status is sell.status is ExecutionStatus.FILLED
    assert buy.fill.fill_time == sell.fill.fill_time == at(10, 15)
    assert buy.fill.reference_price == buy.fill.execution_price == pytest.approx(1.11)
    assert sell.fill.reference_price == sell.fill.execution_price == pytest.approx(1.11)


def test_fixed_cost_is_applied_once_to_reference_open_and_copied_to_fill():
    result = SimulatedExecution(FixedCostModel(spread=0.0002, slippage=0.0001, commission_per_unit=3)).execute(order(), feed=feed())

    assert result.fill.reference_price == pytest.approx(1.11)
    assert result.fill.execution_price == pytest.approx(1.1102)
    assert result.fill.spread_impact == pytest.approx(0.0001)
    assert result.fill.slippage == pytest.approx(0.0001)
    assert result.fill.commission == pytest.approx(6.0)


def test_next_actual_bar_open_respects_signal_close_chronology_and_gaps():
    gapped = feed([at(10), at(10, 30)])
    result = SimulatedExecution(ZeroCostModel()).execute(order(created_at=at(10, 15)), feed=gapped)

    assert result.status is ExecutionStatus.FILLED
    assert result.scheduled_for == result.fill.fill_time == at(10, 30)
    assert result.fill.fill_time >= at(10, 15)


def test_last_candle_without_next_open_is_explicitly_unfilled():
    result = SimulatedExecution(ZeroCostModel()).execute(order(created_at=at(10, 45)), feed=feed())
    assert result.status is ExecutionStatus.UNFILLED
    assert result.fill is None and result.scheduled_for is None
    assert "no next" in result.reason


def test_symbol_mismatch_is_explicitly_rejected_without_fill():
    result = SimulatedExecution(ZeroCostModel()).execute(order(symbol="GBPUSD"), feed=feed())
    assert result.status is ExecutionStatus.REJECTED
    assert result.fill is None and "symbol" in result.reason


def test_execution_is_deterministic_and_traceable():
    execution = SimulatedExecution(FixedCostModel(spread=0.0002))
    first = execution.execute(order(), feed=feed())
    second = execution.execute(order(), feed=feed())

    assert first == second
    assert first.order_id == first.fill.order_id == "one"
    assert first.fill.fill_id == "sim-one"
    assert first.scheduled_for == first.fill.fill_time


def test_execution_rejects_invalid_dependencies_and_result_invariants():
    with pytest.raises(TypeError, match="CostModel"):
        SimulatedExecution(None)
    with pytest.raises(TypeError, match="order"):
        SimulatedExecution(ZeroCostModel()).execute(None, feed=feed())
    with pytest.raises(TypeError, match="feed"):
        SimulatedExecution(ZeroCostModel()).execute(order(), feed=None)
    with pytest.raises(ValueError, match="FILLED"):
        ExecutionResult("order", ExecutionStatus.FILLED, "bad")
    sample_fill = Fill("fill", "other", at(10), 1, 1, 1)
    with pytest.raises(ValueError, match="matching"):
        ExecutionResult("order", ExecutionStatus.FILLED, "bad", at(10), sample_fill)
    with pytest.raises(ValueError, match="non-filled"):
        ExecutionResult("order", ExecutionStatus.UNFILLED, "bad", at(10))
