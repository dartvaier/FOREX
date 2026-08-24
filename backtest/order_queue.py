from dataclasses import dataclass

from backtest.clock import ClockEvent
from backtest.models.enums import (
    OrderStatus,
    SimulationPhase,
)
from backtest.models.order import Order


@dataclass(frozen=True, slots=True)
class _PendingOrderEntry:
    """
    Internal queue bookkeeping.

    submitted_bar_index records the historical bar whose
    BAR_CLOSE event caused this Order to enter the queue.

    This information is intentionally separate from Order
    because it belongs to simulation infrastructure rather
    than to the trading-domain Order itself.
    """

    order: Order
    submitted_bar_index: int


class PendingOrderQueue:
    """
    Deterministic queue of pending Orders waiting for a future
    BAR_OPEN event.

    Baseline temporal rule:

        Order submitted after BAR_CLOSE of bar N

    may execute only at:

        BAR_OPEN of bar M where M > N

    This is critical because:

        BAR_CLOSE bar N
        BAR_OPEN  bar N+1

    may share exactly the same datetime.

    Timestamp comparison alone is therefore insufficient to
    guarantee causal execution.

    The queue does not execute Orders and does not create
    Fills. It only determines which pending Orders are
    eligible for the current BAR_OPEN event.
    """

    def __init__(self) -> None:
        self._entries: list[
            _PendingOrderEntry
        ] = []

        self._known_order_ids: set[str] = set()

    @property
    def pending_count(self) -> int:
        return len(self._entries)

    @property
    def is_empty(self) -> bool:
        return not self._entries

    @property
    def pending_orders(
        self,
    ) -> tuple[Order, ...]:
        return tuple(
            entry.order
            for entry in self._entries
        )

    def enqueue(
        self,
        order: Order,
        *,
        submitted_event: ClockEvent,
    ) -> None:
        """
        Add a pending Order after the BAR_CLOSE event that
        produced it.
        """

        if not isinstance(order, Order):
            raise TypeError(
                "order must be an Order"
            )

        if not isinstance(
            submitted_event,
            ClockEvent,
        ):
            raise TypeError(
                "submitted_event must be a ClockEvent"
            )

        if (
            submitted_event.phase
            != SimulationPhase.BAR_CLOSE
        ):
            raise ValueError(
                "Orders can only be submitted after BAR_CLOSE"
            )

        if order.status != OrderStatus.PENDING:
            raise ValueError(
                "only PENDING Orders can enter the queue"
            )

        if (
            order.order_id
            in self._known_order_ids
        ):
            raise ValueError(
                "duplicate order_id"
            )

        if (
            order.created_at
            != submitted_event.timestamp
        ):
            raise ValueError(
                "order created_at must equal "
                "submitted BAR_CLOSE timestamp"
            )

        self._entries.append(
            _PendingOrderEntry(
                order=order,
                submitted_bar_index=(
                    submitted_event.bar_index
                ),
            )
        )

        self._known_order_ids.add(
            order.order_id
        )


    def pop_eligible(
        self,
        event: ClockEvent,
    ) -> tuple[Order, ...]:
        """
        Remove and return Orders eligible for execution at the
        supplied BAR_OPEN event.

        Eligibility requires:

        - event.phase == BAR_OPEN
        - current bar index is later than submission bar index
        - event timestamp >= order.scheduled_for

        Eligible Orders preserve enqueue order.
        """

        if not isinstance(
            event,
            ClockEvent,
        ):
            raise TypeError(
                "event must be a ClockEvent"
            )

        if (
            event.phase
            != SimulationPhase.BAR_OPEN
        ):
            raise ValueError(
                "pending Orders can only be processed "
                "at BAR_OPEN"
            )

        eligible: list[Order] = []

        remaining: list[
            _PendingOrderEntry
        ] = []

        for entry in self._entries:
            order = entry.order

            is_future_bar = (
                event.bar_index
                > entry.submitted_bar_index
            )

            is_time_eligible = (
                event.timestamp
                >= order.scheduled_for
            )

            if (
                is_future_bar
                and is_time_eligible
            ):
                eligible.append(order)
            else:
                remaining.append(entry)

        self._entries = remaining

        return tuple(eligible)