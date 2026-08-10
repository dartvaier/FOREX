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
from strategy import MultiTimeframeMomentumStrategy


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
    *,
    start: datetime | None = None,
    minutes: int = 15,
) -> MarketBar:
    if start is None:
        start = utc_time(10)

    return MarketBar(
        time=start + timedelta(minutes=index * minutes),
        open=close,
        high=close,
        low=close,
        close=close,
        tick_volume=1000,
    )


def make_bars(
    closes: list[float],
    *,
    start: datetime | None = None,
    minutes: int = 15,
) -> tuple[MarketBar, ...]:
    return tuple(
        make_bar(
            index,
            close,
            start=start,
            minutes=minutes,
        )
        for index, close in enumerate(closes)
    )


def make_context(
    m15_closes: list[float],
    h1_closes: list[float],
    h4_closes: list[float],
) -> BacktestContext:
    m15_bars = make_bars(
        m15_closes,
        start=utc_time(10),
        minutes=15,
    )

    return BacktestContext(
        current_time=m15_bars[-1].time
        + pd.Timedelta(minutes=15),
        phase=SimulationPhase.BAR_CLOSE,
        current_bar_index=len(m15_bars) - 1,
        current_bar=m15_bars[-1],
        closed_bars=m15_bars,
        timeframe_bars={
            Timeframe.H1: make_bars(
                h1_closes,
                start=utc_time(8),
                minutes=60,
            ),
            Timeframe.H4: make_bars(
                h4_closes,
                start=utc_time(0),
                minutes=240,
            ),
        },
    )


def make_strategy() -> MultiTimeframeMomentumStrategy:
    return MultiTimeframeMomentumStrategy(
        symbol="EURUSD",
        m15_lookback=2,
        h1_lookback=2,
        h4_lookback=2,
        m15_entry_threshold=0.005,
        h1_entry_threshold=0.005,
        h4_entry_threshold=0.005,
        exit_threshold=0.0,
    )


def make_config() -> BacktestConfig:
    return BacktestConfig(
        symbol="EURUSD",
        timeframe=Timeframe.M15,
        date_from=utc_time(0),
        date_to=utc_time(13),
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
    times: list[str],
    closes: list[float],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": pd.to_datetime(
                times,
                utc=True,
            ),
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "tick_volume": [
                1000
                for _ in closes
            ],
            "complete": [
                True
                for _ in closes
            ],
        }
    )


def test_strategy_validates_parameters():
    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        MultiTimeframeMomentumStrategy(
            symbol="",
        )

    with pytest.raises(
        ValueError,
        match="m15_lookback",
    ):
        MultiTimeframeMomentumStrategy(
            symbol="EURUSD",
            m15_lookback=0,
        )

    with pytest.raises(
        ValueError,
        match="h1_entry_threshold",
    ):
        MultiTimeframeMomentumStrategy(
            symbol="EURUSD",
            h1_entry_threshold=0.0,
        )


