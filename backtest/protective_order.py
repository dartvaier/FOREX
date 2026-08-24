from datetime import datetime

from backtest.models.config import BacktestConfig
from backtest.models.enums import (
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
)
from backtest.models.order import Order
from backtest.models.position import Position
from backtest.protective_exit import ProtectiveExitDecision


class ProtectiveExitOrderFactory:
    """
    Converts a protective exit decision into a full-position
    MARKET exit Order.

    Protective exits are system generated; they do not originate
    from a Strategy Signal. A deterministic synthetic signal_id
    is therefore used for auditability.
    """

    def __init__(
        self,
        config: BacktestConfig,
    ) -> None:
        if not isinstance(config, BacktestConfig):
            raise TypeError(
                "config must be a BacktestConfig"
            )

        self._config = config

    @property
    def config(self) -> BacktestConfig:
        return self._config

    def create(
        self,
        position: Position,
        decision: ProtectiveExitDecision,
        *,
        execution_time: datetime,
    ) -> Order:
        if not isinstance(position, Position):
            raise TypeError(
                "position must be a Position"
            )

        if not isinstance(
            decision,
            ProtectiveExitDecision,
        ):
            raise TypeError(
                "decision must be a ProtectiveExitDecision"
            )

        if not isinstance(execution_time, datetime):
            raise TypeError(
                "execution_time must be a datetime"
            )

        if position.symbol != self._config.symbol:
            raise ValueError(
                "position symbol does not match BacktestConfig"
            )

        if decision.position_id != position.position_id:
            raise ValueError(
                "decision position_id does not match Position"
            )

        if position.side == PositionSide.LONG:
            side = OrderSide.SELL

        elif position.side == PositionSide.SHORT:
            side = OrderSide.BUY

        else:
            raise ValueError(
                f"unsupported PositionSide: {position.side}"
            )

        return Order(
            order_id=(
                f"ORD-PROTECTIVE-{position.position_id}"
            ),
            signal_id=(
                f"SYS-PROTECTIVE-{position.position_id}"
            ),
            symbol=position.symbol,
            side=side,
            quantity=position.quantity,
            order_type=OrderType.MARKET,
            created_at=execution_time,
            scheduled_for=execution_time,
            status=OrderStatus.PENDING,
            metadata={
                "protective_exit": True,
                "position_id": position.position_id,
                "exit_reason": decision.exit_reason.value,
                "reference_price": decision.reference_price,
                "triggered_at_open": decision.triggered_at_open,
                "ambiguous": decision.ambiguous,
            },
        )