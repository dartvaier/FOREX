from dataclasses import dataclass
from datetime import datetime, timedelta

from backtest.clock import ClockEvent, SimulationClock
from backtest.feed import HistoricalBarFeed
from backtest.models.bar import MarketBar
from backtest.models.enums import SimulationPhase


@dataclass(frozen=True, slots=True)
class BacktestContext:
    """The complete information boundary visible to a Strategy at one event.

    It intentionally exposes immutable bars only, never the source DataFrame,
    feed, future bars, or the current bar while it is unfinished.
    """

    current_time: datetime
    phase: SimulationPhase
    current_bar_index: int
    current_bar: MarketBar | None
    closed_bars: tuple[MarketBar, ...]

    def __post_init__(self) -> None:
        if self.current_time.tzinfo is None or self.current_time.utcoffset() != timedelta(0):
            raise ValueError("current_time must be timezone-aware UTC")
        if not isinstance(self.phase, SimulationPhase):
            raise TypeError("phase must be a SimulationPhase")
        if not isinstance(self.current_bar_index, int) or isinstance(self.current_bar_index, bool) or self.current_bar_index < 0:
            raise ValueError("current_bar_index must be a non-negative integer")
        if not isinstance(self.closed_bars, tuple) or not all(isinstance(bar, MarketBar) for bar in self.closed_bars):
            raise TypeError("closed_bars must be a tuple of MarketBar objects")
        if self.phase is SimulationPhase.BAR_OPEN and self.current_bar is not None:
            raise ValueError("current_bar must be None during BAR_OPEN")
        if self.phase is SimulationPhase.BAR_CLOSE:
            if not isinstance(self.current_bar, MarketBar):
                raise ValueError("current_bar must be a MarketBar during BAR_CLOSE")
            if not self.closed_bars or self.closed_bars[-1] != self.current_bar:
                raise ValueError("current_bar must be the latest closed bar")

    @property
    def last_closed_bar(self) -> MarketBar | None:
        return self.closed_bars[-1] if self.closed_bars else None


class BacktestContextBuilder:
    """Builds a Context while enforcing the no-look-ahead invariant."""

    def __init__(self, feed: HistoricalBarFeed, clock: SimulationClock) -> None:
        if not isinstance(feed, HistoricalBarFeed) or not isinstance(clock, SimulationClock):
            raise TypeError("feed and clock must be HistoricalBarFeed and SimulationClock")
        if feed.config.timeframe != clock.timeframe or feed.bar_starts != clock.bar_starts:
            raise ValueError("feed and clock must describe the same bar sequence")
        self._feed = feed
        self._clock = clock

    def build(self, event: ClockEvent, *, closed_bar_limit: int | None = None) -> BacktestContext:
        if not isinstance(event, ClockEvent):
            raise TypeError("event must be a ClockEvent")
        if event.bar_index < 0 or event.bar_index >= len(self._feed):
            raise ValueError("event bar_index is outside the feed")
        if closed_bar_limit is not None and (not isinstance(closed_bar_limit, int) or isinstance(closed_bar_limit, bool) or closed_bar_limit <= 0):
            raise ValueError("closed_bar_limit must be a positive integer or None")
        bar = self._feed.bars[event.bar_index]
        if event.bar_start != bar.time or event.bar_close != self._clock.bar_close_time(bar.time):
            raise ValueError("event does not match its feed bar")
        if event.phase is SimulationPhase.BAR_OPEN:
            if event.timestamp != bar.time:
                raise ValueError("BAR_OPEN timestamp must equal bar_start")
            end = event.bar_index
            current = None
        elif event.phase is SimulationPhase.BAR_CLOSE:
            if event.timestamp != event.bar_close:
                raise ValueError("BAR_CLOSE timestamp must equal bar_close")
            end = event.bar_index + 1
            current = bar
        else:
            raise ValueError("unsupported simulation phase")
        start = 0 if closed_bar_limit is None else max(0, end - closed_bar_limit)
        return BacktestContext(event.timestamp, event.phase, event.bar_index, current, self._feed.bars[start:end])
