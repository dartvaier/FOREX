from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone



def _validate_utc_timestamp(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{field_name} must be in UTC")


@dataclass(frozen=True, slots=True)
class Fill:
    """Executed order result produced by simulated or broker execution."""

    fill_id: str
    order_id: str
    fill_time: datetime
    reference_price: float
    execution_price: float
    quantity: float
    spread_impact: float = 0.0
    slippage: float = 0.0
    commission: float = 0.0

    def __post_init__(self) -> None:
        if not self.fill_id.strip():
            raise ValueError("fill_id must not be empty")
        if not self.order_id.strip():
            raise ValueError("order_id must not be empty")
        if self.reference_price <= 0:
            raise ValueError("reference_price must be greater than zero")
        if self.execution_price <= 0:
            raise ValueError("execution_price must be greater than zero")
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        if self.spread_impact < 0:
            raise ValueError("spread_impact must be non-negative")
        if self.commission < 0:
            raise ValueError("commission must be non-negative")
        _validate_utc_timestamp(self.fill_time, "fill_time")
