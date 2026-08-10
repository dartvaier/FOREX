"""
Unit tests for the F10 Live Readiness package (roadmap §89-91).

All pure: no broker, no MT5, no network.
"""

import pytest

from readiness.review import (
    ReadinessState,
    collect_module_availability,
    evaluate_readiness,
)
from readiness.risk_limits import (
    RiskLimitConfig,
    evaluate_risk_limits,
    position_size_for_risk,
    risk_amount,
    stop_distance_pips,
)
from readiness.safety import (
    connection_breach_count,
    duplicate_order_ids,
    order_count_per_symbol,
)


# ---------------------------------------------------------------------------
# Readiness review
# ---------------------------------------------------------------------------


def test_module_availability_collects_required_modules():
    availability = collect_module_availability()

    assert availability["execution.interface"] is True
    assert availability["execution.mt5_execution"] is True
    assert availability["execution.monitoring"] is True
    assert availability["execution.comparison"] is True
    assert availability["backtest.risk"] is True


def test_review_ready_when_all_flags_set():
    state = ReadinessState(
        trading_enabled=True,
        kill_switch_available=True,
        monitoring_available=True,
        audit_log_available=True,
        execution_adapter_available=True,
        reconciliation_available=True,
        broker_validation_available=True,
        backtest_done=True,
        oos_done=True,
        cost_stress_done=True,
        risk_engine_done=True,
        demo_validation_done=True,
        ops_procedures_documented=True,
    )

    review = evaluate_readiness(
        state,
        module_availability={
            "backtest.risk": True,
            "execution.mt5_execution": True,
            "execution.order_validation": True,
            "execution.fill_validation": True,
            "execution.reconciliation": True,
            "execution.broker_validation": True,
            "execution.monitoring": True,
            "execution.audit_log": True,
        },
    )

    assert review.ready
    assert review.missing_items == ()


def test_review_not_ready_without_demo_validation():
    state = ReadinessState(
        backtest_done=True,
        oos_done=True,
        cost_stress_done=True,
        risk_engine_done=True,
        ops_procedures_documented=True,
    )

    review = evaluate_readiness(
        state,
        module_availability={
            "backtest.risk": True,
            "execution.mt5_execution": True,
            "execution.order_validation": True,
            "execution.fill_validation": True,
            "execution.reconciliation": True,
            "execution.broker_validation": True,
            "execution.monitoring": True,
            "execution.audit_log": True,
        },
    )

    assert not review.ready

    missing_ids = {item.item_id for item in review.missing_items}
    assert "demo_validation" in missing_ids
    assert "trading_flag" in missing_ids


def test_review_reports_missing_categories():
    review = evaluate_readiness(
        ReadinessState(),
        module_availability={},
    )

    categories = set(review.missing_categories)

    assert "operations" in categories
    assert "validation" in categories


def test_review_flags_missing_module():
    review = evaluate_readiness(
        ReadinessState(backtest_done=True),
        module_availability={
            "execution.mt5_execution": False,
        },
    )

    adapter_item = next(
        item
        for item in review.items
        if item.item_id == "adapter"
    )

    assert not adapter_item.satisfied
    assert "missing" in adapter_item.evidence


def test_review_real_state_reports_expected_gaps():
    # Real modules exist; demo/activation flags are unset by default.
    review = evaluate_readiness(
        ReadinessState(
            backtest_done=True,
            oos_done=True,
            cost_stress_done=True,
            risk_engine_done=True,
            ops_procedures_documented=True,
        )
    )

    assert not review.ready

    missing_ids = {item.item_id for item in review.missing_items}
    assert "demo_validation" in missing_ids
    assert "trading_flag" in missing_ids


# ---------------------------------------------------------------------------
# Risk limits
# ---------------------------------------------------------------------------


def test_risk_amount_is_balance_times_pct():
    assert risk_amount(10000.0, 0.01) == 100.0


def test_risk_amount_rejects_invalid_pct():
    with pytest.raises(ValueError, match="risk_pct"):
        risk_amount(10000.0, 1.5)


def test_stop_distance_pips():
    assert stop_distance_pips(1.1000, 1.0950) == pytest.approx(50.0)


def test_position_size_for_risk():
    # 100 USD risk, 50 pip stop, 10 USD/pip/lot -> 0.2 lots
    lots = position_size_for_risk(
        100.0,
        50.0,
        pip_value_per_lot=10.0,
    )

    assert lots == pytest.approx(0.2)


def test_position_size_rejects_bad_inputs():
    with pytest.raises(ValueError, match="risk_amount"):
        position_size_for_risk(0.0, 50.0, 10.0)

    with pytest.raises(ValueError, match="pip_value"):
        position_size_for_risk(100.0, 50.0, 0.0)


def test_risk_limits_ok():
    report = evaluate_risk_limits(
        balance=10000.0,
        equity=10000.0,
        daily_loss=50.0,
        current_drawdown_pct=0.02,
        open_exposure_notional=2000.0,
    )

    assert report.ok
    assert report.violations == ()


def test_risk_limits_daily_loss_violation():
    report = evaluate_risk_limits(
        balance=10000.0,
        equity=10000.0,
        daily_loss=600.0,
        current_drawdown_pct=0.02,
        open_exposure_notional=2000.0,
    )

    assert not report.ok
    assert any("daily loss" in violation for violation in report.violations)


def test_risk_limits_drawdown_violation():
    report = evaluate_risk_limits(
        balance=10000.0,
        equity=10000.0,
        daily_loss=50.0,
        current_drawdown_pct=0.15,
        open_exposure_notional=2000.0,
    )

    assert not report.ok
    assert any("drawdown" in violation for violation in report.violations)


def test_risk_limits_exposure_and_leverage_violation():
    report = evaluate_risk_limits(
        balance=10000.0,
        equity=10000.0,
        daily_loss=50.0,
        current_drawdown_pct=0.02,
        open_exposure_notional=300000.0,  # 30x leverage, 3000% exposure
        config=RiskLimitConfig(max_leverage=20.0),
    )

    assert not report.ok
    assert any("exposure" in violation for violation in report.violations)
    assert any("leverage" in violation for violation in report.violations)


# ---------------------------------------------------------------------------
# Safety helpers
# ---------------------------------------------------------------------------


def test_duplicate_order_ids_detects_duplicates():
    duplicates = duplicate_order_ids(
        ["A", "B", "A", "C", "B", "D"]
    )

    assert set(duplicates) == {"A", "B"}


def test_duplicate_order_ids_no_duplicates():
    assert duplicate_order_ids(["A", "B", "C"]) == ()


def test_connection_breach_count_trailing_failures():
    assert connection_breach_count(
        [True, True, False, False]
    ) == 2


def test_connection_breach_count_healthy():
    assert connection_breach_count([True, True, True]) == 0


def test_order_count_per_symbol():
    counts = order_count_per_symbol(
        ["EURUSD", "EURUSD", "GBPUSD"]
    )

    assert counts == {"EURUSD": 2, "GBPUSD": 1}
