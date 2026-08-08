from datetime import datetime, timezone

import pandas as pd
import pytest

from backtest.clock import SimulationClock
from backtest.context import (
    BacktestContext,
    BacktestContextBuilder,
)
from backtest.execution import (
    ExecutionResult,
    SimulatedExecution,
)
from backtest.feed import HistoricalBarFeed
from backtest.models import (
    BacktestConfig,
    InstrumentSpecification,
    Order,
    OrderSide,
    PositionSide,
    Signal,
    SignalAction,
    Timeframe,
)
from backtest.models.enums import SimulationPhase
from backtest.order_factory import OrderFactory
from backtest.order_queue import PendingOrderQueue
from backtest.portfolio import (
    Portfolio,
    PositionCloseResult,
)
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


def make_long_dataframe() -> pd.DataFrame:
    """
    Long scenario:

    Signal:
        bar 0 close -> ENTER_LONG

    Entry:
        bar 1 open = 1.1620

    Mark-to-market:
        bar 1 close = 1.1650
        unrealized = +3.00

    Exit Signal:
        bar 1 close -> EXIT

    Exit:
        bar 2 open = 1.1670
        realized = +5.00
    """

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
                1.1620,
                1.1670,
            ],
            "high": [
                1.1620,
                1.1660,
                1.1690,
            ],
            "low": [
                1.1590,
                1.1610,
                1.1650,
            ],
            "close": [
                1.1610,
                1.1650,
                1.1660,
            ],
            "tick_volume": [
                1000,
                1100,
                1200,
            ],
        }
    )


def make_short_dataframe() -> pd.DataFrame:
    """
    Short scenario:

    Signal:
        bar 0 close -> ENTER_SHORT

    Entry:
        bar 1 open = 1.1700

    Exit Signal:
        bar 1 close -> EXIT

    Exit:
        bar 2 open = 1.1640
        realized = +6.00
    """

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
                1.1720,
                1.1700,
                1.1640,
            ],
            "high": [
                1.1730,
                1.1710,
                1.1660,
            ],
            "low": [
                1.1700,
                1.1650,
                1.1620,
            ],
            "close": [
                1.1710,
                1.1660,
                1.1630,
            ],
            "tick_volume": [
                1000,
                1100,
                1200,
            ],
        }
    )


class LongThenExitStrategy:
    @property
    def strategy_id(self) -> str:
        return "LONG-THEN-EXIT"

    def on_bar(
        self,
        context: BacktestContext,
    ) -> Signal:
        if context.current_bar_index == 0:
            action = SignalAction.ENTER_LONG

        elif context.current_bar_index == 1:
            action = SignalAction.EXIT

        else:
            action = SignalAction.HOLD

        return Signal(
            signal_id=(
                f"LONG-{context.current_bar_index}"
            ),
            strategy_id=self.strategy_id,
            symbol="EURUSD",
            timestamp=context.current_time,
            action=action,
        )


class ShortThenExitStrategy:
    @property
    def strategy_id(self) -> str:
        return "SHORT-THEN-EXIT"

    def on_bar(
        self,
        context: BacktestContext,
    ) -> Signal:
        if context.current_bar_index == 0:
            action = SignalAction.ENTER_SHORT

        elif context.current_bar_index == 1:
            action = SignalAction.EXIT

        else:
            action = SignalAction.HOLD

        return Signal(
            signal_id=(
                f"SHORT-{context.current_bar_index}"
            ),
            strategy_id=self.strategy_id,
            symbol="EURUSD",
            timestamp=context.current_time,
            action=action,
        )


def run_portfolio_pipeline(
    dataframe: pd.DataFrame,
    strategy,
):
    config = make_config()
    instrument = make_instrument()

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
        instrument=instrument,
        fixed_quantity=0.01,
    )

    order_factory = OrderFactory(
        config=config,
    )

    queue = PendingOrderQueue()

    execution = SimulatedExecution(
        config=config,
    )

    portfolio = Portfolio(
        config=config,
        instrument=instrument,
    )

    signals: list[Signal] = []
    orders: list[Order] = []
    executions: list[ExecutionResult] = []
    closes: list[PositionCloseResult] = []

    equity_snapshots: list[
        tuple[datetime, float, float]
    ] = []

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

                executions.append(result)

                close_result = (
                    portfolio.apply_execution(
                        result
                    )
                )

                if close_result is not None:
                    closes.append(
                        close_result
                    )

            continue

        context = context_builder.build(
            event
        )

        # At BAR_CLOSE the close price has become available,
        # therefore it is safe to mark the Portfolio using it.
        if context.current_bar is not None:
            portfolio.mark_to_market(
                context.current_bar.close
            )

            equity_snapshots.append(
                (
                    context.current_time,
                    portfolio.equity,
                    portfolio.unrealized_pnl,
                )
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
            current_position=(
                portfolio.current_position
            ),
        )

        if order is None:
            continue

        orders.append(order)

        queue.enqueue(
            order,
            submitted_event=event,
        )

    return {
        "feed": feed,
        "signals": signals,
        "orders": orders,
        "executions": executions,
        "closes": closes,
        "portfolio": portfolio,
        "queue": queue,
        "equity_snapshots": equity_snapshots,
    }


