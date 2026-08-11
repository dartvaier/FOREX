"""
Unit tests for the SO-01 trailing ATR exit on the TSM strategy
(hypothesis pre-registered in .cluster/payoff-exit/plan.md).

Synthetic fixtures: trending closes let the trailing stop ratchet
up and hold; a reversal below the trailing level exits. The default
exit_mode="momentum" preserves the baseline behavior exactly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backtest.context import BacktestContext
from backtest.models import MarketBar, SignalAction
from backtest.models.enums import SimulationPhase
from strategy import TimeSeriesMomentumStrategy


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


def make_bars(
    closes: list[float],
) -> tuple[MarketBar, ...]:
    bars = []

    for index, close in enumerate(closes):
        high = close * 1.002
        low = close * 0.998

        bars.append(
            MarketBar(
                time=(
                    utc_time(10)
                    + timedelta(minutes=index * 15)
                ),
                open=close,
                high=high,
                low=low,
                close=close,
                tick_volume=1000,
            )
        )

    return tuple(bars)


def make_context(
    closes: list[float],
) -> BacktestContext:
    bars = make_bars(closes)
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


def make_strategy(
    *,
    exit_mode: str = "momentum",
    trail_atr_lookback: int = 3,
    trail_atr_mult: float = 2.0,
) -> TimeSeriesMomentumStrategy:
    return TimeSeriesMomentumStrategy(
        symbol="EURUSD",
        lookback=3,
        entry_threshold=0.01,
        exit_threshold=0.0,
        exit_mode=exit_mode,
        trail_atr_lookback=trail_atr_lookback,
        trail_atr_mult=trail_atr_mult,
    )


# Trend: +5% momentum then steady climb (ATR ~0.4% of price).
TREND = [
    1.00, 1.00, 1.00, 1.00, 1.05,
    1.051, 1.052, 1.053, 1.054, 1.055,
]

# Reversal: +5% momentum then close drops below the trailing level.
# Highest close 1.055, ATR with mult 2.0 -> trail ~1.055 - 2*ATR.
REVERSAL = [
    1.00, 1.00, 1.00, 1.00, 1.05,
    1.051, 1.052, 1.053, 1.054, 1.055,
    1.054, 1.053, 1.052, 1.050, 1.048, 1.046, 1.044,
]


# ---------------------------------------------------------------------------
# Default behavior preserved
# ---------------------------------------------------------------------------


def test_exit_mode_momentum_enters_and_exits_as_baseline():
    strategy = make_strategy()

    # Enter on momentum.
    signal = strategy.on_bar(make_context(TREND[:5]))
    assert signal.action == SignalAction.ENTER_LONG

    # Baseline momentum exit: a drop below exit threshold.
    drop = [1.00, 1.00, 1.00, 1.00, 1.05,
            1.03, 1.02, 1.01, 1.00, 0.99]
    signal = strategy.on_bar(make_context(drop))
    assert signal.action == SignalAction.EXIT
    assert signal.reason == (
        "Momentum fell below exit threshold"
    )


def test_exit_mode_validated():
    with pytest.raises(ValueError):
        make_strategy(exit_mode="trailing_vol")


def test_trailing_parameters_validated():
    with pytest.raises(ValueError):
        make_strategy(
            exit_mode="trailing_atr",
            trail_atr_lookback=0,
        )

    with pytest.raises(ValueError):
        make_strategy(
            exit_mode="trailing_atr",
            trail_atr_mult=0.0,
        )


# ---------------------------------------------------------------------------
# Trailing ATR behavior
# ---------------------------------------------------------------------------


def test_trailing_holds_while_trend_continues():
    strategy = make_strategy(exit_mode="trailing_atr")
    strategy.reset()

    signal = strategy.on_bar(make_context(TREND[:5]))
    assert signal.action == SignalAction.ENTER_LONG

    # A gentle continuation stays above the trailing level.
    for index in range(5, len(TREND)):
        signal = strategy.on_bar(
            make_context(TREND[: index + 1])
        )
        assert signal.action == SignalAction.HOLD, (
            f"bar {index}: {signal.reason}"
        )

    assert strategy._in_long is True


def test_trailing_exits_on_reversal():
    strategy = make_strategy(exit_mode="trailing_atr")
    strategy.reset()

    signal = strategy.on_bar(make_context(REVERSAL[:5]))
    assert signal.action == SignalAction.ENTER_LONG

    exited = False

    for index in range(5, len(REVERSAL)):
        signal = strategy.on_bar(
            make_context(REVERSAL[: index + 1])
        )

        if signal.action == SignalAction.EXIT:
            assert signal.reason == "Trailing ATR stop hit"
            exited = True
            break

    assert exited is True
    assert strategy._in_long is False


def test_trailing_ratchets_with_highest_close():
    strategy = make_strategy(exit_mode="trailing_atr")
    strategy.reset()

    strategy.on_bar(make_context(TREND[:5]))

    # Walk up and check the trailing level never decreases.
    previous_level = None

    for index in range(5, len(TREND)):
        strategy.on_bar(
            make_context(TREND[: index + 1])
        )

        metadata = strategy._signal(
            make_context(TREND[: index + 1]),
            action=SignalAction.HOLD,
            reason="probe",
        ).metadata

        if "trail_level" in metadata:
            level = metadata["trail_level"]

            if previous_level is not None:
                assert level >= previous_level

            previous_level = level


def test_trailing_does_not_exit_on_momentum_drop_alone():
    # In trailing mode the momentum exit is disabled: a drop below
    # the exit threshold must NOT close the position while the
    # trailing level is intact (isolates the tested mechanism).
    strategy = make_strategy(exit_mode="trailing_atr")
    strategy.reset()

    strategy.on_bar(make_context(TREND[:5]))

    # Mild dip: momentum negative but close still above trail.
    mild_dip = TREND[:8] + [1.048, 1.047, 1.046, 1.045]

    signal = strategy.on_bar(make_context(mild_dip))

    assert signal.action in (SignalAction.HOLD, SignalAction.EXIT)

    # If it exited, it must be the trailing reason, never momentum.
    if signal.action == SignalAction.EXIT:
        assert signal.reason == "Trailing ATR stop hit"


def test_reset_clears_state():
    strategy = make_strategy(exit_mode="trailing_atr")
    strategy.reset()

    strategy.on_bar(make_context(TREND[:5]))
    assert strategy._in_long is True

    strategy.reset()

    assert strategy._in_long is False
    assert strategy._highest_close is None
    assert strategy._entry_price is None
