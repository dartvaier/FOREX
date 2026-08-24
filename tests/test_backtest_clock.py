from datetime import datetime, timedelta, timezone

import pytest

from backtest.clock import (
    ClockEvent,
    SimulationClock,
)
from backtest.models.enums import (
    SimulationPhase,
    Timeframe,
)


def utc_datetime(
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


def test_m15_clock_duration():
    clock = SimulationClock(
        bar_starts=[
            utc_datetime(10, 0),
        ],
        timeframe=Timeframe.M15,
    )

    assert clock.duration == timedelta(minutes=15)


def test_h1_clock_duration():
    clock = SimulationClock(
        bar_starts=[
            utc_datetime(10, 0),
        ],
        timeframe=Timeframe.H1,
    )

    assert clock.duration == timedelta(hours=1)


def test_h4_clock_duration():
    clock = SimulationClock(
        bar_starts=[
            utc_datetime(8, 0),
        ],
        timeframe=Timeframe.H4,
    )

    assert clock.duration == timedelta(hours=4)


def test_clock_reports_bar_count():
    clock = SimulationClock(
        bar_starts=[
            utc_datetime(10, 0),
            utc_datetime(10, 15),
            utc_datetime(10, 30),
        ],
        timeframe=Timeframe.M15,
    )

    assert clock.bar_count == 3


def test_clock_calculates_bar_close_time():
    clock = SimulationClock(
        bar_starts=[
            utc_datetime(10, 0),
        ],
        timeframe=Timeframe.M15,
    )

    assert (
        clock.bar_close_time(
            utc_datetime(10, 0)
        )
        == utc_datetime(10, 15)
    )


def test_clock_generates_open_and_close_events():
    clock = SimulationClock(
        bar_starts=[
            utc_datetime(10, 0),
        ],
        timeframe=Timeframe.M15,
    )

    events = list(clock.events())

    assert len(events) == 2

    assert events[0] == ClockEvent(
        timestamp=utc_datetime(10, 0),
        phase=SimulationPhase.BAR_OPEN,
        bar_index=0,
        bar_start=utc_datetime(10, 0),
        bar_close=utc_datetime(10, 15),
    )

    assert events[1] == ClockEvent(
        timestamp=utc_datetime(10, 15),
        phase=SimulationPhase.BAR_CLOSE,
        bar_index=0,
        bar_start=utc_datetime(10, 0),
        bar_close=utc_datetime(10, 15),
    )


def test_contiguous_bars_close_before_next_open():
    clock = SimulationClock(
        bar_starts=[
            utc_datetime(10, 0),
            utc_datetime(10, 15),
        ],
        timeframe=Timeframe.M15,
    )

    events = list(clock.events())

    assert events[1].timestamp == utc_datetime(10, 15)
    assert events[1].phase == SimulationPhase.BAR_CLOSE

    assert events[2].timestamp == utc_datetime(10, 15)
    assert events[2].phase == SimulationPhase.BAR_OPEN

    assert events[1].bar_index == 0
    assert events[2].bar_index == 1


def test_clock_does_not_create_events_inside_gap():
    clock = SimulationClock(
        bar_starts=[
            utc_datetime(10, 0),
            utc_datetime(10, 30),
        ],
        timeframe=Timeframe.M15,
    )

    events = list(clock.events())

    assert [
        (event.timestamp, event.phase)
        for event in events
    ] == [
        (
            utc_datetime(10, 0),
            SimulationPhase.BAR_OPEN,
        ),
        (
            utc_datetime(10, 15),
            SimulationPhase.BAR_CLOSE,
        ),
        (
            utc_datetime(10, 30),
            SimulationPhase.BAR_OPEN,
        ),
        (
            utc_datetime(10, 45),
            SimulationPhase.BAR_CLOSE,
        ),
    ]


def test_clock_requires_non_empty_bar_starts():
    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        SimulationClock(
            bar_starts=[],
            timeframe=Timeframe.M15,
        )


def test_clock_requires_timeframe_enum():
    with pytest.raises(
        TypeError,
        match="Timeframe",
    ):
        SimulationClock(
            bar_starts=[
                utc_datetime(10, 0),
            ],
            timeframe="M15",  # type: ignore[arg-type]
        )


def test_clock_requires_timezone_aware_bar_starts():
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        SimulationClock(
            bar_starts=[
                datetime(
                    2026,
                    8,
                    8,
                    10,
                    0,
                ),
            ],
            timeframe=Timeframe.M15,
        )


def test_clock_requires_utc_bar_starts():
    non_utc = timezone(
        timedelta(hours=-3)
    )

    with pytest.raises(
        ValueError,
        match="UTC",
    ):
        SimulationClock(
            bar_starts=[
                datetime(
                    2026,
                    8,
                    8,
                    10,
                    0,
                    tzinfo=non_utc,
                ),
            ],
            timeframe=Timeframe.M15,
        )


def test_clock_requires_strictly_increasing_bar_starts():
    timestamp = utc_datetime(10, 0)

    with pytest.raises(
        ValueError,
        match="strictly increasing",
    ):
        SimulationClock(
            bar_starts=[
                timestamp,
                timestamp,
            ],
            timeframe=Timeframe.M15,
        )


def test_clock_rejects_unsorted_bar_starts():
    with pytest.raises(
        ValueError,
        match="strictly increasing",
    ):
        SimulationClock(
            bar_starts=[
                utc_datetime(10, 15),
                utc_datetime(10, 0),
            ],
            timeframe=Timeframe.M15,
        )


def test_clock_rejects_overlapping_bars():
    with pytest.raises(
        ValueError,
        match="overlap",
    ):
        SimulationClock(
            bar_starts=[
                utc_datetime(10, 0),
                utc_datetime(10, 5),
            ],
            timeframe=Timeframe.M15,
        )


def test_clock_event_is_immutable():
    clock = SimulationClock(
        bar_starts=[
            utc_datetime(10, 0),
        ],
        timeframe=Timeframe.M15,
    )

    event = next(clock.events())

    with pytest.raises(AttributeError):
        event.bar_index = 10  # type: ignore[misc]