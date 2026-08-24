from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from backtest.context import BacktestContext
from backtest.costs import FixedCostModel, ZeroCostModel
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
from strategy import SimpleRegimeDetectionStrategy


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


def make_strategy() -> SimpleRegimeDetectionStrategy:
    return SimpleRegimeDetectionStrategy(
        symbol="EURUSD",
        trend_lookback=3,
        volatility_lookback=3,
        entry_threshold=0.01,
        exit_threshold=0.002,
        max_volatility=0.02,
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


def test_strategy_validates_parameters():
    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        SimpleRegimeDetectionStrategy(
            symbol="",
        )

    with pytest.raises(
        ValueError,
        match="trend_lookback",
    ):
        SimpleRegimeDetectionStrategy(
            symbol="EURUSD",
            trend_lookback=0,
        )

    with pytest.raises(
        ValueError,
        match="entry_threshold",
    ):
        SimpleRegimeDetectionStrategy(
            symbol="EURUSD",
            entry_threshold=0.0,
        )

    with pytest.raises(
        ValueError,
        match="exit_threshold",
    ):
        SimpleRegimeDetectionStrategy(
            symbol="EURUSD",
            entry_threshold=0.01,
            exit_threshold=0.02,
        )


def test_strategy_holds_during_warm_up():
    signal = make_strategy().on_bar(
        make_context(
            [
                1.1000,
                1.1010,
                1.1020,
            ]
        )
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "Warm-up"


def test_strategy_enters_long_in_bullish_low_volatility_regime():
    signal = make_strategy().on_bar(
        make_context(
            [
                1.1000,
                1.1000,
                1.1010,
                1.1130,
            ]
        )
    )

    assert signal.action == SignalAction.ENTER_LONG
    assert signal.reason == "Bullish low-volatility regime"
    assert signal.metadata["trend_return"] > 0.01
    assert (
        signal.metadata["realized_volatility"]
        <= signal.metadata["max_volatility"]
    )
    assert signal.metadata["exposure_side"] == "LONG"


def test_strategy_enters_short_in_bearish_low_volatility_regime():
    signal = make_strategy().on_bar(
        make_context(
            [
                1.1130,
                1.1120,
                1.1110,
                1.1000,
            ]
        )
    )

    assert signal.action == SignalAction.ENTER_SHORT
    assert signal.reason == "Bearish low-volatility regime"
    assert signal.metadata["trend_return"] < -0.01
    assert signal.metadata["exposure_side"] == "SHORT"


def test_strategy_holds_when_same_regime_is_already_active():
    strategy = make_strategy()

    first_signal = strategy.on_bar(
        make_context(
            [
                1.1000,
                1.1000,
                1.1010,
                1.1130,
            ]
        )
    )

    second_signal = strategy.on_bar(
        make_context(
            [
                1.1010,
                1.1020,
                1.1030,
                1.1150,
            ]
        )
    )

    assert first_signal.action == SignalAction.ENTER_LONG
    assert second_signal.action == SignalAction.HOLD
    assert second_signal.reason == "Long regime already active"


def test_strategy_exits_when_regime_changes_direction():
    strategy = make_strategy()

    strategy.on_bar(
        make_context(
            [
                1.1000,
                1.1000,
                1.1010,
                1.1130,
            ]
        )
    )

    signal = strategy.on_bar(
        make_context(
            [
                1.1130,
                1.1120,
                1.1110,
                1.1000,
            ]
        )
    )

    assert signal.action == SignalAction.EXIT
    assert signal.reason == "Regime changed direction"
    assert signal.metadata["exposure_side"] is None


def test_strategy_enters_opposite_side_after_direction_exit():
    strategy = make_strategy()

    strategy.on_bar(
        make_context(
            [
                1.1000,
                1.1000,
                1.1010,
                1.1130,
            ]
        )
    )

    strategy.on_bar(
        make_context(
            [
                1.1130,
                1.1120,
                1.1110,
                1.1000,
            ]
        )
    )

    signal = strategy.on_bar(
        make_context(
            [
                1.1130,
                1.1120,
                1.1110,
                1.1000,
            ]
        )
    )

    assert signal.action == SignalAction.ENTER_SHORT
    assert signal.reason == "Bearish low-volatility regime"


def test_strategy_exits_when_volatility_exceeds_threshold():
    strategy = make_strategy()

    strategy.on_bar(
        make_context(
            [
                1.1000,
                1.1000,
                1.1010,
                1.1130,
            ]
        )
    )

    strategy.max_volatility = 0.001

    signal = strategy.on_bar(
        make_context(
            [
                1.1000,
                1.1300,
                1.0900,
                1.1200,
            ]
        )
    )

    assert signal.action == SignalAction.EXIT
    assert signal.reason == (
        "Regime volatility exceeded threshold"
    )
    assert signal.metadata["exposure_side"] is None


def test_strategy_exits_when_regime_returns_to_neutral():
    strategy = make_strategy()

    strategy.on_bar(
        make_context(
            [
                1.1000,
                1.1000,
                1.1010,
                1.1130,
            ]
        )
    )

    signal = strategy.on_bar(
        make_context(
            [
                1.1000,
                1.1005,
                1.1008,
                1.1010,
            ]
        )
    )

    assert signal.action == SignalAction.EXIT
    assert signal.reason == "Regime returned to neutral"


def test_strategy_reset_allows_new_entry():
    strategy = make_strategy()

    strategy.on_bar(
        make_context(
            [
                1.1000,
                1.1000,
                1.1010,
                1.1130,
            ]
        )
    )

    strategy.reset()

    signal = strategy.on_bar(
        make_context(
            [
                1.1010,
                1.1020,
                1.1030,
                1.1150,
            ]
        )
    )

    assert signal.action == SignalAction.ENTER_LONG


def test_strategy_runs_through_backtest_engine_zero_cost():
    config = make_config()
    instrument = make_instrument()

    engine = BacktestEngine(
        config=config,
        instrument=instrument,
        cost_model=ZeroCostModel(
            instrument,
        ),
        risk_gate=FixedSizeRiskGate(
            instrument=instrument,
            fixed_quantity=0.01,
        ),
    )

    result = engine.run(
        dataframe=make_dataframe(
            [
                1.1000,
                1.1000,
                1.1120,
                1.1130,
                1.1140,
            ]
        ),
        strategy=SimpleRegimeDetectionStrategy(
            symbol="EURUSD",
            trend_lookback=2,
            volatility_lookback=2,
            entry_threshold=0.005,
            exit_threshold=0.001,
            max_volatility=0.02,
        ),
    )

    assert result.signals.count == 5
    assert result.orders.count == 2
    assert result.trades.count == 1
    assert result.portfolio.is_flat is True


def test_strategy_runs_through_backtest_engine_with_costs():
    config = make_config()
    instrument = make_instrument()

    engine = BacktestEngine(
        config=config,
        instrument=instrument,
        cost_model=FixedCostModel(
            instrument=instrument,
            spread_pips=2.0,
            slippage_pips=0.5,
            commission_per_lot_per_side=3.50,
        ),
        risk_gate=FixedSizeRiskGate(
            instrument=instrument,
            fixed_quantity=0.01,
        ),
    )

    result = engine.run(
        dataframe=make_dataframe(
            [
                1.1000,
                1.1000,
                1.1120,
                1.1130,
                1.1140,
            ]
        ),
        strategy=SimpleRegimeDetectionStrategy(
            symbol="EURUSD",
            trend_lookback=2,
            volatility_lookback=2,
            entry_threshold=0.005,
            exit_threshold=0.001,
            max_volatility=0.02,
        ),
    )

    assert result.trades.count == 1
    assert result.fills.count == 2
    assert result.trades.last_trade is not None
    assert result.trades.last_trade.commission == pytest.approx(
        0.07
    )
