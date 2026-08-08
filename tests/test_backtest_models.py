from backtest.models.config import BacktestConfig

from backtest.models.instrument import InstrumentSpecification

from backtest.models.trade import Trade

from dataclasses import replace

from backtest.models.position import Position

from datetime import datetime, timedelta, timezone

from backtest.models.fill import Fill

from backtest.models.order import Order

import pytest

from backtest.models.signal import Signal


from backtest.models.enums import (
    AmbiguousBarPolicy,
    ExitReason,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    SignalAction,
    EndOfBacktestPolicy,
    Timeframe,
)


def test_signal_action_values():
    assert SignalAction.ENTER_LONG == "ENTER_LONG"
    assert SignalAction.ENTER_SHORT == "ENTER_SHORT"
    assert SignalAction.EXIT == "EXIT"
    assert SignalAction.HOLD == "HOLD"


def test_order_side_values():
    assert OrderSide.BUY == "BUY"
    assert OrderSide.SELL == "SELL"


def test_order_type_baseline_is_market():
    assert list(OrderType) == [
        OrderType.MARKET,
    ]


def test_order_status_values():
    assert OrderStatus.PENDING == "PENDING"
    assert OrderStatus.FILLED == "FILLED"
    assert OrderStatus.REJECTED == "REJECTED"
    assert OrderStatus.CANCELLED == "CANCELLED"
    assert OrderStatus.UNFILLED == "UNFILLED"


def test_position_side_values():
    assert PositionSide.LONG == "LONG"
    assert PositionSide.SHORT == "SHORT"


def test_exit_reason_values():
    assert ExitReason.STRATEGY_EXIT == "STRATEGY_EXIT"
    assert ExitReason.STOP_LOSS == "STOP_LOSS"
    assert ExitReason.TAKE_PROFIT == "TAKE_PROFIT"
    assert ExitReason.END_OF_BACKTEST == "END_OF_BACKTEST"
    assert ExitReason.RISK_EXIT == "RISK_EXIT"
    assert ExitReason.KILL_SWITCH == "KILL_SWITCH"
    assert ExitReason.MANUAL_TEST == "MANUAL_TEST"


def test_ambiguous_bar_policy_baseline():
    assert list(AmbiguousBarPolicy) == [
        AmbiguousBarPolicy.WORST_CASE,
    ]


def test_enums_are_serializable_as_strings():
    assert str(SignalAction.ENTER_LONG) == "ENTER_LONG"
    assert str(OrderStatus.PENDING) == "PENDING"
    assert str(PositionSide.LONG) == "LONG"
    assert str(ExitReason.STOP_LOSS) == "STOP_LOSS"
    
def test_signal_is_created_with_valid_data():
    timestamp = datetime(
        2026,
        8,
        8,
        12,
        0,
        tzinfo=timezone.utc,
    )

    signal = Signal(
        signal_id="SIG-001",
        strategy_id="EMA-TREND-001",
        symbol="EURUSD",
        timestamp=timestamp,
        action=SignalAction.ENTER_LONG,
        reason="Fast EMA crossed above slow EMA",
        metadata={"fast_ema": 50, "slow_ema": 200},
    )

    assert signal.signal_id == "SIG-001"
    assert signal.strategy_id == "EMA-TREND-001"
    assert signal.symbol == "EURUSD"
    assert signal.timestamp == timestamp
    assert signal.action == SignalAction.ENTER_LONG
    assert signal.reason == "Fast EMA crossed above slow EMA"

    assert signal.metadata["fast_ema"] == 50
    assert signal.metadata["slow_ema"] == 200


def test_signal_metadata_defaults_to_empty_mapping():
    signal = Signal(
        signal_id="SIG-001",
        strategy_id="TEST",
        symbol="EURUSD",
        timestamp=datetime.now(timezone.utc),
        action=SignalAction.HOLD,
    )

    assert dict(signal.metadata) == {}


def test_signal_requires_non_empty_signal_id():
    with pytest.raises(ValueError, match="signal_id"):
        Signal(
            signal_id="",
            strategy_id="TEST",
            symbol="EURUSD",
            timestamp=datetime.now(timezone.utc),
            action=SignalAction.HOLD,
        )


def test_signal_requires_non_empty_strategy_id():
    with pytest.raises(ValueError, match="strategy_id"):
        Signal(
            signal_id="SIG-001",
            strategy_id="",
            symbol="EURUSD",
            timestamp=datetime.now(timezone.utc),
            action=SignalAction.HOLD,
        )


def test_signal_requires_non_empty_symbol():
    with pytest.raises(ValueError, match="symbol"):
        Signal(
            signal_id="SIG-001",
            strategy_id="TEST",
            symbol="",
            timestamp=datetime.now(timezone.utc),
            action=SignalAction.HOLD,
        )


def test_signal_requires_timezone_aware_timestamp():
    naive_timestamp = datetime(2026, 8, 8, 12, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        Signal(
            signal_id="SIG-001",
            strategy_id="TEST",
            symbol="EURUSD",
            timestamp=naive_timestamp,
            action=SignalAction.HOLD,
        )


def test_signal_requires_signal_action_enum():
    with pytest.raises(TypeError, match="SignalAction"):
        Signal(
            signal_id="SIG-001",
            strategy_id="TEST",
            symbol="EURUSD",
            timestamp=datetime.now(timezone.utc),
            action="ENTER_LONG",  # type: ignore[arg-type]
        )


def test_signal_is_immutable():
    signal = Signal(
        signal_id="SIG-001",
        strategy_id="TEST",
        symbol="EURUSD",
        timestamp=datetime.now(timezone.utc),
        action=SignalAction.ENTER_LONG,
    )

    with pytest.raises(AttributeError):
        signal.action = SignalAction.EXIT  # type: ignore[misc]


def test_signal_metadata_is_immutable():
    signal = Signal(
        signal_id="SIG-001",
        strategy_id="TEST",
        symbol="EURUSD",
        timestamp=datetime.now(timezone.utc),
        action=SignalAction.ENTER_LONG,
        metadata={"value": 123},
    )

    with pytest.raises(TypeError):
        signal.metadata["value"] = 456  # type: ignore[index]


def test_signal_copies_input_metadata():
    metadata = {"value": 123}

    signal = Signal(
        signal_id="SIG-001",
        strategy_id="TEST",
        symbol="EURUSD",
        timestamp=datetime.now(timezone.utc),
        action=SignalAction.ENTER_LONG,
        metadata=metadata,
    )

    metadata["value"] = 999

    assert signal.metadata["value"] == 123

def test_order_is_created_with_valid_data():
    created_at = datetime(
        2026,
        8,
        8,
        12,
        0,
        tzinfo=timezone.utc,
    )

    scheduled_for = created_at + timedelta(minutes=15)

    order = Order(
        order_id="ORD-001",
        signal_id="SIG-001",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.MARKET,
        created_at=created_at,
        scheduled_for=scheduled_for,
        stop_loss=1.1500,
        take_profit=1.1700,
        reason="Risk approved signal",
        metadata={"risk_model": "fixed-size"},
    )

    assert order.order_id == "ORD-001"
    assert order.signal_id == "SIG-001"
    assert order.symbol == "EURUSD"
    assert order.side == OrderSide.BUY
    assert order.quantity == 0.01
    assert order.order_type == OrderType.MARKET

    assert order.created_at == created_at
    assert order.scheduled_for == scheduled_for

    assert order.status == OrderStatus.PENDING

    assert order.stop_loss == 1.1500
    assert order.take_profit == 1.1700

    assert order.reason == "Risk approved signal"
    assert order.metadata["risk_model"] == "fixed-size"


def test_order_defaults_to_pending():
    timestamp = datetime.now(timezone.utc)

    order = Order(
        order_id="ORD-001",
        signal_id="SIG-001",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.MARKET,
        created_at=timestamp,
        scheduled_for=timestamp,
    )

    assert order.status == OrderStatus.PENDING


def test_order_allows_same_timestamp_for_created_and_scheduled():
    timestamp = datetime.now(timezone.utc)

    order = Order(
        order_id="ORD-001",
        signal_id="SIG-001",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.MARKET,
        created_at=timestamp,
        scheduled_for=timestamp,
    )

    assert order.scheduled_for == order.created_at


def test_order_requires_non_empty_order_id():
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="order_id"):
        Order(
            order_id="",
            signal_id="SIG-001",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=0.01,
            order_type=OrderType.MARKET,
            created_at=timestamp,
            scheduled_for=timestamp,
        )


