from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from backtest.feed import HistoricalBarFeed
from backtest.models import (
    BacktestConfig,
    MarketBar,
    Timeframe,
)


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


def make_config(
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    timeframe: Timeframe = Timeframe.M15,
    allow_incomplete_bars: bool = False,
) -> BacktestConfig:
    return BacktestConfig(
        symbol="EURUSD",
        timeframe=timeframe,
        date_from=(
            date_from
            if date_from is not None
            else utc_time(10, 0)
        ),
        date_to=(
            date_to
            if date_to is not None
            else utc_time(12, 0)
        ),
        initial_capital=10000.0,
        allow_incomplete_bars=allow_incomplete_bars,
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


def test_feed_builds_market_bars():
    dataframe = make_dataframe()

    feed = HistoricalBarFeed(
        dataframe=dataframe,
        config=make_config(),
    )

    assert feed.bar_count == 3
    assert len(feed) == 3

    assert all(
        isinstance(bar, MarketBar)
        for bar in feed
    )

    assert feed.bars[0].time == utc_time(10, 0)
    assert feed.bars[1].time == utc_time(10, 15)
    assert feed.bars[2].time == utc_time(10, 30)


def test_feed_reports_input_row_count():
    dataframe = make_dataframe()

    feed = HistoricalBarFeed(
        dataframe=dataframe,
        config=make_config(),
    )

    assert feed.input_row_count == 3


def test_feed_defaults_missing_complete_column_to_true():
    feed = HistoricalBarFeed(
        dataframe=make_dataframe(),
        config=make_config(),
    )

    assert all(
        bar.complete is True
        for bar in feed
    )


def test_feed_applies_half_open_date_range():
    dataframe = make_dataframe()

    feed = HistoricalBarFeed(
        dataframe=dataframe,
        config=make_config(
            date_from=utc_time(10, 15),
            date_to=utc_time(10, 30),
        ),
    )

    assert feed.bar_starts == (
        utc_time(10, 15),
    )


def test_feed_filters_incomplete_bars_by_default():
    dataframe = make_dataframe()

    dataframe["complete"] = [
        True,
        False,
        True,
    ]

    feed = HistoricalBarFeed(
        dataframe=dataframe,
        config=make_config(
            timeframe=Timeframe.H1,
        ),
    )

    assert feed.bar_starts == (
        utc_time(10, 0),
        utc_time(10, 30),
    )

    assert all(
        bar.complete
        for bar in feed
    )


def test_feed_can_preserve_incomplete_bars():
    dataframe = make_dataframe()

    dataframe["complete"] = [
        True,
        False,
        True,
    ]

    feed = HistoricalBarFeed(
        dataframe=dataframe,
        config=make_config(
            timeframe=Timeframe.H1,
            allow_incomplete_bars=True,
        ),
    )

    assert feed.bar_count == 3

    assert [
        bar.complete
        for bar in feed
    ] == [
        True,
        False,
        True,
    ]


def test_feed_preserves_historical_gaps():
    dataframe = pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2026-08-08T10:00:00Z",
                    "2026-08-08T10:15:00Z",
                    "2026-08-08T10:45:00Z",
                ],
                utc=True,
            ),
            "open": [
                1.1600,
                1.1610,
                1.1630,
            ],
            "high": [
                1.1620,
                1.1630,
                1.1650,
            ],
            "low": [
                1.1590,
                1.1600,
                1.1620,
            ],
            "close": [
                1.1610,
                1.1620,
                1.1640,
            ],
            "tick_volume": [
                1000,
                1100,
                1300,
            ],
        }
    )

    feed = HistoricalBarFeed(
        dataframe=dataframe,
        config=make_config(),
    )

    assert feed.bar_starts == (
        utc_time(10, 0),
        utc_time(10, 15),
        utc_time(10, 45),
    )

    assert utc_time(10, 30) not in feed.bar_starts


def test_feed_ignores_non_market_bar_columns():
    dataframe = make_dataframe()

    dataframe["spread"] = [
        2,
        7,
        0,
    ]

    dataframe["real_volume"] = [
        100,
        0,
        999,
    ]

    feed = HistoricalBarFeed(
        dataframe=dataframe,
        config=make_config(),
    )

    bar = feed.bars[0]

    assert not hasattr(bar, "spread")
    assert not hasattr(bar, "real_volume")


