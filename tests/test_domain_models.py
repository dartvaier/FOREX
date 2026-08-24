from datetime import datetime, timedelta, timezone

import pytest

from domain import Fill, OrderIntent, OrderSide, OrderType, Signal, SignalAction


UTC_TIME = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def test_signal_accepts_baseline_action_and_utc_timestamp():
    signal = Signal(
        signal_id="sig-1",
        strategy_id="strategy-1",
        symbol="EURUSD",
        timestamp=UTC_TIME,
        action=SignalAction.ENTER_LONG,
        reason="trend confirmed",
    )

    assert signal.action is SignalAction.ENTER_LONG
    assert signal.timestamp.tzinfo is timezone.utc


def test_signal_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        Signal(
            signal_id="sig-1",
            strategy_id="strategy-1",
            symbol="EURUSD",
            timestamp=datetime(2026, 8, 23, 12, 0),
            action=SignalAction.HOLD,
        )


def test_signal_rejects_non_utc_timestamp():
    non_utc = timezone(timedelta(hours=-3))

    with pytest.raises(ValueError, match="must be in UTC"):
        Signal(
            signal_id="sig-1",
            strategy_id="strategy-1",
            symbol="EURUSD",
            timestamp=datetime(2026, 8, 23, 12, 0, tzinfo=non_utc),
            action=SignalAction.HOLD,
        )


def test_order_intent_requires_positive_quantity():
    with pytest.raises(ValueError, match="quantity"):
        OrderIntent(
            order_id="ord-1",
            signal_id="sig-1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=0,
            order_type=OrderType.MARKET,
            created_at=UTC_TIME,
        )


def test_order_intent_keeps_signal_link_and_risk_sized_quantity():
    order = OrderIntent(
        order_id="ord-1",
        signal_id="sig-1",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.10,
        order_type=OrderType.MARKET,
        created_at=UTC_TIME,
        stop_loss=1.1600,
        take_profit=1.1800,
    )

    assert order.signal_id == "sig-1"
    assert order.quantity == 0.10
    assert order.order_type is OrderType.MARKET


def test_fill_tracks_reference_and_execution_prices():
    fill = Fill(
        fill_id="fill-1",
        order_id="ord-1",
        fill_time=UTC_TIME,
        reference_price=1.1700,
        execution_price=1.1702,
        quantity=0.10,
        spread_impact=0.0001,
        slippage=0.0001,
        commission=0.50,
    )

    assert fill.order_id == "ord-1"
    assert fill.execution_price > fill.reference_price
    assert fill.commission == 0.50


def test_fill_rejects_non_positive_prices_and_quantity():
    with pytest.raises(ValueError, match="reference_price"):
        Fill(
            fill_id="fill-1",
            order_id="ord-1",
            fill_time=UTC_TIME,
            reference_price=0,
            execution_price=1.1700,
            quantity=0.10,
        )

    with pytest.raises(ValueError, match="execution_price"):
        Fill(
            fill_id="fill-1",
            order_id="ord-1",
            fill_time=UTC_TIME,
            reference_price=1.1700,
            execution_price=0,
            quantity=0.10,
        )

    with pytest.raises(ValueError, match="quantity"):
        Fill(
            fill_id="fill-1",
            order_id="ord-1",
            fill_time=UTC_TIME,
            reference_price=1.1700,
            execution_price=1.1700,
            quantity=0,
        )
