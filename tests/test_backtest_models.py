from datetime import datetime, timezone

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