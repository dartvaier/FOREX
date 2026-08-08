from datetime import datetime, timezone

import pytest

from backtest.clock import ClockEvent
from backtest.costs import FixedCostModel, ZeroCostModel
from backtest.execution import ExecutionResult, SimulatedExecution
from backtest.models import (
    BacktestConfig,
    Fill,
    InstrumentSpecification,
    MarketBar,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Timeframe,
)
from backtest.models.enums import SimulationPhase


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


def make_instrument(
    symbol: str = "EURUSD",
) -> InstrumentSpecification:
    return InstrumentSpecification(
        symbol=symbol,
        digits=5,
        point=0.00001,
        pip_size=0.00010,
        contract_size=100000,
        volume_min=0.01,
        volume_max=500.0,
        volume_step=0.01,
        tick_size=0.00001,
    )


def make_execution() -> SimulatedExecution:
    instrument = make_instrument()

    return SimulatedExecution(
        config=make_config(),
        cost_model=ZeroCostModel(
            instrument=instrument,
        ),
    )


def make_order(
    *,
    side: OrderSide = OrderSide.BUY,
    status: OrderStatus = OrderStatus.PENDING,
    symbol: str = "EURUSD",
    created_at: datetime | None = None,
    scheduled_for: datetime | None = None,
) -> Order:
    created_at = (
        created_at
        if created_at is not None
        else utc_time(10, 15)
    )

    scheduled_for = (
        scheduled_for
        if scheduled_for is not None
        else created_at
    )

    return Order(
        order_id="ORD-001",
        signal_id="SIG-001",
        symbol=symbol,
        side=side,
        quantity=0.05,
        order_type=OrderType.MARKET,
        created_at=created_at,
        scheduled_for=scheduled_for,
        status=status,
    )


def make_bar(
    *,
    time: datetime | None = None,
    open_price: float = 1.1610,
) -> MarketBar:
    return MarketBar(
        time=(
            time
            if time is not None
            else utc_time(10, 15)
        ),
        open=open_price,
        high=open_price + 0.0020,
        low=open_price - 0.0020,
        close=open_price + 0.0010,
        tick_volume=1000,
    )


def make_open_event(
    *,
    timestamp: datetime | None = None,
    bar_index: int = 1,
) -> ClockEvent:
    timestamp = (
        timestamp
        if timestamp is not None
        else utc_time(10, 15)
    )

    return ClockEvent(
        timestamp=timestamp,
        phase=SimulationPhase.BAR_OPEN,
        bar_index=bar_index,
        bar_start=timestamp,
        bar_close=(
            timestamp
            + (
                utc_time(10, 30)
                - utc_time(10, 15)
            )
        ),
    )


def test_execution_is_created_with_config_and_cost_model():
    config = make_config()

    cost_model = ZeroCostModel(
        instrument=make_instrument()
    )

    execution = SimulatedExecution(
        config=config,
        cost_model=cost_model,
    )

    assert execution.config is config
    assert execution.cost_model is cost_model


def test_execution_requires_config():
    with pytest.raises(
        TypeError,
        match="BacktestConfig",
    ):
        SimulatedExecution(
            config=None,  # type: ignore[arg-type]
            cost_model=ZeroCostModel(
                instrument=make_instrument()
            ),
        )


def test_execution_requires_cost_model():
    with pytest.raises(
        TypeError,
        match="CostModel",
    ):
        SimulatedExecution(
            config=make_config(),
            cost_model=object(),  # type: ignore[arg-type]
        )


def test_execution_rejects_cost_model_symbol_mismatch():
    cost_model = ZeroCostModel(
        instrument=make_instrument(
            symbol="GBPUSD"
        )
    )

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        SimulatedExecution(
            config=make_config(),
            cost_model=cost_model,
        )


def test_buy_order_executes_at_bar_open():
    execution = make_execution()

    result = execution.execute(
        make_order(
            side=OrderSide.BUY
        ),
        event=make_open_event(),
        bar=make_bar(
            open_price=1.1610
        ),
    )

    assert isinstance(
        result,
        ExecutionResult,
    )

    assert isinstance(
        result.fill,
        Fill,
    )

    assert result.fill.reference_price == pytest.approx(
        1.1610
    )

    assert result.fill.execution_price == pytest.approx(
        1.1610
    )


