from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from backtest.clock import ClockEvent
from backtest.equity_ledger import EquityLedger
from backtest.equity_recorder import EquityRecorder
from backtest.execution import ExecutionResult
from backtest.models import (
    BacktestConfig,
    Fill,
    InstrumentSpecification,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Timeframe,
)
from backtest.models.enums import SimulationPhase
from backtest.portfolio import Portfolio


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
        date_from=utc_time(10),
        date_to=utc_time(12),
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


def make_event(
    *,
    timestamp: datetime,
    bar_index: int,
    phase: SimulationPhase,
) -> ClockEvent:
    bar_start = (
        timestamp
        if phase == SimulationPhase.BAR_OPEN
        else timestamp - timedelta(minutes=15)
    )

    return ClockEvent(
        timestamp=timestamp,
        phase=phase,
        bar_index=bar_index,
        bar_start=bar_start,
        bar_close=(
            bar_start
            + timedelta(minutes=15)
        ),
    )


def open_long_position(
    portfolio: Portfolio,
) -> None:
    timestamp = utc_time(10, 15)

    order = Order(
        order_id="ORD-ENTRY",
        signal_id="SIG-ENTRY",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.MARKET,
        created_at=timestamp,
        scheduled_for=timestamp,
        status=OrderStatus.FILLED,
        metadata={
            "strategy_id": "TEST-STRATEGY",
        },
    )

    fill = Fill(
        fill_id="FILL-ENTRY",
        order_id=order.order_id,
        fill_time=timestamp,
        reference_price=1.1600,
        execution_price=1.1600,
        quantity=0.01,
        spread_impact=0.0,
        slippage=0.0,
        commission=1.0,
    )

    portfolio.apply_execution(
        ExecutionResult(
            filled_order=order,
            fill=fill,
        )
    )


def test_recorder_stores_portfolio_state():
    portfolio = Portfolio(
        config=make_config(),
        instrument=make_instrument(),
    )

    ledger = EquityLedger()
    recorder = EquityRecorder(
        ledger
    )

    event = make_event(
        timestamp=utc_time(10, 0),
        bar_index=0,
        phase=SimulationPhase.BAR_OPEN,
    )

    point = recorder.record(
        event,
        portfolio,
    )

    assert ledger.count == 1
    assert ledger.last_point is point

    assert point.cash == pytest.approx(
        10000.0
    )

    assert point.equity == pytest.approx(
        10000.0
    )

    assert point.realized_pnl == pytest.approx(
        0.0
    )

    assert point.unrealized_pnl == pytest.approx(
        0.0
    )


def test_bar_open_records_state_after_entry_execution():
    portfolio = Portfolio(
        config=make_config(),
        instrument=make_instrument(),
    )

    open_long_position(
        portfolio
    )

    ledger = EquityLedger()
    recorder = EquityRecorder(
        ledger
    )

    event = make_event(
        timestamp=utc_time(10, 15),
        bar_index=1,
        phase=SimulationPhase.BAR_OPEN,
    )

    point = recorder.record(
        event,
        portfolio,
    )

    # Entry commission = 1.00
    assert point.cash == pytest.approx(
        9999.0
    )

    assert point.realized_pnl == pytest.approx(
        -1.0
    )

    assert point.unrealized_pnl == pytest.approx(
        0.0
    )

    assert point.equity == pytest.approx(
        9999.0
    )


def test_bar_close_records_marked_to_market_equity():
    portfolio = Portfolio(
        config=make_config(),
        instrument=make_instrument(),
    )

    open_long_position(
        portfolio
    )

    # LONG entry = 1.1600
    # mark       = 1.1650
    #
    # +0.0050 * 100000 * 0.01
    # = +5.00 unrealized
    portfolio.mark_to_market(
        1.1650
    )

    ledger = EquityLedger()
    recorder = EquityRecorder(
        ledger
    )

    event = make_event(
        timestamp=utc_time(10, 30),
        bar_index=1,
        phase=SimulationPhase.BAR_CLOSE,
    )

    point = recorder.record(
        event,
        portfolio,
    )

    assert point.cash == pytest.approx(
        9999.0
    )

    assert point.unrealized_pnl == pytest.approx(
        5.0
    )

    assert point.equity == pytest.approx(
        10004.0
    )


def test_same_timestamp_close_then_open_is_preserved():
    portfolio = Portfolio(
        config=make_config(),
        instrument=make_instrument(),
    )

    ledger = EquityLedger()
    recorder = EquityRecorder(
        ledger
    )

    recorder.record(
        make_event(
            timestamp=utc_time(10, 15),
            bar_index=0,
            phase=SimulationPhase.BAR_CLOSE,
        ),
        portfolio,
    )

    recorder.record(
        make_event(
            timestamp=utc_time(10, 15),
            bar_index=1,
            phase=SimulationPhase.BAR_OPEN,
        ),
        portfolio,
    )

    assert ledger.count == 2

    assert (
        ledger.points[0].phase
        == SimulationPhase.BAR_CLOSE
    )

    assert (
        ledger.points[1].phase
        == SimulationPhase.BAR_OPEN
    )


def test_recorder_requires_equity_ledger():
    with pytest.raises(
        TypeError,
        match="EquityLedger",
    ):
        EquityRecorder(
            object()  # type: ignore[arg-type]
        )


def test_record_requires_clock_event():
    recorder = EquityRecorder(
        EquityLedger()
    )

    portfolio = Portfolio(
        config=make_config(),
        instrument=make_instrument(),
    )

    with pytest.raises(
        TypeError,
        match="ClockEvent",
    ):
        recorder.record(
            object(),  # type: ignore[arg-type]
            portfolio,
        )


def test_record_requires_portfolio():
    recorder = EquityRecorder(
        EquityLedger()
    )

    event = make_event(
        timestamp=utc_time(10),
        bar_index=0,
        phase=SimulationPhase.BAR_OPEN,
    )

    with pytest.raises(
        TypeError,
        match="Portfolio",
    ):
        recorder.record(
            event,
            object(),  # type: ignore[arg-type]
        )