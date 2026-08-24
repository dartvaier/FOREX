import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from numbers import Integral, Real


@dataclass(frozen=True, slots=True)
class MarketBar:
    """Immutable completed or incomplete OHLCV bar.

    ``time`` is the start of the interval; final OHLC is observable only at
    the corresponding BAR_CLOSE event.
    """

    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    complete: bool = True

    def __post_init__(self) -> None:
        if self.time.tzinfo is None or self.time.utcoffset() != timedelta(0):
            raise ValueError("time must be timezone-aware UTC")
        for name in ("open", "high", "low", "close"):
            value = getattr(self, name)
            if not isinstance(value, Real) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a finite positive number")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be greater than or equal to OHLC")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be less than or equal to OHLC")
        if not isinstance(self.tick_volume, Integral) or isinstance(self.tick_volume, bool) or self.tick_volume < 0:
            raise ValueError("tick_volume must be a non-negative integer")
        if not isinstance(self.complete, bool):
            raise TypeError("complete must be a bool")
