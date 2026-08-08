from dataclasses import dataclass, replace

from backtest.clock import ClockEvent
from backtest.models.bar import MarketBar
from backtest.models.config import BacktestConfig
from backtest.models.enums import (
    OrderStatus,
    SimulationPhase,
)
from backtest.models.fill import Fill
from backtest.models.order import Order


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """
    Immutable result of a successful simulated execution.

    filled_order:
        New immutable Order snapshot with status FILLED.

    fill:
        Execution record produced from the Order.

    The original PENDING Order is never mutated.
    """

    filled_order: Order
    fill: Fill

    def __post_init__(self) -> None:
        if not isinstance(
            self.filled_order,
            Order,
        ):
            raise TypeError(
                "filled_order must be an Order"
            )

        if not isinstance(
            self.fill,
            Fill,
        ):
            raise TypeError(
                "fill must be a Fill"
            )

        if (
            self.filled_order.status
            != OrderStatus.FILLED
        ):
            raise ValueError(
                "filled_order must have FILLED status"
            )

        if (
            self.fill.order_id
            != self.filled_order.order_id
        ):
            raise ValueError(
                "fill order_id must match filled_order"
            )

        if (
            self.fill.quantity
            != self.filled_order.quantity
        ):
            raise ValueError(
                "fill quantity must match filled_order"
            )


class SimulatedExecution:
    """
    Baseline market-order execution simulator.

    Receives Orders already considered eligible by the
    PendingOrderQueue and fills them at the opening price of
    the current historical bar.

    Baseline execution model:

        reference_price = bar.open
        execution_price = bar.open
        spread_impact   = 0
        slippage        = 0
        commission      = 0

    Costs are intentionally neutral here because the official
    CostModel belongs to F5.5.

    The execution layer receives MarketBar directly because it
    is internal BacktestEngine infrastructure.

    Strategy code never receives the opening MarketBar object
    during BAR_OPEN.
    """

    def __init__(
        self,
        config: BacktestConfig,
    ) -> None:
        if not isinstance(
            config,
            BacktestConfig,
        ):
            raise TypeError(
                "config must be a BacktestConfig"
            )

        self._config = config

    @property
    def config(self) -> BacktestConfig:
        return self._config

    def execute(
        self,
        order: Order,
        *,
        event: ClockEvent,
        bar: MarketBar,
    ) -> ExecutionResult:
        """
        Execute one eligible market Order at BAR_OPEN.
        """

        if not isinstance(
            order,
            Order,
        ):
            raise TypeError(
                "order must be an Order"
            )

        if not isinstance(
            event,
            ClockEvent,
        ):
            raise TypeError(
                "event must be a ClockEvent"
            )

        if not isinstance(
            bar,
            MarketBar,
        ):
            raise TypeError(
                "bar must be a MarketBar"
            )

        if order.status != OrderStatus.PENDING:
            raise ValueError(
                "only PENDING Orders can be executed"
            )

        if order.symbol != self._config.symbol:
            raise ValueError(
                "order symbol does not match BacktestConfig"
            )

        if (
            event.phase
            != SimulationPhase.BAR_OPEN
        ):
            raise ValueError(
                "market Orders can only be executed "
                "at BAR_OPEN"
            )

        if event.bar_start != bar.time:
            raise ValueError(
                "event bar_start does not match MarketBar"
            )

        if event.timestamp != bar.time:
            raise ValueError(
                "BAR_OPEN timestamp must equal MarketBar time"
            )

        if (
            event.timestamp
            < order.scheduled_for
        ):
            raise ValueError(
                "Order is not yet eligible for execution"
            )

        reference_price = bar.open
        execution_price = reference_price

        fill = Fill(
            fill_id=self._make_fill_id(order),
            order_id=order.order_id,
            fill_time=event.timestamp,
            reference_price=reference_price,
            execution_price=execution_price,
            quantity=order.quantity,
            spread_impact=0.0,
            slippage=0.0,
            commission=0.0,
        )

        filled_order = replace(
            order,
            status=OrderStatus.FILLED,
        )

        return ExecutionResult(
            filled_order=filled_order,
            fill=fill,
        )

    @staticmethod
    def _make_fill_id(
        order: Order,
    ) -> str:
        """
        Deterministic baseline Fill identifier.

        Current baseline:

            one Order
                ↓
            one Fill
        """

        return f"FILL-{order.order_id}"