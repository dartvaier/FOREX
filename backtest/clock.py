from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from backtest.models.enums import SimulationPhase, Timeframe

_DURATIONS = {Timeframe.M15: timedelta(minutes=15), Timeframe.H1: timedelta(hours=1), Timeframe.H4: timedelta(hours=4)}


@dataclass(frozen=True, slots=True)
class ClockEvent:
    timestamp: datetime
    phase: SimulationPhase
    bar_index: int
    bar_start: datetime
    bar_close: datetime


class SimulationClock:
    """Produces deterministic open/close events without inventing missing bars."""

    def __init__(self, bar_starts: Sequence[datetime], timeframe: Timeframe) -> None:
        if not isinstance(timeframe, Timeframe):
            raise TypeError("timeframe must be a Timeframe")
        if not bar_starts:
            raise ValueError("bar_starts cannot be empty")
        self.timeframe = timeframe
        self.duration = _DURATIONS[timeframe]
        self.bar_starts = tuple(bar_starts)
        previous = None
        for value in self.bar_starts:
            if value.tzinfo is None or value.utcoffset() != timedelta(0):
                raise ValueError("bar_starts must be timezone-aware UTC")
            if previous is not None and value <= previous:
                raise ValueError("bar_starts must be strictly increasing")
            if previous is not None and value < previous + self.duration:
                raise ValueError("bar_starts cannot overlap")
            previous = value

    def bar_close_time(self, bar_start: datetime) -> datetime:
        return bar_start + self.duration

    def events(self) -> Iterator[ClockEvent]:
        for index, start in enumerate(self.bar_starts):
            close = start + self.duration
            yield ClockEvent(start, SimulationPhase.BAR_OPEN, index, start, close)
            yield ClockEvent(close, SimulationPhase.BAR_CLOSE, index, start, close)
