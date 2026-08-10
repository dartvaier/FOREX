"""
Fill validation for the F9 Execution Layer.

A broker-reported fill must be checked against the order it claims to
satisfy before the platform updates its own state (roadmap §83 Fill
Validation). Pure functions: no broker, no MT5.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backtest.models.fill import Fill
from backtest.models.order import Order

PIP_DEFAULT = 0.0001


@dataclass(frozen=True, slots=True)
class FillValidationResult:
    """Verdict of a single fill validation."""

    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)

    def __bool__(self) -> bool:
        return self.valid


def validate_fill(
    order: Order,
    fill: Fill,
    *,
    max_slippage_pips: float,
    pip_size: float = PIP_DEFAULT,
) -> FillValidationResult:
    """
    Validate a broker fill against its order.

    Checks: identity (order_id), exact quantity, positive price,
    causal timing (fill cannot precede order creation) and slippage
    tolerance relative to the reference price.
    """
    errors: list[str] = []

    if fill.order_id != order.order_id:
        errors.append(
            f"fill order_id {fill.order_id!r} "
            f"does not match order {order.order_id!r}"
        )

    if fill.quantity != order.quantity:
        errors.append(
            "fill quantity must equal order quantity "
            f"({fill.quantity} != {order.quantity})"
        )

    if fill.execution_price <= 0:
        errors.append("execution_price must be positive")

    if fill.reference_price <= 0:
        errors.append("reference_price must be positive")

    if fill.fill_time < order.created_at:
        errors.append(
            "fill_time cannot precede order creation "
            "(no look-ahead / causal violation)"
        )

    if (
        fill.execution_price > 0
        and fill.reference_price > 0
    ):
        max_abs_slippage = max_slippage_pips * pip_size
        actual_slippage = abs(
            fill.execution_price - fill.reference_price
        )

        if actual_slippage > max_abs_slippage:
            errors.append(
                "slippage exceeds tolerance: "
                f"{actual_slippage:.5f} > {max_abs_slippage:.5f} "
                f"({max_slippage_pips} pips)"
            )

    if fill.commission < 0:
        errors.append("commission cannot be negative")

    if fill.spread_impact < 0:
        errors.append("spread_impact cannot be negative")

    if fill.slippage < 0:
        errors.append("slippage component cannot be negative")

    return FillValidationResult(
        valid=not errors,
        errors=tuple(errors),
    )
