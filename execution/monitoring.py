"""
Execution monitoring metrics for the F9 Execution Layer.

Aggregates execution reports into the Demo metrics required by
roadmap §87 (signal_time, order_time, fill_time, expected vs actual
price, spread, slippage, commission, latency, rejection).

Pure and immutable: `update_metrics` returns a new ExecutionMetrics
instead of mutating state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backtest.models.enums import OrderStatus
from backtest.models.fill import Fill
from backtest.models.order import Order
from execution.interface import ExecutionReport

PIP_DEFAULT = 0.0001


@dataclass(frozen=True, slots=True)
class ExecutionMetrics:
    """Accumulated execution metrics (immutable)."""

    total_orders: int = 0
    filled: int = 0
    rejected: int = 0
    cancelled: int = 0
    latency_total_seconds: float = 0.0
    latency_max_seconds: float = 0.0
    slippage_total_pips: float = 0.0
    slippage_max_pips: float = 0.0

    @property
    def rejection_rate(self) -> float:
        """Rejections over total orders (0.0 when no orders)."""
        if self.total_orders == 0:
            return 0.0

        return self.rejected / self.total_orders

    @property
    def avg_latency_seconds(self) -> float:
        if self.filled == 0:
            return 0.0

        return self.latency_total_seconds / self.filled

    @property
    def avg_slippage_pips(self) -> float:
        if self.filled == 0:
            return 0.0

        return self.slippage_total_pips / self.filled


def latency_seconds(
    order_created_at: datetime,
    fill_time: datetime,
) -> float:
    """Signal-to-fill latency in seconds (non-negative)."""
    delta = (fill_time - order_created_at).total_seconds()

    return max(delta, 0.0)


def slippage_pips(
    fill: Fill,
    *,
    pip_size: float = PIP_DEFAULT,
) -> float:
    """Observed slippage in pips (non-negative)."""
    if pip_size <= 0:
        raise ValueError("pip_size must be positive")

    return abs(fill.execution_price - fill.reference_price) / pip_size


def update_metrics(
    metrics: ExecutionMetrics,
    report: ExecutionReport,
    order: Order,
    *,
    pip_size: float = PIP_DEFAULT,
) -> ExecutionMetrics:
    """
    Fold one ExecutionReport into the metrics.

    FILLED reports contribute latency (signal->fill) and slippage;
    REJECTED/CANCELLED reports contribute their counters.
    """
    total = metrics.total_orders + 1

    if report.status == OrderStatus.FILLED and report.fill is not None:
        fill_latency = latency_seconds(
            order.created_at,
            report.fill.fill_time,
        )
        fill_slippage = slippage_pips(
            report.fill,
            pip_size=pip_size,
        )

        return ExecutionMetrics(
            total_orders=total,
            filled=metrics.filled + 1,
            rejected=metrics.rejected,
            cancelled=metrics.cancelled,
            latency_total_seconds=(
                metrics.latency_total_seconds + fill_latency
            ),
            latency_max_seconds=max(
                metrics.latency_max_seconds,
                fill_latency,
            ),
            slippage_total_pips=(
                metrics.slippage_total_pips + fill_slippage
            ),
            slippage_max_pips=max(
                metrics.slippage_max_pips,
                fill_slippage,
            ),
        )

    if report.status == OrderStatus.REJECTED:
        return ExecutionMetrics(
            total_orders=total,
            filled=metrics.filled,
            rejected=metrics.rejected + 1,
            cancelled=metrics.cancelled,
            latency_total_seconds=metrics.latency_total_seconds,
            latency_max_seconds=metrics.latency_max_seconds,
            slippage_total_pips=metrics.slippage_total_pips,
            slippage_max_pips=metrics.slippage_max_pips,
        )

    if report.status == OrderStatus.CANCELLED:
        return ExecutionMetrics(
            total_orders=total,
            filled=metrics.filled,
            rejected=metrics.rejected,
            cancelled=metrics.cancelled + 1,
            latency_total_seconds=metrics.latency_total_seconds,
            latency_max_seconds=metrics.latency_max_seconds,
            slippage_total_pips=metrics.slippage_total_pips,
            slippage_max_pips=metrics.slippage_max_pips,
        )

    # Other statuses (e.g. UNFILLED): count the attempt only.
    return ExecutionMetrics(
        total_orders=total,
        filled=metrics.filled,
        rejected=metrics.rejected,
        cancelled=metrics.cancelled,
        latency_total_seconds=metrics.latency_total_seconds,
        latency_max_seconds=metrics.latency_max_seconds,
        slippage_total_pips=metrics.slippage_total_pips,
        slippage_max_pips=metrics.slippage_max_pips,
    )
