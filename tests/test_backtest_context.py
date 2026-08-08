from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from backtest.clock import (
    ClockEvent,
    SimulationClock,
)
from backtest.context import (
    BacktestContext,
    BacktestContextBuilder,
)
from backtest.feed import HistoricalBarFeed
from backtest.models import (
    BacktestConfig,
    MarketBar,
    Timeframe,
)
from backtest.models.enums import SimulationPhase


def utc_time(
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026,
        8,
        8,
        hour,
        minute,
        tzinfo=timezone.utc,
    )


def make_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2026-08-08T10:00:00Z",
                    "2026-08-08T10:15:00Z",
                    "2026-08-08T10:30:00Z",
                ],
                utc=True,
            ),
            "open": [
                1.1600,
                1.1610,
                1.1620,
            ],
            "high": [
                1.1620,
                1.1630,
                1.1640,
            ],
            "low": [
                1.1590,
                1.1600,
                1.1610,
            ],
            "close": [
                1.1610,
                1.1620,
                1.1630,
            ],
            "tick_volume": [
                1000,
                1100,
                1200,
            ],
        }
    )


def make_config(
    timeframe: Timeframe = Timeframe.M15,
) -> BacktestConfig:
    return BacktestConfig(
        symbol="EURUSD",
        timeframe=timeframe,
        date_from=utc_time(10, 0),
        date_to=utc_time(12, 0),
        initial_capital=10000.0,
    )


def make_feed_and_clock():
    feed = HistoricalBarFeed(
        dataframe=make_dataframe(),
        config=make_config(),
    )

    clock = SimulationClock(
        bar_starts=feed.bar_starts,
        timeframe=feed.config.timeframe,
    )

    return feed, clock


def test_first_bar_open_exposes_no_market_bar():
    feed, clock = make_feed_and_clock()

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    event = list(clock.events())[0]

    context = builder.build(event)

    assert context.phase == SimulationPhase.BAR_OPEN
    assert context.current_time == utc_time(10, 0)

    assert context.current_bar is None
    assert context.closed_bars == ()
    assert context.last_closed_bar is None


def test_first_bar_close_exposes_first_bar():
    feed, clock = make_feed_and_clock()

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    event = list(clock.events())[1]

    context = builder.build(event)

    assert context.phase == SimulationPhase.BAR_CLOSE
    assert context.current_time == utc_time(10, 15)

    assert context.current_bar == feed.bars[0]

    assert context.closed_bars == (
        feed.bars[0],
    )

    assert context.last_closed_bar == feed.bars[0]


def test_next_bar_open_does_not_expose_current_future_ohlc():
    feed, clock = make_feed_and_clock()

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    events = list(clock.events())

    first_close = builder.build(
        events[1]
    )

    second_open = builder.build(
        events[2]
    )

    assert (
        first_close.current_time
        == second_open.current_time
        == utc_time(10, 15)
    )

    assert (
        first_close.phase
        == SimulationPhase.BAR_CLOSE
    )

    assert (
        second_open.phase
        == SimulationPhase.BAR_OPEN
    )

    assert second_open.current_bar is None

    assert second_open.closed_bars == (
        feed.bars[0],
    )

    assert feed.bars[1] not in second_open.closed_bars


def test_second_bar_close_makes_second_bar_available():
    feed, clock = make_feed_and_clock()

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    event = list(clock.events())[3]

    context = builder.build(event)

    assert context.current_time == utc_time(10, 30)

    assert context.current_bar == feed.bars[1]

    assert context.closed_bars == (
        feed.bars[0],
        feed.bars[1],
    )


def test_context_never_exposes_future_bars():
    feed, clock = make_feed_and_clock()

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    for event in clock.events():
        context = builder.build(event)

        for bar in context.closed_bars:
            close_time = (
                bar.time
                + clock.duration
            )

            assert close_time <= context.current_time

        future_bars = [
            bar
            for bar in feed.bars
            if (
                bar.time
                + clock.duration
                > context.current_time
            )
        ]

        for future_bar in future_bars:
            assert future_bar not in context.closed_bars


def test_bar_open_never_exposes_opening_bar_object():
    feed, clock = make_feed_and_clock()

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    for event in clock.events():
        if event.phase != SimulationPhase.BAR_OPEN:
            continue

        context = builder.build(event)

        assert context.current_bar is None

        opening_bar = feed.bars[
            event.bar_index
        ]

        assert opening_bar not in context.closed_bars


def test_context_does_not_expose_dataframe_or_feed():
    feed, clock = make_feed_and_clock()

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    context = builder.build(
        next(clock.events())
    )

    assert not hasattr(context, "dataframe")
    assert not hasattr(context, "feed")
    assert not hasattr(context, "future_bars")


def test_context_closed_bars_are_tuple():
    feed, clock = make_feed_and_clock()

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    context = builder.build(
        list(clock.events())[1]
    )

    assert isinstance(
        context.closed_bars,
        tuple,
    )


def test_context_is_immutable():
    feed, clock = make_feed_and_clock()

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    context = builder.build(
        list(clock.events())[1]
    )

    with pytest.raises(AttributeError):
        context.current_time = utc_time(12, 0)  # type: ignore[misc]


