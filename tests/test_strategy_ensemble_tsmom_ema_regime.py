from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from alpha.ledger import AlphaLedger
from alpha.regime import REGIME_RANGING, REGIME_TRENDING_UP
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
from research.runner import STRATEGY_REGISTRY, discover_strategy_class
from strategy import TsmomEmaRegimeGatedEnsembleStrategy


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


def test_regime_gated_ensemble_validates_parameters():
    with pytest.raises(ValueError, match="symbol"):
        TsmomEmaRegimeGatedEnsembleStrategy(
            symbol="",
        )

    with pytest.raises(ValueError, match="regime_trend_lookback"):
        TsmomEmaRegimeGatedEnsembleStrategy(
            symbol="EURUSD",
            regime_trend_lookback=0,
        )

    with pytest.raises(ValueError, match="regime_max_volatility"):
        TsmomEmaRegimeGatedEnsembleStrategy(
            symbol="EURUSD",
            regime_max_volatility=0.0,
        )


def test_regime_gated_ensemble_exposes_combined_closed_bar_limit():
    strategy = TsmomEmaRegimeGatedEnsembleStrategy(
        symbol="EURUSD",
        tsmom_lookback=3,
        ema_fast_period=2,
        ema_slow_period=4,
        regime_trend_lookback=5,
        regime_volatility_lookback=3,
    )

    assert strategy.closed_bar_limit == 6


def test_regime_gated_ensemble_enters_when_trend_regime_allows():
    strategy = TsmomEmaRegimeGatedEnsembleStrategy(
        symbol="EURUSD",
        tsmom_lookback=3,
        tsmom_score_scale=0.02,
        ema_fast_period=2,
        ema_slow_period=4,
        ema_score_scale=0.001,
        regime_trend_lookback=3,
        regime_volatility_lookback=3,
        regime_trend_threshold=0.01,
        regime_max_volatility=0.02,
        min_conviction=0.1,
        enter_long=0.25,
        enter_short=-0.25,
    )

    signal = strategy.on_bar(
        make_context(
                [
                    1.1000,
                    1.1000,
                    1.1010,
                    1.1120,
                    1.1130,
                ]
            )
        )

    assert signal.action == SignalAction.ENTER_LONG
    assert signal.metadata["blended_abstained"] is False
    assert all(
        contributor["model_id"]
        in {
            "TIME-SERIES-MOMENTUM-ALPHA",
            "EMA-TREND-ALPHA",
        }
        for contributor in signal.metadata["contributors"]
    )


def test_regime_gated_ensemble_holds_when_gate_blocks_all_models():
    ledger = AlphaLedger()
    strategy = TsmomEmaRegimeGatedEnsembleStrategy(
        symbol="EURUSD",
        tsmom_lookback=3,
        tsmom_score_scale=0.02,
        ema_fast_period=2,
        ema_slow_period=4,
        ema_score_scale=0.001,
        regime_trend_lookback=3,
        regime_volatility_lookback=3,
        regime_trend_threshold=0.01,
        regime_max_volatility=0.02,
        min_conviction=0.1,
        enter_long=0.25,
        enter_short=-0.25,
        alpha_ledger=ledger,
    )

    signal = strategy.on_bar(
        make_context(
                [
                    1.1000,
                    1.1003,
                    1.1005,
                    1.1006,
                    1.1007,
                ]
            )
        )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "All alpha models abstained"
    assert signal.metadata["blended_abstained"] is True
    assert ledger.count == 2
    assert all(
        record.abstained
        for record in ledger.records
    )
    assert all(
        record.metadata["regime"] == REGIME_RANGING
        for record in ledger.records
    )


def test_regime_gated_ensemble_records_allowed_regime():
    ledger = AlphaLedger()
    strategy = TsmomEmaRegimeGatedEnsembleStrategy(
        symbol="EURUSD",
        tsmom_lookback=3,
        tsmom_score_scale=0.02,
        ema_fast_period=2,
        ema_slow_period=4,
        ema_score_scale=0.001,
        regime_trend_lookback=3,
        regime_volatility_lookback=3,
        regime_trend_threshold=0.01,
        regime_max_volatility=0.02,
        min_conviction=0.1,
        enter_long=0.25,
        enter_short=-0.25,
        alpha_ledger=ledger,
    )

    strategy.on_bar(
        make_context(
                [
                    1.1000,
                    1.1000,
                    1.1010,
                    1.1120,
                    1.1130,
                ]
            )
        )

    assert ledger.count == 2
    assert all(
        record.metadata["regime"] == REGIME_TRENDING_UP
        for record in ledger.records
    )
    assert all(
        record.abstained is False
        for record in ledger.records
    )


def test_regime_gated_ensemble_runs_through_backtest_engine():
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

    strategy = TsmomEmaRegimeGatedEnsembleStrategy(
        symbol="EURUSD",
        tsmom_lookback=3,
        tsmom_score_scale=0.02,
        ema_fast_period=2,
        ema_slow_period=4,
        ema_score_scale=0.001,
        regime_trend_lookback=3,
        regime_volatility_lookback=3,
        regime_trend_threshold=0.01,
        regime_max_volatility=0.02,
        min_conviction=0.1,
        enter_long=0.25,
        enter_short=-1.0,
        exit_long_below=0.0,
    )

    result = engine.run(
        dataframe=make_dataframe(
                [
                    1.1000,
                    1.1000,
                    1.1010,
                    1.1120,
                    1.1130,
                    1.1140,
                    1.1000,
                    1.1050,
                ]
            ),
        strategy=strategy,
    )

    assert result.signals.count == 8
    assert result.orders.count == 2
    assert result.fills.count == 2
    assert result.trades.count == 1
    assert result.portfolio.is_flat is True


def test_research_runner_discovers_regime_gated_ensemble():
    strategy_class = discover_strategy_class(
        STRATEGY_REGISTRY["ensemble_tsmom_ema_regime"]
    )

    assert strategy_class is TsmomEmaRegimeGatedEnsembleStrategy
