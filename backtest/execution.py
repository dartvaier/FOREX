"""Baseline next-available-open simulated execution."""

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from backtest.costs import CostModel
from backtest.feed import HistoricalBarFeed
from domain.fill import Fill
from domain.order_intent import OrderIntent


class ExecutionStatus(StrEnum):
    FILLED = "FILLED"
    UNFILLED = "UNFILLED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Traceable outcome of an OrderIntent without any Portfolio mutation."""

    order_id: str
    status: ExecutionStatus
    reason: str
    scheduled_for: datetime | None = None
    fill: Fill | None = None

    def __post_init__(self) -> None:
        if not self.order_id.strip():
            raise ValueError("order_id must not be empty")
        if not isinstance(self.status, ExecutionStatus):
            raise TypeError("status must be an ExecutionStatus")
        if not self.reason.strip():
            raise ValueError("reason must not be empty")
        if self.status is ExecutionStatus.FILLED:
            if not isinstance(self.fill, Fill) or self.scheduled_for != self.fill.fill_time or self.fill.order_id != self.order_id:
                raise ValueError("FILLED result must contain its matching Fill and timestamp")
        elif self.fill is not None or self.scheduled_for is not None:
            raise ValueError("non-filled result cannot contain a Fill or scheduled time")


@dataclass(frozen=True, slots=True)
class SimulatedExecution:
    """Converts an OrderIntent into a Fill at the next actual bar open.

    The class has no Strategy, Risk, Portfolio or MT5 dependency. It applies
    the supplied CostModel exactly once to the selected bar open.
    """

    cost_model: CostModel

    def __post_init__(self) -> None:
        if not isinstance(self.cost_model, CostModel):
            raise TypeError("cost_model must be a CostModel")

    def execute(self, order: OrderIntent, *, feed: HistoricalBarFeed) -> ExecutionResult:
        if not isinstance(order, OrderIntent):
            raise TypeError("order must be an OrderIntent")
        if not isinstance(feed, HistoricalBarFeed):
            raise TypeError("feed must be a HistoricalBarFeed")
        if order.symbol != feed.config.symbol:
            return ExecutionResult(order.order_id, ExecutionStatus.REJECTED, "order symbol does not match feed symbol")

        index = bisect_left(feed.bar_starts, order.created_at)
        if index == len(feed.bars):
            return ExecutionResult(order.order_id, ExecutionStatus.UNFILLED, "no next available bar open")

        bar = feed.bars[index]
        estimate = self.cost_model.estimate(reference_price=bar.open, side=order.side, quantity=order.quantity)
        fill = Fill(
            fill_id=f"sim-{order.order_id}",
            order_id=order.order_id,
            fill_time=bar.time,
            reference_price=estimate.reference_price,
            execution_price=estimate.execution_price,
            quantity=order.quantity,
            spread_impact=estimate.spread_impact,
            slippage=estimate.slippage,
            commission=estimate.commission,
        )
        return ExecutionResult(order.order_id, ExecutionStatus.FILLED, "filled at next available bar open", bar.time, fill)