def test_sell_order_executes_at_same_open_price_in_neutral_model():
    execution = make_execution()

    result = execution.execute(
        make_order(
            side=OrderSide.SELL
        ),
        event=make_open_event(),
        bar=make_bar(
            open_price=1.1610
        ),
    )

    assert result.fill.execution_price == pytest.approx(
        1.1610
    )


def test_execution_uses_order_quantity():
    order = make_order()

    result = make_execution().execute(
        order,
        event=make_open_event(),
        bar=make_bar(),
    )

    assert result.fill.quantity == order.quantity


def test_execution_produces_filled_order_snapshot():
    order = make_order()

    result = make_execution().execute(
        order,
        event=make_open_event(),
        bar=make_bar(),
    )

    assert result.filled_order.status == OrderStatus.FILLED


def test_execution_does_not_mutate_original_order():
    order = make_order()

    result = make_execution().execute(
        order,
        event=make_open_event(),
        bar=make_bar(),
    )

    assert order.status == OrderStatus.PENDING
    assert result.filled_order is not order


def test_fill_preserves_order_identity():
    order = make_order()

    result = make_execution().execute(
        order,
        event=make_open_event(),
        bar=make_bar(),
    )

    assert result.fill.order_id == order.order_id
    assert result.filled_order.order_id == order.order_id


def test_fill_id_is_deterministic():
    result = make_execution().execute(
        make_order(),
        event=make_open_event(),
        bar=make_bar(),
    )

    assert result.fill.fill_id == "FILL-ORD-001"


def test_fill_time_equals_bar_open_event_time():
    result = make_execution().execute(
        make_order(),
        event=make_open_event(
            timestamp=utc_time(10, 15)
        ),
        bar=make_bar(
            time=utc_time(10, 15)
        ),
    )

    assert result.fill.fill_time == utc_time(10, 15)


def test_same_timestamp_signal_close_and_next_open_is_allowed():
    order = make_order(
        created_at=utc_time(10, 15),
        scheduled_for=utc_time(10, 15),
    )

    result = make_execution().execute(
        order,
        event=make_open_event(
            timestamp=utc_time(10, 15),
            bar_index=1,
        ),
        bar=make_bar(
            time=utc_time(10, 15)
        ),
    )

    assert result.fill.fill_time == order.created_at


def test_gap_execution_uses_next_available_open():
    order = make_order(
        created_at=utc_time(10, 15),
        scheduled_for=utc_time(10, 15),
    )

    result = make_execution().execute(
        order,
        event=make_open_event(
            timestamp=utc_time(10, 45),
            bar_index=1,
        ),
        bar=make_bar(
            time=utc_time(10, 45),
            open_price=1.1650,
        ),
    )

    assert result.fill.fill_time == utc_time(10, 45)
    assert result.fill.reference_price == pytest.approx(1.1650)


def test_zero_cost_model_produces_frictionless_fill():
    result = make_execution().execute(
        make_order(),
        event=make_open_event(),
        bar=make_bar(
            open_price=1.1610
        ),
    )

    assert result.fill.reference_price == pytest.approx(1.1610)
    assert result.fill.execution_price == pytest.approx(1.1610)
    assert result.fill.spread_impact == 0.0
    assert result.fill.slippage == 0.0
    assert result.fill.commission == 0.0


def test_execution_applies_fixed_cost_model():
    cost_model = FixedCostModel(
        instrument=make_instrument(),
        spread_pips=2.0,
        slippage_pips=0.5,
        commission_per_lot_per_side=3.50,
    )

    execution = SimulatedExecution(
        config=make_config(),
        cost_model=cost_model,
    )

    result = execution.execute(
        make_order(
            side=OrderSide.BUY
        ),
        event=make_open_event(),
        bar=make_bar(
            open_price=1.16000
        ),
    )

    fill = result.fill

    assert fill.reference_price == pytest.approx(1.16000)
    assert fill.spread_impact == pytest.approx(0.00010)
    assert fill.slippage == pytest.approx(0.00005)
    assert fill.execution_price == pytest.approx(1.16015)
    assert fill.commission == pytest.approx(0.175)