def test_feed_does_not_modify_source_dataframe():
    dataframe = make_dataframe()
    original = dataframe.copy(deep=True)

    HistoricalBarFeed(
        dataframe=dataframe,
        config=make_config(),
    )

    pd.testing.assert_frame_equal(
        dataframe,
        original,
    )


def test_feed_bars_are_returned_as_tuple():
    feed = HistoricalBarFeed(
        dataframe=make_dataframe(),
        config=make_config(),
    )

    assert isinstance(feed.bars, tuple)
    assert isinstance(feed.bar_starts, tuple)


def test_feed_requires_dataframe():
    with pytest.raises(
        TypeError,
        match="DataFrame",
    ):
        HistoricalBarFeed(
            dataframe=[],  # type: ignore[arg-type]
            config=make_config(),
        )


def test_feed_requires_backtest_config():
    with pytest.raises(
        TypeError,
        match="BacktestConfig",
    ):
        HistoricalBarFeed(
            dataframe=make_dataframe(),
            config=None,  # type: ignore[arg-type]
        )


def test_feed_rejects_empty_dataframe():
    dataframe = pd.DataFrame(
        columns=[
            "time",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
        ]
    )

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        HistoricalBarFeed(
            dataframe=dataframe,
            config=make_config(),
        )


def test_feed_rejects_missing_required_columns():
    dataframe = make_dataframe().drop(
        columns=["tick_volume"]
    )

    with pytest.raises(
        ValueError,
        match="tick_volume",
    ):
        HistoricalBarFeed(
            dataframe=dataframe,
            config=make_config(),
        )


def test_feed_rejects_duplicate_timestamps():
    dataframe = make_dataframe()

    dataframe.loc[
        1,
        "time",
    ] = dataframe.loc[
        0,
        "time",
    ]

    with pytest.raises(
        ValueError,
        match="duplicate",
    ):
        HistoricalBarFeed(
            dataframe=dataframe,
            config=make_config(),
        )


def test_feed_rejects_unsorted_timestamps():
    dataframe = make_dataframe()

    dataframe = dataframe.iloc[
        [1, 0, 2]
    ].reset_index(drop=True)

    with pytest.raises(
        ValueError,
        match="strictly increasing",
    ):
        HistoricalBarFeed(
            dataframe=dataframe,
            config=make_config(),
        )


def test_feed_rejects_naive_timestamps():
    dataframe = make_dataframe()

    dataframe["time"] = [
        datetime(2026, 8, 8, 10, 0),
        datetime(2026, 8, 8, 10, 15),
        datetime(2026, 8, 8, 10, 30),
    ]

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        HistoricalBarFeed(
            dataframe=dataframe,
            config=make_config(),
        )


def test_feed_rejects_non_utc_timestamps():
    dataframe = make_dataframe()

    non_utc = timezone(
        timedelta(hours=-3)
    )

    dataframe["time"] = [
        datetime(
            2026,
            8,
            8,
            10,
            0,
            tzinfo=non_utc,
        ),
        datetime(
            2026,
            8,
            8,
            10,
            15,
            tzinfo=non_utc,
        ),
        datetime(
            2026,
            8,
            8,
            10,
            30,
            tzinfo=non_utc,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="UTC",
    ):
        HistoricalBarFeed(
            dataframe=dataframe,
            config=make_config(),
        )


def test_feed_rejects_invalid_complete_values():
    dataframe = make_dataframe()

    dataframe["complete"] = [
        True,
        1,
        False,
    ]

    with pytest.raises(
        TypeError,
        match="complete",
    ):
        HistoricalBarFeed(
            dataframe=dataframe,
            config=make_config(
                allow_incomplete_bars=True,
            ),
        )


def test_feed_rejects_invalid_tick_volume():
    dataframe = make_dataframe()

    dataframe["tick_volume"] = [
        1000,
        -1,
        1200,
    ]

    with pytest.raises(
        ValueError,
        match="tick_volume",
    ):
        HistoricalBarFeed(
            dataframe=dataframe,
            config=make_config(),
        )


def test_feed_fails_when_range_contains_no_bars():
    dataframe = make_dataframe()

    with pytest.raises(
        ValueError,
        match="no bars available",
    ):
        HistoricalBarFeed(
            dataframe=dataframe,
            config=make_config(
                date_from=utc_time(15, 0),
                date_to=utc_time(16, 0),
            ),
        )