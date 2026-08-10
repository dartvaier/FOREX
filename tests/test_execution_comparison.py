"""
Unit tests for the F9 execution comparison (roadmap §86-87).

Pure functions; no broker, no MT5, no network.
"""

from datetime import datetime, timedelta, timezone

import pytest

from backtest.models.enums import OrderSide
from execution.comparison import (
    OUTSIDE_TOLERANCE,
    WITHIN_TOLERANCE,
    ExpectedExecution,
    ObservedExecution,
    compare_executions,
    comparison_summary,
)

UTC = timezone.utc
T0 = datetime(2026, 8, 10, 12, 0, 0, tzinfo=UTC)


def make_expected(
    *,
    order_id: str = "ORD-1",
    expected_price: float = 1.0950,
    signal_time: datetime = T0,
    expected_spread: float = 2.0,
    expected_commission: float = 0.35,
) -> ExpectedExecution:
    return ExpectedExecution(
        order_id=order_id,
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.1,
        expected_price=expected_price,
        signal_time=signal_time,
        expected_spread=expected_spread,
        expected_commission=expected_commission,
    )


def make_observed(
    *,
    order_id: str = "ORD-1",
    actual_price: float = 1.0951,
    fill_time: datetime = T0 + timedelta(seconds=1),
    actual_spread: float = 2.5,
    actual_commission: float = 0.35,
) -> ObservedExecution:
    return ObservedExecution(
        order_id=order_id,
        fill_time=fill_time,
        actual_price=actual_price,
        actual_spread=actual_spread,
        actual_commission=actual_commission,
    )


def test_within_tolerance():
    comparison = compare_executions(
        make_expected(),
        make_observed(),
        max_price_delta_pips=3.0,
        max_latency_seconds=5.0,
    )

    assert comparison.verdict == WITHIN_TOLERANCE
    assert comparison.issues == ()


def test_price_outside_tolerance():
    comparison = compare_executions(
        make_expected(expected_price=1.0950),
        make_observed(actual_price=1.0960),
        max_price_delta_pips=2.0,
        max_latency_seconds=5.0,
    )

    assert comparison.verdict == OUTSIDE_TOLERANCE
    assert any("price deviation" in issue for issue in comparison.issues)
    assert comparison.price_delta_pips == pytest.approx(10.0)


def test_latency_outside_tolerance():
    comparison = compare_executions(
        make_expected(),
        make_observed(fill_time=T0 + timedelta(seconds=8)),
        max_price_delta_pips=3.0,
        max_latency_seconds=5.0,
    )

    assert comparison.verdict == OUTSIDE_TOLERANCE
    assert any("latency" in issue for issue in comparison.issues)
    assert comparison.latency_seconds == 8.0


def test_both_violations_listed():
    comparison = compare_executions(
        make_expected(),
        make_observed(
            actual_price=1.0960,
            fill_time=T0 + timedelta(seconds=8),
        ),
        max_price_delta_pips=2.0,
        max_latency_seconds=5.0,
    )

    assert comparison.verdict == OUTSIDE_TOLERANCE
    assert len(comparison.issues) == 2


def test_price_delta_sign_preserved():
    comparison = compare_executions(
        make_expected(expected_price=1.0950),
        make_observed(actual_price=1.0940),
        max_price_delta_pips=20.0,
        max_latency_seconds=5.0,
    )

    # BUY filled below expected: negative delta (favorable)
    assert comparison.price_delta == pytest.approx(-0.0010)


def test_spread_and_commission_deltas():
    comparison = compare_executions(
        make_expected(
            expected_spread=2.0,
            expected_commission=0.35,
        ),
        make_observed(
            actual_spread=3.0,
            actual_commission=0.40,
        ),
        max_price_delta_pips=3.0,
        max_latency_seconds=5.0,
    )

    assert comparison.spread_delta == pytest.approx(1.0)
    assert comparison.commission_delta == pytest.approx(0.05)


def test_order_id_mismatch_raises():
    with pytest.raises(ValueError, match="same order"):
        compare_executions(
            make_expected(order_id="ORD-1"),
            make_observed(order_id="ORD-2"),
            max_price_delta_pips=3.0,
            max_latency_seconds=5.0,
        )


def test_non_positive_price_raises():
    with pytest.raises(ValueError, match="expected_price"):
        compare_executions(
            make_expected(expected_price=0.0),
            make_observed(),
            max_price_delta_pips=3.0,
            max_latency_seconds=5.0,
        )


def test_naive_timestamp_raises():
    naive = datetime(2026, 8, 10, 12, 0, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        compare_executions(
            make_expected(signal_time=naive),
            make_observed(),
            max_price_delta_pips=3.0,
            max_latency_seconds=5.0,
        )


def test_latency_clamped_to_zero():
    comparison = compare_executions(
        make_expected(signal_time=T0),
        make_observed(fill_time=T0 - timedelta(seconds=4)),
        max_price_delta_pips=3.0,
        max_latency_seconds=5.0,
    )

    assert comparison.latency_seconds == 0.0


def test_summary_aggregates_batch():
    comparisons = [
        compare_executions(
            make_expected(order_id=f"ORD-{i}"),
            make_observed(
                order_id=f"ORD-{i}",
                actual_price=1.0951,
                fill_time=T0 + timedelta(seconds=2),
            ),
            max_price_delta_pips=2.0,
            max_latency_seconds=5.0,
        )
        for i in range(3)
    ]
    comparisons.append(
        compare_executions(
            make_expected(order_id="ORD-9"),
            make_observed(
                order_id="ORD-9",
                actual_price=1.0970,
            ),
            max_price_delta_pips=2.0,
            max_latency_seconds=5.0,
        )
    )

    summary = comparison_summary(comparisons)

    assert summary.total == 4
    assert summary.within == 3
    assert summary.outside == 1
    assert summary.within_rate == pytest.approx(0.75)
    assert summary.avg_latency_seconds == pytest.approx(1.75)
    assert summary.latency_max_seconds == pytest.approx(2.0)


def test_summary_empty_is_zero():
    summary = comparison_summary([])

    assert summary.total == 0
    assert summary.within_rate == 0.0
    assert summary.avg_price_delta_pips == 0.0
