from datetime import datetime, timedelta, timezone

import pytest

from backtest.portfolio import Portfolio, PortfolioSnapshot
from backtest.position import Position, PositionSide
from domain.fill import Fill


def at(minute: int) -> datetime:
    return datetime(2026, 8, 24, 10, minute, tzinfo=timezone.utc)


def fill(identifier: str, minute: int, price: float, quantity: float = 2.0, commission: float = 0.0) -> Fill:
    return Fill(identifier, f"order-{identifier}", at(minute), price, price, quantity, commission=commission)


def test_open_long_debits_commission_and_creates_position():
    portfolio = Portfolio(symbol="EURUSD", initial_cash=1_000)
    snapshot = portfolio.open_position(fill("entry", 0, 10, commission=2), side=PositionSide.LONG)

    assert snapshot.cash == 998
    assert snapshot.equity == 998
    assert snapshot.realized_pnl == 0
    assert snapshot.unrealized_pnl == 0
    assert snapshot.position is not None
    assert snapshot.position.side is PositionSide.LONG


def test_long_mark_and_close_realize_net_pnl():
    portfolio = Portfolio(symbol="EURUSD", initial_cash=1_000)
    portfolio.open_position(fill("entry", 0, 10, commission=2), side=PositionSide.LONG)
    marked = portfolio.mark_to_market(timestamp=at(1), price=13)
    closed = portfolio.close_position(fill("exit", 2, 14, commission=3))

    assert marked.unrealized_pnl == 6
    assert marked.equity == 1_004
    assert closed.position is None
    assert closed.unrealized_pnl == 0
    assert closed.realized_pnl == 3
    assert closed.cash == closed.equity == 1_003
    assert closed.total_commission == 5


def test_short_mark_and_close_realize_net_pnl():
    portfolio = Portfolio(symbol="EURUSD", initial_cash=1_000)
    portfolio.open_position(fill("entry", 0, 10), side=PositionSide.SHORT)
    marked = portfolio.mark_to_market(timestamp=at(1), price=7)
    closed = portfolio.close_position(fill("exit", 2, 6))

    assert marked.unrealized_pnl == 6
    assert closed.realized_pnl == 8
    assert closed.cash == closed.equity == 1_008


def test_short_loss_is_negative():
    portfolio = Portfolio(symbol="EURUSD", initial_cash=1_000)
    portfolio.open_position(fill("entry", 0, 10), side=PositionSide.SHORT)
    assert portfolio.mark_to_market(timestamp=at(1), price=12).unrealized_pnl == -4


def test_baseline_rejects_second_open_partial_close_and_flat_close():
    portfolio = Portfolio(symbol="EURUSD", initial_cash=1_000)
    with pytest.raises(ValueError, match="flat"):
        portfolio.close_position(fill("exit", 0, 10))
    portfolio.open_position(fill("entry", 0, 10), side=PositionSide.LONG)
    with pytest.raises(ValueError, match="one open"):
        portfolio.open_position(fill("other", 1, 11), side=PositionSide.LONG)
    with pytest.raises(ValueError, match="partial"):
        portfolio.close_position(fill("partial", 1, 11, quantity=1))


def test_rejects_duplicate_out_of_order_and_invalid_marks():
    portfolio = Portfolio(symbol="EURUSD", initial_cash=1_000)
    entry = fill("entry", 1, 10)
    portfolio.open_position(entry, side=PositionSide.LONG)
    with pytest.raises(ValueError, match="already"):
        portfolio.close_position(entry)
    with pytest.raises(ValueError, match="non-decreasing"):
        portfolio.close_position(fill("old", 0, 11))
    with pytest.raises(ValueError, match="non-decreasing"):
        portfolio.mark_to_market(timestamp=at(0), price=10)
    with pytest.raises(ValueError, match="positive"):
        portfolio.mark_to_market(timestamp=at(2), price=0)


def test_snapshot_identity_history_and_immutability():
    portfolio = Portfolio(symbol="EURUSD", initial_cash=1_000)
    first = portfolio.open_position(fill("entry", 0, 10), side=PositionSide.LONG)
    second = portfolio.mark_to_market(timestamp=at(1), price=11)

    assert portfolio.snapshots == (first, second)
    assert second.equity == second.cash + second.unrealized_pnl
    with pytest.raises(AttributeError):
        second.cash = 0  # type: ignore[misc]


@pytest.mark.parametrize("side", ["LONG", None, True])
def test_open_rejects_invalid_side(side):
    with pytest.raises(TypeError, match="PositionSide"):
        Portfolio(symbol="EURUSD", initial_cash=1_000).open_position(fill("entry", 0, 10), side=side)


def test_position_and_snapshot_validate_core_invariants():
    with pytest.raises(ValueError, match="positive"):
        Position("EURUSD", PositionSide.LONG, 0, 1, at(0), "entry")
    with pytest.raises(ValueError, match="equity"):
        PortfolioSnapshot(at(0), 1, 2, 0, 0, 0, None)
    with pytest.raises(ValueError, match="positive"):
        Portfolio(symbol="EURUSD", initial_cash=0)
