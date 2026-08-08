from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from backtest.models.enums import (
    SimulationPhase,
    Timeframe,
)


_TIMEFRAME_DURATIONS = {
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H4: timedelta(hours=4),
}


@dataclass(frozen=True, slots=True)
class ClockEvent:
    """
    Immutable event produced by the SimulationClock.

    bar_start:
        Timestamp representing the beginning of the bar.

    bar_close:
        Timestamp at which the bar becomes fully known.

    timestamp:
        Time of the current simulation event.

    phase:
        BAR_OPEN or BAR_CLOSE.

    bar_index:
        Zero-based index in the supplied historical sequence.
    """

    timestamp: datetime

    phase: SimulationPhase

    bar_index: int

    bar_start: datetime
    bar_close: datetime


class SimulationClock:
    """
    Deterministic bar-based historical simulation clock.

    The clock receives the bar timestamps that actually exist
    in the dataset.

    It does not synthesize missing bars.

    For contiguous bars, the close of bar t and the open of
    bar t+1 may share the same timestamp.

    Event order remains deterministic:

        BAR t CLOSE
        BAR t+1 OPEN

    This ordering allows a Signal produced after BAR_CLOSE
    to generate an Order that executes at the next BAR_OPEN,
    even when both events share the same datetime.
    """

    def __init__(
        self,
        bar_starts: Sequence[datetime],
        timeframe: Timeframe,
    ) -> None:
        if not isinstance(timeframe, Timeframe):
            raise TypeError(
                "timeframe must be a Timeframe"
            )

        if not bar_starts:
            raise ValueError(
                "bar_starts cannot be empty"
            )

        self._timeframe = timeframe
        self._duration = _TIMEFRAME_DURATIONS[timeframe]

        self._bar_starts = tuple(bar_starts)

        self._validate_bar_starts()

    @property
    def timeframe(self) -> Timeframe:
        return self._timeframe

    @property
    def duration(self) -> timedelta:
        return self._duration

    @property
    def bar_count(self) -> int:
        return len(self._bar_starts)

    @property
    def bar_starts(self) -> tuple[datetime, ...]:
        return self._bar_starts

    def bar_close_time(
        self,
        bar_start: datetime,
    ) -> datetime:
        """
        Return the theoretical close time for a bar.
        """

        self._validate_utc_datetime(
            "bar_start",
            bar_start,
        )

        return bar_start + self._duration

    def events(self) -> Iterator[ClockEvent]:
        """
        Yield BAR_OPEN and BAR_CLOSE events in deterministic
        historical order.

        Missing bars are not generated.
        """

        for bar_index, bar_start in enumerate(
            self._bar_starts
        ):
            bar_close = (
                bar_start
                + self._duration
            )

            yield ClockEvent(
                timestamp=bar_start,
                phase=SimulationPhase.BAR_OPEN,
                bar_index=bar_index,
                bar_start=bar_start,
                bar_close=bar_close,
            )

            yield ClockEvent(
                timestamp=bar_close,
                phase=SimulationPhase.BAR_CLOSE,
                bar_index=bar_index,
                bar_start=bar_start,
                bar_close=bar_close,
            )

    def _validate_bar_starts(self) -> None:
        previous_start: datetime | None = None

        for index, bar_start in enumerate(
            self._bar_starts
        ):
            self._validate_utc_datetime(
                f"bar_starts[{index}]",
                bar_start,
            )

            if previous_start is not None:
                if bar_start <= previous_start:
                    raise ValueError(
                        "bar_starts must be strictly increasing"
                    )

                previous_close = (
                    previous_start
                    + self._duration
                )

                if bar_start < previous_close:
                    raise ValueError(
                        "bar_starts cannot overlap"
                    )

            previous_start = bar_start

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