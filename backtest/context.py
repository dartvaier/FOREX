from collections.abc import Mapping
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from types import MappingProxyType

from backtest.clock import ClockEvent, SimulationClock
from backtest.feed import HistoricalBarFeed
from backtest.models.bar import MarketBar
from backtest.models.enums import SimulationPhase, Timeframe


_TIMEFRAME_DURATIONS = {
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H4: timedelta(hours=4),
}


@dataclass(frozen=True, slots=True)
class BacktestContext:
    """
    Strategy-safe snapshot of information available at one
    simulation event.

    This object deliberately does not expose:

    - the source DataFrame
    - the HistoricalBarFeed
    - future MarketBars
    - the current unfinished MarketBar at BAR_OPEN

    BAR_OPEN:
        current_bar is None.

        closed_bars contains only bars that had already closed
        before or at current_time.

    BAR_CLOSE:
        current_bar is the bar that has just become fully known.

        closed_bars contains that bar and all previously closed
        bars.

    Position, cash and equity are intentionally absent for now.
    They will be added when the Portfolio layer exists.
    """

    current_time: datetime
    phase: SimulationPhase
    current_bar_index: int

    current_bar: MarketBar | None
    closed_bars: tuple[MarketBar, ...]
    timeframe_bars: Mapping[
        Timeframe,
        tuple[MarketBar, ...],
    ] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._validate_utc_datetime(
            "current_time",
            self.current_time,
        )

        if not isinstance(
            self.phase,
            SimulationPhase,
        ):
            raise TypeError(
                "phase must be a SimulationPhase"
            )

        if (
            not isinstance(self.current_bar_index, int)
            or isinstance(self.current_bar_index, bool)
            or self.current_bar_index < 0
        ):
            raise ValueError(
                "current_bar_index must be a "
                "non-negative integer"
            )

        if not isinstance(
            self.closed_bars,
            tuple,
        ):
            raise TypeError(
                "closed_bars must be a tuple"
            )

        if not all(
            isinstance(bar, MarketBar)
            for bar in self.closed_bars
        ):
            raise TypeError(
                "closed_bars must contain only MarketBar objects"
            )

        if not isinstance(
            self.timeframe_bars,
            Mapping,
        ):
            raise TypeError(
                "timeframe_bars must be a mapping"
            )

        normalized_timeframe_bars = {}

        for timeframe, bars in self.timeframe_bars.items():
            if not isinstance(
                timeframe,
                Timeframe,
            ):
                raise TypeError(
                    "timeframe_bars keys must be Timeframe values"
                )

            if not isinstance(
                bars,
                tuple,
            ):
                raise TypeError(
                    "timeframe_bars values must be tuples"
                )

            if not all(
                isinstance(bar, MarketBar)
                for bar in bars
            ):
                raise TypeError(
                    "timeframe_bars values must contain only "
                    "MarketBar objects"
                )

            normalized_timeframe_bars[timeframe] = bars

        object.__setattr__(
            self,
            "timeframe_bars",
            MappingProxyType(normalized_timeframe_bars),
        )

        if self.phase == SimulationPhase.BAR_OPEN:
            if self.current_bar is not None:
                raise ValueError(
                    "current_bar must be None during BAR_OPEN"
                )

        if self.phase == SimulationPhase.BAR_CLOSE:
            if not isinstance(
                self.current_bar,
                MarketBar,
            ):
                raise ValueError(
                    "current_bar must be a MarketBar "
                    "during BAR_CLOSE"
                )

            if not self.closed_bars:
                raise ValueError(
                    "closed_bars cannot be empty "
                    "during BAR_CLOSE"
                )

            if (
                self.closed_bars[-1]
                != self.current_bar
            ):
                raise ValueError(
                    "current_bar must be the latest "
                    "closed bar"
                )

    @property
    def last_closed_bar(
        self,
    ) -> MarketBar | None:
        """
        Most recently available closed bar.
        """

        if not self.closed_bars:
            return None

        return self.closed_bars[-1]

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


