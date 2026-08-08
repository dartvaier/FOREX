from datetime import datetime, timedelta, timezone

from datetime import datetime, timezone

import pytest

from backtest.clock import ClockEvent
from backtest.costs import FixedCostModel
from backtest.execution import SimulatedExecution
from backtest.models import (
    BacktestConfig,
    InstrumentSpecification,
    MarketBar,
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


def make_execution(
    instrument: InstrumentSpecification,
) -> SimulatedExecution:
    return SimulatedExecution(
        config=make_config(),
        cost_model=FixedCostModel(
            instrument=instrument,
            spread_pips=2.0,
            slippage_pips=0.5,
            commission_per_lot_per_side=3.50,
        ),
    )


def make_order(
    *,
    order_id: str,
    signal_id: str,
    side: OrderSide,
    timestamp: datetime,
    quantity: float = 0.10,
) -> Order:
    return Order(
        order_id=order_id,
        signal_id=signal_id,
        symbol="EURUSD",
        side=side,
        quantity=quantity,
        order_type=OrderType.MARKET,
        created_at=timestamp,
        scheduled_for=timestamp,
        status=OrderStatus.PENDING,
    )


def make_bar(
    timestamp: datetime,
    *,
    price: float = 1.16000,
) -> MarketBar:
    return MarketBar(
        time=timestamp,
        open=price,
        high=price,
        low=price,
        close=price,
        tick_volume=1000,
    )


def make_open_event(
    timestamp: datetime,
    *,
    bar_index: int,
) -> ClockEvent:
    return ClockEvent(
        timestamp=timestamp,
        phase=SimulationPhase.BAR_OPEN,
        bar_index=bar_index,
        bar_start=timestamp,
        bar_close=(
            timestamp
            + timedelta(minutes=15)
        ),
    )


def test_long_round_trip_cost_is_applied_exactly_once():
    instrument = make_instrument()

    execution = make_execution(
        instrument
    )

    portfolio = Portfolio(
        config=make_config(),
        instrument=instrument,
    )

    entry_time = utc_time(10, 15)
    exit_time = utc_time(10, 30)

    entry = execution.execute(
        make_order(
            order_id="ORD-LONG-ENTRY",
            signal_id="SIG-LONG-ENTRY",
            side=OrderSide.BUY,
            timestamp=entry_time,
        ),
        event=make_open_event(
            entry_time,
            bar_index=1,
        ),
        bar=make_bar(entry_time),
    )

    portfolio.apply_execution(entry)

    exit_execution = execution.execute(
        make_order(
            order_id="ORD-LONG-EXIT",
            signal_id="SIG-LONG-EXIT",
            side=OrderSide.SELL,
            timestamp=exit_time,
        ),
        event=make_open_event(
            exit_time,
            bar_index=2,
        ),
        bar=make_bar(exit_time),
    )

    close_result = portfolio.apply_execution(
        exit_execution
    )

    assert close_result is not None

    # Reference market price never moved.
    assert entry.fill.reference_price == pytest.approx(
        1.16000
    )

    assert (
        exit_execution.fill.reference_price
        == pytest.approx(1.16000)
    )

    # BUY:
    # 1 pip half-spread
    # + 0.5 pip slippage
    # = +1.5 pips
    assert entry.fill.execution_price == pytest.approx(
        1.16015
    )

    # SELL:
    # 1 pip half-spread
    # + 0.5 pip slippage
    # = -1.5 pips
    assert (
        exit_execution.fill.execution_price
        == pytest.approx(1.15985)
    )

    # Total adverse price movement:
    #
    # 3 pips
    #
    # 0.00030 * 100000 * 0.10
    # = 3.00
    assert close_result.gross_pnl == pytest.approx(
        -3.00
    )

    # Commission:
    #
    # 3.50 * 0.10 = 0.35 per side
    # round trip = 0.70
    assert close_result.commission == pytest.approx(
        0.70
    )

    assert close_result.net_pnl == pytest.approx(
        -3.70
    )

    assert portfolio.cash == pytest.approx(
        9996.30
    )

    assert portfolio.realized_pnl == pytest.approx(
        -3.70
    )


def test_short_round_trip_cost_is_applied_exactly_once():
    instrument = make_instrument()

    execution = make_execution(
        instrument
    )

    portfolio = Portfolio(
        config=make_config(),
        instrument=instrument,
    )

    entry_time = utc_time(10, 15)
    exit_time = utc_time(10, 30)

    entry = execution.execute(
        make_order(
            order_id="ORD-SHORT-ENTRY",
            signal_id="SIG-SHORT-ENTRY",
            side=OrderSide.SELL,
            timestamp=entry_time,
        ),
        event=make_open_event(
            entry_time,
            bar_index=1,
        ),
        bar=make_bar(entry_time),
    )

    portfolio.apply_execution(entry)

    exit_execution = execution.execute(
        make_order(
            order_id="ORD-SHORT-EXIT",
            signal_id="SIG-SHORT-EXIT",
            side=OrderSide.BUY,
            timestamp=exit_time,
        ),
        event=make_open_event(
            exit_time,
            bar_index=2,
        ),
        bar=make_bar(exit_time),
    )

    close_result = portfolio.apply_execution(
        exit_execution
    )

    assert close_result is not None

    assert entry.fill.execution_price == pytest.approx(
        1.15985
    )

    assert (
        exit_execution.fill.execution_price
        == pytest.approx(1.16015)
    )

    assert close_result.gross_pnl == pytest.approx(
        -3.00
    )

    assert close_result.commission == pytest.approx(
        0.70
    )

    assert close_result.net_pnl == pytest.approx(
        -3.70
    )

    assert portfolio.cash == pytest.approx(
        9996.30
    )

    assert portfolio.realized_pnl == pytest.approx(
        -3.70
    )