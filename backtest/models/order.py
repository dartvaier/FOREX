import math
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

from backtest.models.enums import (
    OrderSide,
    OrderStatus,
    OrderType,
)


@dataclass(frozen=True, slots=True)
class Order:
    """
    Immutable order intent approved by the Risk layer.

    An Order represents an execution instruction.

    It is distinct from:
    - Signal: strategy intent
    - Fill: actual execution

    In the baseline backtester, MARKET orders are scheduled
    for the next available bar open.
    """

    order_id: str
    signal_id: str
    symbol: str
    side: OrderSide
    quantity: float

    order_type: OrderType

    created_at: datetime
    scheduled_for: datetime

    status: OrderStatus = OrderStatus.PENDING

    stop_loss: float | None = None
    take_profit: float | None = None

    reason: str | None = None

    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.order_id or not self.order_id.strip():
            raise ValueError("order_id must be a non-empty string")

        if not self.signal_id or not self.signal_id.strip():
            raise ValueError("signal_id must be a non-empty string")

        if not self.symbol or not self.symbol.strip():
            raise ValueError("symbol must be a non-empty string")

        if not isinstance(self.side, OrderSide):
            raise TypeError("side must be an OrderSide")

        if not isinstance(self.order_type, OrderType):
            raise TypeError("order_type must be an OrderType")

        if not isinstance(self.status, OrderStatus):
            raise TypeError("status must be an OrderStatus")

        if (
            not isinstance(self.quantity, (int, float))
            or isinstance(self.quantity, bool)
            or not math.isfinite(self.quantity)
            or self.quantity <= 0
        ):
            raise ValueError(
                "quantity must be a finite positive number"
            )

        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
        ):
            raise ValueError(
                "created_at must be timezone-aware"
            )

        if (
            self.scheduled_for.tzinfo is None
            or self.scheduled_for.utcoffset() is None
        ):
            raise ValueError(
                "scheduled_for must be timezone-aware"
            )

        if self.scheduled_for < self.created_at:
            raise ValueError(
                "scheduled_for cannot be earlier than created_at"
            )

        if self.stop_loss is not None:
            if (
                not isinstance(self.stop_loss, (int, float))
                or isinstance(self.stop_loss, bool)
                or not math.isfinite(self.stop_loss)
                or self.stop_loss <= 0
            ):
                raise ValueError(
                    "stop_loss must be a finite positive number or None"
                )

        if self.take_profit is not None:
            if (
                not isinstance(self.take_profit, (int, float))
                or isinstance(self.take_profit, bool)
                or not math.isfinite(self.take_profit)
                or self.take_profit <= 0
            ):
                raise ValueError(
                    "take_profit must be a finite positive number or None"
                )

        if self.reason is not None and not isinstance(
            self.reason,
            str,
        ):
            raise TypeError(
                "reason must be a string or None"
            )

        if not isinstance(self.metadata, Mapping):
            raise TypeError(
                "metadata must be a mapping"
            )

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )