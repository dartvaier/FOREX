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
from strategy import AsianRangeBreakoutStrategy


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


def feed_strategy(
    strategy: AsianRangeBreakoutStrategy,
    bars: list[MarketBar],
):
    signals = []

    for index, bar in enumerate(bars):
        signals.append(
            strategy.on_bar(
                make_context(
                    bar,
                    bar_index=index,
                )
            )
        )

    return signals


def make_strategy() -> AsianRangeBreakoutStrategy:
    return AsianRangeBreakoutStrategy(
        symbol="EURUSD",
        range_start_hour_utc=0,
        range_end_hour_utc=3,
        trade_end_hour_utc=6,
        min_range_pips=10.0,
        pip_size=0.00010,
    )


def make_config() -> BacktestConfig:
    return BacktestConfig(
        symbol="EURUSD",
        timeframe=Timeframe.M15,
        date_from=utc_time(0),
        date_to=utc_time(8),
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
        AsianRangeBreakoutStrategy(
            symbol="",
        )

    with pytest.raises(
        ValueError,
        match="range_start",
    ):
        AsianRangeBreakoutStrategy(
            symbol="EURUSD",
            range_start_hour_utc=6,
            range_end_hour_utc=3,
        )

    with pytest.raises(
        ValueError,
        match="pip_size",
    ):
        AsianRangeBreakoutStrategy(
            symbol="EURUSD",
            pip_size=0.0,
        )


def test_strategy_builds_range_during_asian_window():
    strategy = make_strategy()

    signals = feed_strategy(
        strategy,
        [
            make_bar(
                0,
                open_=1.1000,
                high=1.1010,
                low=1.0990,
                close=1.1000,
            ),
            make_bar(
                1,
                open_=1.1000,
                high=1.1020,
                low=1.0985,
                close=1.1010,
            ),
        ],
    )

    assert all(
        signal.action == SignalAction.HOLD
        for signal in signals
    )
    assert signals[-1].reason == "Building Asian range"
    assert signals[-1].metadata["range_high"] == pytest.approx(
        1.1020
    )
    assert signals[-1].metadata["range_low"] == pytest.approx(
        1.0985
    )


def test_strategy_enters_long_on_break_above_range():
    strategy = make_strategy()

    signals = feed_strategy(
        strategy,
        [
            make_bar(
                0,
                open_=1.1000,
                high=1.1010,
                low=1.0990,
                close=1.1000,
            ),
            make_bar(
                1,
                open_=1.1000,
                high=1.1020,
                low=1.0985,
                close=1.1010,
            ),
            make_bar(
                2,
                open_=1.1010,
                high=1.1015,
                low=1.0995,
                close=1.1005,
            ),
            make_bar(
                3,
                open_=1.1005,
                high=1.1035,
                low=1.1000,
                close=1.1030,
            ),
        ],
    )

    assert signals[-1].action == SignalAction.ENTER_LONG
    assert signals[-1].reason == (
        "Close broke above Asian range"
    )


def test_strategy_enters_short_on_break_below_range():
    strategy = make_strategy()

    signals = feed_strategy(
        strategy,
        [
            make_bar(
                0,
                open_=1.1000,
                high=1.1010,
                low=1.0990,
                close=1.1000,
            ),
            make_bar(
                1,
                open_=1.1000,
                high=1.1020,
                low=1.0985,
                close=1.1010,
            ),
            make_bar(
                2,
                open_=1.1010,
                high=1.1015,
                low=1.0995,
                close=1.1005,
            ),
            make_bar(
                3,
                open_=1.1005,
                high=1.1010,
                low=1.0970,
                close=1.0980,
            ),
        ],
    )

    assert signals[-1].action == SignalAction.ENTER_SHORT
    assert signals[-1].reason == (
        "Close broke below Asian range"
    )


def test_strategy_blocks_small_range():
    strategy = make_strategy()

    signals = feed_strategy(
        strategy,
        [
            make_bar(
                0,
                open_=1.1000,
                high=1.1002,
                low=1.1000,
                close=1.1001,
            ),
            make_bar(
                1,
                open_=1.1001,
                high=1.1003,
                low=1.1001,
                close=1.1002,
            ),
            make_bar(
                2,
                open_=1.1002,
                high=1.1004,
                low=1.1002,
                close=1.1003,
            ),
            make_bar(
                3,
                open_=1.1003,
                high=1.1010,
                low=1.1003,
                close=1.1008,
            ),
        ],
    )

    assert signals[-1].action == SignalAction.HOLD
    assert signals[-1].reason == "Asian range too small"


def test_strategy_exits_at_trade_end_after_breakout():
    strategy = make_strategy()

    signals = feed_strategy(
        strategy,
        [
            make_bar(
                0,
                open_=1.1000,
                high=1.1010,
                low=1.0990,
                close=1.1000,
            ),
            make_bar(
                1,
                open_=1.1000,
                high=1.1020,
                low=1.0985,
                close=1.1010,
            ),
            make_bar(
                2,
                open_=1.1010,
                high=1.1015,
                low=1.0995,
                close=1.1005,
            ),
            make_bar(
                3,
                open_=1.1005,
                high=1.1035,
                low=1.1000,
                close=1.1030,
            ),
            make_bar(
                6,
                open_=1.1030,
                high=1.1040,
                low=1.1020,
                close=1.1035,
            ),
        ],
    )

    assert signals[-1].action == SignalAction.EXIT
    assert signals[-1].reason == "Asian breakout time exit"


def test_strategy_reset_starts_new_session_cleanly():
    strategy = make_strategy()

    feed_strategy(
        strategy,
        [
            make_bar(
                0,
                open_=1.1000,
                high=1.1010,
                low=1.0990,
                close=1.1000,
            ),
        ],
    )

    strategy.reset()

    signal = strategy.on_bar(
        make_context(
            make_bar(
                3,
                open_=1.1000,
                high=1.1030,
                low=1.1000,
                close=1.1030,
            ),
            bar_index=0,
        )
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "No Asian range"


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
                1.1020,
                1.1005,
                1.1030,
                1.1040,
                1.1035,
                1.1030,
                1.1025,
            ]
        ),
        strategy=make_strategy(),
    )

    assert result.signals.count == 8
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
                1.1020,
                1.1005,
                1.1030,
                1.1040,
                1.1035,
                1.1030,
                1.1025,
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
