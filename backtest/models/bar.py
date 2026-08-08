import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from numbers import Integral, Real


@dataclass(frozen=True, slots=True)
class MarketBar:
    """
    Immutable OHLCV market bar available to the BacktestEngine.

    `time` represents the beginning of the bar.

    Example for M15:

        time = 10:00

    represents the interval:

        10:00 -> 10:15

    The final OHLC values are only considered available after
    the corresponding bar close event.

    Historical spread and real_volume are intentionally not
    part of this model because they are not trusted execution
    inputs in the current research dataset.
    """

    time: datetime

    open: float
    high: float
    low: float
    close: float

    tick_volume: int

    complete: bool = True

    def __post_init__(self) -> None:
        self._validate_utc_datetime(
            "time",
            self.time,
        )

        self._validate_positive_number(
            "open",
            self.open,
        )

        self._validate_positive_number(
            "high",
            self.high,
        )

        self._validate_positive_number(
            "low",
            self.low,
        )

        self._validate_positive_number(
            "close",
            self.close,
        )

        if self.high < max(
            self.open,
            self.close,
            self.low,
        ):
            raise ValueError(
                "high must be greater than or equal to "
                "open, close and low"
            )

        if self.low > min(
            self.open,
            self.close,
            self.high,
        ):
            raise ValueError(
                "low must be less than or equal to "
                "open, close and high"
            )

        if (
            not isinstance(self.tick_volume, Integral)
            or isinstance(self.tick_volume, bool)
            or self.tick_volume < 0
        ):
            raise ValueError(
                "tick_volume must be a non-negative integer"
            )

        if not isinstance(self.complete, bool):
            raise TypeError(
                "complete must be a bool"
            )

    @staticmethod
    def _validate_utc_datetime(
        name: str,
        value: datetime,
    ) -> None:
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                f"{name} must be timezone-aware"
            )

        if value.utcoffset() != timedelta(0):
            raise ValueError(
                f"{name} must use UTC"
            )

    @staticmethod
    def _validate_positive_number(
        name: str,
        value: Real,
    ) -> None:
        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(
                f"{name} must be a finite positive number"
            )