def test_order_requires_non_empty_signal_id():
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="signal_id"):
        Order(
            order_id="ORD-001",
            signal_id="",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=0.01,
            order_type=OrderType.MARKET,
            created_at=timestamp,
            scheduled_for=timestamp,
        )


def test_order_requires_non_empty_symbol():
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="symbol"):
        Order(
            order_id="ORD-001",
            signal_id="SIG-001",
            symbol="",
            side=OrderSide.BUY,
            quantity=0.01,
            order_type=OrderType.MARKET,
            created_at=timestamp,
            scheduled_for=timestamp,
        )


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        -0.01,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_order_requires_positive_finite_quantity(quantity):
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="quantity"):
        Order(
            order_id="ORD-001",
            signal_id="SIG-001",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=quantity,
            order_type=OrderType.MARKET,
            created_at=timestamp,
            scheduled_for=timestamp,
        )


def test_order_requires_timezone_aware_created_at():
    naive_timestamp = datetime(2026, 8, 8, 12, 0)
    scheduled_for = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="created_at"):
        Order(
            order_id="ORD-001",
            signal_id="SIG-001",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=0.01,
            order_type=OrderType.MARKET,
            created_at=naive_timestamp,
            scheduled_for=scheduled_for,
        )


def test_order_requires_timezone_aware_scheduled_for():
    created_at = datetime.now(timezone.utc)
    naive_timestamp = datetime(2026, 8, 8, 12, 15)

    with pytest.raises(ValueError, match="scheduled_for"):
        Order(
            order_id="ORD-001",
            signal_id="SIG-001",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=0.01,
            order_type=OrderType.MARKET,
            created_at=created_at,
            scheduled_for=naive_timestamp,
        )


def test_order_cannot_be_scheduled_before_creation():
    created_at = datetime(
        2026,
        8,
        8,
        12,
        15,
        tzinfo=timezone.utc,
    )

    scheduled_for = created_at - timedelta(minutes=15)

    with pytest.raises(ValueError, match="scheduled_for"):
        Order(
            order_id="ORD-001",
            signal_id="SIG-001",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=0.01,
            order_type=OrderType.MARKET,
            created_at=created_at,
            scheduled_for=scheduled_for,
        )


def test_order_requires_order_side_enum():
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(TypeError, match="OrderSide"):
        Order(
            order_id="ORD-001",
            signal_id="SIG-001",
            symbol="EURUSD",
            side="BUY",  # type: ignore[arg-type]
            quantity=0.01,
            order_type=OrderType.MARKET,
            created_at=timestamp,
            scheduled_for=timestamp,
        )


def test_order_requires_order_type_enum():
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(TypeError, match="OrderType"):
        Order(
            order_id="ORD-001",
            signal_id="SIG-001",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=0.01,
            order_type="MARKET",  # type: ignore[arg-type]
            created_at=timestamp,
            scheduled_for=timestamp,
        )


def test_order_requires_order_status_enum():
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(TypeError, match="OrderStatus"):
        Order(
            order_id="ORD-001",
            signal_id="SIG-001",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=0.01,
            order_type=OrderType.MARKET,
            created_at=timestamp,
            scheduled_for=timestamp,
            status="PENDING",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "stop_loss",
    [
        0,
        -1.0,
        float("inf"),
        float("nan"),
    ],
)
def test_order_validates_stop_loss(stop_loss):
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="stop_loss"):
        Order(
            order_id="ORD-001",
            signal_id="SIG-001",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=0.01,
            order_type=OrderType.MARKET,
            created_at=timestamp,
            scheduled_for=timestamp,
            stop_loss=stop_loss,
        )


@pytest.mark.parametrize(
    "take_profit",
    [
        0,
        -1.0,
        float("inf"),
        float("nan"),
    ],
)
def test_order_validates_take_profit(take_profit):
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="take_profit"):
        Order(
            order_id="ORD-001",
            signal_id="SIG-001",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=0.01,
            order_type=OrderType.MARKET,
            created_at=timestamp,
            scheduled_for=timestamp,
            take_profit=take_profit,
        )


def test_order_is_immutable():
    timestamp = datetime.now(timezone.utc)

    order = Order(
        order_id="ORD-001",
        signal_id="SIG-001",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.MARKET,
        created_at=timestamp,
        scheduled_for=timestamp,
    )

    with pytest.raises(AttributeError):
        order.quantity = 1.0  # type: ignore[misc]


def test_order_metadata_is_immutable_and_copied():
    timestamp = datetime.now(timezone.utc)

    metadata = {
        "risk_model": "fixed-size",
    }

    order = Order(
        order_id="ORD-001",
        signal_id="SIG-001",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.MARKET,
        created_at=timestamp,
        scheduled_for=timestamp,
        metadata=metadata,
    )

    metadata["risk_model"] = "changed"

    assert order.metadata["risk_model"] == "fixed-size"

    with pytest.raises(TypeError):
        order.metadata["risk_model"] = "other"  # type: ignore[index]

