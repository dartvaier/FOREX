"""Deterministic execution-cost estimates for the backtest baseline."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
from numbers import Real

from domain.order_intent import OrderSide


def _positive(name: str, value: object) -> float:
    if not isinstance(value, Real) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return float(value)


def _non_negative(name: str, value: object) -> float:
    if not isinstance(value, Real) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return float(value)


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Costed execution terms that an Execution layer may later turn into a Fill."""

    reference_price: float
    execution_price: float
    spread_impact: float
    slippage: float
    commission: float

    def __post_init__(self) -> None:
        _positive("reference_price", self.reference_price)
        _positive("execution_price", self.execution_price)
        _non_negative("spread_impact", self.spread_impact)
        _non_negative("slippage", self.slippage)
        _non_negative("commission", self.commission)


class CostModel(ABC):
    """Maps a reference price to deterministic execution terms; it never creates a Fill."""

    @abstractmethod
    def estimate(self, *, reference_price: float, side: OrderSide, quantity: float) -> CostEstimate:
        """Return the terms for one execution without changing model state."""


@dataclass(frozen=True, slots=True)
class ZeroCostModel(CostModel):
    """Explicit no-cost diagnostic model."""

    def estimate(self, *, reference_price: float, side: OrderSide, quantity: float) -> CostEstimate:
        price = _positive("reference_price", reference_price)
        _validate_side_and_quantity(side, quantity)
        return CostEstimate(price, price, 0.0, 0.0, 0.0)


@dataclass(frozen=True, slots=True)
class FixedCostModel(CostModel):
    """Constant full spread, adverse slippage and commission per executed unit.

    ``spread`` is the complete Bid/Ask distance. Since ``reference_price`` is
    the mid price, a BUY receives ``+spread / 2`` and a SELL ``-spread / 2``.
    This is applied once per fill, so a round trip pays exactly one full spread.
    """

    spread: float = 0.0
    slippage: float = 0.0
    commission_per_unit: float = 0.0

    def __post_init__(self) -> None:
        _non_negative("spread", self.spread)
        _non_negative("slippage", self.slippage)
        _non_negative("commission_per_unit", self.commission_per_unit)

    def estimate(self, *, reference_price: float, side: OrderSide, quantity: float) -> CostEstimate:
        price = _positive("reference_price", reference_price)
        amount = _validate_side_and_quantity(side, quantity)
        spread_impact = float(self.spread) / 2.0
        adverse_price_impact = spread_impact + float(self.slippage)
        execution_price = price + adverse_price_impact if side is OrderSide.BUY else price - adverse_price_impact
        if execution_price <= 0:
            raise ValueError("costs produce a non-positive execution_price")
        return CostEstimate(price, execution_price, spread_impact, float(self.slippage), float(self.commission_per_unit) * amount)


def _validate_side_and_quantity(side: object, quantity: object) -> float:
    if not isinstance(side, OrderSide):
        raise TypeError("side must be an OrderSide")
    return _positive("quantity", quantity)
