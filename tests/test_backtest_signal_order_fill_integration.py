from datetime import datetime, timezone

import pandas as pd

from backtest.clock import SimulationClock
from backtest.context import BacktestContext, BacktestContextBuilder
from backtest.execution import SimulatedExecution
from backtest.feed import HistoricalBarFeed
from backtest.models import (
    BacktestConfig,
    InstrumentSpecification,
    OrderSide,
    Signal,
    SignalAction,
    Timeframe,
)
from backtest.models.enums import SimulationPhase
from backtest.order_factory import OrderFactory
from backtest.order_queue import PendingOrderQueue
from backtest.risk import FixedSizeRiskGate
from backtest.signal_processor import SignalProcessor


def utc_time(
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026,
        8,
        8,
        hour,
        minute,
        tzinfo=timezone.utc,
    )


def make_config() -> BacktestConfig:
    return BacktestConfig(
        symbol="EURUSD",
        timeframe=Timeframe.M15,
        date_from=utc_time(10, 0),
        date_to=utc_time(12, 0),
        initial_capital=10000.0,
    )


def make_instrument() -> InstrumentSpecification:
    return InstrumentSpecification(
        symbol="EURUSD",
        digits=5,
        point=0.00001,
        pip_size=0.00010,
        contract_size=100000,
        volume_min=0.01,
        volume_max=500.0,
        volume_step=0.01,
        tick_size=0.00001,
    )


def make_contiguous_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2026-08-08T10:00:00Z",
                    "2026-08-08T10:15:00Z",
                    "2026-08-08T10:30:00Z",
                ],
                utc=True,
            ),
            "open": [
                1.1600,
                1.1625,
                1.1630,
            ],
            "high": [
                1.1615,
                1.1640,
                1.1650,
            ],
            "low": [
                1.1590,
                1.1610,
                1.1620,
            ],
            "close": [
                1.1608,
                1.1630,
                1.1640,
            ],
            "tick_volume": [
                1000,
                1100,
                1200,
            ],
        }
    )


class EnterLongOnFirstClose:
    @property
    def strategy_id(self) -> str:
        return "ENTER-LONG-FIRST-CLOSE"

    def on_bar(
        self,
        context: BacktestContext,
    ) -> Signal:
        action = (
            SignalAction.ENTER_LONG
            if context.current_bar_index == 0
            else SignalAction.HOLD
        )

        return Signal(
            signal_id=(
                f"SIG-{context.current_bar_index}"
            ),
            strategy_id=self.strategy_id,
            symbol="EURUSD",
            timestamp=context.current_time,
            action=action,
        )


class HoldStrategy:
    @property
    def strategy_id(self) -> str:
        return "ALWAYS-HOLD"

    def on_bar(
        self,
        context: BacktestContext,
    ) -> Signal:
        return Signal(
            signal_id=(
                f"HOLD-{context.current_bar_index}"
            ),
            strategy_id=self.strategy_id,
            symbol="EURUSD",
            timestamp=context.current_time,
            action=SignalAction.HOLD,
        )


class EnterLongOnFinalClose:
    @property
    def strategy_id(self) -> str:
        return "ENTER-LONG-FINAL-CLOSE"

    def on_bar(
        self,
        context: BacktestContext,
    ) -> Signal:
        action = (
            SignalAction.ENTER_LONG
            if context.current_bar_index == 2
            else SignalAction.HOLD
        )

        return Signal(
            signal_id=(
                f"FINAL-{context.current_bar_index}"
            ),
            strategy_id=self.strategy_id,
            symbol="EURUSD",
            timestamp=context.current_time,
            action=action,
        )


def run_signal_order_fill_pipeline(
    dataframe: pd.DataFrame,
    strategy,
):
    config = make_config()

    feed = HistoricalBarFeed(
        dataframe=dataframe,
        config=config,
    )

    clock = SimulationClock(
        bar_starts=feed.bar_starts,
        timeframe=config.timeframe,
    )

    context_builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    signal_processor = SignalProcessor(
        config=config,
    )

    risk_gate = FixedSizeRiskGate(
        instrument=make_instrument(),
        fixed_quantity=0.01,
    )

    order_factory = OrderFactory(
        config=config,
    )

    queue = PendingOrderQueue()

    execution = SimulatedExecution(
        config=config,
    )

    signals = []
    created_orders = []
    execution_results = []

    for event in clock.events():
        if event.phase == SimulationPhase.BAR_OPEN:
            eligible_orders = queue.pop_eligible(
                event
            )

            bar = feed.bars[
                event.bar_index
            ]

            for order in eligible_orders:
                result = execution.execute(
                    order,
                    event=event,
                    bar=bar,
                )

                execution_results.append(
                    result
                )

            continue

        context = context_builder.build(
            event
        )

        signal = signal_processor.process(
            strategy=strategy,
            context=context,
        )

        signals.append(signal)

        decision = risk_gate.evaluate(
            signal
        )

        order = order_factory.create(
            signal=signal,
            risk_decision=decision,
            current_position=None,
        )

        if order is None:
            continue

        created_orders.append(order)

        queue.enqueue(
            order,
            submitted_event=event,
        )

    return (
        feed,
        signals,
        created_orders,
        execution_results,
        queue,
    )


