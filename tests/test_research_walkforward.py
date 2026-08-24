"""
Unit tests for the walk-forward harness (roadmap §75).

Synthetic fixtures only: window geometry, pre-registered
selection rules, summary verdicts and the OOS lockbox guard
never touch real market data.
"""

from __future__ import annotations

import pytest

from research.walkforward import (
    SELECTION_METRIC,
    TIEBREAK_METRIC,
    WalkForwardWindow,
    build_wf_windows,
    select_best,
    summarize_wf,
    windows_touch_oos,
)


# ---------------------------------------------------------------------------
# Window geometry
# ---------------------------------------------------------------------------


def test_build_wf_windows_standard_geometry():
    windows = build_wf_windows()

    assert len(windows) == 7
    assert windows[0].label == "WF-01"
    assert windows[-1].label == "WF-07"

    # Contiguity: train ends exactly where validation begins.
    for window in windows:
        assert window.train_to == window.val_from

    # Coverage: starts at the pre-registered start and ends at the
    # pre-registered exclusive end (OOS lockbox boundary).
    assert windows[0].train_from == "2015-01-01"
    assert windows[-1].val_to == "2024-01-01"

    # Train is 2 years, validation is 1 year.
    first = windows[0]
    assert first.train_from == "2015-01-01"
    assert first.train_to == "2017-01-01"
    assert first.val_from == "2017-01-01"
    assert first.val_to == "2018-01-01"

    # Step of 1 year between windows.
    assert windows[1].train_from == "2016-01-01"
    assert windows[1].train_to == "2018-01-01"
    assert windows[1].val_to == "2019-01-01"


def test_build_wf_windows_last_window_fits_end():
    # With a longer window horizon the last window must still fit
    # exactly inside the requested end.
    windows = build_wf_windows(end="2025-01-01")

    assert len(windows) == 8
    assert windows[-1].val_to == "2025-01-01"


def test_build_wf_windows_rejects_invalid_args():
    with pytest.raises(ValueError):
        build_wf_windows(train_years=0)

    with pytest.raises(ValueError):
        build_wf_windows(val_years=-1)

    with pytest.raises(ValueError):
        build_wf_windows(step_years=0)

    with pytest.raises(ValueError):
        build_wf_windows(start="2020-01-01", end="2019-01-01")


def test_build_wf_windows_happy_path_fixture():
    # A short fixture: 2 windows over 2015..2018 with 1y/1y.
    windows = build_wf_windows(
        start="2015-01-01",
        end="2018-01-01",
        train_years=1,
        val_years=1,
        step_years=1,
    )

    assert len(windows) == 2
    assert windows[0].train_to == windows[0].val_from
    assert windows[1].train_from == "2016-01-01"
    assert windows[1].val_to == "2018-01-01"


# ---------------------------------------------------------------------------
# OOS lockbox guard
# ---------------------------------------------------------------------------


def test_standard_windows_never_touch_oos():
    windows = build_wf_windows()

    assert windows_touch_oos(windows) is False


def test_custom_window_touching_oos_detected():
    windows = [
        WalkForwardWindow(
            label="WF-99",
            train_from="2020-01-01",
            train_to="2023-01-01",
            val_from="2023-01-01",
            val_to="2025-01-01",
        )
    ]

    assert windows_touch_oos(windows) is True


def test_window_ending_exactly_at_oos_boundary_ok():
    windows = [
        WalkForwardWindow(
            label="WF-07",
            train_from="2021-01-01",
            train_to="2023-01-01",
            val_from="2023-01-01",
            val_to="2024-01-01",
        )
    ]

    assert windows_touch_oos(windows) is False


# ---------------------------------------------------------------------------
# Pre-registered selection
# ---------------------------------------------------------------------------


def _row(
    expectancy: float,
    profit_factor: float,
) -> dict:
    return {
        "param_value": f"v-{expectancy}-{profit_factor}",
        "expectancy": expectancy,
        "profit_factor": profit_factor,
        "net_profit": 1.0,
    }


def test_select_best_maximizes_expectancy():
    rows = [
        _row(0.10, 1.2),
        _row(0.25, 0.9),
        _row(0.05, 2.0),
    ]

    best = select_best(rows)

    assert best["param_value"] == "v-0.25-0.9"


