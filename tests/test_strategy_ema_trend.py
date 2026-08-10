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
from strategy import SimpleEmaTrendStrategy


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
    timestamp = utc_time(10) + timedelta(
        minutes=index * 15
    )

    return MarketBar(
        time=timestamp,
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

    current_time = utc_time(10) + timedelta(
        minutes=(current_index + 1) * 15
    )

    return BacktestContext(
        current_time=current_time,
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


def make_strategy() -> SimpleEmaTrendStrategy:
    return SimpleEmaTrendStrategy(
        symbol="EURUSD",
        fast_period=2,
        slow_period=4,
    )


def test_strategy_validates_parameters():
    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        SimpleEmaTrendStrategy(
            symbol="",
        )

    with pytest.raises(
        ValueError,
        match="fast_period",
    ):
        SimpleEmaTrendStrategy(
            symbol="EURUSD",
            fast_period=0,
        )

    with pytest.raises(
        ValueError,
        match="smaller",
    ):
        SimpleEmaTrendStrategy(
            symbol="EURUSD",
            fast_period=10,
            slow_period=10,
        )


def test_strategy_holds_during_warm_up():
    signal = make_strategy().on_bar(
        make_context(
            [
                10.0,
                10.0,
                10.0,
                10.0,
            ]
        )
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "Warm-up"


def test_strategy_enters_long_on_fast_ema_cross_above():
    signal = make_strategy().on_bar(
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

    assert signal.action == SignalAction.ENTER_LONG
    assert signal.reason == (
        "Fast EMA crossed above slow EMA"
    )
    assert signal.metadata["fast_ema"] > (
        signal.metadata["slow_ema"]
    )


def test_strategy_exits_on_fast_ema_cross_below():
    signal = make_strategy().on_bar(
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

    assert signal.action == SignalAction.EXIT
    assert signal.reason == (
        "Fast EMA crossed below slow EMA"
    )
    assert signal.metadata["fast_ema"] < (
        signal.metadata["slow_ema"]
    )


def test_strategy_holds_without_new_cross():
    signal = make_strategy().on_bar(
        make_context(
            [
                10.0,
                11.0,
                12.0,
                13.0,
                14.0,
            ]
        )
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "No EMA crossover"


def test_strategy_signal_is_causal_and_auditable():
    context = make_context(
        [
            10.0,
            10.0,
            10.0,
            10.0,
            12.0,
        ]
    )

    strategy = make_strategy()
    signal = strategy.on_bar(context)

    assert signal.strategy_id == strategy.strategy_id
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
                10.0,
                10.0,
                10.0,
                10.0,
                12.0,
                12.0,
            ]
        ),
        strategy=make_strategy(),
    )

    assert result.signals.count == 6
    assert result.orders.count == 2
    assert result.trades.count == 1
    assert result.portfolio.is_flat is True
    assert result.trades.last_trade is not None
    assert (
        result.trades.last_trade.exit_reason
        == "END_OF_BACKTEST"
    )


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
                10.0,
                10.0,
                10.0,
                10.0,
                12.0,
                12.0,
            ]
        ),
        strategy=make_strategy(),
    )

    assert result.trades.count == 1
    assert result.fills.count == 2
    assert (
        result.trades.last_trade is not None
    )
    assert result.trades.last_trade.commission == pytest.approx(
        0.07
    )
    assert result.trades.last_trade.spread_cost == pytest.approx(
        0.2
    )
    assert result.trades.last_trade.slippage_cost == pytest.approx(
        0.1
    )