def test_strategy_holds_during_multitimeframe_warm_up():
    signal = make_strategy().on_bar(
        make_context(
            [1.1000, 1.1010, 1.1020],
            [1.1000, 1.1010],
            [1.1000, 1.1010, 1.1020],
        )
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "Warm-up"


def test_strategy_enters_long_on_bullish_alignment():
    signal = make_strategy().on_bar(
        make_context(
            [1.1000, 1.1010, 1.1120],
            [1.1000, 1.1010, 1.1120],
            [1.1000, 1.1010, 1.1120],
        )
    )

    assert signal.action == SignalAction.ENTER_LONG
    assert signal.reason == (
        "Bullish multi-timeframe alignment"
    )
    assert signal.metadata["exposure_side"] == "LONG"
    assert signal.metadata["m15_return"] > 0.005
    assert signal.metadata["h1_return"] > 0.005
    assert signal.metadata["h4_return"] > 0.005


def test_strategy_enters_short_on_bearish_alignment():
    signal = make_strategy().on_bar(
        make_context(
            [1.1120, 1.1110, 1.1000],
            [1.1120, 1.1110, 1.1000],
            [1.1120, 1.1110, 1.1000],
        )
    )

    assert signal.action == SignalAction.ENTER_SHORT
    assert signal.reason == (
        "Bearish multi-timeframe alignment"
    )
    assert signal.metadata["exposure_side"] == "SHORT"


def test_strategy_holds_when_alignment_is_already_active():
    strategy = make_strategy()

    first_signal = strategy.on_bar(
        make_context(
            [1.1000, 1.1010, 1.1120],
            [1.1000, 1.1010, 1.1120],
            [1.1000, 1.1010, 1.1120],
        )
    )

    second_signal = strategy.on_bar(
        make_context(
            [1.1010, 1.1020, 1.1130],
            [1.1010, 1.1020, 1.1130],
            [1.1010, 1.1020, 1.1130],
        )
    )

    assert first_signal.action == SignalAction.ENTER_LONG
    assert second_signal.action == SignalAction.HOLD
    assert second_signal.reason == (
        "Long alignment already active"
    )


def test_strategy_exits_when_long_alignment_is_lost():
    strategy = make_strategy()

    strategy.on_bar(
        make_context(
            [1.1000, 1.1010, 1.1120],
            [1.1000, 1.1010, 1.1120],
            [1.1000, 1.1010, 1.1120],
        )
    )

    signal = strategy.on_bar(
        make_context(
            [1.1120, 1.1110, 1.1000],
            [1.1000, 1.1010, 1.1120],
            [1.1000, 1.1010, 1.1120],
        )
    )

    assert signal.action == SignalAction.EXIT
    assert signal.reason == (
        "Multi-timeframe long alignment lost"
    )
    assert signal.metadata["exposure_side"] is None


def test_strategy_reset_allows_new_entry():
    strategy = make_strategy()

    strategy.on_bar(
        make_context(
            [1.1000, 1.1010, 1.1120],
            [1.1000, 1.1010, 1.1120],
            [1.1000, 1.1010, 1.1120],
        )
    )

    strategy.reset()

    signal = strategy.on_bar(
        make_context(
            [1.1010, 1.1020, 1.1130],
            [1.1010, 1.1020, 1.1130],
            [1.1010, 1.1020, 1.1130],
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

    strategy = MultiTimeframeMomentumStrategy(
        symbol="EURUSD",
        m15_lookback=1,
        h1_lookback=1,
        h4_lookback=1,
        m15_entry_threshold=0.0001,
        h1_entry_threshold=0.0001,
        h4_entry_threshold=0.0001,
    )

    result = engine.run(
        dataframe=make_dataframe(
            [
                "2026-08-08T11:45:00Z",
                "2026-08-08T12:00:00Z",
                "2026-08-08T12:15:00Z",
            ],
            [
                1.1000,
                1.1010,
                1.1020,
            ],
        ),
        strategy=strategy,
        higher_timeframe_dataframes={
            Timeframe.H1: make_dataframe(
                [
                    "2026-08-08T10:00:00Z",
                    "2026-08-08T11:00:00Z",
                ],
                [
                    1.1000,
                    1.1010,
                ],
            ),
            Timeframe.H4: make_dataframe(
                [
                    "2026-08-08T00:00:00Z",
                    "2026-08-08T08:00:00Z",
                ],
                [
                    1.1000,
                    1.1010,
                ],
            ),
        },
    )

    assert result.signals.count == 3
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

    strategy = MultiTimeframeMomentumStrategy(
        symbol="EURUSD",
        m15_lookback=1,
        h1_lookback=1,
        h4_lookback=1,
        m15_entry_threshold=0.0001,
        h1_entry_threshold=0.0001,
        h4_entry_threshold=0.0001,
    )

    result = engine.run(
        dataframe=make_dataframe(
            [
                "2026-08-08T11:45:00Z",
                "2026-08-08T12:00:00Z",
                "2026-08-08T12:15:00Z",
            ],
            [
                1.1000,
                1.1010,
                1.1020,
            ],
        ),
        strategy=strategy,
        higher_timeframe_dataframes={
            Timeframe.H1: make_dataframe(
                [
                    "2026-08-08T10:00:00Z",
                    "2026-08-08T11:00:00Z",
                ],
                [
                    1.1000,
                    1.1010,
                ],
            ),
            Timeframe.H4: make_dataframe(
                [
                    "2026-08-08T00:00:00Z",
                    "2026-08-08T08:00:00Z",
                ],
                [
                    1.1000,
                    1.1010,
                ],
            ),
        },
    )

    assert result.trades.count == 1
    assert result.fills.count == 2
    assert result.trades.last_trade is not None
    assert result.trades.last_trade.commission == pytest.approx(
        0.07
    )
