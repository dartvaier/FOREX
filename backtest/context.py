from dataclasses import dataclass
from datetime import datetime, timedelta

from backtest.clock import ClockEvent, SimulationClock
from backtest.feed import HistoricalBarFeed
from backtest.models.bar import MarketBar
from backtest.models.enums import SimulationPhase


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

    def build(
        self,
        event: ClockEvent,
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
                closed_bars=self._feed.bars[
                    :event.bar_index
                ],
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
                closed_bars=self._feed.bars[
                    :event.bar_index + 1
                ],
            )

        raise ValueError(
            f"unsupported simulation phase: {event.phase}"
        )