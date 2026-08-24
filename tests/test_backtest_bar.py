from datetime import datetime, timedelta, timezone

import pytest

from backtest.models.bar import MarketBar


def utc_time() -> datetime:
    return datetime(
        2026,
        8,
        8,
        10,
        0,
        tzinfo=timezone.utc,
    )


def test_market_bar_is_created_with_valid_data():
    bar = MarketBar(
        time=utc_time(),
        open=1.1600,
        high=1.1620,
        low=1.1590,
        close=1.1610,
        tick_volume=1200,
        complete=True,
    )

    assert bar.time == utc_time()

    assert bar.open == 1.1600
    assert bar.high == 1.1620
    assert bar.low == 1.1590
    assert bar.close == 1.1610

    assert bar.tick_volume == 1200
    assert bar.complete is True


def test_market_bar_complete_defaults_to_true():
    bar = MarketBar(
        time=utc_time(),
        open=1.1600,
        high=1.1620,
        low=1.1590,
        close=1.1610,
        tick_volume=1200,
    )

    assert bar.complete is True


def test_market_bar_allows_zero_tick_volume():
    bar = MarketBar(
        time=utc_time(),
        open=1.1600,
        high=1.1620,
        low=1.1590,
        close=1.1610,
        tick_volume=0,
    )

    assert bar.tick_volume == 0


def test_market_bar_requires_timezone_aware_time():
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        MarketBar(
            time=datetime(
                2026,
                8,
                8,
                10,
                0,
            ),
            open=1.1600,
            high=1.1620,
            low=1.1590,
            close=1.1610,
            tick_volume=1200,
        )


def test_market_bar_requires_utc_time():
    non_utc = timezone(
        timedelta(hours=-3)
    )

    with pytest.raises(
        ValueError,
        match="UTC",
    ):
        MarketBar(
            time=datetime(
                2026,
                8,
                8,
                10,
                0,
                tzinfo=non_utc,
            ),
            open=1.1600,
            high=1.1620,
            low=1.1590,
            close=1.1610,
            tick_volume=1200,
        )


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("open", 0),
        ("open", -1),
        ("open", float("inf")),
        ("open", float("-inf")),
        ("open", float("nan")),

        ("high", 0),
        ("high", -1),
        ("high", float("inf")),
        ("high", float("-inf")),
        ("high", float("nan")),

        ("low", 0),
        ("low", -1),
        ("low", float("inf")),
        ("low", float("-inf")),
        ("low", float("nan")),

        ("close", 0),
        ("close", -1),
        ("close", float("inf")),
        ("close", float("-inf")),
        ("close", float("nan")),
    ],
)
def test_market_bar_requires_positive_finite_prices(
    field_name,
    field_value,
):
    kwargs = {
        "time": utc_time(),
        "open": 1.1600,
        "high": 1.1620,
        "low": 1.1590,
        "close": 1.1610,
        "tick_volume": 1200,
    }

    kwargs[field_name] = field_value

    with pytest.raises(
        ValueError,
        match=field_name,
    ):
        MarketBar(**kwargs)


def test_market_bar_high_must_contain_ohlc_prices():
    with pytest.raises(
        ValueError,
        match="high",
    ):
        MarketBar(
            time=utc_time(),
            open=1.1600,
            high=1.1590,
            low=1.1580,
            close=1.1610,
            tick_volume=1200,
        )


def test_market_bar_low_must_contain_ohlc_prices():
    with pytest.raises(
        ValueError,
        match="low",
    ):
        MarketBar(
            time=utc_time(),
            open=1.1600,
            high=1.1630,
            low=1.1610,
            close=1.1620,
            tick_volume=1200,
        )


@pytest.mark.parametrize(
    "tick_volume",
    [
        -1,
        1.5,
        True,
    ],
)
def test_market_bar_requires_non_negative_integer_tick_volume(
    tick_volume,
):
    with pytest.raises(
        ValueError,
        match="tick_volume",
    ):
        MarketBar(
            time=utc_time(),
            open=1.1600,
            high=1.1620,
            low=1.1590,
            close=1.1610,
            tick_volume=tick_volume,
        )


def test_market_bar_requires_boolean_complete():
    with pytest.raises(
        TypeError,
        match="complete",
    ):
        MarketBar(
            time=utc_time(),
            open=1.1600,
            high=1.1620,
            low=1.1590,
            close=1.1610,
            tick_volume=1200,
            complete=1,  # type: ignore[arg-type]
        )


def test_market_bar_is_immutable():
    bar = MarketBar(
        time=utc_time(),
        open=1.1600,
        high=1.1620,
        low=1.1590,
        close=1.1610,
        tick_volume=1200,
    )

    with pytest.raises(AttributeError):
        bar.close = 1.1700  # type: ignore[misc]