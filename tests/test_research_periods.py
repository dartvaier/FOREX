"""
Unit tests for the F8 Development / Validation / OOS period
definitions and the lockbox guard (roadmap §74, §78).

Only pure helpers are tested; backtests reuse run_single().
"""

import pytest

from research.periods import (
    DEVELOPMENT_DATE_FROM,
    DEVELOPMENT_DATE_TO,
    OOS_DATE_FROM,
    OOS_DATE_TO,
    OOS_LOCKBOX_LABEL,
    PERIOD_ORDER,
    RESEARCH_PERIODS,
    VALIDATION_DATE_FROM,
    VALIDATION_DATE_TO,
    require_oos_allowed,
    resolve_period,
)
from research.sweep import compare_period_rows


def test_periods_are_contiguous_in_time():
    assert DEVELOPMENT_DATE_TO == VALIDATION_DATE_FROM
    assert VALIDATION_DATE_TO == OOS_DATE_FROM


def test_periods_cover_the_full_dataset():
    assert DEVELOPMENT_DATE_FROM == "2015-01-01"
    assert OOS_DATE_TO == "2027-01-01"


def test_oos_is_the_most_recent_period():
    assert OOS_DATE_FROM > VALIDATION_DATE_FROM
    assert OOS_DATE_FROM > DEVELOPMENT_DATE_FROM


def test_period_roles_match_pre_registered_contract():
    assert RESEARCH_PERIODS["dev"].role == "development"
    assert RESEARCH_PERIODS["val"].role == "validation"
    assert RESEARCH_PERIODS["oos"].role == "out-of-sample-lockbox"


def test_period_order_is_oldest_to_most_recent():
    assert PERIOD_ORDER == ("dev", "val", "oos")


def test_resolve_period_accepts_all_labels():
    for label in PERIOD_ORDER:
        period = resolve_period(label)
        assert period.label == label
        assert period.date_from < period.date_to


def test_resolve_period_is_case_insensitive():
    assert resolve_period("DEV").label == "dev"
    assert resolve_period("Val").label == "val"


def test_resolve_period_rejects_unknown():
    with pytest.raises(
        ValueError,
        match="unknown period",
    ):
        resolve_period("backtest")


def test_oos_guard_refuses_without_allow_flag():
    with pytest.raises(
        ValueError,
        match="lockbox",
    ):
        require_oos_allowed(allow_oos=False)


def test_oos_guard_accepts_explicit_allow():
    require_oos_allowed(allow_oos=True)


def test_oos_label_constant_matches_registry():
    assert OOS_LOCKBOX_LABEL == "oos"
    assert OOS_LOCKBOX_LABEL in RESEARCH_PERIODS


def test_compare_period_rows_consistent_sign():
    dev = {
        "net_profit": 100.0,
        "return_pct": 1.0,
        "max_dd_pct": 5.0,
        "win_rate": 40.0,
        "profit_factor": 1.2,
    }
    val = {
        "net_profit": 50.0,
        "return_pct": 0.5,
        "max_dd_pct": 6.0,
        "win_rate": 38.0,
        "profit_factor": 1.1,
    }

    comparison = compare_period_rows(dev, val)

    assert comparison["period"] == "dev-vs-val"
    assert comparison["signal_consistent"] is True
    assert comparison["return_delta_pct"] == -0.5
    assert comparison["net_profit_delta"] == -50.0
    assert comparison["profit_factor_delta"] == -0.1


def test_compare_period_rows_flipped_sign():
    dev = {
        "net_profit": 100.0,
        "return_pct": 1.0,
        "max_dd_pct": 5.0,
        "win_rate": 40.0,
        "profit_factor": 1.2,
    }
    val = {
        "net_profit": -30.0,
        "return_pct": -0.3,
        "max_dd_pct": 6.0,
        "win_rate": 38.0,
        "profit_factor": 0.9,
    }

    comparison = compare_period_rows(dev, val)

    assert comparison["signal_consistent"] is False


def test_compare_period_rows_zero_treated_as_neutral():
    dev = {
        "net_profit": 0.0,
        "return_pct": 0.0,
        "max_dd_pct": 5.0,
        "win_rate": 40.0,
        "profit_factor": 1.0,
    }
    val = {
        "net_profit": 0.0,
        "return_pct": 0.0,
        "max_dd_pct": 6.0,
        "win_rate": 38.0,
        "profit_factor": 1.0,
    }

    comparison = compare_period_rows(dev, val)

    assert comparison["signal_consistent"] is True
