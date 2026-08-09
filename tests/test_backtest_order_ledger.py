from dataclasses import replace
from datetime import datetime, timezone

import pytest

from backtest.models import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)
from backtest.order_ledger import OrderLedger


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


def make_order(
    order_id: str,
    *,
    created_at: datetime | None = None,
) -> Order:
    timestamp = (
        created_at
        if created_at is not None
        else utc_time(10, 15)
    )

    return Order(
        order_id=order_id,
        signal_id=f"SIG-{order_id}",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.MARKET,
        created_at=timestamp,
        scheduled_for=timestamp,
        status=OrderStatus.PENDING,
    )


def test_ledger_starts_empty():
    ledger = OrderLedger()

    assert ledger.count == 0
    assert ledger.history_count == 0
    assert ledger.is_empty is True
    assert ledger.orders == ()
    assert ledger.history == ()
    assert ledger.last_record is None


def test_append_pending_order():
    ledger = OrderLedger()

    order = make_order("ORD-001")

    ledger.append(order)

    assert ledger.count == 1
    assert ledger.history_count == 1
    assert ledger.orders == (order,)
    assert ledger.last_record == order


def test_new_order_must_start_pending():
    ledger = OrderLedger()

    order = replace(
        make_order("ORD-001"),
        status=OrderStatus.FILLED,
    )

    with pytest.raises(
        ValueError,
        match="must start as PENDING",
    ):
        ledger.append(order)


def test_pending_can_transition_to_filled():
    ledger = OrderLedger()

    pending = make_order("ORD-001")

    filled = replace(
        pending,
        status=OrderStatus.FILLED,
    )

    ledger.append(pending)
    ledger.append(filled)

    assert ledger.count == 1
    assert ledger.history_count == 2

    assert ledger.get(
        "ORD-001"
    ) == filled

    assert ledger.get_history(
        "ORD-001"
    ) == (
        pending,
        filled,
    )


@pytest.mark.parametrize(
    "terminal_status",
    [
        OrderStatus.FILLED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
        OrderStatus.UNFILLED,
    ],
)
def test_pending_can_transition_to_terminal_status(
    terminal_status,
):
    ledger = OrderLedger()

    pending = make_order("ORD-001")

    terminal = replace(
        pending,
        status=terminal_status,
    )

    ledger.append(pending)
    ledger.append(terminal)

    assert ledger.get(
        "ORD-001"
    ).status == terminal_status


def test_rejects_duplicate_pending_snapshot():
    ledger = OrderLedger()

    pending = make_order("ORD-001")

    ledger.append(pending)

    with pytest.raises(
        ValueError,
        match="duplicate PENDING",
    ):
        ledger.append(pending)


def test_terminal_order_cannot_transition_again():
    ledger = OrderLedger()

    pending = make_order("ORD-001")

    filled = replace(
        pending,
        status=OrderStatus.FILLED,
    )

    cancelled = replace(
        pending,
        status=OrderStatus.CANCELLED,
    )

    ledger.append(pending)
    ledger.append(filled)

    with pytest.raises(
        ValueError,
        match="terminal Order",
    ):
        ledger.append(cancelled)


def test_transition_cannot_change_quantity():
    ledger = OrderLedger()

    pending = make_order("ORD-001")

    invalid = replace(
        pending,
        quantity=0.02,
        status=OrderStatus.FILLED,
    )

    ledger.append(pending)

    with pytest.raises(
        ValueError,
        match="quantity",
    ):
        ledger.append(invalid)


def test_preserves_unique_order_creation_order():
    ledger = OrderLedger()

    first = make_order(
        "ORD-001",
        created_at=utc_time(10, 15),
    )

    second = make_order(
        "ORD-002",
        created_at=utc_time(10, 30),
    )

    ledger.append(first)
    ledger.append(second)

    ledger.append(
        replace(
            first,
            status=OrderStatus.FILLED,
        )
    )

    assert [
        order.order_id
        for order in ledger.orders
    ] == [
        "ORD-001",
        "ORD-002",
    ]

    assert (
        ledger.orders[0].status
        == OrderStatus.FILLED
    )


def test_rejects_new_order_created_at_regression():
    ledger = OrderLedger()

    ledger.append(
        make_order(
            "ORD-001",
            created_at=utc_time(10, 30),
        )
    )

    with pytest.raises(
        ValueError,
        match="cannot move backward",
    ):
        ledger.append(
            make_order(
                "ORD-002",
                created_at=utc_time(10, 15),
            )
        )


def test_allows_equal_created_at():
    ledger = OrderLedger()

    ledger.append(
        make_order(
            "ORD-001",
            created_at=utc_time(10, 15),
        )
    )

    ledger.append(
        make_order(
            "ORD-002",
            created_at=utc_time(10, 15),
        )
    )

    assert ledger.count == 2


def test_get_returns_none_for_unknown_order():
    ledger = OrderLedger()

    assert ledger.get(
        "ORD-UNKNOWN"
    ) is None


def test_get_history_returns_empty_for_unknown_order():
    ledger = OrderLedger()

    assert ledger.get_history(
        "ORD-UNKNOWN"
    ) == ()


def test_append_requires_order():
    ledger = OrderLedger()

    with pytest.raises(
        TypeError,
        match="Order",
    ):
        ledger.append(
            object()  # type: ignore[arg-type]
        )


def test_iteration_returns_latest_snapshots():
    ledger = OrderLedger()

    first = make_order(
        "ORD-001",
        created_at=utc_time(10, 15),
    )

    second = make_order(
        "ORD-002",
        created_at=utc_time(10, 30),
    )

    ledger.append(first)
    ledger.append(second)

    filled_first = replace(
        first,
        status=OrderStatus.FILLED,
    )

    ledger.append(filled_first)

    assert list(ledger) == [
        filled_first,
        second,
    ]