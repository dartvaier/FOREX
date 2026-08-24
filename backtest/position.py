from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class PositionSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class Position:
    """One fully-filled baseline position; partial fills and reversals are out of scope."""

    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    entry_time: datetime
    entry_fill_id: str
    entry_commission: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol must be a non-empty string")
        if not isinstance(self.side, PositionSide):
            raise TypeError("side must be a PositionSide")
        if self.quantity <= 0 or self.entry_price <= 0:
            raise ValueError("quantity and entry_price must be positive")
        if not self.entry_fill_id.strip():
            raise ValueError("entry_fill_id must not be empty")
        if self.entry_time.tzinfo is None or self.entry_time.utcoffset() != timedelta(0):
            raise ValueError("entry_time must be timezone-aware UTC")
        if self.entry_commission < 0:
            raise ValueError("entry_commission must be non-negative")

    def gross_unrealized_pnl(self, mark_price: float) -> float:
        if mark_price <= 0:
            raise ValueError("mark_price must be positive")
        difference = mark_price - self.entry_price
        return difference * self.quantity if self.side is PositionSide.LONG else -difference * self.quantity