def test_sell_execution_applies_costs_adversely():
    cost_model = FixedCostModel(
        instrument=make_instrument(),
        spread_pips=2.0,
        slippage_pips=0.5,
        commission_per_lot_per_side=3.50,
    )

    execution = SimulatedExecution(
        config=make_config(),
        cost_model=cost_model,
    )

    result = execution.execute(
        make_order(
            side=OrderSide.SELL
        ),
        event=make_open_event(),
        bar=make_bar(
            open_price=1.16000
        ),
    )

    fill = result.fill

    assert fill.reference_price == pytest.approx(1.16000)
    assert fill.execution_price == pytest.approx(1.15985)
    assert fill.spread_impact == pytest.approx(0.00010)
    assert fill.slippage == pytest.approx(0.00005)
    assert fill.commission == pytest.approx(0.175)


def test_execution_requires_order():
    execution = make_execution()

    with pytest.raises(
        TypeError,
        match="Order",
    ):
        execution.execute(
            object(),  # type: ignore[arg-type]
            event=make_open_event(),
            bar=make_bar(),
        )


def test_execution_requires_clock_event():
    execution = make_execution()

    with pytest.raises(
        TypeError,
        match="ClockEvent",
    ):
        execution.execute(
            make_order(),
            event=object(),  # type: ignore[arg-type]
            bar=make_bar(),
        )


def test_execution_requires_market_bar():
    execution = make_execution()

    with pytest.raises(
        TypeError,
        match="MarketBar",
    ):
        execution.execute(
            make_order(),
            event=make_open_event(),
            bar=object(),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "status",
    [
        OrderStatus.FILLED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
        OrderStatus.UNFILLED,
    ],
)
def test_execution_accepts_only_pending_orders(
    status,
):
    execution = make_execution()

    with pytest.raises(
        ValueError,
        match="PENDING",
    ):
        execution.execute(
            make_order(
                status=status
            ),
            event=make_open_event(),
            bar=make_bar(),
        )


def test_execution_rejects_order_symbol_mismatch():
    execution = make_execution()

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        execution.execute(
            make_order(
                symbol="GBPUSD"
            ),
            event=make_open_event(),
            bar=make_bar(),
        )


def test_execution_only_occurs_at_bar_open():
    execution = make_execution()

    event = ClockEvent(
        timestamp=utc_time(10, 30),
        phase=SimulationPhase.BAR_CLOSE,
        bar_index=1,
        bar_start=utc_time(10, 15),
        bar_close=utc_time(10, 30),
    )

    with pytest.raises(
        ValueError,
        match="BAR_OPEN",
    ):
        execution.execute(
            make_order(),
            event=event,
            bar=make_bar(),
        )


def test_execution_rejects_event_for_different_bar():
    execution = make_execution()

    event = make_open_event(
        timestamp=utc_time(10, 30)
    )

    bar = make_bar(
        time=utc_time(10, 15)
    )

    with pytest.raises(
        ValueError,
        match="bar_start",
    ):
        execution.execute(
            make_order(),
            event=event,
            bar=bar,
        )


def test_execution_rejects_order_before_scheduled_time():
    execution = make_execution()

    order = make_order(
        created_at=utc_time(10, 15),
        scheduled_for=utc_time(10, 45),
    )

    with pytest.raises(
        ValueError,
        match="not yet eligible",
    ):
        execution.execute(
            order,
            event=make_open_event(
                timestamp=utc_time(10, 30),
                bar_index=2,
            ),
            bar=make_bar(
                time=utc_time(10, 30)
            ),
        )


def test_execution_result_is_immutable():
    result = make_execution().execute(
        make_order(),
        event=make_open_event(),
        bar=make_bar(),
    )

    with pytest.raises(AttributeError):
        result.fill = None  # type: ignore[misc]