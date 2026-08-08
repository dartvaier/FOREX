from pathlib import Path

import pandas as pd


FILE = Path(
    "data/raw/EURUSD/M15.parquet"
)


def load_data():
    return pd.read_parquet(FILE)


def test_historical_file_exists():
    assert FILE.exists()


def test_historical_dataset_not_empty():
    df = load_data()

    assert not df.empty


def test_historical_timestamps_are_unique():
    df = load_data()

    assert df["time"].duplicated().sum() == 0


def test_historical_timestamps_are_sorted():
    df = load_data()

    assert df["time"].is_monotonic_increasing


def test_historical_data_is_utc():
    df = load_data()

    assert str(df["time"].dt.tz) == "UTC"


def test_historical_has_no_nulls():
    df = load_data()

    assert df.isna().sum().sum() == 0


def test_historical_ohlc_integrity():
    df = load_data()

    assert (df["high"] >= df["low"]).all()

    assert (
        df["high"] >= df["open"]
    ).all()

    assert (
        df["high"] >= df["close"]
    ).all()

    assert (
        df["low"] <= df["open"]
    ).all()

    assert (
        df["low"] <= df["close"]
    ).all()


def test_historical_prices_are_positive():
    df = load_data()

    columns = [
        "open",
        "high",
        "low",
        "close",
    ]

    for column in columns:
        assert (df[column] > 0).all()