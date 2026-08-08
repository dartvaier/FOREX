from backtest.models.config import BacktestConfig
from backtest.models.enums import (
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    SignalAction,
)
from backtest.models.order import Order
from backtest.models.position import Position
from backtest.models.signal import Signal
from backtest.risk import RiskDecision


class OrderFactory:
    """
    Converts a validated Signal and RiskDecision into a
    pending market Order when the baseline trading rules
    require one.

    Baseline position policy:

    - one position at a time
    - no pyramiding
    - no automatic reversal
    - EXIT closes the full current position
    - HOLD creates no Order
    - rejected RiskDecision creates no Order

    `scheduled_for` represents the earliest timestamp at which
    the Order is eligible for execution.

    Actual execution is controlled later by the pending-order
    queue and BAR_OPEN event ordering.
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

    def create(
        self,
        signal: Signal,
        risk_decision: RiskDecision,
        current_position: Position | None = None,
    ) -> Order | None:
        if not isinstance(
            signal,
            Signal,
        ):
            raise TypeError(
                "signal must be a Signal"
            )

        if not isinstance(
            risk_decision,
            RiskDecision,
        ):
            raise TypeError(
                "risk_decision must be a RiskDecision"
            )

        if (
            current_position is not None
            and not isinstance(
                current_position,
                Position,
            )
        ):
            raise TypeError(
                "current_position must be a Position or None"
            )

        if signal.symbol != self._config.symbol:
            raise ValueError(
                "signal symbol does not match BacktestConfig"
            )

        if (
            risk_decision.signal_id
            != signal.signal_id
        ):
            raise ValueError(
                "risk_decision signal_id does not match Signal"
            )

        if (
            current_position is not None
            and current_position.symbol != signal.symbol
        ):
            raise ValueError(
                "current_position symbol does not match Signal"
            )

        if not risk_decision.approved:
            return None

        if signal.action == SignalAction.HOLD:
            return None

        if signal.action == SignalAction.EXIT:
            return self._create_exit_order(
                signal=signal,
                current_position=current_position,
                risk_decision=risk_decision,
            )

        if signal.action in (
            SignalAction.ENTER_LONG,
            SignalAction.ENTER_SHORT,
        ):
            return self._create_entry_order(
                signal=signal,
                current_position=current_position,
                risk_decision=risk_decision,
            )

        raise ValueError(
            f"unsupported SignalAction: {signal.action}"
        )

    def _create_entry_order(
        self,
        *,
        signal: Signal,
        current_position: Position | None,
        risk_decision: RiskDecision,
    ) -> Order | None:
        # Baseline:
        #
        # any existing position blocks a new entry.
        #
        # Same side:
        #   prevents pyramiding.
        #
        # Opposite side:
        #   prevents automatic reversal.
        if current_position is not None:
            return None

        if risk_decision.quantity is None:
            raise ValueError(
                "approved entry requires quantity"
            )

        if signal.action == SignalAction.ENTER_LONG:
            side = OrderSide.BUY

        elif signal.action == SignalAction.ENTER_SHORT:
            side = OrderSide.SELL

        else:
            raise ValueError(
                "entry order requires ENTER_LONG "
                "or ENTER_SHORT"
            )

        return Order(
            order_id=self._make_order_id(
                signal
            ),
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            side=side,
            quantity=risk_decision.quantity,
            order_type=OrderType.MARKET,
            created_at=signal.timestamp,
            scheduled_for=signal.timestamp,
            status=OrderStatus.PENDING,
            reason=signal.reason,
            metadata={
                "strategy_id": signal.strategy_id,
                "signal_action": signal.action.value,
                "risk_reason": risk_decision.reason,
            },
        )

    def _create_exit_order(
        self,
        *,
        signal: Signal,
        current_position: Position | None,
        risk_decision: RiskDecision,
    ) -> Order | None:
        if current_position is None:
            return None

        if current_position.side == PositionSide.LONG:
            side = OrderSide.SELL

        elif current_position.side == PositionSide.SHORT:
            side = OrderSide.BUY

        else:
            raise ValueError(
                f"unsupported PositionSide: "
                f"{current_position.side}"
            )

        return Order(
            order_id=self._make_order_id(
                signal
            ),
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            side=side,
            quantity=current_position.quantity,
            order_type=OrderType.MARKET,
            created_at=signal.timestamp,
            scheduled_for=signal.timestamp,
            status=OrderStatus.PENDING,
            reason=signal.reason,
            metadata={
                "strategy_id": signal.strategy_id,
                "signal_action": signal.action.value,
                "risk_reason": risk_decision.reason,
                "position_id": current_position.position_id,
            },
        )

    @staticmethod
    def _make_order_id(
        signal: Signal,
    ) -> str:
        """
        Deterministic baseline identifier.

        One Signal can create at most one Order in the current
        baseline.
        """

        return f"ORD-{signal.signal_id}"