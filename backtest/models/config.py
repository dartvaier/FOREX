import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from numbers import Real

from backtest.models.enums import (
    AmbiguousBarPolicy,
    EndOfBacktestPolicy,
    Timeframe,
)


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """
    Immutable configuration for a single BacktestEngine run.

    The evaluation interval follows:

        [date_from, date_to)

    meaning:

        date_from is inclusive
        date_to is exclusive

    Strategy parameters, Risk configuration and CostModel
    configuration are intentionally not stored here.

    Those components have their own contracts and will be
    recorded separately by the future experiment manifest.
    """

    symbol: str
    timeframe: Timeframe

    date_from: datetime
    date_to: datetime

    initial_capital: float

    ambiguous_bar_policy: AmbiguousBarPolicy = (
        AmbiguousBarPolicy.WORST_CASE
    )

    end_of_backtest_policy: EndOfBacktestPolicy = (
        EndOfBacktestPolicy.FORCE_CLOSE_AT_FINAL_AVAILABLE_CLOSE
    )

    allow_incomplete_bars: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.symbol, str)
            or not self.symbol.strip()
        ):
            raise ValueError(
                "symbol must be a non-empty string"
            )

        if not isinstance(self.timeframe, Timeframe):
            raise TypeError(
                "timeframe must be a Timeframe"
            )

        self._validate_utc_datetime(
            "date_from",
            self.date_from,
        )

        self._validate_utc_datetime(
            "date_to",
            self.date_to,
        )

        if self.date_to <= self.date_from:
            raise ValueError(
                "date_to must be later than date_from"
            )

        self._validate_positive_number(
            "initial_capital",
            self.initial_capital,
        )

        if not isinstance(
            self.ambiguous_bar_policy,
            AmbiguousBarPolicy,
        ):
            raise TypeError(
                "ambiguous_bar_policy must be "
                "an AmbiguousBarPolicy"
            )

        if not isinstance(
            self.end_of_backtest_policy,
            EndOfBacktestPolicy,
        ):
            raise TypeError(
                "end_of_backtest_policy must be "
                "an EndOfBacktestPolicy"
            )

        if not isinstance(
            self.allow_incomplete_bars,
            bool,
        ):
            raise TypeError(
                "allow_incomplete_bars must be a bool"
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