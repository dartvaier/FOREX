from datetime import datetime, timedelta, timezone

import pytest

from alpha.models import AlphaSignal
from alpha.protocol import AlphaModel
from alpha.quant import EmaTrendAlphaModel
from backtest.context import BacktestContext
from backtest.models import MarketBar
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


def make_bar(
    index: int,
    close: float,
) -> MarketBar:
    return MarketBar(
        time=utc_time(10)
        + timedelta(minutes=index * 15),
        open=close,
        high=close,
        low=close,
        close=close,
        tick_volume=1000,
    )


def make_context(
    closes: list[float],
) -> BacktestContext:
    bars = tuple(
        make_bar(index, close)
        for index, close in enumerate(closes)
    )
    current_index = len(bars) - 1

    return BacktestContext(
        current_time=(
            utc_time(10)
            + timedelta(
                minutes=(current_index + 1) * 15
            )
        ),
        phase=SimulationPhase.BAR_CLOSE,
        current_bar_index=current_index,
        current_bar=bars[-1],
        closed_bars=bars,
    )


def test_ema_trend_alpha_model_validates_parameters():
    with pytest.raises(ValueError, match="symbol"):
        EmaTrendAlphaModel(
            symbol="",
        )

    with pytest.raises(ValueError, match="model_id"):
        EmaTrendAlphaModel(
            symbol="EURUSD",
            model_id="",
        )

    with pytest.raises(ValueError, match="fast_period"):
        EmaTrendAlphaModel(
            symbol="EURUSD",
            fast_period=0,
        )

    with pytest.raises(ValueError, match="smaller"):
        EmaTrendAlphaModel(
            symbol="EURUSD",
            fast_period=4,
            slow_period=4,
        )

    with pytest.raises(ValueError, match="score_scale"):
        EmaTrendAlphaModel(
            symbol="EURUSD",
            score_scale=0.0,
        )

    with pytest.raises(ValueError, match="pip_size"):
        EmaTrendAlphaModel(
            symbol="EURUSD",
            pip_size=0.0,
        )


def test_ema_trend_alpha_model_satisfies_alpha_model_protocol():
    model = EmaTrendAlphaModel(
        symbol="EURUSD",
    )

    assert isinstance(model, AlphaModel)


def test_ema_trend_alpha_model_reports_closed_bar_limit():
    model = EmaTrendAlphaModel(
        symbol="EURUSD",
        fast_period=2,
        slow_period=4,
    )

    assert model.closed_bar_limit == 5


def test_ema_trend_alpha_model_abstains_during_warm_up():
    model = EmaTrendAlphaModel(
        symbol="EURUSD",
        fast_period=2,
        slow_period=4,
        score_scale=1.0,
    )

    signal = model.predict(
        make_context(
            [
                10.0,
                10.0,
                10.0,
                10.0,
            ]
        )
    )

    assert isinstance(signal, AlphaSignal)
    assert signal.abstained is True
    assert signal.value == 0.0
    assert signal.reason == "Warm-up"
    assert signal.metadata["required_closed_bars"] == 5


def test_ema_trend_alpha_model_scores_positive_trend():
    model = EmaTrendAlphaModel(
        symbol="EURUSD",
        fast_period=2,
        slow_period=4,
        score_scale=1.0,
    )

    signal = model.predict(
        make_context(
            [
                10.0,
                10.0,
                10.0,
                10.0,
                12.0,
            ]
        )
    )

    assert signal.abstained is False
    assert signal.value > 0.0
    assert signal.reason == "Positive EMA trend"
    assert signal.metadata["fast_ema"] > signal.metadata["slow_ema"]
    assert signal.metadata["ema_spread"] > 0.0
    assert signal.metadata["pip_size"] == 0.00010
    assert signal.metadata["expected_move_pips"] == pytest.approx(
        signal.metadata["ema_spread"] / 0.00010
    )


def test_ema_trend_alpha_model_scores_negative_trend():
    model = EmaTrendAlphaModel(
        symbol="EURUSD",
        fast_period=2,
        slow_period=4,
        score_scale=1.0,
    )

    signal = model.predict(
        make_context(
            [
                12.0,
                12.0,
                12.0,
                12.0,
                10.0,
            ]
        )
    )

    assert signal.abstained is False
    assert signal.value < 0.0
    assert signal.reason == "Negative EMA trend"
    assert signal.metadata["fast_ema"] < signal.metadata["slow_ema"]
    assert signal.metadata["ema_spread"] < 0.0


def test_ema_trend_alpha_model_distinguishes_neutral_from_abstain():
    model = EmaTrendAlphaModel(
        symbol="EURUSD",
        fast_period=2,
        slow_period=4,
        score_scale=1.0,
    )

    signal = model.predict(
        make_context(
            [
                10.0,
                10.0,
                10.0,
                10.0,
                10.0,
            ]
        )
    )

    assert signal.abstained is False
    assert signal.value == 0.0
    assert signal.reason == "Neutral EMA trend"


def test_ema_trend_alpha_model_bounds_score():
    model = EmaTrendAlphaModel(
        symbol="EURUSD",
        fast_period=2,
        slow_period=4,
        score_scale=0.0001,
    )

    signal = model.predict(
        make_context(
            [
                10.0,
                10.0,
                10.0,
                10.0,
                12.0,
            ]
        )
    )

    assert signal.value == pytest.approx(1.0)


def test_ema_trend_alpha_model_uses_context_time_and_closed_bars():
    context = make_context(
        [
            10.0,
            10.0,
            10.0,
            10.0,
            12.0,
        ]
    )
    model = EmaTrendAlphaModel(
        symbol="EURUSD",
        fast_period=2,
        slow_period=4,
        score_scale=1.0,
    )

    signal = model.predict(context)

    assert signal.symbol == "EURUSD"
    assert signal.timestamp == context.current_time
    assert not hasattr(
        context,
        "dataframe",
    )
    assert not hasattr(
        context,
        "future_bars",
    )


def test_ema_trend_alpha_model_requires_backtest_context():
    model = EmaTrendAlphaModel(
        symbol="EURUSD",
    )

    with pytest.raises(TypeError, match="BacktestContext"):
        model.predict(object())  # type: ignore[arg-type]
