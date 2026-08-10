"""
Order validation for the F9 Execution Layer.

Orders must be validated BEFORE reaching the broker (roadmap §83
Order Validation). This module is pure: no broker, no MT5, no side
effects. The engine's RiskGate already handles exposure/sizing policy;
this validator enforces broker-level constraints (symbol eligibility,
lot limits, margin, structural SL/TP sanity).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backtest.models.order import Order
from execution.interface import BrokerAccountState


@dataclass(frozen=True, slots=True)
class OrderValidationConfig:
    """Broker-level constraints for order validation."""

    max_quantity: float = 10.0
    min_quantity: float = 0.01
    allowed_symbols: tuple[str, ...] = ()
    margin_per_lot: float = 100.0
    require_stop_loss: bool = False


@dataclass(frozen=True, slots=True)
class OrderValidationResult:
    """Verdict of a single order validation."""

    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __bool__(self) -> bool:
        return self.valid


def validate_order(
    order: Order,
    account: BrokerAccountState,
    config: OrderValidationConfig,
) -> OrderValidationResult:
    """
    Validate an order against broker-level constraints.

    Pure function: raises nothing on invalid input; collects every
    violation into the result.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if config.allowed_symbols and (
        order.symbol not in config.allowed_symbols
    ):
        errors.append(
            f"symbol {order.symbol!r} not in allowed symbols"
        )

    if order.quantity <= 0:
        errors.append("quantity must be positive")

    if order.quantity < config.min_quantity:
        errors.append(
            f"quantity below minimum ({config.min_quantity})"
        )

    if order.quantity > config.max_quantity:
        errors.append(
            f"quantity above maximum ({config.max_quantity})"
        )

    if order.stop_loss is not None and order.stop_loss <= 0:
        errors.append("stop_loss must be positive")

    if order.take_profit is not None and order.take_profit <= 0:
        errors.append("take_profit must be positive")

    if (
        order.stop_loss is not None
        and order.take_profit is not None
        and order.stop_loss == order.take_profit
    ):
        errors.append("stop_loss and take_profit cannot be equal")

    if config.require_stop_loss and order.stop_loss is None:
        errors.append("stop_loss is required")
    elif order.stop_loss is None:
        warnings.append("order has no stop_loss")

    estimated_margin = order.quantity * config.margin_per_lot

    if estimated_margin > account.margin_free:
        errors.append(
            "insufficient free margin: "
            f"requires {estimated_margin:.2f} "
            f"({account.currency}), "
            f"free {account.margin_free:.2f}"
        )

    return OrderValidationResult(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
