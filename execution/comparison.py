"""
Execution comparison for the F9 Demo phase (roadmap §86-87).

Demo's objective is to compare EXPECTED execution against OBSERVED
execution:

    signal_time -> expected_price (tick at signal)
    fill_time   -> actual_price (broker fill)

This module is pure: `compare_executions` folds one expected/observed
pair into a verdict with tolerances, and `comparison_summary` aggregates
a batch of comparisons (the Demo validation period).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backtest.models.enums import OrderSide

PIP_DEFAULT = 0.0001

WITHIN_TOLERANCE = "WITHIN_TOLERANCE"
OUTSIDE_TOLERANCE = "OUTSIDE_TOLERANCE"


@dataclass(frozen=True, slots=True)
class ExpectedExecution:
    """The execution the platform expected at signal time."""

    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    expected_price: float
    signal_time: datetime
    expected_spread: float = 0.0
    expected_commission: float = 0.0


@dataclass(frozen=True, slots=True)
class ObservedExecution:
    """The execution the broker actually delivered."""

    order_id: str
    fill_time: datetime
    actual_price: float
    actual_spread: float = 0.0
    actual_commission: float = 0.0


@dataclass(frozen=True, slots=True)
class ExecutionComparison:
    """Verdict of one expected vs observed execution pair."""

    order_id: str
    price_delta: float
    price_delta_pips: float
    latency_seconds: float
    spread_delta: float
    commission_delta: float
    verdict: str
    issues: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ComparisonSummary:
    """Aggregate of a batch of comparisons (Demo validation period)."""

    total: int = 0
    within: int = 0
    outside: int = 0
    price_delta_pips_total: float = 0.0
    latency_total_seconds: float = 0.0
    latency_max_seconds: float = 0.0

    @property
    def within_rate(self) -> float:
        if self.total == 0:
            return 0.0

        return self.within / self.total

    @property
    def avg_price_delta_pips(self) -> float:
        if self.total == 0:
            return 0.0

        return self.price_delta_pips_total / self.total

    @property
    def avg_latency_seconds(self) -> float:
        if self.total == 0:
            return 0.0

        return self.latency_total_seconds / self.total


def _require_utc(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def compare_executions(
    expected: ExpectedExecution,
    observed: ObservedExecution,
    *,
    max_price_delta_pips: float,
    max_latency_seconds: float,
    pip_size: float = PIP_DEFAULT,
) -> ExecutionComparison:
    """
    Compare one expected/observed execution pair.

    Verdict is WITHIN_TOLERANCE when BOTH the absolute price deviation
    (in pips) and the signal->fill latency stay within their limits;
    every violation is listed in `issues`.
    """
    if expected.order_id != observed.order_id:
        raise ValueError(
            "expected and observed must reference the same order: "
            f"{expected.order_id!r} != {observed.order_id!r}"
        )

    if expected.expected_price <= 0:
        raise ValueError("expected_price must be positive")

    if observed.actual_price <= 0:
        raise ValueError("actual_price must be positive")

    _require_utc(expected.signal_time, "signal_time")
    _require_utc(observed.fill_time, "fill_time")

    if pip_size <= 0:
        raise ValueError("pip_size must be positive")

    price_delta = observed.actual_price - expected.expected_price
    price_delta_pips = abs(price_delta) / pip_size

    latency = max(
        (observed.fill_time - expected.signal_time).total_seconds(),
        0.0,
    )

    issues: list[str] = []

    if price_delta_pips > max_price_delta_pips:
        issues.append(
            f"price deviation {price_delta_pips:.2f} pips exceeds "
            f"tolerance {max_price_delta_pips:.2f}"
        )

    if latency > max_latency_seconds:
        issues.append(
            f"latency {latency:.3f}s exceeds tolerance "
            f"{max_latency_seconds:.3f}s"
        )

    return ExecutionComparison(
        order_id=expected.order_id,
        price_delta=price_delta,
        price_delta_pips=price_delta_pips,
        latency_seconds=latency,
        spread_delta=(
            observed.actual_spread - expected.expected_spread
        ),
        commission_delta=(
            observed.actual_commission - expected.expected_commission
        ),
        verdict=(
            WITHIN_TOLERANCE
            if not issues
            else OUTSIDE_TOLERANCE
        ),
        issues=tuple(issues),
    )


def comparison_summary(
    comparisons: list[ExecutionComparison],
) -> ComparisonSummary:
    """Aggregate a batch of comparisons (Demo validation period)."""
    total = len(comparisons)
    within = sum(
        1
        for comparison in comparisons
        if comparison.verdict == WITHIN_TOLERANCE
    )

    price_total = sum(
        comparison.price_delta_pips
        for comparison in comparisons
    )

    latency_total = sum(
        comparison.latency_seconds
        for comparison in comparisons
    )

    latency_max = max(
        (
            comparison.latency_seconds
            for comparison in comparisons
        ),
        default=0.0,
    )

    return ComparisonSummary(
        total=total,
        within=within,
        outside=total - within,
        price_delta_pips_total=price_total,
        latency_total_seconds=latency_total,
        latency_max_seconds=latency_max,
    )
