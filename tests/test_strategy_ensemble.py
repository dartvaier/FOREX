from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from alpha.blender import WeightedAlphaBlender
from alpha.ledger import AlphaLedger
from alpha.models import AlphaSignal
from alpha.quant import TimeSeriesMomentumAlphaModel
from backtest.context import BacktestContext
from backtest.costs import ZeroCostModel
from backtest.engine import BacktestEngine
from backtest.models import (
    BacktestConfig,
    InstrumentSpecification,
    MarketBar,
    SignalAction,
    Timeframe,
)
from backtest.models.enums import SimulationPhase
from backtest.risk import FixedSizeRiskGate
from strategy import EnsembleStrategy


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


def make_config() -> BacktestConfig:
    return BacktestConfig(
        symbol="EURUSD",
        timeframe=Timeframe.M15,
        date_from=utc_time(10),
        date_to=utc_time(12),
        initial_capital=10000.0,
    )


def make_instrument() -> InstrumentSpecification:
    return InstrumentSpecification(
        symbol="EURUSD",
        digits=5,
        point=0.00001,
        pip_size=0.00010,
        contract_size=100000,
        volume_min=0.01,
        volume_max=500.0,
        volume_step=0.01,
        tick_size=0.00001,
    )


def make_dataframe(
    closes: list[float],
) -> pd.DataFrame:
    times = pd.date_range(
        "2026-08-08T10:00:00Z",
        periods=len(closes),
        freq="15min",
    )

    return pd.DataFrame(
        {
            "time": times,
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "tick_volume": [
                1000
                for _ in closes
            ],
        }
    )


@dataclass(frozen=True, slots=True)
class StaticAlphaModel:
    model_id: str
    value: float
    symbol: str = "EURUSD"

    def predict(
        self,
        context,
    ) -> AlphaSignal:
        return AlphaSignal(
            model_id=self.model_id,
            symbol=self.symbol,
            timestamp=context.current_time,
            value=self.value,
        )


@dataclass(frozen=True, slots=True)
class AbstainingAlphaModel:
    model_id: str
    symbol: str = "EURUSD"

    def predict(
        self,
        context,
    ) -> AlphaSignal:
        return AlphaSignal.abstain(
            model_id=self.model_id,
            symbol=self.symbol,
            timestamp=context.current_time,
            reason="Synthetic abstention",
        )


@dataclass(frozen=True, slots=True)
class SequenceAlphaModel:
    model_id: str
    values: tuple[float, ...]
    symbol: str = "EURUSD"

    def predict(
        self,
        context,
    ) -> AlphaSignal:
        value = self.values[
            context.current_bar_index
        ]

        return AlphaSignal(
            model_id=self.model_id,
            symbol=self.symbol,
            timestamp=context.current_time,
            value=value,
        )


def test_ensemble_strategy_validates_parameters():
    model = StaticAlphaModel(
        model_id="ema",
        value=0.2,
    )
    blender = WeightedAlphaBlender(
        {
            "ema": 1.0,
        }
    )

    with pytest.raises(ValueError, match="symbol"):
        EnsembleStrategy(
            symbol="",
            models=(model,),
            blender=blender,
        )

    with pytest.raises(ValueError, match="models"):
        EnsembleStrategy(
            symbol="EURUSD",
            models=(),
            blender=blender,
        )

    with pytest.raises(ValueError, match="missing blender weight"):
        EnsembleStrategy(
            symbol="EURUSD",
            models=(
                StaticAlphaModel(
                    model_id="tsmom",
                    value=0.2,
                ),
            ),
            blender=blender,
        )

    with pytest.raises(ValueError, match="unique model_id"):
        EnsembleStrategy(
            symbol="EURUSD",
            models=(model, model),
            blender=blender,
        )


