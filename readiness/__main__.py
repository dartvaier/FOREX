"""
CLI: F10 Live Readiness review.

Usage:

    python -m readiness
    python -m readiness --backtest-done --oos-done --cost-stress-done \
        --risk-engine-done --ops-documented
    python -m readiness --demo-validation-done --trading-enabled \
        --balance 10000 --equity 10000 --daily-loss 50 \
        --drawdown-pct 0.02 --exposure-notional 2000

Exit code: 0 when the review is READY, 1 otherwise (scriptable).
"""

from __future__ import annotations

import argparse

from readiness.review import (
    ReadinessReview,
    ReadinessState,
    evaluate_readiness,
)
from readiness.risk_limits import (
    RiskLimitConfig,
    RiskLimitsReport,
    evaluate_risk_limits,
)

# CLI flag -> ReadinessState field.
_STATE_FLAGS = {
    "--backtest-done": "backtest_done",
    "--oos-done": "oos_done",
    "--cost-stress-done": "cost_stress_done",
    "--risk-engine-done": "risk_engine_done",
    "--ops-documented": "ops_procedures_documented",
    "--demo-validation-done": "demo_validation_done",
    "--trading-enabled": "trading_enabled",
}

_FLAG_HELP = {
    "--backtest-done": "robust backtest completed",
    "--oos-done": "OOS lockbox consulted",
    "--cost-stress-done": "cost stress executed",
    "--risk-engine-done": "risk engine validated",
    "--ops-documented": "operational procedures documented",
    "--demo-validation-done": "demo validation period completed",
    "--trading-enabled": "trading flag explicitly enabled",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "F10 Live Readiness review "
            "(roadmap §90-91)"
        )
    )

    for flag, field in _STATE_FLAGS.items():
        parser.add_argument(
            flag,
            action="store_true",
            help=_FLAG_HELP[flag],
        )

    parser.add_argument(
        "--balance",
        type=float,
        default=None,
        help="account balance (enables the risk limits check)",
    )

    parser.add_argument(
        "--equity",
        type=float,
        default=None,
        help="account equity (defaults to balance)",
    )

    parser.add_argument(
        "--daily-loss",
        type=float,
        default=0.0,
        help="realized loss today",
    )

    parser.add_argument(
        "--drawdown-pct",
        type=float,
        default=0.0,
        help="current drawdown as a fraction (0.02 = 2 percent)",
    )

    parser.add_argument(
        "--exposure-notional",
        type=float,
        default=0.0,
        help="open exposure notional (for leverage/exposure checks)",
    )

    return parser


def format_review(review: ReadinessReview) -> str:
    """Render the review as a human-readable table."""
    lines = [
        "F10 Live Readiness Review",
        "=" * 56,
    ]

    for item in review.items:
        mark = "OK " if item.satisfied else "!! "
        lines.append(
            f"{mark}[{item.category:11s}] "
            f"{item.item_id:20s} {item.description}"
        )

        if not item.satisfied:
            lines.append(f"        -> {item.evidence}")

    lines.append("=" * 56)
    lines.append(f"READY: {review.ready}")

    if not review.ready:
        lines.append(
            "Missing categories: "
            + ", ".join(review.missing_categories)
        )

    return "\n".join(lines)


def format_risk(report: RiskLimitsReport) -> str:
    """Render the risk limits check result."""
    lines = [
        "Risk Limits",
        "=" * 56,
    ]

    if report.ok:
        lines.append("OK: all risk limits within bounds")
    else:
        for violation in report.violations:
            lines.append(f"VIOLATION: {violation}")

    return "\n".join(lines)


def _dest(flag: str) -> str:
    """Namespace attribute argparse derives from the flag."""
    return flag.lstrip("-").replace("-", "_")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    state = ReadinessState(
        **{
            field: bool(getattr(args, _dest(flag)))
            for flag, field in _STATE_FLAGS.items()
        }
    )

    review = evaluate_readiness(state)
    print(format_review(review))

    if args.balance is not None:
        report = evaluate_risk_limits(
            balance=args.balance,
            equity=args.equity if args.equity is not None else args.balance,
            daily_loss=args.daily_loss,
            current_drawdown_pct=args.drawdown_pct,
            open_exposure_notional=args.exposure_notional,
            config=RiskLimitConfig(),
        )
        print()
        print(format_risk(report))

    return 0 if review.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