def test_select_best_tiebreak_by_profit_factor():
    rows = [
        _row(0.20, 1.1),
        _row(0.20, 1.7),
        _row(0.15, 3.0),
    ]

    best = select_best(rows)

    assert best["param_value"] == "v-0.2-1.7"


def test_select_best_rejects_empty():
    with pytest.raises(ValueError):
        select_best([])


def test_select_best_rejects_missing_metric():
    rows = [{"param_value": "x", "net_profit": 1.0}]

    with pytest.raises(ValueError):
        select_best(rows)

    with pytest.raises(ValueError):
        select_best(
            [{"expectancy": 1.0, "net_profit": 1.0}],
            tiebreak="missing",
        )


def test_selection_metric_constants_are_stable():
    # The pre-registered selection rule must not drift silently.
    assert SELECTION_METRIC == "expectancy"
    assert TIEBREAK_METRIC == "profit_factor"


# ---------------------------------------------------------------------------
# Summary verdicts
# ---------------------------------------------------------------------------


def _val_row(
    window: str,
    net_profit: float,
    expectancy: float,
    param: str,
    return_pct: float = 0.1,
    profit_factor: float = 1.0,
    trades: int = 10,
) -> dict:
    return {
        "window": window,
        "net_profit": net_profit,
        "expectancy": expectancy,
        "return_pct": return_pct,
        "profit_factor": profit_factor,
        "trades": trades,
        "selected_param_value": param,
        "selected_param_key": "lookback",
        "train_expectancy": 0.2,
        "train_profit_factor": 1.5,
        "train_net_profit": 100.0,
        "train_from": "2015-01-01",
        "train_to": "2017-01-01",
        "val_from": "2017-01-01",
        "val_to": "2018-01-01",
    }


def test_summarize_wf_accepts_transferable_edge():
    rows = [
        _val_row(f"WF-{i:02d}", 50.0, 0.35, "96")
        for i in range(1, 6)
    ]
    rows += [
        _val_row(f"WF-{i:02d}", -10.0, -0.1, "128")
        for i in range(6, 8)
    ]

    summary = summarize_wf(rows)

    assert summary["windows_total"] == 7
    assert summary["windows_positive"] == 5
    assert summary["positive_rate"] == pytest.approx(round(5 / 7, 4))
    assert summary["avg_val_expectancy"] > 0
    assert summary["signal_consistent"] is True
    assert summary["accepted"] is True
    assert summary["param_most_selected"] == "96"
    assert summary["param_selection_count"] == 5
    assert summary["param_distinct_count"] == 2


def test_summarize_wf_rejects_mixed_signal():
    rows = [
        _val_row(f"WF-{i:02d}", 50.0, 0.35, "96")
        for i in range(1, 4)
    ]
    rows += [
        _val_row(f"WF-{i:02d}", -40.0, -0.3, "128")
        for i in range(4, 8)
    ]

    summary = summarize_wf(rows)

    assert summary["windows_positive"] == 3
    assert summary["signal_consistent"] is False
    assert summary["accepted"] is False


def test_summarize_wf_rejects_positive_rate_but_negative_expectancy():
    # Profitable count alone is not enough: mean expectancy must be
    # positive (AGENTS.md §11 — never optimize win rate alone).
    rows = [
        _val_row(f"WF-{i:02d}", 5.0, -0.05, "96")
        for i in range(1, 6)
    ]
    rows += [
        _val_row(f"WF-{i:02d}", -10.0, -0.4, "128")
        for i in range(6, 8)
    ]

    summary = summarize_wf(rows)

    assert summary["windows_positive"] == 5
    assert summary["avg_val_expectancy"] < 0
    assert summary["accepted"] is False


def test_summarize_wf_rejects_empty():
    with pytest.raises(ValueError):
        summarize_wf([])


def test_summarize_wf_erratically_selected_params():
    # Erratic parameter selection across windows signals instability.
    rows = [
        _val_row(f"WF-{i:02d}", -30.0, -0.2, str(value))
        for i, value in enumerate(("64", "96", "128", "160",
                                   "192", "64", "128"))
    ]

    summary = summarize_wf(rows)

    assert summary["windows_positive"] == 0
    assert summary["param_distinct_count"] == 5
    assert summary["accepted"] is False
