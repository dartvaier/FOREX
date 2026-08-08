from datetime import datetime, timezone

import pytest

from backtest.models import (
    BacktestConfig,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionSide,
    Signal,
    SignalAction,
    Timeframe,
)
from backtest.order_factory import OrderFactory
from backtest.risk import RiskDecision


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


def make_signal(
    action: SignalAction,
    *,
    signal_id: str = "SIG-001",
    symbol: str = "EURUSD",
) -> Signal:
    return Signal(
        signal_id=signal_id,
        strategy_id="TEST",
        symbol=symbol,
        timestamp=utc_time(10, 15),
        action=action,
        reason="Synthetic test",
    )


def make_decision(
    signal: Signal,
    *,
    approved: bool = True,
    quantity: float | None = 0.05,
) -> RiskDecision:
    return RiskDecision(
        signal_id=signal.signal_id,
        approved=approved,
        quantity=quantity,
        reason="Synthetic risk decision",
    )


def make_position(
    side: PositionSide,
    *,
    quantity: float = 0.37,
    symbol: str = "EURUSD",
) -> Position:
    return Position(
        position_id="POS-001",
        entry_fill_id="FILL-001",
        symbol=symbol,
        side=side,
        quantity=quantity,
        entry_time=utc_time(10, 0),
        entry_price=1.1600,
    )


def test_order_factory_is_created_with_config():
    config = make_config()

    factory = OrderFactory(
        config=config,
    )

    assert factory.config is config


def test_order_factory_requires_config():
    with pytest.raises(
        TypeError,
        match="BacktestConfig",
    ):
        OrderFactory(
            config=None,  # type: ignore[arg-type]
        )


def test_enter_long_creates_pending_buy_order():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_LONG
    )

    order = factory.create(
        signal=signal,
        risk_decision=make_decision(
            signal,
            quantity=0.05,
        ),
    )

    assert isinstance(order, Order)

    assert order.side == OrderSide.BUY
    assert order.quantity == 0.05
    assert order.order_type == OrderType.MARKET
    assert order.status == OrderStatus.PENDING


def test_enter_short_creates_pending_sell_order():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_SHORT
    )

    order = factory.create(
        signal=signal,
        risk_decision=make_decision(
            signal,
            quantity=0.07,
        ),
    )

    assert isinstance(order, Order)

    assert order.side == OrderSide.SELL
    assert order.quantity == 0.07


def test_order_preserves_signal_identity():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_LONG,
        signal_id="SIG-ABC",
    )

    order = factory.create(
        signal=signal,
        risk_decision=make_decision(signal),
    )

    assert order is not None

    assert order.signal_id == "SIG-ABC"
    assert order.order_id == "ORD-SIG-ABC"


def test_order_is_created_at_signal_time():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_LONG
    )

    order = factory.create(
        signal=signal,
        risk_decision=make_decision(signal),
    )

    assert order is not None

    assert order.created_at == signal.timestamp
    assert order.scheduled_for == signal.timestamp


def test_order_metadata_preserves_audit_information():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_LONG
    )

    decision = make_decision(signal)

    order = factory.create(
        signal=signal,
        risk_decision=decision,
    )

    assert order is not None

    assert (
        order.metadata["strategy_id"]
        == signal.strategy_id
    )

    assert (
        order.metadata["signal_action"]
        == SignalAction.ENTER_LONG.value
    )

    assert (
        order.metadata["risk_reason"]
        == decision.reason
    )


def test_hold_creates_no_order():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.HOLD
    )

    order = factory.create(
        signal=signal,
        risk_decision=make_decision(
            signal,
            quantity=None,
        ),
    )

    assert order is None


def test_rejected_risk_decision_creates_no_order():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_LONG
    )

    order = factory.create(
        signal=signal,
        risk_decision=make_decision(
            signal,
            approved=False,
            quantity=None,
        ),
    )

    assert order is None


def test_entry_requires_risk_quantity():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_LONG
    )

    with pytest.raises(
        ValueError,
        match="requires quantity",
    ):
        factory.create(
            signal=signal,
            risk_decision=make_decision(
                signal,
                quantity=None,
            ),
        )


