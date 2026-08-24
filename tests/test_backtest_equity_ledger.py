from datetime import datetime, timezone

import pytest

from backtest.equity_ledger import (
    EquityLedger,
    EquityPoint,
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


def make_point(
    *,
    timestamp: datetime | None = None,
    bar_index: int = 0,
    phase: SimulationPhase = SimulationPhase.BAR_CLOSE,
    cash: float = 10000.0,
    unrealized_pnl: float = 0.0,
    realized_pnl: float = 0.0,
) -> EquityPoint:
    return EquityPoint(
        timestamp=(
            timestamp
            if timestamp is not None
            else utc_time(10, 15)
        ),
        bar_index=bar_index,
        phase=phase,
        cash=cash,
        equity=(
            cash
            + unrealized_pnl
        ),
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
    )


def test_ledger_starts_empty():
    ledger = EquityLedger()

    assert ledger.is_empty is True
    assert ledger.count == 0
    assert ledger.points == ()
    assert ledger.last_point is None


def test_append_equity_point():
    ledger = EquityLedger()
    point = make_point()

    ledger.append(point)

    assert ledger.count == 1
    assert ledger.last_point is point
    assert ledger.points == (point,)


def test_ledger_preserves_order():
    ledger = EquityLedger()

    first = make_point(
        timestamp=utc_time(10, 15),
        bar_index=0,
    )

    second = make_point(
        timestamp=utc_time(10, 30),
        bar_index=1,
    )

    ledger.append(first)
    ledger.append(second)

    assert ledger.points == (
        first,
        second,
    )


def test_equal_timestamps_are_allowed():
    ledger = EquityLedger()

    close_point = make_point(
        timestamp=utc_time(10, 15),
        bar_index=0,
        phase=SimulationPhase.BAR_CLOSE,
    )

    open_point = make_point(
        timestamp=utc_time(10, 15),
        bar_index=1,
        phase=SimulationPhase.BAR_OPEN,
    )

    ledger.append(close_point)
    ledger.append(open_point)

    assert ledger.count == 2


def test_timestamp_cannot_move_backward():
    ledger = EquityLedger()

    ledger.append(
        make_point(
            timestamp=utc_time(10, 30),
        )
    )

    with pytest.raises(
        ValueError,
        match="backward",
    ):
        ledger.append(
            make_point(
                timestamp=utc_time(10, 15),
            )
        )


def test_equity_must_equal_cash_plus_unrealized():
    with pytest.raises(
        ValueError,
        match="cash",
    ):
        EquityPoint(
            timestamp=utc_time(10, 15),
            bar_index=0,
            phase=SimulationPhase.BAR_CLOSE,
            cash=10000.0,
            equity=10005.0,
            realized_pnl=0.0,
            unrealized_pnl=3.0,
        )


def test_point_can_record_open_position_profit():
    point = make_point(
        cash=9999.50,
        realized_pnl=-0.50,
        unrealized_pnl=4.00,
    )

    assert point.cash == pytest.approx(
        9999.50
    )

    assert point.unrealized_pnl == pytest.approx(
        4.00
    )

    assert point.equity == pytest.approx(
        10003.50
    )


def test_points_are_exposed_as_tuple():
    ledger = EquityLedger()

    ledger.append(
        make_point()
    )

    assert isinstance(
        ledger.points,
        tuple,
    )


def test_iteration_preserves_order():
    ledger = EquityLedger()

    first = make_point(
        timestamp=utc_time(10, 15),
        bar_index=0,
    )

    second = make_point(
        timestamp=utc_time(10, 30),
        bar_index=1,
    )

    ledger.append(first)
    ledger.append(second)

    assert list(ledger) == [
        first,
        second,
    ]


def test_append_requires_equity_point():
    ledger = EquityLedger()

    with pytest.raises(
        TypeError,
        match="EquityPoint",
    ):
        ledger.append(
            object()  # type: ignore[arg-type]
        )
        