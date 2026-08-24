from datetime import datetime, timezone

import pandas as pd
import pytest

from backtest.clock import ClockEvent, SimulationClock
from backtest.context import BacktestContext, BacktestContextBuilder
from backtest.feed import HistoricalBarFeed
from backtest.models import BacktestConfig, MarketBar, SimulationPhase, Timeframe


def utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 24, hour, minute, tzinfo=timezone.utc)


def feed_and_clock(times: list[datetime] | None = None) -> tuple[HistoricalBarFeed, SimulationClock]:
    starts = times or [utc(10), utc(10, 15), utc(10, 30)]
    data = pd.DataFrame({"time": starts, "open": [1.10 + index / 1000 for index in range(len(starts))], "high": [1.11 + index / 1000 for index in range(len(starts))], "low": [1.09 + index / 1000 for index in range(len(starts))], "close": [1.105 + index / 1000 for index in range(len(starts))], "tick_volume": [100] * len(starts)})
    config = BacktestConfig("EURUSD", Timeframe.M15, utc(9), utc(12), 10_000)
    feed = HistoricalBarFeed(data, config)
    return feed, SimulationClock(feed.bar_starts, Timeframe.M15)


def test_first_open_exposes_no_ohlc_information():
    feed, clock = feed_and_clock()
    context = BacktestContextBuilder(feed, clock).build(next(clock.events()))
    assert context.phase is SimulationPhase.BAR_OPEN
    assert context.current_bar is None
    assert context.closed_bars == ()
    assert context.last_closed_bar is None


def test_close_exposes_only_the_bar_that_has_closed():
    feed, clock = feed_and_clock()
    context = BacktestContextBuilder(feed, clock).build(list(clock.events())[1])
    assert context.current_time == utc(10, 15)
    assert context.current_bar == feed.bars[0]
    assert context.closed_bars == (feed.bars[0],)


def test_next_open_never_exposes_its_unfinished_ohlc():
    feed, clock = feed_and_clock()
    context = BacktestContextBuilder(feed, clock).build(list(clock.events())[2])
    assert context.current_time == utc(10, 15)
    assert context.current_bar is None
    assert context.closed_bars == (feed.bars[0],)
    assert feed.bars[1] not in context.closed_bars


def test_every_visible_bar_was_closed_at_or_before_simulation_time():
    feed, clock = feed_and_clock()
    builder = BacktestContextBuilder(feed, clock)
    for event in clock.events():
        context = builder.build(event)
        assert all(bar.time + clock.duration <= context.current_time for bar in context.closed_bars)
        assert all(bar.time + clock.duration <= context.current_time for bar in (context.current_bar,) if bar is not None)


def test_future_bars_are_never_visible_even_at_later_gaps():
    feed, clock = feed_and_clock([utc(10), utc(10, 30)])
    context = BacktestContextBuilder(feed, clock).build(list(clock.events())[2])
    assert context.current_time == utc(10, 30)
    assert context.closed_bars == (feed.bars[0],)
    assert feed.bars[1] not in context.closed_bars


def test_context_does_not_expose_mutable_source_or_feed():
    feed, clock = feed_and_clock()
    context = BacktestContextBuilder(feed, clock).build(next(clock.events()))
    assert not hasattr(context, "dataframe")
    assert not hasattr(context, "feed")
    assert isinstance(context.closed_bars, tuple)
    with pytest.raises(AttributeError):
        context.current_time = utc(12)  # type: ignore[misc]


def test_context_can_limit_history_without_relaxing_causality():
    feed, clock = feed_and_clock()
    context = BacktestContextBuilder(feed, clock).build(list(clock.events())[5], closed_bar_limit=2)
    assert context.closed_bars == (feed.bars[1], feed.bars[2])


@pytest.mark.parametrize("limit", [0, -1, True, "2"])
def test_context_rejects_invalid_history_limit(limit):
    feed, clock = feed_and_clock()
    with pytest.raises(ValueError, match="closed_bar_limit"):
        BacktestContextBuilder(feed, clock).build(list(clock.events())[1], closed_bar_limit=limit)


def test_builder_rejects_mismatched_clock_and_feed():
    feed, _ = feed_and_clock()
    other = SimulationClock([utc(10), utc(10, 15)], Timeframe.M15)
    with pytest.raises(ValueError, match="same bar sequence"):
        BacktestContextBuilder(feed, other)


def test_builder_rejects_tampered_event_that_could_reveal_future_data():
    feed, clock = feed_and_clock()
    event = ClockEvent(utc(10, 15), SimulationPhase.BAR_CLOSE, 0, utc(10), utc(10, 20))
    with pytest.raises(ValueError, match="event does not match"):
        BacktestContextBuilder(feed, clock).build(event)


def test_direct_context_rejects_current_bar_at_open():
    bar = MarketBar(utc(10), 1.1, 1.11, 1.09, 1.105, 100)
    with pytest.raises(ValueError, match="current_bar"):
        BacktestContext(utc(10), SimulationPhase.BAR_OPEN, 0, bar, ())


def test_direct_context_requires_current_bar_to_be_latest_closed_bar():
    first = MarketBar(utc(10), 1.1, 1.11, 1.09, 1.105, 100)
    second = MarketBar(utc(10, 15), 1.2, 1.21, 1.19, 1.205, 100)
    with pytest.raises(ValueError, match="latest closed"):
        BacktestContext(utc(10, 30), SimulationPhase.BAR_CLOSE, 1, first, (first, second))