def test_existing_long_blocks_additional_long_entry():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_LONG
    )

    order = factory.create(
        signal=signal,
        risk_decision=make_decision(signal),
        current_position=make_position(
            PositionSide.LONG
        ),
    )

    assert order is None


def test_existing_short_blocks_additional_short_entry():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_SHORT
    )

    order = factory.create(
        signal=signal,
        risk_decision=make_decision(signal),
        current_position=make_position(
            PositionSide.SHORT
        ),
    )

    assert order is None


def test_long_position_blocks_automatic_short_reversal():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_SHORT
    )

    order = factory.create(
        signal=signal,
        risk_decision=make_decision(signal),
        current_position=make_position(
            PositionSide.LONG
        ),
    )

    assert order is None


def test_short_position_blocks_automatic_long_reversal():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_LONG
    )

    order = factory.create(
        signal=signal,
        risk_decision=make_decision(signal),
        current_position=make_position(
            PositionSide.SHORT
        ),
    )

    assert order is None


def test_exit_long_creates_sell_for_full_position():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.EXIT
    )

    position = make_position(
        PositionSide.LONG,
        quantity=0.37,
    )

    order = factory.create(
        signal=signal,
        risk_decision=make_decision(
            signal,
            quantity=None,
        ),
        current_position=position,
    )

    assert isinstance(order, Order)

    assert order.side == OrderSide.SELL
    assert order.quantity == 0.37

    assert (
        order.metadata["position_id"]
        == position.position_id
    )


def test_exit_short_creates_buy_for_full_position():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.EXIT
    )

    position = make_position(
        PositionSide.SHORT,
        quantity=0.23,
    )

    order = factory.create(
        signal=signal,
        risk_decision=make_decision(
            signal,
            quantity=None,
        ),
        current_position=position,
    )

    assert isinstance(order, Order)

    assert order.side == OrderSide.BUY
    assert order.quantity == 0.23


def test_exit_without_position_creates_no_order():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.EXIT
    )

    order = factory.create(
        signal=signal,
        risk_decision=make_decision(
            signal,
            quantity=None,
        ),
        current_position=None,
    )

    assert order is None


def test_factory_requires_signal():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.HOLD
    )

    with pytest.raises(
        TypeError,
        match="Signal",
    ):
        factory.create(
            signal=object(),  # type: ignore[arg-type]
            risk_decision=make_decision(signal),
        )


def test_factory_requires_risk_decision():
    factory = OrderFactory(
        config=make_config(),
    )

    with pytest.raises(
        TypeError,
        match="RiskDecision",
    ):
        factory.create(
            signal=make_signal(
                SignalAction.HOLD
            ),
            risk_decision=None,  # type: ignore[arg-type]
        )


def test_factory_requires_position_or_none():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_LONG
    )

    with pytest.raises(
        TypeError,
        match="Position or None",
    ):
        factory.create(
            signal=signal,
            risk_decision=make_decision(signal),
            current_position=object(),  # type: ignore[arg-type]
        )


def test_factory_rejects_signal_symbol_mismatch():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_LONG,
        symbol="GBPUSD",
    )

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        factory.create(
            signal=signal,
            risk_decision=make_decision(signal),
        )


def test_factory_rejects_risk_decision_for_another_signal():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.ENTER_LONG
    )

    decision = RiskDecision(
        signal_id="SIG-OTHER",
        approved=True,
        quantity=0.05,
        reason="Wrong signal",
    )

    with pytest.raises(
        ValueError,
        match="signal_id",
    ):
        factory.create(
            signal=signal,
            risk_decision=decision,
        )


def test_factory_rejects_position_symbol_mismatch():
    factory = OrderFactory(
        config=make_config(),
    )

    signal = make_signal(
        SignalAction.EXIT
    )

    position = make_position(
        PositionSide.LONG,
        symbol="GBPUSD",
    )

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        factory.create(
            signal=signal,
            risk_decision=make_decision(
                signal,
                quantity=None,
            ),
            current_position=position,
        )