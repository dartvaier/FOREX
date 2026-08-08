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