from backtest.models.fill import Fill


class FillLedger:
    """
    Ordered ledger of executed Fills.

    Responsibilities:

    - preserve insertion order;
    - expose immutable Fill snapshots;
    - reject duplicate fill IDs;
    - reject more than one Fill for the same Order;
    - reject chronological regression.

    The baseline does not support partial fills.
    """

    def __init__(self) -> None:
        self._fills: list[Fill] = []
        self._fill_ids: set[str] = set()
        self._order_ids: set[str] = set()

    @property
    def fills(self) -> tuple[Fill, ...]:
        return tuple(self._fills)

    @property
    def count(self) -> int:
        return len(self._fills)

    @property
    def is_empty(self) -> bool:
        return not self._fills

    @property
    def last_fill(self) -> Fill | None:
        if not self._fills:
            return None

        return self._fills[-1]

    def append(
        self,
        fill: Fill,
    ) -> None:
        if not isinstance(fill, Fill):
            raise TypeError(
                "fill must be a Fill"
            )

        if fill.fill_id in self._fill_ids:
            raise ValueError(
                "duplicate fill_id"
            )

        if fill.order_id in self._order_ids:
            raise ValueError(
                "Order already has a Fill"
            )

        if self._fills:
            previous = self._fills[-1]

            if fill.fill_time < previous.fill_time:
                raise ValueError(
                    "Fill fill_time cannot move backward"
                )

        self._fills.append(fill)
        self._fill_ids.add(fill.fill_id)
        self._order_ids.add(fill.order_id)

    def get(
        self,
        fill_id: str,
    ) -> Fill | None:
        self._validate_id(
            "fill_id",
            fill_id,
        )

        for fill in self._fills:
            if fill.fill_id == fill_id:
                return fill

        return None

    def get_by_order_id(
        self,
        order_id: str,
    ) -> Fill | None:
        self._validate_id(
            "order_id",
            order_id,
        )

        for fill in self._fills:
            if fill.order_id == order_id:
                return fill

        return None

    @staticmethod
    def _validate_id(
        name: str,
        value: str,
    ) -> None:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{name} must be a non-empty string"
            )

    def __len__(self) -> int:
        return len(self._fills)

    def __iter__(self):
        return iter(self.fills)