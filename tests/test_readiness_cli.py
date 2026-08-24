"""
Unit tests for the F10 readiness CLI (readiness/__main__.py).

format_review / format_risk are pure; main() returns the exit code
(no SystemExit) so it is directly testable.
"""

import pytest

from readiness.__main__ import (
    build_parser,
    format_review,
    format_risk,
    main,
)
from readiness.review import (
    ReadinessState,
    evaluate_readiness,
)
from readiness.risk_limits import (
    RiskLimitsReport,
    evaluate_risk_limits,
)


def _full_availability():
    return {
        "backtest.risk": True,
        "execution.mt5_execution": True,
        "execution.order_validation": True,
        "execution.fill_validation": True,
        "execution.reconciliation": True,
        "execution.broker_validation": True,
        "execution.monitoring": True,
        "execution.audit_log": True,
    }


def test_format_review_ready():
    review = evaluate_readiness(
        ReadinessState(
            backtest_done=True,
            oos_done=True,
            cost_stress_done=True,
            risk_engine_done=True,
            ops_procedures_documented=True,
            demo_validation_done=True,
            trading_enabled=True,
        ),
        module_availability=_full_availability(),
    )

    text = format_review(review)

    assert "READY: True" in text
    assert "!! " not in text


def test_format_review_missing_shows_evidence():
    review = evaluate_readiness(
        ReadinessState(backtest_done=True),
        module_availability={},
    )

    text = format_review(review)

    assert "READY: False" in text
    assert "!! " in text
    assert "Missing categories" in text
    assert "missing" in text


def test_format_risk_ok():
    report = evaluate_risk_limits(
        balance=10000.0,
        equity=10000.0,
        daily_loss=50.0,
        current_drawdown_pct=0.02,
        open_exposure_notional=2000.0,
    )

    text = format_risk(report)

    assert "OK" in text


def test_format_risk_violation():
    report = RiskLimitsReport(
        violations=("drawdown 15.00% exceeds limit 10.00%",)
    )

    text = format_risk(report)

    assert "VIOLATION" in text
    assert "drawdown" in text


def test_main_exit_one_when_not_ready():
    assert main([]) == 1


def test_main_exit_zero_when_fully_ready():
    assert (
        main(
            [
                "--backtest-done",
                "--oos-done",
                "--cost-stress-done",
                "--risk-engine-done",
                "--ops-documented",
                "--demo-validation-done",
                "--trading-enabled",
            ]
        )
        == 0
    )


def test_main_risk_limits_section(capsys):
    code = main(
        [
            "--backtest-done",
            "--oos-done",
            "--cost-stress-done",
            "--risk-engine-done",
            "--ops-documented",
            "--demo-validation-done",
            "--trading-enabled",
            "--balance",
            "10000",
            "--daily-loss",
            "600",
        ]
    )

    captured = capsys.readouterr()

    assert code == 0
    assert "Risk Limits" in captured.out
    assert "VIOLATION: daily loss" in captured.out


def test_parser_flags_map_to_state_fields():
    args = build_parser().parse_args(
        ["--trading-enabled", "--demo-validation-done"]
    )

    assert args.trading_enabled is True
    assert args.demo_validation_done is True
    assert args.backtest_done is False


@pytest.mark.parametrize(
    "flag,field",
    [
        ("--backtest-done", "backtest_done"),
        ("--oos-done", "oos_done"),
        ("--cost-stress-done", "cost_stress_done"),
        ("--risk-engine-done", "risk_engine_done"),
        ("--ops-documented", "ops_procedures_documented"),
        ("--demo-validation-done", "demo_validation_done"),
        ("--trading-enabled", "trading_enabled"),
    ],
)
def test_parser_accepts_every_state_flag(flag, field):
    args = build_parser().parse_args([flag])

    # argparse derives the namespace attribute from the flag
    dest = flag.lstrip("-").replace("-", "_")
    assert getattr(args, dest) is True
    assert field in ReadinessState.__dataclass_fields__
