from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from alpha.models import AlphaSignal
from alpha.protocol import AlphaModel
from alpha.regime import (
    REGIME_HIGH_VOLATILITY,
    REGIME_RANGING,
    REGIME_TRENDING_DOWN,
    REGIME_TRENDING_UP,
    REGIME_WARM_UP,
    RegimeDecision,
    RegimeGatedAlphaModel,
    TrendVolatilityRegimeGate,
)
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


@dataclass(frozen=True, slots=True)
class StaticAlphaModel:
    symbol: str = "EURUSD"
    model_id: str = "static-alpha"
    value: float = 0.5

    @property
    def closed_bar_limit(self) -> int:
        return 2

    def predict(
        self,
        context,
    ) -> AlphaSignal:
        return AlphaSignal(
            model_id=self.model_id,
            symbol=self.symbol,
            timestamp=context.current_time,
            value=self.value,
            metadata={"inner": True},
        )


def make_gate(
    *,
    allowed_regimes=(
        REGIME_TRENDING_UP,
        REGIME_TRENDING_DOWN,
    ),
) -> TrendVolatilityRegimeGate:
    return TrendVolatilityRegimeGate(
        trend_lookback=3,
        volatility_lookback=3,
        trend_threshold=0.01,
        max_volatility=0.02,
        allowed_regimes=allowed_regimes,
    )


def test_regime_decision_is_immutable_and_metadata_is_read_only():
    metadata = {
        "trend_return": 0.02,
    }
    decision = RegimeDecision(
        regime=REGIME_TRENDING_UP,
        allowed=True,
        reason="Bullish trend regime",
        metadata=metadata,
    )

    metadata["trend_return"] = 0.0

    assert decision.metadata["trend_return"] == 0.02

    with pytest.raises(TypeError):
        decision.metadata["trend_return"] = 1.0  # type: ignore[index]


def test_regime_gate_validates_parameters():
    with pytest.raises(ValueError, match="trend_lookback"):
        TrendVolatilityRegimeGate(
            trend_lookback=0,
        )

    with pytest.raises(ValueError, match="trend_threshold"):
        TrendVolatilityRegimeGate(
            trend_threshold=0.0,
        )

    with pytest.raises(ValueError, match="allowed_regimes"):
        TrendVolatilityRegimeGate(
            allowed_regimes=(),
        )

    with pytest.raises(ValueError, match="allowed_regimes"):
        TrendVolatilityRegimeGate(
            allowed_regimes=("unknown",),
        )


def test_regime_gate_reports_closed_bar_limit():
    gate = make_gate()

    assert gate.closed_bar_limit == 4


def test_regime_gate_returns_warm_up_when_bars_are_insufficient():
    decision = make_gate().evaluate(
        make_context(
            [
                1.1000,
                1.1010,
                1.1020,
            ]
        )
    )

    assert decision.regime == REGIME_WARM_UP
    assert decision.allowed is False
    assert decision.reason == "Regime warm-up"
    assert decision.metadata["required_closed_bars"] == 4


def test_regime_gate_allows_bullish_trend_regime():
    decision = make_gate().evaluate(
        make_context(
            [
                1.1000,
                1.1000,
                1.1010,
                1.1130,
            ]
        )
    )

    assert decision.regime == REGIME_TRENDING_UP
    assert decision.allowed is True
    assert decision.metadata["trend_return"] > 0.01


def test_regime_gate_allows_bearish_trend_regime():
    decision = make_gate().evaluate(
        make_context(
            [
                1.1130,
                1.1120,
                1.1110,
                1.1000,
            ]
        )
    )

    assert decision.regime == REGIME_TRENDING_DOWN
    assert decision.allowed is True
    assert decision.metadata["trend_return"] < -0.01


def test_regime_gate_blocks_ranging_regime():
    decision = make_gate().evaluate(
        make_context(
            [
                1.1000,
                1.1005,
                1.1008,
                1.1010,
            ]
        )
    )

    assert decision.regime == REGIME_RANGING
    assert decision.allowed is False


def test_regime_gate_blocks_high_volatility_regime():
    decision = make_gate().evaluate(
        make_context(
            [
                1.1000,
                1.1300,
                1.0900,
                1.1200,
            ]
        )
    )

    assert decision.regime == REGIME_HIGH_VOLATILITY
    assert decision.allowed is False


def test_regime_gated_alpha_model_satisfies_alpha_model_protocol():
    model = RegimeGatedAlphaModel(
        inner=StaticAlphaModel(),
        gate=make_gate(),
    )

    assert isinstance(model, AlphaModel)


def test_regime_gated_alpha_model_uses_max_closed_bar_limit():
    model = RegimeGatedAlphaModel(
        inner=StaticAlphaModel(),
        gate=make_gate(),
    )

    assert model.closed_bar_limit == 4


def test_regime_gated_alpha_model_abstains_when_gate_blocks():
    model = RegimeGatedAlphaModel(
        inner=StaticAlphaModel(),
        gate=make_gate(),
    )

    signal = model.predict(
        make_context(
            [
                1.1000,
                1.1005,
                1.1008,
                1.1010,
            ]
        )
    )

    assert signal.abstained is True
    assert signal.value == 0.0
    assert signal.model_id == "static-alpha"
    assert signal.reason == "Regime gate blocked: Ranging regime"
    assert signal.metadata["regime"] == REGIME_RANGING
    assert signal.metadata["regime_allowed"] is False


def test_regime_gated_alpha_model_returns_inner_signal_when_allowed():
    model = RegimeGatedAlphaModel(
        inner=StaticAlphaModel(),
        gate=make_gate(),
    )

    signal = model.predict(
        make_context(
            [
                1.1000,
                1.1000,
                1.1010,
                1.1130,
            ]
        )
    )

    assert signal.abstained is False
    assert signal.value == 0.5
    assert signal.metadata["inner"] is True
    assert signal.metadata["regime"] == REGIME_TRENDING_UP
    assert signal.metadata["regime_allowed"] is True
    assert signal.metadata["regime_trend_return"] > 0.01


def test_regime_gated_alpha_model_can_allow_ranging_regime():
    model = RegimeGatedAlphaModel(
        inner=StaticAlphaModel(),
        gate=make_gate(
            allowed_regimes=(REGIME_RANGING,)
        ),
    )

    signal = model.predict(
        make_context(
            [
                1.1000,
                1.1005,
                1.1008,
                1.1010,
            ]
        )
    )

    assert signal.abstained is False
    assert signal.metadata["regime"] == REGIME_RANGING
