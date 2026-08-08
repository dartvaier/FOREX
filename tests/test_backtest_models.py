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