"""Risk approval and order sizing for the one-position backtest baseline."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
from numbers import Real

from backtest.position import Position, PositionSide
from domain.order_intent import OrderIntent, OrderSide, OrderType
from domain.signal import Signal, SignalAction


@dataclass(frozen=True, slots=True)
class RiskLimits:
    """Deliberately narrow limits for the initial single-symbol baseline."""

    symbol: str
    max_open_positions: int = 1
    allow_pyramiding: bool = False
    allow_hedge: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol must be a non-empty string")
        if not isinstance(self.max_open_positions, int) or isinstance(self.max_open_positions, bool) or self.max_open_positions != 1:
            raise ValueError("baseline supports exactly one open position")
        if not isinstance(self.allow_pyramiding, bool):
            raise TypeError("allow_pyramiding must be a bool")
        if not isinstance(self.allow_hedge, bool):
            raise TypeError("allow_hedge must be a bool")
        if self.allow_pyramiding:
            raise ValueError("baseline does not allow pyramiding")
        if self.allow_hedge:
            raise ValueError("baseline does not allow hedge")


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """Immutable result of evaluating one Signal against the baseline limits."""

    approved: bool
    reason: str
    order_intent: OrderIntent | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.approved, bool):
            raise TypeError("approved must be a bool")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must be a non-empty string")
        if self.approved and not isinstance(self.order_intent, OrderIntent):
            raise ValueError("approved decision must contain an OrderIntent")
        if not self.approved and self.order_intent is not None:
            raise ValueError("rejected decision cannot contain an OrderIntent")


class RiskModel(ABC):
    """Transforms a Signal into an approved OrderIntent or a rejection."""

    @abstractmethod
    def evaluate(self, signal: Signal, *, position: Position | None = None) -> RiskDecision:
        """Evaluate one strategy intent without mutating Portfolio state."""


@dataclass(frozen=True, slots=True)
class FixedSizeRiskModel(RiskModel):
    """One-symbol, one-position risk gate with deterministic fixed entry size."""

    limits: RiskLimits
    fixed_quantity: float

    def __post_init__(self) -> None:
        if not isinstance(self.limits, RiskLimits):
            raise TypeError("limits must be a RiskLimits")
        if not isinstance(self.fixed_quantity, Real) or isinstance(self.fixed_quantity, bool) or not math.isfinite(self.fixed_quantity) or self.fixed_quantity <= 0:
            raise ValueError("fixed_quantity must be a finite positive number")

    def evaluate(self, signal: Signal, *, position: Position | None = None) -> RiskDecision:
        if not isinstance(signal, Signal):
            raise TypeError("signal must be a Signal")
        if position is not None and not isinstance(position, Position):
            raise TypeError("position must be a Position or None")
        if signal.symbol != self.limits.symbol:
            return RiskDecision(False, "signal symbol is outside risk limits")
        if position is not None and position.symbol != self.limits.symbol:
            return RiskDecision(False, "open position symbol is outside risk limits")
        if signal.action is SignalAction.HOLD:
            return RiskDecision(False, "HOLD does not create an order")
        if signal.action is SignalAction.ENTER_LONG:
            return self._entry(signal, position, OrderSide.BUY)
        if signal.action is SignalAction.ENTER_SHORT:
            return self._entry(signal, position, OrderSide.SELL)
        if signal.action is SignalAction.EXIT:
            return self._exit(signal, position)
        return RiskDecision(False, "unsupported signal action")

    def _entry(self, signal: Signal, position: Position | None, side: OrderSide) -> RiskDecision:
        if position is not None:
            return RiskDecision(False, "baseline permits no pyramiding or hedge")
        return RiskDecision(True, "approved fixed-size entry", self._order(signal, side, float(self.fixed_quantity)))

    def _exit(self, signal: Signal, position: Position | None) -> RiskDecision:
        if position is None:
            return RiskDecision(False, "cannot EXIT without an open position")
        side = OrderSide.SELL if position.side is PositionSide.LONG else OrderSide.BUY
        return RiskDecision(True, "approved position close", self._order(signal, side, position.quantity))

    @staticmethod
    def _order(signal: Signal, side: OrderSide, quantity: float) -> OrderIntent:
        return OrderIntent(
            order_id=f"risk-{signal.signal_id}",
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            created_at=signal.timestamp,
            metadata={"risk_action": signal.action.value},
        )
