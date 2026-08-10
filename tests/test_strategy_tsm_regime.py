"""
Unit tests for the RF-01 regime filter on the TSM strategy
(hypothesis pre-registered in .cluster/regime-filter/plan.md).

Synthetic fixtures only: M15 closes drive the momentum signal and
H4 closed bars drive the volatility regime check. The default
regime_filter="none" must preserve the baseline behavior exactly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backtest.context import BacktestContext
from backtest.models import (
    MarketBar,
    SignalAction,
    Timeframe,
)
from backtest.models.enums import SimulationPhase
from strategy import TimeSeriesMomentumStrategy

ENTRY_THRESHOLD = 0.01


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
    timeframe_minutes: int = 15,
) -> MarketBar:
    return MarketBar(
        time=(
            utc_time(10)
            + timedelta(
                minutes=index * timeframe_minutes
            )
        ),
        open=close,
        high=close,
        low=close,
        close=close,
        tick_volume=1000,
    )


def make_m15_closes(
    closes: list[float],
) -> tuple[MarketBar, ...]:
    return tuple(
        make_bar(index, close)
        for index, close in enumerate(closes)
    )


def make_h4_closes(
    closes: list[float],
) -> tuple[MarketBar, ...]:
    return tuple(
        make_bar(index, close, timeframe_minutes=240)
        for index, close in enumerate(closes)
    )


def make_context(
    m15_closes: list[float],
    h4_closes: list[float] | None = None,
) -> BacktestContext:
    bars = make_m15_closes(m15_closes)
    current_index = len(bars) - 1

    timeframe_bars = {}

    if h4_closes is not None:
        timeframe_bars[Timeframe.H4] = make_h4_closes(
            h4_closes
        )

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
        timeframe_bars=timeframe_bars,
    )


def make_strategy(
    *,
    regime_filter: str = "none",
    regime_lookback: int = 48,
    regime_context_lookback: int = 250,
) -> TimeSeriesMomentumStrategy:
    return TimeSeriesMomentumStrategy(
        symbol="EURUSD",
        lookback=3,
        entry_threshold=ENTRY_THRESHOLD,
        exit_threshold=0.0,
        regime_filter=regime_filter,
        regime_lookback=regime_lookback,
        regime_context_lookback=regime_context_lookback,
    )


# Momentum fixture: 5 closes with a +5% move over the last 4 bars,
# above the 1% entry threshold.
MOMENTUM_UP = [1.0, 1.0, 1.0, 1.0, 1.05]
MOMENTUM_DOWN = [1.0, 1.0, 1.0, 1.0, 0.95]

# High-vol regime: flat 250-bar context (median |ret| = 0) and an
# alternating recent window (std >> 0) -> favorable.
H4_HIGH_VOL = (
    [1.0] * 203
    + [1.0, 1.1] * 24
    + [1.0]
)

# Low-vol regime: flat everything -> recent std = 0, not > 0.
H4_LOW_VOL = [1.0] * 251

# H4 warm-up: not enough closed H4 bars for the context window.
H4_WARMUP = [1.0] * 10


# ---------------------------------------------------------------------------
# Default behavior preserved (regression contract)
# ---------------------------------------------------------------------------


def test_regime_filter_none_has_no_higher_timeframes():
    strategy = make_strategy()

    assert strategy.higher_timeframes == ()
    assert strategy.higher_timeframe_bar_limits == {}


def test_regime_filter_none_enters_on_momentum_without_h4():
    strategy = make_strategy()
    context = make_context(MOMENTUM_UP)

    signal = strategy.on_bar(context)

    assert signal.action == SignalAction.ENTER_LONG
    assert signal.reason == "Positive time-series momentum"


def test_regime_filter_none_exits_on_momentum_drop():
    strategy = make_strategy()
    context = make_context(MOMENTUM_DOWN)

    signal = strategy.on_bar(context)

    assert signal.action == SignalAction.EXIT


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_regime_filter_invalid_value_rejected():
    with pytest.raises(ValueError):
        make_strategy(regime_filter="h4_vol_low")


def test_regime_lookback_must_be_positive():
    with pytest.raises(ValueError):
        make_strategy(
            regime_filter="h4_vol_high",
            regime_lookback=0,
        )


def test_regime_lookback_must_be_smaller_than_context():
    with pytest.raises(ValueError):
        make_strategy(
            regime_filter="h4_vol_high",
            regime_lookback=250,
            regime_context_lookback=250,
        )


def test_regime_context_must_be_positive():
    with pytest.raises(ValueError):
        make_strategy(
            regime_filter="h4_vol_high",
            regime_context_lookback=0,
        )


# ---------------------------------------------------------------------------
# Active filter behavior
# ---------------------------------------------------------------------------


def test_regime_filter_active_exposes_h4():
    strategy = make_strategy(regime_filter="h4_vol_high")

    assert strategy.higher_timeframes == (Timeframe.H4,)
    assert strategy.higher_timeframe_bar_limits == {
        Timeframe.H4: 251,
    }


def test_regime_favorable_high_vol_allows_entry():
    strategy = make_strategy(regime_filter="h4_vol_high")
    context = make_context(MOMENTUM_UP, H4_HIGH_VOL)

    signal = strategy.on_bar(context)

    assert signal.action == SignalAction.ENTER_LONG
    assert signal.reason == (
        "Positive momentum in favorable regime"
    )
    assert signal.metadata["regime_ok"] is True
    assert signal.metadata["regime_vol_recente"] > 0
    assert "regime_vol_mediana" in signal.metadata


def test_regime_unfavorable_low_vol_blocks_entry():
    strategy = make_strategy(regime_filter="h4_vol_high")
    context = make_context(MOMENTUM_UP, H4_LOW_VOL)

    signal = strategy.on_bar(context)

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "Regime filter blocked entry"
    assert signal.metadata["regime_ok"] is False


def test_regime_exit_is_never_blocked():
    strategy = make_strategy(regime_filter="h4_vol_high")
    context = make_context(MOMENTUM_DOWN, H4_LOW_VOL)

    signal = strategy.on_bar(context)

    assert signal.action == SignalAction.EXIT


def test_regime_h4_warmup_blocks_entry():
    strategy = make_strategy(regime_filter="h4_vol_high")
    context = make_context(MOMENTUM_UP, H4_WARMUP)

    signal = strategy.on_bar(context)

    assert signal.action == SignalAction.HOLD
    assert signal.metadata["regime_reason"] == "H4 warm-up"


def test_regime_no_h4_bars_blocks_entry():
    strategy = make_strategy(regime_filter="h4_vol_high")
    context = make_context(MOMENTUM_UP)

    signal = strategy.on_bar(context)

    assert signal.action == SignalAction.HOLD
    assert signal.metadata["regime_reason"] == "H4 warm-up"


def test_regime_no_momentum_holds_regardless_of_regime():
    strategy = make_strategy(regime_filter="h4_vol_high")
    closes = [1.0, 1.0, 1.0, 1.0, 1.005]  # below threshold

    signal = strategy.on_bar(
        make_context(closes, H4_HIGH_VOL)
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "No time-series momentum signal"
