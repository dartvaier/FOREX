from datetime import datetime, timezone

import pytest

from backtest.clock import ClockEvent
from backtest.models import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)
from backtest.models.enums import SimulationPhase
from backtest.order_queue import PendingOrderQueue


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
    *,
    order_id: str = "ORD-001",
    created_at: datetime | None = None,
    scheduled_for: datetime | None = None,
    status: OrderStatus = OrderStatus.PENDING,
) -> Order:
    created_at = (
        created_at
        if created_at is not None
        else utc_time(10, 15)
    )

    scheduled_for = (
        scheduled_for
        if scheduled_for is not None
        else created_at
    )

    return Order(
        order_id=order_id,
        signal_id="SIG-001",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.MARKET,
        created_at=created_at,
        scheduled_for=scheduled_for,
        status=status,
    )


def make_close_event(
    *,
    bar_index: int = 0,
    timestamp: datetime | None = None,
) -> ClockEvent:
    timestamp = (
        timestamp
        if timestamp is not None
        else utc_time(10, 15)
    )

    return ClockEvent(
        timestamp=timestamp,
        phase=SimulationPhase.BAR_CLOSE,
        bar_index=bar_index,
        bar_start=utc_time(10, 0),
        bar_close=timestamp,
    )


def make_open_event(
    *,
    bar_index: int = 1,
    timestamp: datetime | None = None,
) -> ClockEvent:
    timestamp = (
        timestamp
        if timestamp is not None
        else utc_time(10, 15)
    )

    return ClockEvent(
        timestamp=timestamp,
        phase=SimulationPhase.BAR_OPEN,
        bar_index=bar_index,
        bar_start=timestamp,
        bar_close=utc_time(10, 30),
    )


def test_queue_starts_empty():
    queue = PendingOrderQueue()

    assert queue.pending_count == 0
    assert queue.is_empty is True
    assert queue.pending_orders == ()


def test_enqueue_adds_pending_order():
    queue = PendingOrderQueue()

    order = make_order()

    queue.enqueue(
        order,
        submitted_event=make_close_event(),
    )

    assert queue.pending_count == 1
    assert queue.is_empty is False

    assert queue.pending_orders == (
        order,
    )


def test_queue_requires_order():
    queue = PendingOrderQueue()

    with pytest.raises(
        TypeError,
        match="Order",
    ):
        queue.enqueue(
            object(),  # type: ignore[arg-type]
            submitted_event=make_close_event(),
        )


def test_queue_requires_submission_event():
    queue = PendingOrderQueue()

    with pytest.raises(
        TypeError,
        match="ClockEvent",
    ):
        queue.enqueue(
            make_order(),
            submitted_event=None,  # type: ignore[arg-type]
        )


def test_order_can_only_be_submitted_after_bar_close():
    queue = PendingOrderQueue()

    event = make_open_event(
        bar_index=0,
        timestamp=utc_time(10, 15),
    )

    with pytest.raises(
        ValueError,
        match="BAR_CLOSE",
    ):
        queue.enqueue(
            make_order(),
            submitted_event=event,
        )


@pytest.mark.parametrize(
    "status",
    [
        OrderStatus.FILLED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
        OrderStatus.UNFILLED,
    ],
)
def test_queue_accepts_only_pending_orders(
    status,
):
    queue = PendingOrderQueue()

    with pytest.raises(
        ValueError,
        match="PENDING",
    ):
        queue.enqueue(
            make_order(
                status=status,
            ),
            submitted_event=make_close_event(),
        )


def test_order_created_at_must_match_submission_time():
    queue = PendingOrderQueue()

    order = make_order(
        created_at=utc_time(10, 30),
        scheduled_for=utc_time(10, 30),
    )

    with pytest.raises(
        ValueError,
        match="created_at",
    ):
        queue.enqueue(
            order,
            submitted_event=make_close_event(
                timestamp=utc_time(10, 15)
            ),
        )


def test_queue_rejects_duplicate_order_id():
    queue = PendingOrderQueue()

    first = make_order(
        order_id="ORD-001",
    )

    second = make_order(
        order_id="ORD-001",
    )

    event = make_close_event()

    queue.enqueue(
        first,
        submitted_event=event,
    )

    with pytest.raises(
        ValueError,
        match="duplicate",
    ):
        queue.enqueue(
            second,
            submitted_event=event,
        )


def test_same_timestamp_next_bar_open_is_eligible():
    queue = PendingOrderQueue()

    order = make_order(
        created_at=utc_time(10, 15),
        scheduled_for=utc_time(10, 15),
    )

    queue.enqueue(
        order,
        submitted_event=make_close_event(
            bar_index=0,
            timestamp=utc_time(10, 15),
        ),
    )

    eligible = queue.pop_eligible(
        make_open_event(
            bar_index=1,
            timestamp=utc_time(10, 15),
        )
    )

    assert eligible == (
        order,
    )

    assert queue.is_empty is True


def test_order_cannot_execute_on_submission_bar():
    queue = PendingOrderQueue()

    order = make_order()

    queue.enqueue(
        order,
        submitted_event=make_close_event(
            bar_index=0,
        ),
    )

    eligible = queue.pop_eligible(
        make_open_event(
            bar_index=0,
            timestamp=utc_time(10, 15),
        )
    )

    assert eligible == ()

    assert queue.pending_orders == (
        order,
    )