def test_ensemble_strategy_holds_when_all_models_abstain():
    strategy = EnsembleStrategy(
        symbol="EURUSD",
        models=(
            AbstainingAlphaModel(
                model_id="session",
            ),
        ),
        blender=WeightedAlphaBlender(
            {
                "session": 1.0,
            }
        ),
        min_conviction=0.1,
        enter_long=0.3,
        enter_short=-0.3,
    )

    signal = strategy.on_bar(
        make_context(
            [
                1.1000,
            ]
        )
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "All alpha models abstained"
    assert signal.metadata["blended_abstained"] is True
    assert signal.metadata["abstained_models"] == ("session",)


def test_ensemble_strategy_enters_long_from_blended_alpha():
    strategy = EnsembleStrategy(
        symbol="EURUSD",
        models=(
            StaticAlphaModel(
                model_id="ema",
                value=0.4,
            ),
        ),
        blender=WeightedAlphaBlender(
            {
                "ema": 1.0,
            }
        ),
        min_conviction=0.1,
        enter_long=0.3,
        enter_short=-0.3,
    )

    signal = strategy.on_bar(
        make_context(
            [
                1.1000,
            ]
        )
    )

    assert signal.action == SignalAction.ENTER_LONG
    assert signal.reason == (
        "Blended alpha crossed long entry threshold"
    )
    assert signal.metadata["blended_value"] == pytest.approx(0.4)
    assert signal.metadata["contributors"][0]["model_id"] == "ema"


def test_ensemble_strategy_enters_short_from_blended_alpha():
    strategy = EnsembleStrategy(
        symbol="EURUSD",
        models=(
            StaticAlphaModel(
                model_id="tsmom",
                value=-0.4,
            ),
        ),
        blender=WeightedAlphaBlender(
            {
                "tsmom": 1.0,
            }
        ),
        min_conviction=0.1,
        enter_long=0.3,
        enter_short=-0.3,
    )

    signal = strategy.on_bar(
        make_context(
            [
                1.1000,
            ]
        )
    )

    assert signal.action == SignalAction.ENTER_SHORT
    assert signal.reason == (
        "Blended alpha crossed short entry threshold"
    )


def test_ensemble_strategy_holds_below_minimum_conviction():
    strategy = EnsembleStrategy(
        symbol="EURUSD",
        models=(
            StaticAlphaModel(
                model_id="weak",
                value=0.05,
            ),
        ),
        blender=WeightedAlphaBlender(
            {
                "weak": 1.0,
            }
        ),
        min_conviction=0.1,
        enter_long=0.3,
        enter_short=-0.3,
    )

    signal = strategy.on_bar(
        make_context(
            [
                1.1000,
            ]
        )
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == (
        "Blended alpha below minimum conviction"
    )


def test_ensemble_strategy_distinguishes_neutral_from_abstain():
    strategy = EnsembleStrategy(
        symbol="EURUSD",
        models=(
            StaticAlphaModel(
                model_id="neutral",
                value=0.0,
            ),
        ),
        blender=WeightedAlphaBlender(
            {
                "neutral": 1.0,
            }
        ),
        min_conviction=0.1,
        enter_long=0.3,
        enter_short=-0.3,
    )

    signal = strategy.on_bar(
        make_context(
            [
                1.1000,
            ]
        )
    )

    assert signal.action == SignalAction.HOLD
    assert signal.metadata["blended_abstained"] is False
    assert signal.metadata["contributors"][0]["model_id"] == (
        "neutral"
    )


def test_ensemble_strategy_exits_long_when_alpha_weakens():
    strategy = EnsembleStrategy(
        symbol="EURUSD",
        models=(
            SequenceAlphaModel(
                model_id="seq",
                values=(0.5, 0.1),
            ),
        ),
        blender=WeightedAlphaBlender(
            {
                "seq": 1.0,
            }
        ),
        min_conviction=0.1,
        enter_long=0.3,
        enter_short=-0.3,
        exit_long_below=0.2,
    )

    entry = strategy.on_bar(
        make_context(
            [
                1.1000,
            ]
        )
    )
    exit_signal = strategy.on_bar(
        make_context(
            [
                1.1000,
                1.1010,
            ]
        )
    )

    assert entry.action == SignalAction.ENTER_LONG
    assert exit_signal.action == SignalAction.EXIT
    assert exit_signal.reason == (
        "Blended alpha fell below long exit threshold"
    )


def test_ensemble_strategy_hysteresis_holds_above_exit_band():
    no_hysteresis = EnsembleStrategy(
        symbol="EURUSD",
        models=(
            SequenceAlphaModel(
                model_id="seq",
                values=(0.5, 0.2),
            ),
        ),
        blender=WeightedAlphaBlender(
            {
                "seq": 1.0,
            }
        ),
        min_conviction=0.1,
        enter_long=0.4,
        enter_short=-0.4,
        exit_long_below=0.3,
        exit_short_above=-0.3,
    )
    hysteresis = EnsembleStrategy(
        symbol="EURUSD",
        models=(
            SequenceAlphaModel(
                model_id="seq",
                values=(0.5, 0.2),
            ),
        ),
        blender=WeightedAlphaBlender(
            {
                "seq": 1.0,
            }
        ),
        min_conviction=0.1,
        enter_long=0.4,
        enter_short=-0.4,
        exit_long_below=0.05,
        exit_short_above=-0.05,
    )

    no_hysteresis.on_bar(
        make_context(
            [
                1.1000,
            ]
        )
    )
    hysteresis.on_bar(
        make_context(
            [
                1.1000,
            ]
        )
    )

    no_hysteresis_signal = no_hysteresis.on_bar(
        make_context(
            [
                1.1000,
                1.1010,
            ]
        )
    )
    hysteresis_signal = hysteresis.on_bar(
        make_context(
            [
                1.1000,
                1.1010,
            ]
        )
    )

    assert no_hysteresis_signal.action == SignalAction.EXIT
    assert hysteresis_signal.action == SignalAction.HOLD
    assert hysteresis_signal.reason == "Long held by blended alpha"


def test_ensemble_strategy_reset_clears_position_state():
    strategy = EnsembleStrategy(
        symbol="EURUSD",
        models=(
            SequenceAlphaModel(
                model_id="seq",
                values=(0.5,),
            ),
        ),
        blender=WeightedAlphaBlender(
            {
                "seq": 1.0,
            }
        ),
        min_conviction=0.1,
        enter_long=0.3,
        enter_short=-0.3,
    )

    first = strategy.on_bar(
        make_context(
            [
                1.1000,
            ]
        )
    )

    strategy.reset()

    second = strategy.on_bar(
        make_context(
            [
                1.1000,
            ]
        )
    )

    assert first.action == SignalAction.ENTER_LONG
    assert second.action == SignalAction.ENTER_LONG


def test_ensemble_strategy_uses_max_model_closed_bar_limit():
    tsmom = TimeSeriesMomentumAlphaModel(
        symbol="EURUSD",
        lookback=3,
        score_scale=0.01,
    )
    other = StaticAlphaModel(
        model_id="other",
        value=0.0,
    )

    strategy = EnsembleStrategy(
        symbol="EURUSD",
        models=(tsmom, other),
        blender=WeightedAlphaBlender(
            {
                tsmom.model_id: 1.0,
                "other": 1.0,
            }
        ),
        min_conviction=0.1,
        enter_long=0.3,
        enter_short=-0.3,
    )

    assert strategy.closed_bar_limit == 4


def test_ensemble_strategy_rejects_invalid_alpha_output():
    strategy = EnsembleStrategy(
        symbol="EURUSD",
        models=(
            StaticAlphaModel(
                model_id="wrong-symbol",
                value=0.3,
                symbol="GBPUSD",
            ),
        ),
        blender=WeightedAlphaBlender(
            {
                "wrong-symbol": 1.0,
            }
        ),
        min_conviction=0.1,
        enter_long=0.3,
        enter_short=-0.3,
    )

    with pytest.raises(ValueError, match="symbol"):
        strategy.on_bar(
            make_context(
                [
                    1.1000,
                ]
            )
        )


def test_ensemble_strategy_records_alpha_diagnostics():
    ledger = AlphaLedger()
    strategy = EnsembleStrategy(
        symbol="EURUSD",
        models=(
            StaticAlphaModel(
                model_id="ema",
                value=0.5,
            ),
            StaticAlphaModel(
                model_id="tsmom",
                value=0.3,
            ),
        ),
        blender=WeightedAlphaBlender(
            {
                "ema": 1.0,
                "tsmom": 1.0,
            }
        ),
        min_conviction=0.1,
        enter_long=0.3,
        enter_short=-0.3,
        alpha_ledger=ledger,
    )

    signal = strategy.on_bar(
        make_context(
            [
                1.1000,
            ]
        )
    )

    assert signal.action == SignalAction.ENTER_LONG
    assert ledger.count == 2

    records = ledger.records

    assert {
        record.model_id
        for record in records
    } == {
        "ema",
        "tsmom",
    }
    assert all(
        record.blended_value == pytest.approx(0.4)
        for record in records
    )
    assert all(
        record.strategy_decision == "ENTER_LONG"
        for record in records
    )


def test_ensemble_strategy_runs_through_backtest_engine():
    instrument = make_instrument()

    engine = BacktestEngine(
        config=make_config(),
        instrument=instrument,
        cost_model=ZeroCostModel(
            instrument,
        ),
        risk_gate=FixedSizeRiskGate(
            instrument=instrument,
            fixed_quantity=0.01,
        ),
    )
    model = TimeSeriesMomentumAlphaModel(
        symbol="EURUSD",
        lookback=3,
        score_scale=0.01,
    )
    strategy = EnsembleStrategy(
        symbol="EURUSD",
        models=(model,),
        blender=WeightedAlphaBlender(
            {
                model.model_id: 1.0,
            }
        ),
        min_conviction=0.1,
        enter_long=0.5,
        enter_short=-1.0,
        exit_long_below=0.0,
    )

    result = engine.run(
        dataframe=make_dataframe(
                [
                    1.1000,
                    1.1010,
                    1.1020,
                    1.1110,
                    1.1120,
                    1.1000,
                    1.1050,
                ]
            ),
            strategy=strategy,
        )

    assert result.signals.count == 7
    assert result.orders.count == 2
    assert result.fills.count == 2
    assert result.trades.count == 1
    assert result.portfolio.is_flat is True