def test_fill_is_created_with_valid_data():
    fill_time = datetime(
        2026,
        8,
        8,
        12,
        15,
        tzinfo=timezone.utc,
    )

    fill = Fill(
        fill_id="FILL-001",
        order_id="ORD-001",
        fill_time=fill_time,
        reference_price=1.16000,
        execution_price=1.16007,
        quantity=0.01,
        spread_impact=0.00005,
        slippage=0.00002,
        commission=0.07,
    )

    assert fill.fill_id == "FILL-001"
    assert fill.order_id == "ORD-001"

    assert fill.fill_time == fill_time

    assert fill.reference_price == 1.16000
    assert fill.execution_price == 1.16007
    assert fill.quantity == 0.01

    assert fill.spread_impact == 0.00005
    assert fill.slippage == 0.00002
    assert fill.commission == 0.07


def test_fill_costs_default_to_zero():
    fill = Fill(
        fill_id="FILL-001",
        order_id="ORD-001",
        fill_time=datetime.now(timezone.utc),
        reference_price=1.16000,
        execution_price=1.16000,
        quantity=0.01,
    )

    assert fill.spread_impact == 0.0
    assert fill.slippage == 0.0
    assert fill.commission == 0.0


def test_fill_requires_non_empty_fill_id():
    with pytest.raises(ValueError, match="fill_id"):
        Fill(
            fill_id="",
            order_id="ORD-001",
            fill_time=datetime.now(timezone.utc),
            reference_price=1.16000,
            execution_price=1.16000,
            quantity=0.01,
        )


def test_fill_requires_non_empty_order_id():
    with pytest.raises(ValueError, match="order_id"):
        Fill(
            fill_id="FILL-001",
            order_id="",
            fill_time=datetime.now(timezone.utc),
            reference_price=1.16000,
            execution_price=1.16000,
            quantity=0.01,
        )