def test_future_scheduled_order_remains_pending():
    queue = PendingOrderQueue()

    order = make_order(
        created_at=utc_time(10, 15),
        scheduled_for=utc_time(10, 45),
    )

    queue.enqueue(
        order,
        submitted_event=make_close_event(
            bar_index=0,
            timestamp=utc_time(10, 15),
        ),
    )

    eligible = queue.pop_eligible(
        make_open_event(
            bar_index=1,
            timestamp=utc_time(10, 30),
        )
    )

    assert eligible == ()

    assert queue.pending_orders == (
        order,
    )


def test_order_becomes_eligible_when_scheduled_time_arrives():
    queue = PendingOrderQueue()

    order = make_order(
        created_at=utc_time(10, 15),
        scheduled_for=utc_time(10, 45),
    )

    queue.enqueue(
        order,
        submitted_event=make_close_event(
            bar_index=0,
            timestamp=utc_time(10, 15),
        ),
    )

    eligible = queue.pop_eligible(
        make_open_event(
            bar_index=2,
            timestamp=utc_time(10, 45),
        )
    )

    assert eligible == (
        order,
    )


def test_gap_executes_at_next_available_open():
    queue = PendingOrderQueue()

    order = make_order(
        created_at=utc_time(10, 15),
        scheduled_for=utc_time(10, 15),
    )

    queue.enqueue(
        order,
        submitted_event=make_close_event(
            bar_index=0,
            timestamp=utc_time(10, 15),
        ),
    )

    eligible = queue.pop_eligible(
        make_open_event(
            bar_index=1,
            timestamp=utc_time(10, 45),
        )
    )

    assert eligible == (
        order,
    )


def test_pop_requires_clock_event():
    queue = PendingOrderQueue()

    with pytest.raises(
        TypeError,
        match="ClockEvent",
    ):
        queue.pop_eligible(
            object()  # type: ignore[arg-type]
        )


def test_pending_orders_can_only_be_processed_at_bar_open():
    queue = PendingOrderQueue()

    queue.enqueue(
        make_order(),
        submitted_event=make_close_event(),
    )

    with pytest.raises(
        ValueError,
        match="BAR_OPEN",
    ):
        queue.pop_eligible(
            make_close_event(
                bar_index=1,
                timestamp=utc_time(10, 30),
            )
        )


def test_multiple_eligible_orders_preserve_enqueue_order():
    queue = PendingOrderQueue()

    first = make_order(
        order_id="ORD-001",
    )

    second = Order(
        order_id="ORD-002",
        signal_id="SIG-002",
        symbol="EURUSD",
        side=OrderSide.SELL,
        quantity=0.02,
        order_type=OrderType.MARKET,
        created_at=utc_time(10, 15),
        scheduled_for=utc_time(10, 15),
        status=OrderStatus.PENDING,
    )

    event = make_close_event()

    queue.enqueue(
        first,
        submitted_event=event,
    )

    queue.enqueue(
        second,
        submitted_event=event,
    )

    eligible = queue.pop_eligible(
        make_open_event(
            bar_index=1,
            timestamp=utc_time(10, 15),
        )
    )

    assert eligible == (
        first,
        second,
    )


def test_ineligible_order_does_not_block_later_eligible_order():
    queue = PendingOrderQueue()

    later = make_order(
        order_id="ORD-LATER",
        created_at=utc_time(10, 15),
        scheduled_for=utc_time(11, 0),
    )

    now = Order(
        order_id="ORD-NOW",
        signal_id="SIG-NOW",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.MARKET,
        created_at=utc_time(10, 15),
        scheduled_for=utc_time(10, 15),
        status=OrderStatus.PENDING,
    )

    event = make_close_event()

    queue.enqueue(
        later,
        submitted_event=event,
    )

    queue.enqueue(
        now,
        submitted_event=event,
    )

    eligible = queue.pop_eligible(
        make_open_event(
            bar_index=1,
            timestamp=utc_time(10, 15),
        )
    )

    assert eligible == (
        now,
    )

    assert queue.pending_orders == (
        later,
    )


def test_popped_order_cannot_be_enqueued_again():
    queue = PendingOrderQueue()

    order = make_order()

    queue.enqueue(
        order,
        submitted_event=make_close_event(),
    )

    queue.pop_eligible(
        make_open_event(
            bar_index=1,
            timestamp=utc_time(10, 15),
        )
    )

    with pytest.raises(
        ValueError,
        match="duplicate",
    ):
        queue.enqueue(
            order,
            submitted_event=make_close_event(
                bar_index=1,
                timestamp=utc_time(10, 30),
            ),
        )


def test_popped_order_remains_pending_until_execution_layer():
    queue = PendingOrderQueue()

    order = make_order()

    queue.enqueue(
        order,
        submitted_event=make_close_event(),
    )

    eligible = queue.pop_eligible(
        make_open_event(
            bar_index=1,
            timestamp=utc_time(10, 15),
        )
    )

    assert eligible[0].status == (
        OrderStatus.PENDING
    )