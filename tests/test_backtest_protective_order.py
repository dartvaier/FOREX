from datetime import datetime, timezone

import pytest

from backtest.models import (
    BacktestConfig,
    OrderSide,
    Position,
    PositionSide,
    Timeframe,
)
from backtest.models.enums import ExitReason
from backtest.protective_exit import ProtectiveExitDecision
from backtest.protective_order import ProtectiveExitOrderFactory


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


def make_position(
    side: PositionSide,
) -> Position:
    return Position(
        position_id="POS-001",
        entry_fill_id="FILL-001",
        symbol="EURUSD",
        side=side,
        quantity=0.05,
        entry_time=utc_time(10),
        entry_price=1.1600,
        unrealized_pnl=0.0,
    )


def make_decision() -> ProtectiveExitDecision:
    return ProtectiveExitDecision(
        position_id="POS-001",
        bar_time=utc_time(10, 15),
        exit_reason=ExitReason.STOP_LOSS,
        reference_price=1.1500,
        triggered_at_open=False,
        ambiguous=False,
    )


def test_long_creates_sell_order():
    order = ProtectiveExitOrderFactory(
        make_config()
    ).create(
        make_position(PositionSide.LONG),
        make_decision(),
        execution_time=utc_time(10, 30),
    )

    assert order.side == OrderSide.SELL
    assert order.quantity == pytest.approx(0.05)


def test_short_creates_buy_order():
    order = ProtectiveExitOrderFactory(
        make_config()
    ).create(
        make_position(PositionSide.SHORT),
        make_decision(),
        execution_time=utc_time(10, 30),
    )

    assert order.side == OrderSide.BUY
    assert order.quantity == pytest.approx(0.05)


def test_protective_order_is_deterministic():
    order = ProtectiveExitOrderFactory(
        make_config()
    ).create(
        make_position(PositionSide.LONG),
        make_decision(),
        execution_time=utc_time(10, 30),
    )

    assert order.order_id == "ORD-PROTECTIVE-POS-001"
    assert order.signal_id == "SYS-PROTECTIVE-POS-001"


def test_order_preserves_protective_metadata():
    order = ProtectiveExitOrderFactory(
        make_config()
    ).create(
        make_position(PositionSide.LONG),
        make_decision(),
        execution_time=utc_time(10, 30),
    )

    assert order.metadata["protective_exit"] is True
    assert order.metadata["exit_reason"] == ExitReason.STOP_LOSS.value
    assert order.metadata["reference_price"] == pytest.approx(1.1500)


def test_decision_must_match_position():
    decision = ProtectiveExitDecision(
        position_id="POS-OTHER",
        bar_time=utc_time(10, 15),
        exit_reason=ExitReason.STOP_LOSS,
        reference_price=1.1500,
        triggered_at_open=False,
        ambiguous=False,
    )

    with pytest.raises(
        ValueError,
        match="position_id",
    ):
        ProtectiveExitOrderFactory(
            make_config()
        ).create(
            make_position(PositionSide.LONG),
            decision,
            execution_time=utc_time(10, 30),
        )