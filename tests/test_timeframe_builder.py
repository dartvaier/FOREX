from pathlib import Path

import pandas as pd
import pytest

from data.timeframe_builder import TimeframeBuilder


SOURCE = Path(
    "data/raw/EURUSD/M15.parquet"
)

if not SOURCE.exists():
    pytest.skip(
        "dataset historico local nao disponivel",
        allow_module_level=True,
    )


def get_source():
    return pd.read_parquet(SOURCE)


def test_h1_is_created():
    df = get_source()

    builder = TimeframeBuilder()

    h1 = builder.build(
        df,
        "H1",
    )

    assert not h1.empty


def test_h4_is_created():
    df = get_source()

    builder = TimeframeBuilder()

    h4 = builder.build(
        df,
        "H4",
    )

    assert not h4.empty


def test_h1_complete_bars_have_four_m15():
    df = get_source()

    builder = TimeframeBuilder()

    h1 = builder.build(
        df,
        "H1",
    )

    complete = h1[
        h1["complete"]
    ]

    assert (
        complete["source_bar_count"] == 4
    ).all()


def test_h4_complete_bars_have_sixteen_m15():
    df = get_source()

    builder = TimeframeBuilder()

    h4 = builder.build(
        df,
        "H4",
    )

    complete = h4[
        h4["complete"]
    ]

    assert (
        complete["source_bar_count"] == 16
    ).all()


def test_h1_alignment():
    df = get_source()

    builder = TimeframeBuilder()

    h1 = builder.build(
        df,
        "H1",
    )

    assert (
        h1["time"].dt.minute == 0
    ).all()


def test_h4_alignment():
    df = get_source()

    builder = TimeframeBuilder()

    h4 = builder.build(
        df,
        "H4",
    )

    assert (
        h4["time"].dt.minute == 0
    ).all()

    assert (
        h4["time"].dt.hour % 4 == 0
    ).all()


def test_generated_timeframes_are_utc():
    df = get_source()

    builder = TimeframeBuilder()

    for timeframe in [
        "H1",
        "H4",
    ]:

        result = builder.build(
            df,
            timeframe,
        )

        assert (
            str(result["time"].dt.tz)
            == "UTC"
        )


def test_generated_ohlc_integrity():
    df = get_source()

    builder = TimeframeBuilder()

    for timeframe in [
        "H1",
        "H4",
    ]:

        result = builder.build(
            df,
            timeframe,
        )

        assert (
            result["high"]
            >= result["low"]
        ).all()

        assert (
            result["high"]
            >= result["open"]
        ).all()

        assert (
            result["high"]
            >= result["close"]
        ).all()

        assert (
            result["low"]
            <= result["open"]
        ).all()

        assert (
            result["low"]
            <= result["close"]
        ).all()
