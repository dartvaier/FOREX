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
from strategy import VolatilityBreakoutStrategy


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
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
) -> MarketBar:
    return MarketBar(
        time=utc_time(10)
        + timedelta(minutes=index * 15),
        open=open_,
        high=high,
        low=low,
        close=close,
        tick_volume=1000,
    )


def make_context(
    bars: list[MarketBar],
) -> BacktestContext:
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
        closed_bars=tuple(bars),
    )


def make_strategy() -> VolatilityBreakoutStrategy:
    return VolatilityBreakoutStrategy(
        symbol="EURUSD",
        entry_lookback=3,
        exit_lookback=2,
        min_range_pips=10.0,
        pip_size=0.00010,
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


def make_breakout_bars() -> list[MarketBar]:
    return [
        make_bar(
            0,
            open_=1.1000,
            high=1.1010,
            low=1.1000,
            close=1.1005,
        ),
        make_bar(
            1,
            open_=1.1005,
            high=1.1020,
            low=1.1005,
            close=1.1015,
        ),
        make_bar(
            2,
            open_=1.1015,
            high=1.1030,
            low=1.1010,
            close=1.1025,
        ),
        make_bar(
            3,
            open_=1.1025,
            high=1.1045,
            low=1.1020,
            close=1.1040,
        ),
    ]


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
        VolatilityBreakoutStrategy(
            symbol="",
        )

    with pytest.raises(
        ValueError,
        match="entry_lookback",
    ):
        VolatilityBreakoutStrategy(
            symbol="EURUSD",
            entry_lookback=0,
        )

    with pytest.raises(
        ValueError,
        match="pip_size",
    ):
        VolatilityBreakoutStrategy(
            symbol="EURUSD",
            pip_size=0.0,
        )


def test_strategy_holds_during_warm_up():
    bars = make_breakout_bars()[:3]

    signal = make_strategy().on_bar(
        make_context(bars)
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "Warm-up"


def test_strategy_enters_long_on_valid_breakout():
    signal = make_strategy().on_bar(
        make_context(
            make_breakout_bars()
        )
    )

    assert signal.action == SignalAction.ENTER_LONG
    assert signal.reason == (
        "Close broke above volatility channel"
    )
    assert signal.metadata["channel_high"] == pytest.approx(
        1.1030
    )
    assert signal.metadata["range_pips"] == pytest.approx(
        30.0
    )


def test_strategy_blocks_breakout_when_range_is_too_small():
    bars = [
        make_bar(
            0,
            open_=1.1000,
            high=1.1003,
            low=1.1000,
            close=1.1001,
        ),
        make_bar(
            1,
            open_=1.1001,
            high=1.1004,
            low=1.1001,
            close=1.1002,
        ),
        make_bar(
            2,
            open_=1.1002,
            high=1.1005,
            low=1.1002,
            close=1.1003,
        ),
        make_bar(
            3,
            open_=1.1003,
            high=1.1010,
            low=1.1003,
            close=1.1007,
        ),
    ]

    signal = make_strategy().on_bar(
        make_context(bars)
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "No volatility breakout"
    assert signal.metadata["range_pips"] == pytest.approx(
        5.0
    )


def test_strategy_exits_when_close_breaks_exit_channel_low():
    bars = [
        make_bar(
            0,
            open_=1.1000,
            high=1.1030,
            low=1.1000,
            close=1.1020,
        ),
        make_bar(
            1,
            open_=1.1020,
            high=1.1035,
            low=1.1010,
            close=1.1025,
        ),
        make_bar(
            2,
            open_=1.1025,
            high=1.1040,
            low=1.1015,
            close=1.1030,
        ),
        make_bar(
            3,
            open_=1.1030,
            high=1.1032,
            low=1.0990,
            close=1.0995,
        ),
    ]

    signal = make_strategy().on_bar(
        make_context(bars)
    )

    assert signal.action == SignalAction.EXIT
    assert signal.reason == (
        "Close broke below exit channel"
    )
    assert signal.metadata["exit_channel_low"] == pytest.approx(
        1.1010
    )


def test_strategy_holds_without_breakout_or_exit():
    bars = make_breakout_bars()

    bars[-1] = make_bar(
        3,
        open_=1.1025,
        high=1.1028,
        low=1.1020,
        close=1.1028,
    )

    signal = make_strategy().on_bar(
        make_context(bars)
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "No volatility breakout"


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
                1.1010,
                1.1020,
                1.1040,
                1.1050,
            ]
        ),
        strategy=make_strategy(),
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
                1.1010,
                1.1020,
                1.1040,
                1.1050,
            ]
        ),
        strategy=make_strategy(),
    )

    assert result.trades.count == 1
    assert result.fills.count == 2
    assert result.trades.last_trade is not None
    assert result.trades.last_trade.commission == pytest.approx(
        0.07
    )