class BacktestContextBuilder:
    """
    Builds Strategy-safe BacktestContext objects from a
    validated HistoricalBarFeed and SimulationClock.

    The builder enforces that the Feed and Clock describe
    exactly the same historical bar sequence.
    """

    def __init__(
        self,
        feed: HistoricalBarFeed,
        clock: SimulationClock,
        higher_timeframe_feeds: Mapping[
            Timeframe,
            HistoricalBarFeed,
        ]
        | None = None,
        higher_timeframe_bar_limits: Mapping[
            Timeframe,
            int,
        ]
        | None = None,
    ) -> None:
        if not isinstance(
            feed,
            HistoricalBarFeed,
        ):
            raise TypeError(
                "feed must be a HistoricalBarFeed"
            )

        if not isinstance(
            clock,
            SimulationClock,
        ):
            raise TypeError(
                "clock must be a SimulationClock"
            )

        if (
            feed.config.timeframe
            != clock.timeframe
        ):
            raise ValueError(
                "feed and clock must use the same timeframe"
            )

        if (
            feed.bar_starts
            != clock.bar_starts
        ):
            raise ValueError(
                "feed and clock must use the same bar sequence"
            )

        self._feed = feed
        self._clock = clock
        self._higher_timeframe_feeds = (
            self._validate_higher_timeframe_feeds(
                higher_timeframe_feeds
            )
        )
        self._higher_timeframe_bar_limits = (
            self._validate_higher_timeframe_bar_limits(
                higher_timeframe_bar_limits
            )
        )
        self._higher_timeframe_close_times = {
            timeframe: tuple(
                bar.time + _TIMEFRAME_DURATIONS[timeframe]
                for bar in feed.bars
            )
            for timeframe, feed in (
                self._higher_timeframe_feeds.items()
            )
        }

    def build(
        self,
        event: ClockEvent,
        *,
        closed_bar_limit: int | None = None,
    ) -> BacktestContext:
        """
        Build the information snapshot that is safe to expose
        at the supplied simulation event.
        """

        if not isinstance(
            event,
            ClockEvent,
        ):
            raise TypeError(
                "event must be a ClockEvent"
            )

        if (
            event.bar_index < 0
            or event.bar_index >= len(self._feed)
        ):
            raise ValueError(
                "event bar_index is outside the feed"
            )

        if closed_bar_limit is not None:
            if (
                not isinstance(closed_bar_limit, int)
                or isinstance(closed_bar_limit, bool)
                or closed_bar_limit <= 0
            ):
                raise ValueError(
                    "closed_bar_limit must be a positive "
                    "integer or None"
                )

        bar = self._feed.bars[
            event.bar_index
        ]

        expected_close = (
            self._clock.bar_close_time(
                bar.time
            )
        )

        if event.bar_start != bar.time:
            raise ValueError(
                "event bar_start does not match feed bar"
            )

        if event.bar_close != expected_close:
            raise ValueError(
                "event bar_close does not match timeframe"
            )

        if event.phase == SimulationPhase.BAR_OPEN:
            if event.timestamp != bar.time:
                raise ValueError(
                    "BAR_OPEN timestamp must equal bar_start"
                )

            return BacktestContext(
                current_time=event.timestamp,
                phase=event.phase,
                current_bar_index=event.bar_index,
                current_bar=None,
                closed_bars=self._closed_bars(
                    end_index=event.bar_index,
                    closed_bar_limit=closed_bar_limit,
                ),
                timeframe_bars=self._higher_timeframe_bars(
                    timestamp=event.timestamp,
                ),
            )

        if event.phase == SimulationPhase.BAR_CLOSE:
            if event.timestamp != expected_close:
                raise ValueError(
                    "BAR_CLOSE timestamp must equal bar_close"
                )

            return BacktestContext(
                current_time=event.timestamp,
                phase=event.phase,
                current_bar_index=event.bar_index,
                current_bar=bar,
                closed_bars=self._closed_bars(
                    end_index=event.bar_index + 1,
                    closed_bar_limit=closed_bar_limit,
                ),
                timeframe_bars=self._higher_timeframe_bars(
                    timestamp=event.timestamp,
                ),
            )

        raise ValueError(
            f"unsupported simulation phase: {event.phase}"
        )

    def _closed_bars(
        self,
        *,
        end_index: int,
        closed_bar_limit: int | None,
    ) -> tuple[MarketBar, ...]:
        if closed_bar_limit is None:
            start_index = 0

        else:
            start_index = max(
                0,
                end_index - closed_bar_limit,
            )

        return self._feed.bars[
            start_index:end_index
        ]

    def _higher_timeframe_bars(
        self,
        *,
        timestamp: datetime,
    ) -> dict[Timeframe, tuple[MarketBar, ...]]:
        result = {}

        for timeframe, feed in self._higher_timeframe_feeds.items():
            end_index = bisect_right(
                self._higher_timeframe_close_times[timeframe],
                timestamp,
            )

            limit = self._higher_timeframe_bar_limits.get(
                timeframe
            )

            start_index = (
                0
                if limit is None
                else max(
                    0,
                    end_index - limit,
                )
            )

            result[timeframe] = feed.bars[
                start_index:end_index
            ]

        return result

    def _validate_higher_timeframe_feeds(
        self,
        feeds: Mapping[
            Timeframe,
            HistoricalBarFeed,
        ]
        | None,
    ) -> Mapping[Timeframe, HistoricalBarFeed]:
        if feeds is None:
            return MappingProxyType({})

        if not isinstance(
            feeds,
            Mapping,
        ):
            raise TypeError(
                "higher_timeframe_feeds must be a mapping"
            )

        normalized = {}

        for timeframe, feed in feeds.items():
            if not isinstance(
                timeframe,
                Timeframe,
            ):
                raise TypeError(
                    "higher_timeframe_feeds keys must be Timeframe "
                    "values"
                )

            if timeframe == self._clock.timeframe:
                raise ValueError(
                    "higher_timeframe_feeds cannot include the "
                    "base timeframe"
                )

            if timeframe not in _TIMEFRAME_DURATIONS:
                raise ValueError(
                    f"unsupported higher timeframe: {timeframe}"
                )

            if not isinstance(
                feed,
                HistoricalBarFeed,
            ):
                raise TypeError(
                    "higher_timeframe_feeds values must be "
                    "HistoricalBarFeed objects"
                )

            if feed.config.symbol != self._feed.config.symbol:
                raise ValueError(
                    "higher timeframe feed symbol must match base "
                    "feed"
                )

            if feed.config.timeframe != timeframe:
                raise ValueError(
                    "higher timeframe feed config must match "
                    "mapping key"
                )

            normalized[timeframe] = feed

        return MappingProxyType(normalized)

    @staticmethod
    def _validate_higher_timeframe_bar_limits(
        limits: Mapping[
            Timeframe,
            int,
        ]
        | None,
    ) -> Mapping[Timeframe, int]:
        if limits is None:
            return MappingProxyType({})

        if not isinstance(
            limits,
            Mapping,
        ):
            raise TypeError(
                "higher_timeframe_bar_limits must be a mapping"
            )

        normalized = {}

        for timeframe, limit in limits.items():
            if not isinstance(
                timeframe,
                Timeframe,
            ):
                raise TypeError(
                    "higher_timeframe_bar_limits keys must be "
                    "Timeframe values"
                )

            if (
                not isinstance(limit, int)
                or isinstance(limit, bool)
                or limit <= 0
            ):
                raise ValueError(
                    "higher_timeframe_bar_limits values must be "
                    "positive integers"
                )

            normalized[timeframe] = limit

        return MappingProxyType(normalized)
