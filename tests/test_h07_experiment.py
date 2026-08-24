"""Regression tests for chronological H07 weekly-gap detection."""

import pandas as pd
import pytest

from research.h07_experiment import _atr_h1_14_before, detect_gaps


def test_atr_excludes_h1_bar_that_has_not_closed_before_decision():
    times = pd.date_range(
        "2025-03-09T10:00:00Z",
        periods=15,
        freq="1h",
    )
    h1 = pd.DataFrame(
        {
            "time": times,
            "high": [1.0010] * 14 + [1.1000],
            "low": [0.9990] * 14 + [0.9000],
            "close": [1.0000] * 15,
        }
    )

    atr = _atr_h1_14_before(
        h1,
        pd.Timestamp("2025-03-10T00:15:00Z"),
    )

    assert atr == pytest.approx(0.0020)


def test_detect_gaps_preserves_chronological_iso_week_order():
    """Weeks 09/10/11 must not be ordered lexicographically as 10/11/09."""
    m15 = pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2025-02-24T00:00:00Z",  # ISO week 09
                    "2025-03-03T00:00:00Z",  # ISO week 10
                    "2025-03-10T00:00:00Z",  # ISO week 11
                ],
                utc=True,
            ),
            "open": [1.0000, 1.0010, 1.0030],
            "high": [1.0005, 1.0015, 1.0035],
            "low": [0.9995, 1.0005, 1.0025],
            "close": [1.0000, 1.0020, 1.0040],
        }
    )
    h1_times = pd.date_range(
        "2025-02-20T00:00:00Z",
        "2025-03-10T00:00:00Z",
        freq="1h",
        inclusive="left",
    )
    h1 = pd.DataFrame(
        {
            "time": h1_times,
            "high": 1.0010,
            "low": 0.9990,
            "close": 1.0000,
        }
    )

    events = detect_gaps(m15, h1, threshold=0.0)

    assert [event["week"] for event in events] == [
        "2025-W10",
        "2025-W11",
    ]
    assert [event["first_idx"] for event in events] == [1, 2]
    assert [event["gap"] for event in events] == pytest.approx(
        [0.0010, 0.0010]
    )
