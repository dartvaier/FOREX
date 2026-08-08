from datetime import timezone

import MetaTrader5 as mt5
import pytest

pytestmark = pytest.mark.integration

from broker.mt5_client import MT5Client
from data.market_data import MarketData


SYMBOL = "EURUSD"


@pytest.fixture
def market():
    """
    Cria conexão com MT5 para os testes
    e garante encerramento ao final.
    """

    client = MT5Client()
    client.connect()

    market_data = MarketData(client)

    yield market_data

    client.disconnect()


def test_current_quote_is_valid(market):
    quote = market.get_current_quote(SYMBOL)

    assert quote["symbol"] == SYMBOL

    assert quote["bid"] > 0
    assert quote["ask"] > 0

    # Ask nunca deve ficar abaixo do Bid.
    assert quote["ask"] >= quote["bid"]

    assert quote["point"] > 0
    assert quote["pip_size"] > 0

    assert quote["spread_points"] >= 0
    assert quote["spread_pips"] >= 0


def test_closed_bars_count(market):
    bars = market.get_closed_bars(
        symbol=SYMBOL,
        timeframe=mt5.TIMEFRAME_M15,
        count=100,
    )

    assert len(bars) == 100


def test_closed_bars_are_sorted(market):
    bars = market.get_closed_bars(
        symbol=SYMBOL,
        timeframe=mt5.TIMEFRAME_M15,
        count=100,
    )

    assert bars["time"].is_monotonic_increasing


def test_closed_bars_have_no_duplicate_timestamps(market):
    bars = market.get_closed_bars(
        symbol=SYMBOL,
        timeframe=mt5.TIMEFRAME_M15,
        count=100,
    )

    assert bars["time"].duplicated().sum() == 0


def test_closed_bars_are_utc(market):
    bars = market.get_closed_bars(
        symbol=SYMBOL,
        timeframe=mt5.TIMEFRAME_M15,
        count=100,
    )

    assert bars["time"].dt.tz is not None

    assert str(bars["time"].dt.tz) == "UTC"


def test_ohlc_integrity(market):
    bars = market.get_closed_bars(
        symbol=SYMBOL,
        timeframe=mt5.TIMEFRAME_M15,
        count=100,
    )

    # High deve ser >= Open e Close
    assert (bars["high"] >= bars["open"]).all()
    assert (bars["high"] >= bars["close"]).all()

    # Low deve ser <= Open e Close
    assert (bars["low"] <= bars["open"]).all()
    assert (bars["low"] <= bars["close"]).all()

    # High nunca pode ser menor que Low
    assert (bars["high"] >= bars["low"]).all()


def test_prices_are_positive(market):
    bars = market.get_closed_bars(
        symbol=SYMBOL,
        timeframe=mt5.TIMEFRAME_M15,
        count=100,
    )

    price_columns = [
        "open",
        "high",
        "low",
        "close",
    ]

    for column in price_columns:
        assert (bars[column] > 0).all()


def test_tick_volume_is_non_negative(market):
    bars = market.get_closed_bars(
        symbol=SYMBOL,
        timeframe=mt5.TIMEFRAME_M15,
        count=100,
    )

    assert (bars["tick_volume"] >= 0).all()

def test_closed_bars_do_not_include_current_bar(market):
    bars = market.get_closed_bars(
        symbol=SYMBOL,
        timeframe=mt5.TIMEFRAME_M15,
        count=100,
    )

    current_bar = market.client.current_bar(
        SYMBOL,
        mt5.TIMEFRAME_M15
    )

    import pandas as pd

    current_bar_time = pd.to_datetime(
        current_bar["time"],
        unit="s",
        utc=True,
    )

    last_closed_time = bars.iloc[-1]["time"]

    assert last_closed_time < current_bar_time