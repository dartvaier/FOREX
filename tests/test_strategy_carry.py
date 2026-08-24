from datetime import datetime, timezone

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
from strategy import SimpleCarryStrategy


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
    hour: int,
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
) -> MarketBar:
    return MarketBar(
        time=utc_time(hour),
        open=open_,
        high=high,
        low=low,
        close=close,
        tick_volume=1000,
    )


def make_context(
    bar: MarketBar,
    *,
    bar_index: int,
) -> BacktestContext:
    return BacktestContext(
        current_time=bar.time + pd.Timedelta(hours=1),
        phase=SimulationPhase.BAR_CLOSE,
        current_bar_index=bar_index,
        current_bar=bar,
        closed_bars=(bar,),
    )


def make_strategy(
    *,
    carry_score: float,
) -> SimpleCarryStrategy:
    return SimpleCarryStrategy(
        symbol="EURUSD",
        carry_score=carry_score,
        entry_threshold=0.5,
        exit_threshold=0.0,
    )


def make_config() -> BacktestConfig:
    return BacktestConfig(
        symbol="EURUSD",
        timeframe=Timeframe.M15,
        date_from=utc_time(0),
        date_to=utc_time(5),
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
        "2026-08-08T00:00:00Z",
        periods=len(closes),
        freq="1h",
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
        SimpleCarryStrategy(
            symbol="",
        )

    with pytest.raises(
        ValueError,
        match="carry_score",
    ):
        SimpleCarryStrategy(
            symbol="EURUSD",
            carry_score=float("nan"),
        )

    with pytest.raises(
        ValueError,
        match="entry_threshold",
    ):
        SimpleCarryStrategy(
            symbol="EURUSD",
            entry_threshold=-0.1,
        )

    with pytest.raises(
        ValueError,
        match="exit_threshold",
    ):
        SimpleCarryStrategy(
            symbol="EURUSD",
            entry_threshold=0.5,
            exit_threshold=0.6,
        )


def test_strategy_enters_long_for_positive_carry_score():
    strategy = make_strategy(
        carry_score=1.0,
    )

    signal = strategy.on_bar(
        make_context(
            make_bar(
                0,
                open_=1.1000,
                high=1.1010,
                low=1.0990,
                close=1.1005,
            ),
            bar_index=0,
        )
    )

    assert signal.action == SignalAction.ENTER_LONG
    assert signal.reason == "Positive carry score"
    assert signal.metadata["carry_score"] == pytest.approx(
        1.0
    )
    assert signal.metadata["exposed"] is True


def test_strategy_enters_short_for_negative_carry_score():
    strategy = make_strategy(
        carry_score=-1.0,
    )

    signal = strategy.on_bar(
        make_context(
            make_bar(
                0,
                open_=1.1000,
                high=1.1010,
                low=1.0990,
                close=1.1005,
            ),
            bar_index=0,
        )
    )

    assert signal.action == SignalAction.ENTER_SHORT
    assert signal.reason == "Negative carry score"
    assert signal.metadata["carry_score"] == pytest.approx(
        -1.0
    )
    assert signal.metadata["exposed"] is True


def test_strategy_holds_for_neutral_carry_score():
    strategy = make_strategy(
        carry_score=0.25,
    )

    signal = strategy.on_bar(
        make_context(
            make_bar(
                0,
                open_=1.1000,
                high=1.1010,
                low=1.0990,
                close=1.1005,
            ),
            bar_index=0,
        )
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "Carry score inside neutral zone"


def test_strategy_holds_while_exposure_is_active():
    strategy = make_strategy(
        carry_score=-1.0,
    )

    first_signal = strategy.on_bar(
        make_context(
            make_bar(
                0,
                open_=1.1000,
                high=1.1010,
                low=1.0990,
                close=1.1005,
            ),
            bar_index=0,
        )
    )

    second_signal = strategy.on_bar(
        make_context(
            make_bar(
                1,
                open_=1.1005,
                high=1.1010,
                low=1.0990,
                close=1.1000,
            ),
            bar_index=1,
        )
    )

    assert first_signal.action == SignalAction.ENTER_SHORT
    assert second_signal.action == SignalAction.HOLD
    assert second_signal.reason == "Carry exposure already active"


def test_strategy_exits_when_carry_score_returns_to_neutral():
    strategy = make_strategy(
        carry_score=-1.0,
    )

    strategy.on_bar(
        make_context(
            make_bar(
                0,
                open_=1.1000,
                high=1.1010,
                low=1.0990,
                close=1.1005,
            ),
            bar_index=0,
        )
    )

    strategy.carry_score = 0.0

    signal = strategy.on_bar(
        make_context(
            make_bar(
                1,
                open_=1.1005,
                high=1.1010,
                low=1.0990,
                close=1.1000,
            ),
            bar_index=1,
        )
    )

    assert signal.action == SignalAction.EXIT
    assert signal.reason == "Carry score returned to neutral"
    assert signal.metadata["exposed"] is False


def test_strategy_reset_allows_new_entry():
    strategy = make_strategy(
        carry_score=1.0,
    )

    strategy.on_bar(
        make_context(
            make_bar(
                0,
                open_=1.1000,
                high=1.1010,
                low=1.0990,
                close=1.1005,
            ),
            bar_index=0,
        )
    )

    strategy.reset()

    signal = strategy.on_bar(
        make_context(
            make_bar(
                1,
                open_=1.1005,
                high=1.1010,
                low=1.0990,
                close=1.1000,
            ),
            bar_index=1,
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
                1.0990,
                1.0980,
                1.0970,
            ]
        ),
        strategy=make_strategy(
            carry_score=-1.0,
        ),
    )

    assert result.signals.count == 4
    assert result.orders.count == 2
    assert result.trades.count == 1
    assert result.portfolio.is_flat is True
    assert (
        result.trades.last_trade.net_pnl
        > 0.0
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
                1.1000,
                1.0990,
                1.0980,
                1.0970,
            ]
        ),
        strategy=make_strategy(
            carry_score=-1.0,
        ),
    )

    assert result.trades.count == 1
    assert result.fills.count == 2
    assert result.trades.last_trade is not None
    assert result.trades.last_trade.commission == pytest.approx(
        0.07
    )
