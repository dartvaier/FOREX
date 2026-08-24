from backtest.models.enums import OrderStatus
from backtest.models.order import Order


class OrderLedger:
    """
    Ordered audit ledger of Order lifecycle snapshots.

    A single order_id may appear more than once in history
    because Order is immutable and lifecycle transitions create
    new snapshots.

    Baseline lifecycle:

        PENDING
            ->
        FILLED | REJECTED | CANCELLED | UNFILLED

    Terminal states cannot transition again.
    """

    _TERMINAL_STATUSES = {
        OrderStatus.FILLED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
        OrderStatus.UNFILLED,
    }

    def __init__(self) -> None:
        self._order_ids: list[str] = []
        self._latest: dict[str, Order] = {}
        self._history: list[Order] = []

    @property
    def orders(self) -> tuple[Order, ...]:
        """
        Latest snapshot of each unique Order, preserving the
        creation order of order_ids.
        """
        return tuple(
            self._latest[order_id]
            for order_id in self._order_ids
        )

    @property
    def history(self) -> tuple[Order, ...]:
        """
        Complete lifecycle history in recording order.
        """
        return tuple(self._history)

    @property
    def count(self) -> int:
        """
        Number of unique Orders.
        """
        return len(self._order_ids)

    @property
    def history_count(self) -> int:
        """
        Number of lifecycle snapshots recorded.
        """
        return len(self._history)

    @property
    def is_empty(self) -> bool:
        return not self._order_ids

    @property
    def last_record(self) -> Order | None:
        if not self._history:
            return None

        return self._history[-1]

    def append(
        self,
        order: Order,
    ) -> None:
        if not isinstance(order, Order):
            raise TypeError(
                "order must be an Order"
            )

        previous = self._latest.get(
            order.order_id
        )

        if previous is None:
            self._append_new(order)
            return

        self._append_transition(
            previous,
            order,
        )

    def get(
        self,
        order_id: str,
    ) -> Order | None:
        self._validate_order_id(order_id)

        return self._latest.get(order_id)

    def get_history(
        self,
        order_id: str,
    ) -> tuple[Order, ...]:
        self._validate_order_id(order_id)

        return tuple(
            order
            for order in self._history
            if order.order_id == order_id
        )

    def _append_new(
        self,
        order: Order,
    ) -> None:
        if order.status != OrderStatus.PENDING:
            raise ValueError(
                "new Order must start as PENDING"
            )

        if self._order_ids:
            previous_order = self._latest[
                self._order_ids[-1]
            ]

            if (
                order.created_at
                < previous_order.created_at
            ):
                raise ValueError(
                    "Order created_at cannot move backward"
                )

        self._order_ids.append(
            order.order_id
        )

        self._latest[
            order.order_id
        ] = order

        self._history.append(order)

    def _append_transition(
        self,
        previous: Order,
        order: Order,
    ) -> None:
        if (
            previous.status
            in self._TERMINAL_STATUSES
        ):
            raise ValueError(
                "terminal Order cannot transition"
            )

        if previous.status != OrderStatus.PENDING:
            raise ValueError(
                "unsupported Order status transition"
            )

        if order.status == OrderStatus.PENDING:
            raise ValueError(
                "duplicate PENDING Order snapshot"
            )

        if (
            order.status
            not in self._TERMINAL_STATUSES
        ):
            raise ValueError(
                "unsupported Order status transition"
            )

        self._validate_same_order(
            previous,
            order,
        )

        self._latest[
            order.order_id
        ] = order

        self._history.append(order)

    @staticmethod
    def _validate_same_order(
        previous: Order,
        current: Order,
    ) -> None:
        """
        Lifecycle transitions may change status/reason/metadata,
        but must not silently change the execution instruction.
        """

        immutable_fields = (
            "signal_id",
            "symbol",
            "side",
            "quantity",
            "order_type",
            "created_at",
            "scheduled_for",
            "stop_loss",
            "take_profit",
        )

        for field_name in immutable_fields:
            if (
                getattr(previous, field_name)
                != getattr(current, field_name)
            ):
                raise ValueError(
                    "Order lifecycle transition "
                    f"cannot change {field_name}"
                )

    @staticmethod
    def _validate_order_id(
        order_id: str,
    ) -> None:
        if (
            not isinstance(order_id, str)
            or not order_id.strip()
        ):
            raise ValueError(
                "order_id must be a non-empty string"
            )

    def __len__(self) -> int:
        return self.count

    def __iter__(self):
        return iter(self.orders)