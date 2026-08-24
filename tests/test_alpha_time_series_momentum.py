from datetime import datetime, timedelta, timezone

import pytest

from alpha.models import AlphaSignal
from alpha.protocol import AlphaModel
from alpha.quant import TimeSeriesMomentumAlphaModel
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


def test_tsmom_alpha_model_validates_parameters():
    with pytest.raises(ValueError, match="symbol"):
        TimeSeriesMomentumAlphaModel(
            symbol="",
        )

    with pytest.raises(ValueError, match="model_id"):
        TimeSeriesMomentumAlphaModel(
            symbol="EURUSD",
            model_id="",
        )

    with pytest.raises(ValueError, match="lookback"):
        TimeSeriesMomentumAlphaModel(
            symbol="EURUSD",
            lookback=0,
        )

    with pytest.raises(ValueError, match="score_scale"):
        TimeSeriesMomentumAlphaModel(
            symbol="EURUSD",
            score_scale=0.0,
        )

    with pytest.raises(ValueError, match="pip_size"):
        TimeSeriesMomentumAlphaModel(
            symbol="EURUSD",
            pip_size=0.0,
        )


def test_tsmom_alpha_model_satisfies_alpha_model_protocol():
    model = TimeSeriesMomentumAlphaModel(
        symbol="EURUSD",
    )

    assert isinstance(model, AlphaModel)


def test_tsmom_alpha_model_reports_closed_bar_limit():
    model = TimeSeriesMomentumAlphaModel(
        symbol="EURUSD",
        lookback=3,
    )

    assert model.closed_bar_limit == 4


def test_tsmom_alpha_model_abstains_during_warm_up():
    model = TimeSeriesMomentumAlphaModel(
        symbol="EURUSD",
        lookback=3,
        score_scale=0.02,
    )

    signal = model.predict(
        make_context(
            [
                1.1000,
                1.1010,
                1.1020,
            ]
        )
    )

    assert isinstance(signal, AlphaSignal)
    assert signal.abstained is True
    assert signal.value == 0.0
    assert signal.reason == "Warm-up"
    assert signal.metadata["required_closed_bars"] == 4
    assert signal.metadata["available_closed_bars"] == 3


def test_tsmom_alpha_model_scores_positive_momentum():
    model = TimeSeriesMomentumAlphaModel(
        symbol="EURUSD",
        lookback=3,
        score_scale=0.02,
    )

    signal = model.predict(
        make_context(
            [
                1.1000,
                1.1010,
                1.1020,
                1.1110,
            ]
        )
    )

    expected_return = 1.1110 / 1.1000 - 1.0

    assert signal.abstained is False
    assert signal.value == pytest.approx(
        expected_return / 0.02
    )
    assert signal.reason == "Positive time-series momentum"
    assert signal.metadata["momentum_return"] == pytest.approx(
        expected_return
    )
    assert signal.metadata["pip_size"] == 0.00010
    assert signal.metadata["expected_move_pips"] == pytest.approx(
        abs(
            1.1110
            * expected_return
        )
        / 0.00010
    )


def test_tsmom_alpha_model_scores_negative_momentum():
    model = TimeSeriesMomentumAlphaModel(
        symbol="EURUSD",
        lookback=3,
        score_scale=0.02,
    )

    signal = model.predict(
        make_context(
            [
                1.1000,
                1.0990,
                1.0980,
                1.0890,
            ]
        )
    )

    expected_return = 1.0890 / 1.1000 - 1.0

    assert signal.abstained is False
    assert signal.value == pytest.approx(
        expected_return / 0.02
    )
    assert signal.reason == "Negative time-series momentum"


def test_tsmom_alpha_model_distinguishes_neutral_from_abstain():
    model = TimeSeriesMomentumAlphaModel(
        symbol="EURUSD",
        lookback=3,
        score_scale=0.02,
    )

    signal = model.predict(
        make_context(
            [
                1.1000,
                1.1010,
                1.0990,
                1.1000,
            ]
        )
    )

    assert signal.abstained is False
    assert signal.value == 0.0
    assert signal.reason == "Neutral time-series momentum"


def test_tsmom_alpha_model_clamps_score_to_normalized_range():
    model = TimeSeriesMomentumAlphaModel(
        symbol="EURUSD",
        lookback=3,
        score_scale=0.01,
    )

    strong_positive = model.predict(
        make_context(
            [
                1.1000,
                1.1010,
                1.1020,
                1.1300,
            ]
        )
    )
    strong_negative = model.predict(
        make_context(
            [
                1.1000,
                1.0990,
                1.0980,
                1.0700,
            ]
        )
    )

    assert strong_positive.value == 1.0
    assert strong_negative.value == -1.0


def test_tsmom_alpha_model_uses_context_time_and_closed_bars():
    context = make_context(
        [
            1.1000,
            1.1010,
            1.1020,
            1.1110,
        ]
    )
    model = TimeSeriesMomentumAlphaModel(
        symbol="EURUSD",
        lookback=3,
        score_scale=0.02,
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


def test_tsmom_alpha_model_requires_backtest_context():
    model = TimeSeriesMomentumAlphaModel(
        symbol="EURUSD",
    )

    with pytest.raises(TypeError, match="BacktestContext"):
        model.predict(object())  # type: ignore[arg-type]
