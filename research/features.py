"""
H03 research features: intraday-clock volatility surprise.

docs/26 §H03: a candle is a true volatility expansion only when its
range is abnormal for that same time-of-day slot, not just versus
immediately preceding candles.

volatility_surprise =
    true_range(candle) /
    median(true_range of the SAME slot over the last `lookback_slots`
    trading days, using only already-closed prior candles)

Pure functions: no broker, no engine, no dataset I/O. Causal by
construction (a candle never contributes to its own median).
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from statistics import median
from typing import Sequence


def true_range(
    high: float,
    low: float,
    previous_close: float | None,
) -> float | None:
    """
    True range of one bar (candle) relative to the previous close.

    Returns None when `previous_close` is unavailable (first bar of
    the series) so callers can treat it as "no signal" instead of
    fabricating a value (docs/26: no invented candles).
    """
    if (
        not isinstance(high, (int, float))
        or not isinstance(low, (int, float))
    ):
        raise TypeError("high and low must be numbers")

    if high < low:
        raise ValueError("high cannot be below low")

    if previous_close is None:
        return None

    return max(
        high - low,
        abs(high - previous_close),
        abs(low - previous_close),
    )


def _slot_key(timestamp: datetime) -> str:
    """UTC slot key (HH:MM). All slots are computed in UTC; session
    boundaries (London/New York) are applied downstream, never with
    fixed offsets (docs/26)."""
    utc = timestamp.astimezone(__import__("zoneinfo").ZoneInfo("UTC"))
    return f"{utc.hour:02d}:{utc.minute:02d}"


def volatility_surprise(
    *,
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    timestamps: Sequence[datetime],
    lookback_slots: int = 60,
) -> list[float | None]:
    """
    Compute the H03 volatility surprise for each closed candle.

    For each candle, the median true range of the same UTC slot over
    the last `lookback_slots` PRIOR observations of that slot is used
    as the denominator. The current candle never contributes to its
    own median (causal). Returns None while the slot has no history
    (cold start -> no signal).

    All inputs must be aligned by index; timestamps must be
    timezone-aware.
    """
    if not (
        len(highs) == len(lows) == len(closes) == len(timestamps)
    ):
        raise ValueError("highs/lows/closes/timestamps must be aligned")

    if not isinstance(lookback_slots, int) or lookback_slots <= 0:
        raise ValueError("lookback_slots must be a positive integer")

    # per-slot rolling window of past true ranges (causal)
    slot_history: dict[str, deque[float]] = defaultdict(
        lambda: deque(maxlen=lookback_slots)
    )

    surprises: list[float | None] = []

    previous_close: float | None = None

    for high, low, close, timestamp in zip(
        highs, lows, closes, timestamps
    ):
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            raise ValueError(
                "timestamps must be timezone-aware datetimes (UTC)"
            )

        tr = true_range(high, low, previous_close)

        slot = _slot_key(timestamp)

        history = slot_history[slot]

        if tr is None or not history:
            surprises.append(None)
        else:
            surprises.append(tr / median(history))

        # publish this candle only AFTER its own surprise is computed
        if tr is not None:
            history.append(tr)

        previous_close = close

    return surprises


def directional_efficiency(
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> float | None:
    """
    H05/H06 feature (docs/26): abs(close - open) / (high - low).

    Returns None when high == low (no range): explicitly never
    divides by zero and never fabricates a signal.
    """
    if high < low:
        raise ValueError("high cannot be below low")

    rng = high - low

    if rng == 0:
        return None

    return abs(close - open_price) / rng


def slot_percentile(
    *,
    values: Sequence[float],
    timestamps: Sequence[datetime],
    lookback_slots: int = 60,
) -> list[float | None]:
    """
    Percentile (fraction 0-1) of each value within the historical
    distribution of the SAME UTC slot (H05/H06: p90 by time-of-day).

    percentile = count(prior values of the slot <= current) / count.
    Causal: the current observation never contributes to its own
    distribution. None on cold start (no prior history).
    """
    if len(values) != len(timestamps):
        raise ValueError("values and timestamps must be aligned")

    if not isinstance(lookback_slots, int) or lookback_slots <= 0:
        raise ValueError("lookback_slots must be a positive integer")

    slot_history: dict[str, deque[float]] = defaultdict(
        lambda: deque(maxlen=lookback_slots)
    )

    percentiles: list[float | None] = []

    for value, timestamp in zip(values, timestamps):
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            raise ValueError(
                "timestamps must be timezone-aware datetimes (UTC)"
            )

        slot = _slot_key(timestamp)
        history = slot_history[slot]

        if not history:
            percentiles.append(None)
        else:
            below = sum(1 for prior in history if prior <= value)
            percentiles.append(below / len(history))

        history.append(value)

    return percentiles

