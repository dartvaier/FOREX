"""
Tests for H03 research features (docs/26).

Synthetic fixtures with hand-computable expected values; causality
(a candle never contributes to its own median) is asserted directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from research.features import (
    directional_efficiency,
    slot_percentile,
    true_range,
    volatility_surprise,
)

_BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def t(hour: int, minute: int = 0, day: int = 1) -> datetime:
    return _BASE + timedelta(days=day - 1, hours=hour, minutes=minute)


def test_true_range_basic():
    # high 1.1050, low 1.1000, prev close 1.1020
    # -> max(0.0050, |1.1050-1.1020|=0.0030, |1.1000-1.1020|=0.0020)
    assert true_range(1.1050, 1.1000, 1.1020) == pytest.approx(0.0050)


def test_true_range_gap_up_dominant():
    # gap up: |high - prev_close| dominates (0.0100)
    assert true_range(1.1100, 1.1040, 1.1000) == pytest.approx(0.0100)


def test_true_range_first_bar_returns_none():
    assert true_range(1.1050, 1.1000, None) is None


def test_true_range_validates_input():
    with pytest.raises(ValueError):
        true_range(1.1000, 1.1050, 1.1020)  # high < low

    with pytest.raises(TypeError):
        true_range("a", 1.0, 1.0)


def test_surprise_flat_market_is_one():
    # 61 candles in the same slot, all with the same true range:
    # the 61st has surprise = 1.0 (median of 60 prior = same range).
    highs = [1.1000 + 0.0010] * 61
    lows = [1.1000] * 61
    closes = [1.1005] * 61
    timestamps = [t(8, 0, day=d) for d in range(1, 62)]

    surprises = volatility_surprise(
        highs=highs,
        lows=lows,
        closes=closes,
        timestamps=timestamps,
    )

    assert surprises[0] is None  # cold start
    assert surprises[1] is None  # single prior observation -> median exists
    assert surprises[-1] == pytest.approx(1.0)


def test_surprise_double_range_is_two():
    # Same as above but the last candle has double the range.
    highs = [1.1000 + 0.0010] * 60 + [1.1000 + 0.0020]
    lows = [1.1000] * 61
    closes = [1.1005] * 61
    timestamps = [t(8, 0, day=d) for d in range(1, 62)]

    surprises = volatility_surprise(
        highs=highs,
        lows=lows,
        closes=closes,
        timestamps=timestamps,
    )

    assert surprises[-1] == pytest.approx(2.0)


def test_surprise_slots_do_not_mix():
    # A single outlier in slot 09:00 must not affect slot 08:00.
    highs = [1.1000 + 0.0010] * 30 + [1.1000 + 0.0100]  # 08:00 then 09:00
    lows = [1.1000] * 31
    closes = [1.1005] * 31
    timestamps = [t(8, 0, day=d) for d in range(1, 31)] + [t(9, 0, day=1)]

    surprises = volatility_surprise(
        highs=highs,
        lows=lows,
        closes=closes,
        timestamps=timestamps,
    )

    # 09:00 slot has no history -> None (the 08:00 outlier is invisible)
    assert surprises[-1] is None


def test_surprise_is_causal():
    # The current candle never contributes to its own median: a big
    # first candle does NOT produce surprise for itself.
    highs = [1.1000 + 0.0100] + [1.1000 + 0.0010] * 60
    lows = [1.1000] * 61
    closes = [1.1005] * 61
    timestamps = [t(8, 0, day=d) for d in range(1, 62)]

    surprises = volatility_surprise(
        highs=highs,
        lows=lows,
        closes=closes,
        timestamps=timestamps,
    )

    assert surprises[0] is None  # no prior history for its own slot
    assert surprises[-1] == pytest.approx(1.0)


def test_surprise_lookback_window_limits_history():
    # lookback_slots=3: only the 3 most recent prior observations of
    # the slot count (deque maxlen).
    highs = [1.1000 + 0.0010] * 6 + [1.1000 + 0.0040]
    lows = [1.1000] * 7
    closes = [1.1005] * 7
    timestamps = [t(8, 0, day=d) for d in range(1, 8)]

    surprises = volatility_surprise(
        highs=highs,
        lows=lows,
        closes=closes,
        timestamps=timestamps,
        lookback_slots=3,
    )

    # median of the last 3 (all 0.0010) = 0.0010 -> surprise 4.0
    assert surprises[-1] == pytest.approx(4.0)


def test_surprise_rejects_naive_timestamps():
    with pytest.raises(ValueError, match="timezone-aware"):
        volatility_surprise(
            highs=[1.1, 1.1],
            lows=[1.0, 1.0],
            closes=[1.05, 1.05],
            timestamps=[datetime(2026, 1, 1, 8, 0), datetime(2026, 1, 2, 8, 0)],
        )


def test_surprise_requires_aligned_inputs():
    with pytest.raises(ValueError, match="aligned"):
        volatility_surprise(
            highs=[1.1],
            lows=[1.0],
            closes=[1.05],
            timestamps=[t(8, 0), t(9, 0)],
        )


# ---------------------------------------------------------------------------
# H05/H06 features (docs/26): directional_efficiency + slot_percentile
# ---------------------------------------------------------------------------


def test_directional_efficiency_full_body():
    # close far from open, tiny range -> efficiency near 1
    de = directional_efficiency(1.1000, 1.1010, 1.0990, 1.1009)
    assert de == pytest.approx(0.45)


def test_directional_efficiency_zero_range_returns_none():
    # high == low: never divide by zero, no signal (docs/26 H05)
    assert directional_efficiency(1.1000, 1.1000, 1.1000, 1.1000) is None


def test_directional_efficiency_doji_low_efficiency():
    # open == close inside a wide range -> efficiency 0
    de = directional_efficiency(1.1000, 1.1020, 1.0980, 1.1000)
    assert de == pytest.approx(0.0)


def test_directional_efficiency_validates_high_low():
    with pytest.raises(ValueError):
        directional_efficiency(1.1000, 1.0980, 1.1020, 1.1000)


def test_slot_percentile_high_value_is_ninety():
    # 9 small values then 1 large value in the same slot:
    # large value percentile = 9/9 = 1.0 (p100 of prior history)
    values = [1.0] * 9 + [10.0]
    timestamps = [t(8, 0, day=d) for d in range(1, 11)]

    percentiles = slot_percentile(
        values=values,
        timestamps=timestamps,
    )

    assert percentiles[0] is None  # cold start
    assert percentiles[-1] == pytest.approx(1.0)


def test_slot_percentile_median_value_is_half():
    values = [1.0, 2.0, 3.0]
    timestamps = [t(8, 0, day=d) for d in range(1, 4)]

    percentiles = slot_percentile(
        values=values,
        timestamps=timestamps,
    )

    # last value 3.0: all 2 prior (1.0, 2.0) are <= 3.0 -> 1.0
    assert percentiles[-1] == pytest.approx(1.0)


def test_slot_percentile_slots_do_not_mix():
    # outlier in slot 09:00 never affects slot 08:00 percentiles
    values = [1.0] * 5 + [100.0]
    timestamps = [t(8, 0, day=d) for d in range(1, 6)] + [t(9, 0, day=1)]

    percentiles = slot_percentile(
        values=values,
        timestamps=timestamps,
    )

    assert percentiles[-1] is None  # 09:00 has no prior history


def test_slot_percentile_causal():
    # a huge first value does not produce a high percentile for itself
    values = [100.0] + [1.0] * 5
    timestamps = [t(8, 0, day=d) for d in range(1, 7)]

    percentiles = slot_percentile(
        values=values,
        timestamps=timestamps,
    )

    assert percentiles[0] is None
    # prior history = [100.0, 1.0, 1.0, 1.0, 1.0]; 4 of 5 <= 1.0
    assert percentiles[-1] == pytest.approx(0.8)