def test_long_position_opens_and_closes_end_to_end():
    result = run_portfolio_pipeline(
        dataframe=make_long_dataframe(),
        strategy=LongThenExitStrategy(),
    )

    signals = result["signals"]
    orders = result["orders"]
    executions = result["executions"]
    closes = result["closes"]
    portfolio = result["portfolio"]

    assert len(signals) == 3
    assert len(orders) == 2
    assert len(executions) == 2
    assert len(closes) == 1

    assert (
        signals[0].action
        == SignalAction.ENTER_LONG
    )

    assert (
        signals[1].action
        == SignalAction.EXIT
    )

    assert orders[0].side == OrderSide.BUY
    assert orders[1].side == OrderSide.SELL

    assert executions[0].fill.execution_price == (
        pytest.approx(1.1620)
    )

    assert executions[1].fill.execution_price == (
        pytest.approx(1.1670)
    )

    close_result = closes[0]

    assert (
        close_result.position.side
        == PositionSide.LONG
    )

    assert close_result.gross_pnl == (
        pytest.approx(5.0)
    )

    assert close_result.net_pnl == (
        pytest.approx(5.0)
    )

    assert portfolio.is_flat is True

    assert portfolio.cash == pytest.approx(
        10005.0
    )

    assert portfolio.realized_pnl == (
        pytest.approx(5.0)
    )

    assert portfolio.equity == pytest.approx(
        10005.0
    )


def test_long_mark_to_market_uses_closed_bar_price():
    result = run_portfolio_pipeline(
        dataframe=make_long_dataframe(),
        strategy=LongThenExitStrategy(),
    )

    snapshots = result[
        "equity_snapshots"
    ]

    # BAR 1 closes at 10:30.
    #
    # Position entered at 1.1620.
    # Close price = 1.1650.
    #
    # 0.0030 * 100000 * 0.01 = 3.00
    snapshot = next(
        snapshot
        for snapshot in snapshots
        if snapshot[0] == utc_time(10, 30)
    )

    _, equity, unrealized = snapshot

    assert unrealized == pytest.approx(
        3.0
    )

    assert equity == pytest.approx(
        10003.0
    )


def test_exit_order_uses_full_current_position_quantity():
    result = run_portfolio_pipeline(
        dataframe=make_long_dataframe(),
        strategy=LongThenExitStrategy(),
    )

    orders = result["orders"]

    entry_order = orders[0]
    exit_order = orders[1]

    assert entry_order.quantity == (
        pytest.approx(0.01)
    )

    assert exit_order.quantity == (
        entry_order.quantity
    )


def test_position_preserves_entry_fill_identity():
    result = run_portfolio_pipeline(
        dataframe=make_long_dataframe(),
        strategy=LongThenExitStrategy(),
    )

    executions = result["executions"]
    close_result = result["closes"][0]

    entry_fill = executions[0].fill

    assert (
        close_result.position.entry_fill_id
        == entry_fill.fill_id
    )

    assert (
        close_result.position.entry_price
        == entry_fill.execution_price
    )


def test_close_result_preserves_exit_fill_identity():
    result = run_portfolio_pipeline(
        dataframe=make_long_dataframe(),
        strategy=LongThenExitStrategy(),
    )

    exit_execution = result[
        "executions"
    ][1]

    close_result = result["closes"][0]

    assert (
        close_result.exit_fill_id
        == exit_execution.fill.fill_id
    )

    assert (
        close_result.exit_order_id
        == exit_execution.filled_order.order_id
    )


def test_short_position_opens_and_closes_end_to_end():
    result = run_portfolio_pipeline(
        dataframe=make_short_dataframe(),
        strategy=ShortThenExitStrategy(),
    )

    orders = result["orders"]
    executions = result["executions"]
    closes = result["closes"]
    portfolio = result["portfolio"]

    assert len(orders) == 2
    assert len(executions) == 2
    assert len(closes) == 1

    assert orders[0].side == OrderSide.SELL
    assert orders[1].side == OrderSide.BUY

    assert executions[0].fill.execution_price == (
        pytest.approx(1.1700)
    )

    assert executions[1].fill.execution_price == (
        pytest.approx(1.1640)
    )

    close_result = closes[0]

    assert (
        close_result.position.side
        == PositionSide.SHORT
    )

    # (1.1700 - 1.1640)
    # * 100000
    # * 0.01
    # = 6.00
    assert close_result.gross_pnl == (
        pytest.approx(6.0)
    )

    assert close_result.net_pnl == (
        pytest.approx(6.0)
    )

    assert portfolio.is_flat is True

    assert portfolio.cash == pytest.approx(
        10006.0
    )

    assert portfolio.realized_pnl == (
        pytest.approx(6.0)
    )


def test_pipeline_ends_with_empty_order_queue():
    result = run_portfolio_pipeline(
        dataframe=make_long_dataframe(),
        strategy=LongThenExitStrategy(),
    )

    queue = result["queue"]

    assert queue.is_empty is True
    assert queue.pending_count == 0


def test_neutral_execution_has_no_commission_effect():
    result = run_portfolio_pipeline(
        dataframe=make_long_dataframe(),
        strategy=LongThenExitStrategy(),
    )

    executions = result["executions"]
    close_result = result["closes"][0]

    assert all(
        execution.fill.commission == 0.0
        for execution in executions
    )

    assert close_result.commission == 0.0

    assert (
        close_result.net_pnl
        == close_result.gross_pnl
    )