def test_signal_becomes_order_and_fill_on_next_open():
    (
        feed,
        signals,
        orders,
        executions,
        queue,
    ) = run_signal_order_fill_pipeline(
        dataframe=make_contiguous_dataframe(),
        strategy=EnterLongOnFirstClose(),
    )

    assert len(signals) == 3
    assert len(orders) == 1
    assert len(executions) == 1

    signal = signals[0]
    order = orders[0]
    result = executions[0]
    fill = result.fill

    assert (
        signal.action
        == SignalAction.ENTER_LONG
    )

    assert signal.timestamp == utc_time(
        10,
        15,
    )

    assert order.signal_id == signal.signal_id

    assert order.side == OrderSide.BUY
    assert order.quantity == 0.01

    assert order.created_at == utc_time(
        10,
        15,
    )

    assert order.scheduled_for == utc_time(
        10,
        15,
    )

    assert fill.order_id == order.order_id

    assert fill.fill_time == utc_time(
        10,
        15,
    )

    assert (
        fill.reference_price
        == feed.bars[1].open
        == 1.1625
    )

    assert fill.execution_price == 1.1625

    assert queue.is_empty is True


def test_same_timestamp_close_and_next_open_remains_causal():
    (
        feed,
        signals,
        orders,
        executions,
        _,
    ) = run_signal_order_fill_pipeline(
        dataframe=make_contiguous_dataframe(),
        strategy=EnterLongOnFirstClose(),
    )

    signal = signals[0]
    order = orders[0]
    fill = executions[0].fill

    assert signal.timestamp == utc_time(
        10,
        15,
    )

    assert order.created_at == utc_time(
        10,
        15,
    )

    assert fill.fill_time == utc_time(
        10,
        15,
    )

    # Despite identical datetimes, the Fill belongs to the
    # next bar open, not to the bar that generated the Signal.
    assert fill.reference_price == (
        feed.bars[1].open
    )

    assert fill.reference_price != (
        feed.bars[0].close
    )


def test_hold_signals_create_no_orders_or_fills():
    (
        _,
        signals,
        orders,
        executions,
        queue,
    ) = run_signal_order_fill_pipeline(
        dataframe=make_contiguous_dataframe(),
        strategy=HoldStrategy(),
    )

    assert len(signals) == 3

    assert all(
        signal.action
        == SignalAction.HOLD
        for signal in signals
    )

    assert orders == []
    assert executions == []

    assert queue.is_empty is True


def test_signal_on_final_bar_has_no_future_open_to_fill():
    (
        _,
        signals,
        orders,
        executions,
        queue,
    ) = run_signal_order_fill_pipeline(
        dataframe=make_contiguous_dataframe(),
        strategy=EnterLongOnFinalClose(),
    )

    assert signals[-1].action == (
        SignalAction.ENTER_LONG
    )

    assert len(orders) == 1

    assert executions == []

    assert queue.pending_count == 1

    pending_order = (
        queue.pending_orders[0]
    )

    assert pending_order == orders[0]


def test_gap_fills_at_next_available_bar_open():
    dataframe = pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2026-08-08T10:00:00Z",
                    "2026-08-08T10:45:00Z",
                ],
                utc=True,
            ),
            "open": [
                1.1600,
                1.1700,
            ],
            "high": [
                1.1610,
                1.1720,
            ],
            "low": [
                1.1590,
                1.1690,
            ],
            "close": [
                1.1605,
                1.1710,
            ],
            "tick_volume": [
                1000,
                1300,
            ],
        }
    )

    (
        feed,
        signals,
        orders,
        executions,
        queue,
    ) = run_signal_order_fill_pipeline(
        dataframe=dataframe,
        strategy=EnterLongOnFirstClose(),
    )

    assert signals[0].timestamp == utc_time(
        10,
        15,
    )

    assert orders[0].created_at == utc_time(
        10,
        15,
    )

    fill = executions[0].fill

    assert fill.fill_time == utc_time(
        10,
        45,
    )

    assert (
        fill.reference_price
        == feed.bars[1].open
        == 1.1700
    )

    assert queue.is_empty is True