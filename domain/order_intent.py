from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"


def _validate_utc_timestamp(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{field_name} must be in UTC")


@dataclass(frozen=True, slots=True)
class OrderIntent:
    """Risk-approved intent that may be submitted to simulated or live execution."""

    order_id: str
    signal_id: str
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    created_at: datetime
    stop_loss: float | None = None
    take_profit: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.order_id.strip():
            raise ValueError("order_id must not be empty")
        if not self.signal_id.strip():
            raise ValueError("signal_id must not be empty")
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        if self.stop_loss is not None and self.stop_loss <= 0:
            raise ValueError("stop_loss must be greater than zero")
        if self.take_profit is not None and self.take_profit <= 0:
            raise ValueError("take_profit must be greater than zero")
        _validate_utc_timestamp(self.created_at, "created_at")