def test_fill_requires_timezone_aware_fill_time():
    naive_time = datetime(
        2026,
        8,
        8,
        12,
        15,
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        Fill(
            fill_id="FILL-001",
            order_id="ORD-001",
            fill_time=naive_time,
            reference_price=1.16000,
            execution_price=1.16000,
            quantity=0.01,
        )


@pytest.mark.parametrize(
    "reference_price",
    [
        0,
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_fill_requires_positive_finite_reference_price(
    reference_price,
):
    with pytest.raises(
        ValueError,
        match="reference_price",
    ):
        Fill(
            fill_id="FILL-001",
            order_id="ORD-001",
            fill_time=datetime.now(timezone.utc),
            reference_price=reference_price,
            execution_price=1.16000,
            quantity=0.01,
        )


@pytest.mark.parametrize(
    "execution_price",
    [
        0,
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_fill_requires_positive_finite_execution_price(
    execution_price,
):
    with pytest.raises(
        ValueError,
        match="execution_price",
    ):
        Fill(
            fill_id="FILL-001",
            order_id="ORD-001",
            fill_time=datetime.now(timezone.utc),
            reference_price=1.16000,
            execution_price=execution_price,
            quantity=0.01,
        )


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        -0.01,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_fill_requires_positive_finite_quantity(
    quantity,
):
    with pytest.raises(
        ValueError,
        match="quantity",
    ):
        Fill(
            fill_id="FILL-001",
            order_id="ORD-001",
            fill_time=datetime.now(timezone.utc),
            reference_price=1.16000,
            execution_price=1.16000,
            quantity=quantity,
        )


@pytest.mark.parametrize(
    "spread_impact",
    [
        -0.00001,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_fill_requires_non_negative_finite_spread_impact(
    spread_impact,
):
    with pytest.raises(
        ValueError,
        match="spread_impact",
    ):
        Fill(
            fill_id="FILL-001",
            order_id="ORD-001",
            fill_time=datetime.now(timezone.utc),
            reference_price=1.16000,
            execution_price=1.16000,
            quantity=0.01,
            spread_impact=spread_impact,
        )


@pytest.mark.parametrize(
    "slippage",
    [
        -0.00001,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_fill_requires_non_negative_finite_slippage(
    slippage,
):
    with pytest.raises(
        ValueError,
        match="slippage",
    ):
        Fill(
            fill_id="FILL-001",
            order_id="ORD-001",
            fill_time=datetime.now(timezone.utc),
            reference_price=1.16000,
            execution_price=1.16000,
            quantity=0.01,
            slippage=slippage,
        )


@pytest.mark.parametrize(
    "commission",
    [
        -0.01,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_fill_requires_non_negative_finite_commission(
    commission,
):
    with pytest.raises(
        ValueError,
        match="commission",
    ):
        Fill(
            fill_id="FILL-001",
            order_id="ORD-001",
            fill_time=datetime.now(timezone.utc),
            reference_price=1.16000,
            execution_price=1.16000,
            quantity=0.01,
            commission=commission,
        )


def test_fill_is_immutable():
    fill = Fill(
        fill_id="FILL-001",
        order_id="ORD-001",
        fill_time=datetime.now(timezone.utc),
        reference_price=1.16000,
        execution_price=1.16000,
        quantity=0.01,
    )

    with pytest.raises(AttributeError):
        fill.execution_price = 1.17000  # type: ignore[misc]

def test_position_is_created_with_valid_data():
    entry_time = datetime(
        2026,
        8,
        8,
        12,
        15,
        tzinfo=timezone.utc,
    )

    position = Position(
        position_id="POS-001",
        entry_fill_id="FILL-001",
        symbol="EURUSD",
        side=PositionSide.LONG,
        quantity=0.01,
        entry_time=entry_time,
        entry_price=1.16000,
        stop_loss=1.15000,
        take_profit=1.18000,
        unrealized_pnl=12.50,
        metadata={"strategy_id": "EMA-TREND-001"},
    )

    assert position.position_id == "POS-001"
    assert position.entry_fill_id == "FILL-001"

    assert position.symbol == "EURUSD"
    assert position.side == PositionSide.LONG
    assert position.quantity == 0.01

    assert position.entry_time == entry_time
    assert position.entry_price == 1.16000

    assert position.stop_loss == 1.15000
    assert position.take_profit == 1.18000

    assert position.unrealized_pnl == 12.50

    assert (
        position.metadata["strategy_id"]
        == "EMA-TREND-001"
    )


def test_position_unrealized_pnl_defaults_to_zero():
    position = Position(
        position_id="POS-001",
        entry_fill_id="FILL-001",
        symbol="EURUSD",
        side=PositionSide.LONG,
        quantity=0.01,
        entry_time=datetime.now(timezone.utc),
        entry_price=1.16000,
    )

    assert position.unrealized_pnl == 0.0


def test_position_allows_negative_unrealized_pnl():
    position = Position(
        position_id="POS-001",
        entry_fill_id="FILL-001",
        symbol="EURUSD",
        side=PositionSide.LONG,
        quantity=0.01,
        entry_time=datetime.now(timezone.utc),
        entry_price=1.16000,
        unrealized_pnl=-25.75,
    )

    assert position.unrealized_pnl == -25.75


def test_position_requires_non_empty_position_id():
    with pytest.raises(
        ValueError,
        match="position_id",
    ):
        Position(
            position_id="",
            entry_fill_id="FILL-001",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=0.01,
            entry_time=datetime.now(timezone.utc),
            entry_price=1.16000,
        )


def test_position_requires_non_empty_entry_fill_id():
    with pytest.raises(
        ValueError,
        match="entry_fill_id",
    ):
        Position(
            position_id="POS-001",
            entry_fill_id="",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=0.01,
            entry_time=datetime.now(timezone.utc),
            entry_price=1.16000,
        )


def test_position_requires_non_empty_symbol():
    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        Position(
            position_id="POS-001",
            entry_fill_id="FILL-001",
            symbol="",
            side=PositionSide.LONG,
            quantity=0.01,
            entry_time=datetime.now(timezone.utc),
            entry_price=1.16000,
        )


def test_position_requires_position_side_enum():
    with pytest.raises(
        TypeError,
        match="PositionSide",
    ):
        Position(
            position_id="POS-001",
            entry_fill_id="FILL-001",
            symbol="EURUSD",
            side="LONG",  # type: ignore[arg-type]
            quantity=0.01,
            entry_time=datetime.now(timezone.utc),
            entry_price=1.16000,
        )


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        -0.01,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_position_requires_positive_finite_quantity(
    quantity,
):
    with pytest.raises(
        ValueError,
        match="quantity",
    ):
        Position(
            position_id="POS-001",
            entry_fill_id="FILL-001",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=quantity,
            entry_time=datetime.now(timezone.utc),
            entry_price=1.16000,
        )


@pytest.mark.parametrize(
    "entry_price",
    [
        0,
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_position_requires_positive_finite_entry_price(
    entry_price,
):
    with pytest.raises(
        ValueError,
        match="entry_price",
    ):
        Position(
            position_id="POS-001",
            entry_fill_id="FILL-001",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=0.01,
            entry_time=datetime.now(timezone.utc),
            entry_price=entry_price,
        )


def test_position_requires_timezone_aware_entry_time():
    naive_time = datetime(
        2026,
        8,
        8,
        12,
        15,
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        Position(
            position_id="POS-001",
            entry_fill_id="FILL-001",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=0.01,
            entry_time=naive_time,
            entry_price=1.16000,
        )


@pytest.mark.parametrize(
    "stop_loss",
    [
        0,
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_position_validates_stop_loss(
    stop_loss,
):
    with pytest.raises(
        ValueError,
        match="stop_loss",
    ):
        Position(
            position_id="POS-001",
            entry_fill_id="FILL-001",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=0.01,
            entry_time=datetime.now(timezone.utc),
            entry_price=1.16000,
            stop_loss=stop_loss,
        )


@pytest.mark.parametrize(
    "take_profit",
    [
        0,
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_position_validates_take_profit(
    take_profit,
):
    with pytest.raises(
        ValueError,
        match="take_profit",
    ):
        Position(
            position_id="POS-001",
            entry_fill_id="FILL-001",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=0.01,
            entry_time=datetime.now(timezone.utc),
            entry_price=1.16000,
            take_profit=take_profit,
        )


@pytest.mark.parametrize(
    "unrealized_pnl",
    [
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_position_requires_finite_unrealized_pnl(
    unrealized_pnl,
):
    with pytest.raises(
        ValueError,
        match="unrealized_pnl",
    ):
        Position(
            position_id="POS-001",
            entry_fill_id="FILL-001",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=0.01,
            entry_time=datetime.now(timezone.utc),
            entry_price=1.16000,
            unrealized_pnl=unrealized_pnl,
        )


def test_position_is_immutable():
    position = Position(
        position_id="POS-001",
        entry_fill_id="FILL-001",
        symbol="EURUSD",
        side=PositionSide.LONG,
        quantity=0.01,
        entry_time=datetime.now(timezone.utc),
        entry_price=1.16000,
    )

    with pytest.raises(AttributeError):
        position.quantity = 1.0  # type: ignore[misc]


def test_position_can_create_new_snapshot():
    position = Position(
        position_id="POS-001",
        entry_fill_id="FILL-001",
        symbol="EURUSD",
        side=PositionSide.LONG,
        quantity=0.01,
        entry_time=datetime.now(timezone.utc),
        entry_price=1.16000,
    )

    updated_position = replace(
        position,
        unrealized_pnl=-15.25,
    )

    assert position.unrealized_pnl == 0.0
    assert updated_position.unrealized_pnl == -15.25

    assert (
        updated_position.position_id
        == position.position_id
    )


def test_position_metadata_is_immutable_and_copied():
    metadata = {
        "strategy_id": "EMA-TREND-001",
    }

    position = Position(
        position_id="POS-001",
        entry_fill_id="FILL-001",
        symbol="EURUSD",
        side=PositionSide.LONG,
        quantity=0.01,
        entry_time=datetime.now(timezone.utc),
        entry_price=1.16000,
        metadata=metadata,
    )

    metadata["strategy_id"] = "CHANGED"

    assert (
        position.metadata["strategy_id"]
        == "EMA-TREND-001"
    )

    with pytest.raises(TypeError):
        position.metadata["strategy_id"] = "OTHER"  # type: ignore[index]
        
def test_trade_is_created_with_valid_data():
    entry_time = datetime(
        2026,
        8,
        8,
        12,
        15,
        tzinfo=timezone.utc,
    )

    exit_time = entry_time + timedelta(hours=2)

    trade = Trade(
        trade_id="TRD-001",
        position_id="POS-001",
        strategy_id="EMA-TREND-001",
        symbol="EURUSD",
        side=PositionSide.LONG,
        entry_fill_id="FILL-ENTRY-001",
        exit_fill_id="FILL-EXIT-001",
        entry_time=entry_time,
        exit_time=exit_time,
        entry_price=1.16000,
        exit_price=1.16500,
        quantity=0.01,
        gross_pnl=5.00,
        net_pnl=4.72,
        spread_cost=0.10,
        slippage_cost=0.03,
        commission=0.15,
        swap=0.0,
        bars_held=8,
        exit_reason=ExitReason.STRATEGY_EXIT,
        metadata={"experiment_id": "EXP-001"},
    )

    assert trade.trade_id == "TRD-001"
    assert trade.position_id == "POS-001"

    assert trade.strategy_id == "EMA-TREND-001"
    assert trade.symbol == "EURUSD"
    assert trade.side == PositionSide.LONG

    assert trade.entry_fill_id == "FILL-ENTRY-001"
    assert trade.exit_fill_id == "FILL-EXIT-001"

    assert trade.entry_time == entry_time
    assert trade.exit_time == exit_time

    assert trade.entry_price == 1.16000
    assert trade.exit_price == 1.16500
    assert trade.quantity == 0.01

    assert trade.gross_pnl == 5.00
    assert trade.net_pnl == 4.72

    assert trade.spread_cost == 0.10
    assert trade.slippage_cost == 0.03
    assert trade.commission == 0.15
    assert trade.swap == 0.0

    assert trade.bars_held == 8
    assert trade.exit_reason == ExitReason.STRATEGY_EXIT

    assert trade.metadata["experiment_id"] == "EXP-001"


def test_trade_costs_default_to_zero():
    timestamp = datetime.now(timezone.utc)

    trade = Trade(
        trade_id="TRD-001",
        position_id="POS-001",
        strategy_id="TEST",
        symbol="EURUSD",
        side=PositionSide.LONG,
        entry_fill_id="FILL-001",
        exit_fill_id="FILL-002",
        entry_time=timestamp,
        exit_time=timestamp,
        entry_price=1.16000,
        exit_price=1.16000,
        quantity=0.01,
        gross_pnl=0.0,
        net_pnl=0.0,
    )

    assert trade.spread_cost == 0.0
    assert trade.slippage_cost == 0.0
    assert trade.commission == 0.0
    assert trade.swap == 0.0


def test_trade_allows_negative_pnl():
    timestamp = datetime.now(timezone.utc)

    trade = Trade(
        trade_id="TRD-001",
        position_id="POS-001",
        strategy_id="TEST",
        symbol="EURUSD",
        side=PositionSide.LONG,
        entry_fill_id="FILL-001",
        exit_fill_id="FILL-002",
        entry_time=timestamp,
        exit_time=timestamp,
        entry_price=1.16000,
        exit_price=1.15500,
        quantity=0.01,
        gross_pnl=-5.00,
        net_pnl=-5.25,
    )

    assert trade.gross_pnl == -5.00
    assert trade.net_pnl == -5.25


def test_trade_allows_signed_swap():
    timestamp = datetime.now(timezone.utc)

    debit_trade = Trade(
        trade_id="TRD-001",
        position_id="POS-001",
        strategy_id="TEST",
        symbol="EURUSD",
        side=PositionSide.LONG,
        entry_fill_id="FILL-001",
        exit_fill_id="FILL-002",
        entry_time=timestamp,
        exit_time=timestamp,
        entry_price=1.16000,
        exit_price=1.16100,
        quantity=0.01,
        gross_pnl=1.00,
        net_pnl=0.50,
        swap=-0.50,
    )

    credit_trade = Trade(
        trade_id="TRD-002",
        position_id="POS-002",
        strategy_id="TEST",
        symbol="EURUSD",
        side=PositionSide.SHORT,
        entry_fill_id="FILL-003",
        exit_fill_id="FILL-004",
        entry_time=timestamp,
        exit_time=timestamp,
        entry_price=1.16000,
        exit_price=1.15900,
        quantity=0.01,
        gross_pnl=1.00,
        net_pnl=1.20,
        swap=0.20,
    )

    assert debit_trade.swap == -0.50
    assert credit_trade.swap == 0.20


def test_trade_allows_same_entry_and_exit_time():
    timestamp = datetime.now(timezone.utc)

    trade = Trade(
        trade_id="TRD-001",
        position_id="POS-001",
        strategy_id="TEST",
        symbol="EURUSD",
        side=PositionSide.LONG,
        entry_fill_id="FILL-001",
        exit_fill_id="FILL-002",
        entry_time=timestamp,
        exit_time=timestamp,
        entry_price=1.16000,
        exit_price=1.16050,
        quantity=0.01,
        gross_pnl=0.50,
        net_pnl=0.50,
        bars_held=0,
    )

    assert trade.exit_time == trade.entry_time
    assert trade.bars_held == 0


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("trade_id", ""),
        ("position_id", ""),
        ("strategy_id", ""),
        ("symbol", ""),
        ("entry_fill_id", ""),
        ("exit_fill_id", ""),
    ],
)
def test_trade_requires_non_empty_identifiers(
    field_name,
    field_value,
):
    timestamp = datetime.now(timezone.utc)

    kwargs = {
        "trade_id": "TRD-001",
        "position_id": "POS-001",
        "strategy_id": "TEST",
        "symbol": "EURUSD",
        "side": PositionSide.LONG,
        "entry_fill_id": "FILL-001",
        "exit_fill_id": "FILL-002",
        "entry_time": timestamp,
        "exit_time": timestamp,
        "entry_price": 1.16000,
        "exit_price": 1.16100,
        "quantity": 0.01,
        "gross_pnl": 1.00,
        "net_pnl": 1.00,
    }

    kwargs[field_name] = field_value

    with pytest.raises(ValueError, match=field_name):
        Trade(**kwargs)


def test_trade_requires_position_side_enum():
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(TypeError, match="PositionSide"):
        Trade(
            trade_id="TRD-001",
            position_id="POS-001",
            strategy_id="TEST",
            symbol="EURUSD",
            side="LONG",  # type: ignore[arg-type]
            entry_fill_id="FILL-001",
            exit_fill_id="FILL-002",
            entry_time=timestamp,
            exit_time=timestamp,
            entry_price=1.16000,
            exit_price=1.16100,
            quantity=0.01,
            gross_pnl=1.00,
            net_pnl=1.00,
        )


def test_trade_requires_exit_reason_enum():
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(TypeError, match="ExitReason"):
        Trade(
            trade_id="TRD-001",
            position_id="POS-001",
            strategy_id="TEST",
            symbol="EURUSD",
            side=PositionSide.LONG,
            entry_fill_id="FILL-001",
            exit_fill_id="FILL-002",
            entry_time=timestamp,
            exit_time=timestamp,
            entry_price=1.16000,
            exit_price=1.16100,
            quantity=0.01,
            gross_pnl=1.00,
            net_pnl=1.00,
            exit_reason="STOP_LOSS",  # type: ignore[arg-type]
        )


def test_trade_requires_timezone_aware_entry_time():
    naive_time = datetime(2026, 8, 8, 12, 0)

    with pytest.raises(
        ValueError,
        match="entry_time",
    ):
        Trade(
            trade_id="TRD-001",
            position_id="POS-001",
            strategy_id="TEST",
            symbol="EURUSD",
            side=PositionSide.LONG,
            entry_fill_id="FILL-001",
            exit_fill_id="FILL-002",
            entry_time=naive_time,
            exit_time=datetime.now(timezone.utc),
            entry_price=1.16000,
            exit_price=1.16100,
            quantity=0.01,
            gross_pnl=1.00,
            net_pnl=1.00,
        )


def test_trade_requires_timezone_aware_exit_time():
    entry_time = datetime(
        2026,
        8,
        8,
        12,
        0,
        tzinfo=timezone.utc,
    )

    naive_exit = datetime(
        2026,
        8,
        8,
        13,
        0,
    )

    with pytest.raises(
        ValueError,
        match="exit_time",
    ):
        Trade(
            trade_id="TRD-001",
            position_id="POS-001",
            strategy_id="TEST",
            symbol="EURUSD",
            side=PositionSide.LONG,
            entry_fill_id="FILL-001",
            exit_fill_id="FILL-002",
            entry_time=entry_time,
            exit_time=naive_exit,
            entry_price=1.16000,
            exit_price=1.16100,
            quantity=0.01,
            gross_pnl=1.00,
            net_pnl=1.00,
        )


def test_trade_exit_cannot_precede_entry():
    entry_time = datetime(
        2026,
        8,
        8,
        13,
        0,
        tzinfo=timezone.utc,
    )

    exit_time = entry_time - timedelta(minutes=15)

    with pytest.raises(
        ValueError,
        match="exit_time",
    ):
        Trade(
            trade_id="TRD-001",
            position_id="POS-001",
            strategy_id="TEST",
            symbol="EURUSD",
            side=PositionSide.LONG,
            entry_fill_id="FILL-001",
            exit_fill_id="FILL-002",
            entry_time=entry_time,
            exit_time=exit_time,
            entry_price=1.16000,
            exit_price=1.16100,
            quantity=0.01,
            gross_pnl=1.00,
            net_pnl=1.00,
        )


@pytest.mark.parametrize(
    "entry_price",
    [
        0,
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_trade_requires_positive_finite_entry_price(
    entry_price,
):
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="entry_price"):
        Trade(
            trade_id="TRD-001",
            position_id="POS-001",
            strategy_id="TEST",
            symbol="EURUSD",
            side=PositionSide.LONG,
            entry_fill_id="FILL-001",
            exit_fill_id="FILL-002",
            entry_time=timestamp,
            exit_time=timestamp,
            entry_price=entry_price,
            exit_price=1.16100,
            quantity=0.01,
            gross_pnl=1.00,
            net_pnl=1.00,
        )


@pytest.mark.parametrize(
    "exit_price",
    [
        0,
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_trade_requires_positive_finite_exit_price(
    exit_price,
):
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="exit_price"):
        Trade(
            trade_id="TRD-001",
            position_id="POS-001",
            strategy_id="TEST",
            symbol="EURUSD",
            side=PositionSide.LONG,
            entry_fill_id="FILL-001",
            exit_fill_id="FILL-002",
            entry_time=timestamp,
            exit_time=timestamp,
            entry_price=1.16000,
            exit_price=exit_price,
            quantity=0.01,
            gross_pnl=1.00,
            net_pnl=1.00,
        )


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        -0.01,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_trade_requires_positive_finite_quantity(
    quantity,
):
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="quantity"):
        Trade(
            trade_id="TRD-001",
            position_id="POS-001",
            strategy_id="TEST",
            symbol="EURUSD",
            side=PositionSide.LONG,
            entry_fill_id="FILL-001",
            exit_fill_id="FILL-002",
            entry_time=timestamp,
            exit_time=timestamp,
            entry_price=1.16000,
            exit_price=1.16100,
            quantity=quantity,
            gross_pnl=1.00,
            net_pnl=1.00,
        )


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("gross_pnl", float("inf")),
        ("gross_pnl", float("-inf")),
        ("gross_pnl", float("nan")),
        ("net_pnl", float("inf")),
        ("net_pnl", float("-inf")),
        ("net_pnl", float("nan")),
        ("swap", float("inf")),
        ("swap", float("-inf")),
        ("swap", float("nan")),
    ],
)
def test_trade_requires_finite_signed_values(
    field_name,
    field_value,
):
    timestamp = datetime.now(timezone.utc)

    kwargs = {
        "trade_id": "TRD-001",
        "position_id": "POS-001",
        "strategy_id": "TEST",
        "symbol": "EURUSD",
        "side": PositionSide.LONG,
        "entry_fill_id": "FILL-001",
        "exit_fill_id": "FILL-002",
        "entry_time": timestamp,
        "exit_time": timestamp,
        "entry_price": 1.16000,
        "exit_price": 1.16100,
        "quantity": 0.01,
        "gross_pnl": 1.00,
        "net_pnl": 1.00,
    }

    kwargs[field_name] = field_value

    with pytest.raises(ValueError, match=field_name):
        Trade(**kwargs)


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("spread_cost", -0.01),
        ("spread_cost", float("inf")),
        ("spread_cost", float("nan")),
        ("slippage_cost", -0.01),
        ("slippage_cost", float("inf")),
        ("slippage_cost", float("nan")),
        ("commission", -0.01),
        ("commission", float("inf")),
        ("commission", float("nan")),
    ],
)
def test_trade_requires_non_negative_costs(
    field_name,
    field_value,
):
    timestamp = datetime.now(timezone.utc)

    kwargs = {
        "trade_id": "TRD-001",
        "position_id": "POS-001",
        "strategy_id": "TEST",
        "symbol": "EURUSD",
        "side": PositionSide.LONG,
        "entry_fill_id": "FILL-001",
        "exit_fill_id": "FILL-002",
        "entry_time": timestamp,
        "exit_time": timestamp,
        "entry_price": 1.16000,
        "exit_price": 1.16100,
        "quantity": 0.01,
        "gross_pnl": 1.00,
        "net_pnl": 1.00,
    }

    kwargs[field_name] = field_value

    with pytest.raises(ValueError, match=field_name):
        Trade(**kwargs)


@pytest.mark.parametrize(
    "bars_held",
    [
        -1,
        1.5,
        True,
    ],
)
def test_trade_requires_non_negative_integer_bars_held(
    bars_held,
):
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="bars_held"):
        Trade(
            trade_id="TRD-001",
            position_id="POS-001",
            strategy_id="TEST",
            symbol="EURUSD",
            side=PositionSide.LONG,
            entry_fill_id="FILL-001",
            exit_fill_id="FILL-002",
            entry_time=timestamp,
            exit_time=timestamp,
            entry_price=1.16000,
            exit_price=1.16100,
            quantity=0.01,
            gross_pnl=1.00,
            net_pnl=1.00,
            bars_held=bars_held,
        )


def test_trade_is_immutable():
    timestamp = datetime.now(timezone.utc)

    trade = Trade(
        trade_id="TRD-001",
        position_id="POS-001",
        strategy_id="TEST",
        symbol="EURUSD",
        side=PositionSide.LONG,
        entry_fill_id="FILL-001",
        exit_fill_id="FILL-002",
        entry_time=timestamp,
        exit_time=timestamp,
        entry_price=1.16000,
        exit_price=1.16100,
        quantity=0.01,
        gross_pnl=1.00,
        net_pnl=1.00,
    )

    with pytest.raises(AttributeError):
        trade.net_pnl = 999.0  # type: ignore[misc]


def test_trade_metadata_is_immutable_and_copied():
    timestamp = datetime.now(timezone.utc)

    metadata = {
        "experiment_id": "EXP-001",
    }

    trade = Trade(
        trade_id="TRD-001",
        position_id="POS-001",
        strategy_id="TEST",
        symbol="EURUSD",
        side=PositionSide.LONG,
        entry_fill_id="FILL-001",
        exit_fill_id="FILL-002",
        entry_time=timestamp,
        exit_time=timestamp,
        entry_price=1.16000,
        exit_price=1.16100,
        quantity=0.01,
        gross_pnl=1.00,
        net_pnl=1.00,
        metadata=metadata,
    )

    metadata["experiment_id"] = "CHANGED"

    assert (
        trade.metadata["experiment_id"]
        == "EXP-001"
    )

    with pytest.raises(TypeError):
        trade.metadata["experiment_id"] = "OTHER"  # type: ignore[index]
        
def test_instrument_specification_is_created_with_valid_data():
    instrument = InstrumentSpecification(
        symbol="EURUSD",
        digits=5,
        point=0.00001,
        pip_size=0.00010,
        contract_size=100000,
        volume_min=0.01,
        volume_max=500.0,
        volume_step=0.01,
        tick_size=0.00001,
        tick_value=1.0,
    )

    assert instrument.symbol == "EURUSD"

    assert instrument.digits == 5

    assert instrument.point == 0.00001
    assert instrument.pip_size == 0.00010

    assert instrument.contract_size == 100000

    assert instrument.volume_min == 0.01
    assert instrument.volume_max == 500.0
    assert instrument.volume_step == 0.01

    assert instrument.tick_size == 0.00001
    assert instrument.tick_value == 1.0


def test_instrument_tick_value_is_optional():
    instrument = InstrumentSpecification(
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

    assert instrument.tick_value is None


def test_instrument_calculates_points_per_pip():
    instrument = InstrumentSpecification(
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

    assert instrument.points_per_pip == pytest.approx(10.0)


def test_instrument_requires_non_empty_symbol():
    with pytest.raises(ValueError, match="symbol"):
        InstrumentSpecification(
            symbol="",
            digits=5,
            point=0.00001,
            pip_size=0.00010,
            contract_size=100000,
            volume_min=0.01,
            volume_max=500.0,
            volume_step=0.01,
            tick_size=0.00001,
        )


@pytest.mark.parametrize(
    "digits",
    [
        -1,
        1.5,
        True,
    ],
)
def test_instrument_requires_non_negative_integer_digits(
    digits,
):
    with pytest.raises(ValueError, match="digits"):
        InstrumentSpecification(
            symbol="EURUSD",
            digits=digits,
            point=0.00001,
            pip_size=0.00010,
            contract_size=100000,
            volume_min=0.01,
            volume_max=500.0,
            volume_step=0.01,
            tick_size=0.00001,
        )


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("point", 0),
        ("point", -0.00001),
        ("point", float("inf")),
        ("point", float("nan")),

        ("pip_size", 0),
        ("pip_size", -0.0001),
        ("pip_size", float("inf")),
        ("pip_size", float("nan")),

        ("contract_size", 0),
        ("contract_size", -100000),
        ("contract_size", float("inf")),
        ("contract_size", float("nan")),

        ("volume_min", 0),
        ("volume_min", -0.01),
        ("volume_min", float("inf")),
        ("volume_min", float("nan")),

        ("volume_max", 0),
        ("volume_max", -1),
        ("volume_max", float("inf")),
        ("volume_max", float("nan")),

        ("volume_step", 0),
        ("volume_step", -0.01),
        ("volume_step", float("inf")),
        ("volume_step", float("nan")),

        ("tick_size", 0),
        ("tick_size", -0.00001),
        ("tick_size", float("inf")),
        ("tick_size", float("nan")),
    ],
)
def test_instrument_requires_positive_finite_numeric_fields(
    field_name,
    field_value,
):
    kwargs = {
        "symbol": "EURUSD",
        "digits": 5,
        "point": 0.00001,
        "pip_size": 0.00010,
        "contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 500.0,
        "volume_step": 0.01,
        "tick_size": 0.00001,
    }

    kwargs[field_name] = field_value

    with pytest.raises(ValueError, match=field_name):
        InstrumentSpecification(**kwargs)


@pytest.mark.parametrize(
    "tick_value",
    [
        0,
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_instrument_validates_tick_value_when_provided(
    tick_value,
):
    with pytest.raises(ValueError, match="tick_value"):
        InstrumentSpecification(
            symbol="EURUSD",
            digits=5,
            point=0.00001,
            pip_size=0.00010,
            contract_size=100000,
            volume_min=0.01,
            volume_max=500.0,
            volume_step=0.01,
            tick_size=0.00001,
            tick_value=tick_value,
        )


def test_instrument_volume_max_cannot_be_smaller_than_min():
    with pytest.raises(
        ValueError,
        match="volume_max",
    ):
        InstrumentSpecification(
            symbol="EURUSD",
            digits=5,
            point=0.00001,
            pip_size=0.00010,
            contract_size=100000,
            volume_min=1.0,
            volume_max=0.5,
            volume_step=0.01,
            tick_size=0.00001,
        )


def test_instrument_volume_step_cannot_exceed_volume_max():
    with pytest.raises(
        ValueError,
        match="volume_step",
    ):
        InstrumentSpecification(
            symbol="EURUSD",
            digits=5,
            point=0.00001,
            pip_size=0.00010,
            contract_size=100000,
            volume_min=0.01,
            volume_max=1.0,
            volume_step=2.0,
            tick_size=0.00001,
        )


def test_instrument_pip_size_cannot_be_smaller_than_point():
    with pytest.raises(
        ValueError,
        match="pip_size",
    ):
        InstrumentSpecification(
            symbol="TEST",
            digits=5,
            point=0.001,
            pip_size=0.0001,
            contract_size=1,
            volume_min=0.01,
            volume_max=1.0,
            volume_step=0.01,
            tick_size=0.001,
        )


def test_instrument_tick_size_cannot_be_smaller_than_point():
    with pytest.raises(
        ValueError,
        match="tick_size",
    ):
        InstrumentSpecification(
            symbol="TEST",
            digits=5,
            point=0.001,
            pip_size=0.01,
            contract_size=1,
            volume_min=0.01,
            volume_max=1.0,
            volume_step=0.01,
            tick_size=0.0001,
        )


def test_instrument_is_immutable():
    instrument = InstrumentSpecification(
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

    with pytest.raises(AttributeError):
        instrument.contract_size = 1  # type: ignore[misc]

def test_timeframe_baseline_values():
    assert list(Timeframe) == [
        Timeframe.M15,
        Timeframe.H1,
        Timeframe.H4,
    ]


def test_end_of_backtest_policy_values():
    assert list(EndOfBacktestPolicy) == [
        EndOfBacktestPolicy.FORCE_CLOSE_AT_FINAL_AVAILABLE_CLOSE,
        EndOfBacktestPolicy.LEAVE_OPEN,
    ]
    
def test_backtest_config_is_created_with_valid_data():
    date_from = datetime(
        2020,
        1,
        1,
        tzinfo=timezone.utc,
    )

    date_to = datetime(
        2021,
        1,
        1,
        tzinfo=timezone.utc,
    )

    config = BacktestConfig(
        symbol="EURUSD",
        timeframe=Timeframe.M15,
        date_from=date_from,
        date_to=date_to,
        initial_capital=10000.0,
        ambiguous_bar_policy=(
            AmbiguousBarPolicy.WORST_CASE
        ),
        end_of_backtest_policy=(
            EndOfBacktestPolicy
            .FORCE_CLOSE_AT_FINAL_AVAILABLE_CLOSE
        ),
        allow_incomplete_bars=False,
    )

    assert config.symbol == "EURUSD"
    assert config.timeframe == Timeframe.M15

    assert config.date_from == date_from
    assert config.date_to == date_to

    assert config.initial_capital == 10000.0

    assert (
        config.ambiguous_bar_policy
        == AmbiguousBarPolicy.WORST_CASE
    )

    assert (
        config.end_of_backtest_policy
        == EndOfBacktestPolicy
        .FORCE_CLOSE_AT_FINAL_AVAILABLE_CLOSE
    )

    assert config.allow_incomplete_bars is False


def test_backtest_config_baseline_defaults():
    config = BacktestConfig(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        date_from=datetime(
            2020,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        date_to=datetime(
            2021,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        initial_capital=10000.0,
    )

    assert (
        config.ambiguous_bar_policy
        == AmbiguousBarPolicy.WORST_CASE
    )

    assert (
        config.end_of_backtest_policy
        == EndOfBacktestPolicy
        .FORCE_CLOSE_AT_FINAL_AVAILABLE_CLOSE
    )

    assert config.allow_incomplete_bars is False


def test_backtest_config_requires_non_empty_symbol():
    with pytest.raises(ValueError, match="symbol"):
        BacktestConfig(
            symbol="",
            timeframe=Timeframe.M15,
            date_from=datetime(
                2020,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            date_to=datetime(
                2021,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            initial_capital=10000.0,
        )


def test_backtest_config_requires_timeframe_enum():
    with pytest.raises(TypeError, match="Timeframe"):
        BacktestConfig(
            symbol="EURUSD",
            timeframe="M15",  # type: ignore[arg-type]
            date_from=datetime(
                2020,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            date_to=datetime(
                2021,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            initial_capital=10000.0,
        )


def test_backtest_config_requires_timezone_aware_date_from():
    with pytest.raises(
        ValueError,
        match="date_from",
    ):
        BacktestConfig(
            symbol="EURUSD",
            timeframe=Timeframe.M15,
            date_from=datetime(
                2020,
                1,
                1,
            ),
            date_to=datetime(
                2021,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            initial_capital=10000.0,
        )


def test_backtest_config_requires_timezone_aware_date_to():
    with pytest.raises(
        ValueError,
        match="date_to",
    ):
        BacktestConfig(
            symbol="EURUSD",
            timeframe=Timeframe.M15,
            date_from=datetime(
                2020,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            date_to=datetime(
                2021,
                1,
                1,
            ),
            initial_capital=10000.0,
        )


def test_backtest_config_requires_utc_date_from():
    non_utc = timezone(
        timedelta(hours=-3)
    )

    with pytest.raises(
        ValueError,
        match="UTC",
    ):
        BacktestConfig(
            symbol="EURUSD",
            timeframe=Timeframe.M15,
            date_from=datetime(
                2020,
                1,
                1,
                tzinfo=non_utc,
            ),
            date_to=datetime(
                2021,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            initial_capital=10000.0,
        )


def test_backtest_config_requires_utc_date_to():
    non_utc = timezone(
        timedelta(hours=-3)
    )

    with pytest.raises(
        ValueError,
        match="UTC",
    ):
        BacktestConfig(
            symbol="EURUSD",
            timeframe=Timeframe.M15,
            date_from=datetime(
                2020,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            date_to=datetime(
                2021,
                1,
                1,
                tzinfo=non_utc,
            ),
            initial_capital=10000.0,
        )


def test_backtest_config_date_to_must_be_after_date_from():
    timestamp = datetime(
        2020,
        1,
        1,
        tzinfo=timezone.utc,
    )

    with pytest.raises(
        ValueError,
        match="date_to",
    ):
        BacktestConfig(
            symbol="EURUSD",
            timeframe=Timeframe.M15,
            date_from=timestamp,
            date_to=timestamp,
            initial_capital=10000.0,
        )


@pytest.mark.parametrize(
    "initial_capital",
    [
        0,
        -1000,
        float("inf"),
        float("-inf"),
        float("nan"),
        True,
    ],
)
def test_backtest_config_requires_positive_initial_capital(
    initial_capital,
):
    with pytest.raises(
        ValueError,
        match="initial_capital",
    ):
        BacktestConfig(
            symbol="EURUSD",
            timeframe=Timeframe.M15,
            date_from=datetime(
                2020,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            date_to=datetime(
                2021,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            initial_capital=initial_capital,
        )


def test_backtest_config_requires_ambiguous_bar_policy_enum():
    with pytest.raises(
        TypeError,
        match="AmbiguousBarPolicy",
    ):
        BacktestConfig(
            symbol="EURUSD",
            timeframe=Timeframe.M15,
            date_from=datetime(
                2020,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            date_to=datetime(
                2021,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            initial_capital=10000.0,
            ambiguous_bar_policy="WORST_CASE",  # type: ignore[arg-type]
        )


def test_backtest_config_requires_end_policy_enum():
    with pytest.raises(
        TypeError,
        match="EndOfBacktestPolicy",
    ):
        BacktestConfig(
            symbol="EURUSD",
            timeframe=Timeframe.M15,
            date_from=datetime(
                2020,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            date_to=datetime(
                2021,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            initial_capital=10000.0,
            end_of_backtest_policy="LEAVE_OPEN",  # type: ignore[arg-type]
        )


def test_backtest_config_requires_boolean_incomplete_policy():
    with pytest.raises(
        TypeError,
        match="allow_incomplete_bars",
    ):
        BacktestConfig(
            symbol="EURUSD",
            timeframe=Timeframe.M15,
            date_from=datetime(
                2020,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            date_to=datetime(
                2021,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            initial_capital=10000.0,
            allow_incomplete_bars=1,  # type: ignore[arg-type]
        )


def test_backtest_config_is_immutable():
    config = BacktestConfig(
        symbol="EURUSD",
        timeframe=Timeframe.M15,
        date_from=datetime(
            2020,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        date_to=datetime(
            2021,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        initial_capital=10000.0,
    )

    with pytest.raises(AttributeError):
        config.initial_capital = 50000.0  # type: ignore[misc]