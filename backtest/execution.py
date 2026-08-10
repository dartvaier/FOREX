from datetime import datetime

from backtest.costs import CostModel

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

from backtest.protective_exit import ProtectiveExitDecision

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

    The MarketBar open is treated as the frictionless
    reference price.

    The configured CostModel is responsible for converting
    that reference into:

        execution_price
        spread_impact
        slippage
        commission

    Cost configuration is mandatory.

    Frictionless execution must therefore be declared
    explicitly through ZeroCostModel.
    """

    def execute_protective(
        self,
        order: Order,
        *,
        decision: ProtectiveExitDecision,
        bar: MarketBar,
        fill_time: datetime,
    ) -> ExecutionResult:
        """
        Execute a protective Stop Loss / Take Profit Order.

        The evaluator determines the frictionless reference price.

        fill_time is deterministic simulation time:

            triggered_at_open=True
                -> BAR_OPEN timestamp

            triggered_at_open=False
                -> BAR_CLOSE timestamp

        For intrabar exits, fill_time does not pretend to represent
        the unknown exact touch time inside the candle.
        """

        if not isinstance(order, Order):
            raise TypeError(
                "order must be an Order"
            )

        if not isinstance(
            decision,
            ProtectiveExitDecision,
        ):
            raise TypeError(
                "decision must be a ProtectiveExitDecision"
            )

        if not isinstance(bar, MarketBar):
            raise TypeError(
                "bar must be a MarketBar"
            )

        if not isinstance(fill_time, datetime):
            raise TypeError(
                "fill_time must be a datetime"
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
            order.metadata.get("protective_exit")
            is not True
        ):
            raise ValueError(
                "order is not a protective exit Order"
            )

        if (
            order.metadata.get("position_id")
            != decision.position_id
        ):
            raise ValueError(
                "protective Order position_id does not "
                "match decision"
            )

        if decision.bar_time != bar.time:
            raise ValueError(
                "decision bar_time does not match MarketBar"
            )

        if order.created_at != fill_time:
            raise ValueError(
                "protective Order created_at must equal fill_time"
            )

        if order.scheduled_for != fill_time:
            raise ValueError(
                "protective Order scheduled_for must equal fill_time"
            )

        if (
            decision.triggered_at_open
            and fill_time != bar.time
        ):
            raise ValueError(
                "open-triggered protective exit must fill at BAR_OPEN"
            )

        if (
            not decision.triggered_at_open
            and fill_time <= bar.time
        ):
            raise ValueError(
                "intrabar protective exit must fill after BAR_OPEN"
            )

        return self._execute_from_reference(
            order,
            fill_time=fill_time,
            reference_price=decision.reference_price,
        )


    def _execute_from_reference(
        self,
        order: Order,
        *,
        fill_time: datetime,
        reference_price: float,
    ) -> ExecutionResult:
        cost = self._cost_model.calculate(
            order,
            reference_price=reference_price,
        )
    
        fill = Fill(
            fill_id=self._make_fill_id(order),
            order_id=order.order_id,
            fill_time=fill_time,
            reference_price=cost.reference_price,
            execution_price=cost.execution_price,
            quantity=order.quantity,
            spread_impact=cost.spread_impact,
            slippage=cost.slippage,
            commission=cost.commission,
        )
    
        filled_order = replace(
            order,
            status=OrderStatus.FILLED,
        )
    
        return ExecutionResult(
            filled_order=filled_order,
            fill=fill,
        )


    def __init__(
        self,
        config: BacktestConfig,
        cost_model: CostModel,
    ) -> None:
        if not isinstance(
            config,
            BacktestConfig,
        ):
            raise TypeError(
                "config must be a BacktestConfig"
            )

        if not isinstance(
            cost_model,
            CostModel,
        ):
            raise TypeError(
                "cost_model must satisfy the CostModel protocol"
            )

        if (
            cost_model.instrument.symbol
            != config.symbol
        ):
            raise ValueError(
                "cost_model instrument symbol does not match "
                "BacktestConfig"
            )

        self._config = config
        self._cost_model = cost_model

    @property
    def config(self) -> BacktestConfig:
        return self._config

    @property
    def cost_model(self) -> CostModel:
        return self._cost_model

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

        return self._execute_from_reference(
            order,
            fill_time=event.timestamp,
            reference_price=bar.open,
        )

    def execute_at_reference(
        self,
        order: Order,
        *,
        fill_time: datetime,
        reference_price: float,
    ) -> ExecutionResult:
        """
        Execute a pending market Order at an explicit reference
        price selected by simulation policy.
        """

        if not isinstance(
            order,
            Order,
        ):
            raise TypeError(
                "order must be an Order"
            )

        if not isinstance(
            fill_time,
            datetime,
        ):
            raise TypeError(
                "fill_time must be a datetime"
            )

        if order.status != OrderStatus.PENDING:
            raise ValueError(
                "only PENDING Orders can be executed"
            )

        if order.symbol != self._config.symbol:
            raise ValueError(
                "order symbol does not match BacktestConfig"
            )

        if fill_time < order.scheduled_for:
            raise ValueError(
                "Order is not yet eligible for execution"
            )

        return self._execute_from_reference(
            order,
            fill_time=fill_time,
            reference_price=reference_price,
        )

    @staticmethod
    def _make_fill_id(
        order: Order,
    ) -> str:
        return f"FILL-{order.order_id}"
