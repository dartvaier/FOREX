from datetime import datetime, timezone

import pytest

from backtest.models import (
    PositionSide,
    Trade,
)
from backtest.models.enums import ExitReason
from backtest.trade_ledger import TradeLedger


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


def make_trade(
    *,
    trade_id: str = "TRADE-001",
    position_id: str = "POS-001",
    exit_time: datetime | None = None,
) -> Trade:
    return Trade(
        trade_id=trade_id,
        position_id=position_id,
        strategy_id="TEST-STRATEGY",
        symbol="EURUSD",
        side=PositionSide.LONG,
        entry_fill_id=f"FILL-ENTRY-{position_id}",
        exit_fill_id=f"FILL-EXIT-{position_id}",
        entry_time=utc_time(10, 15),
        exit_time=(
            exit_time
            if exit_time is not None
            else utc_time(10, 45)
        ),
        entry_price=1.1600,
        exit_price=1.1700,
        quantity=0.01,
        gross_pnl=10.0,
        net_pnl=9.0,
        spread_cost=0.20,
        slippage_cost=0.10,
        commission=0.70,
        bars_held=2,
        exit_reason=ExitReason.TAKE_PROFIT,
    )


def test_ledger_starts_empty():
    ledger = TradeLedger()

    assert ledger.is_empty is True
    assert ledger.count == 0
    assert len(ledger) == 0
    assert ledger.trades == ()
    assert ledger.last_trade is None


def test_append_trade():
    ledger = TradeLedger()
    trade = make_trade()

    ledger.append(trade)

    assert ledger.is_empty is False
    assert ledger.count == 1
    assert ledger.trades == (trade,)
    assert ledger.last_trade is trade


def test_ledger_preserves_insertion_order():
    ledger = TradeLedger()

    first = make_trade(
        trade_id="TRADE-001",
        position_id="POS-001",
        exit_time=utc_time(10, 45),
    )

    second = make_trade(
        trade_id="TRADE-002",
        position_id="POS-002",
        exit_time=utc_time(11, 15),
    )

    ledger.append(first)
    ledger.append(second)

    assert ledger.trades == (
        first,
        second,
    )


def test_trades_are_exposed_as_tuple():
    ledger = TradeLedger()
    ledger.append(make_trade())

    assert isinstance(
        ledger.trades,
        tuple,
    )


def test_duplicate_trade_id_is_rejected():
    ledger = TradeLedger()

    ledger.append(
        make_trade(
            trade_id="TRADE-001",
            position_id="POS-001",
        )
    )

    with pytest.raises(
        ValueError,
        match="trade_id",
    ):
        ledger.append(
            make_trade(
                trade_id="TRADE-001",
                position_id="POS-002",
            )
        )


def test_same_position_cannot_create_two_trades():
    ledger = TradeLedger()

    ledger.append(
        make_trade(
            trade_id="TRADE-001",
            position_id="POS-001",
        )
    )

    with pytest.raises(
        ValueError,
        match="Position",
    ):
        ledger.append(
            make_trade(
                trade_id="TRADE-002",
                position_id="POS-001",
            )
        )


def test_exit_time_cannot_move_backward():
    ledger = TradeLedger()

    ledger.append(
        make_trade(
            trade_id="TRADE-001",
            position_id="POS-001",
            exit_time=utc_time(11, 0),
        )
    )

    with pytest.raises(
        ValueError,
        match="backward",
    ):
        ledger.append(
            make_trade(
                trade_id="TRADE-002",
                position_id="POS-002",
                exit_time=utc_time(10, 45),
            )
        )


def test_equal_exit_times_are_allowed():
    ledger = TradeLedger()

    first = make_trade(
        trade_id="TRADE-001",
        position_id="POS-001",
        exit_time=utc_time(11, 0),
    )

    second = make_trade(
        trade_id="TRADE-002",
        position_id="POS-002",
        exit_time=utc_time(11, 0),
    )

    ledger.append(first)
    ledger.append(second)

    assert ledger.count == 2


def test_get_returns_trade_by_id():
    ledger = TradeLedger()
    trade = make_trade()

    ledger.append(trade)

    assert ledger.get(
        "TRADE-001"
    ) is trade


def test_get_unknown_trade_returns_none():
    ledger = TradeLedger()

    assert ledger.get(
        "TRADE-UNKNOWN"
    ) is None


def test_iteration_preserves_order():
    ledger = TradeLedger()

    first = make_trade(
        trade_id="TRADE-001",
        position_id="POS-001",
        exit_time=utc_time(10, 45),
    )

    second = make_trade(
        trade_id="TRADE-002",
        position_id="POS-002",
        exit_time=utc_time(11, 0),
    )

    ledger.append(first)
    ledger.append(second)

    assert list(ledger) == [
        first,
        second,
    ]


def test_append_requires_trade():
    ledger = TradeLedger()

    with pytest.raises(
        TypeError,
        match="Trade",
    ):
        ledger.append(
            object()  # type: ignore[arg-type]
        )