def test_context_builder_requires_feed():
    _, clock = make_feed_and_clock()

    with pytest.raises(
        TypeError,
        match="HistoricalBarFeed",
    ):
        BacktestContextBuilder(
            feed=None,  # type: ignore[arg-type]
            clock=clock,
        )


def test_context_builder_requires_clock():
    feed, _ = make_feed_and_clock()

    with pytest.raises(
        TypeError,
        match="SimulationClock",
    ):
        BacktestContextBuilder(
            feed=feed,
            clock=None,  # type: ignore[arg-type]
        )


def test_context_builder_rejects_different_timeframe():
    feed, _ = make_feed_and_clock()

    clock = SimulationClock(
        bar_starts=[
            feed.bar_starts[0],
        ],
        timeframe=Timeframe.H1,
    )

    with pytest.raises(
        ValueError,
        match="same timeframe",
    ):
        BacktestContextBuilder(
            feed=feed,
            clock=clock,
        )


def test_context_builder_rejects_different_bar_sequence():
    feed, _ = make_feed_and_clock()

    clock = SimulationClock(
        bar_starts=(
            utc_time(10, 0),
            utc_time(10, 15),
        ),
        timeframe=Timeframe.M15,
    )

    with pytest.raises(
        ValueError,
        match="same bar sequence",
    ):
        BacktestContextBuilder(
            feed=feed,
            clock=clock,
        )


def test_context_builder_requires_clock_event():
    feed, clock = make_feed_and_clock()

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    with pytest.raises(
        TypeError,
        match="ClockEvent",
    ):
        builder.build(
            object()  # type: ignore[arg-type]
        )


def test_context_builder_rejects_event_outside_feed():
    feed, clock = make_feed_and_clock()

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    event = ClockEvent(
        timestamp=utc_time(11, 0),
        phase=SimulationPhase.BAR_OPEN,
        bar_index=99,
        bar_start=utc_time(11, 0),
        bar_close=utc_time(11, 15),
    )

    with pytest.raises(
        ValueError,
        match="bar_index",
    ):
        builder.build(event)


def test_context_builder_rejects_wrong_bar_start():
    feed, clock = make_feed_and_clock()

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    event = ClockEvent(
        timestamp=utc_time(10, 5),
        phase=SimulationPhase.BAR_OPEN,
        bar_index=0,
        bar_start=utc_time(10, 5),
        bar_close=utc_time(10, 20),
    )

    with pytest.raises(
        ValueError,
        match="bar_start",
    ):
        builder.build(event)


def test_context_builder_rejects_wrong_close_time():
    feed, clock = make_feed_and_clock()

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    event = ClockEvent(
        timestamp=utc_time(10, 20),
        phase=SimulationPhase.BAR_CLOSE,
        bar_index=0,
        bar_start=utc_time(10, 0),
        bar_close=utc_time(10, 20),
    )

    with pytest.raises(
        ValueError,
        match="bar_close",
    ):
        builder.build(event)


def test_gap_does_not_make_missing_bar_available():
    dataframe = pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2026-08-08T10:00:00Z",
                    "2026-08-08T10:30:00Z",
                ],
                utc=True,
            ),
            "open": [
                1.1600,
                1.1620,
            ],
            "high": [
                1.1620,
                1.1640,
            ],
            "low": [
                1.1590,
                1.1610,
            ],
            "close": [
                1.1610,
                1.1630,
            ],
            "tick_volume": [
                1000,
                1200,
            ],
        }
    )

    feed = HistoricalBarFeed(
        dataframe=dataframe,
        config=make_config(),
    )

    clock = SimulationClock(
        bar_starts=feed.bar_starts,
        timeframe=Timeframe.M15,
    )

    builder = BacktestContextBuilder(
        feed=feed,
        clock=clock,
    )

    events = list(clock.events())

    context = builder.build(
        events[2]
    )

    assert context.current_time == utc_time(10, 30)
    assert context.phase == SimulationPhase.BAR_OPEN

    assert context.closed_bars == (
        feed.bars[0],
    )

    assert all(
        bar.time != utc_time(10, 15)
        for bar in context.closed_bars
    )


def test_direct_context_rejects_current_bar_at_open():
    bar = MarketBar(
        time=utc_time(10, 0),
        open=1.1600,
        high=1.1620,
        low=1.1590,
        close=1.1610,
        tick_volume=1000,
    )

    with pytest.raises(
        ValueError,
        match="current_bar",
    ):
        BacktestContext(
            current_time=utc_time(10, 0),
            phase=SimulationPhase.BAR_OPEN,
            current_bar_index=0,
            current_bar=bar,
            closed_bars=(),
        )


def test_direct_context_requires_current_bar_at_close():
    with pytest.raises(
        ValueError,
        match="current_bar",
    ):
        BacktestContext(
            current_time=utc_time(10, 15),
            phase=SimulationPhase.BAR_CLOSE,
            current_bar_index=0,
            current_bar=None,
            closed_bars=(),
        )