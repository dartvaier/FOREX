import math
from dataclasses import dataclass
from numbers import Real
from typing import Protocol, runtime_checkable

from backtest.models.enums import OrderSide
from backtest.models.instrument import InstrumentSpecification
from backtest.models.order import Order


@dataclass(frozen=True, slots=True)
class ExecutionCost:
    """
    Immutable execution-cost calculation.

    reference_price:
        Frictionless market reference used by the execution
        simulator.

    execution_price:
        Final simulated price after spread and slippage.

    spread_impact:
        Price-distance contribution from spread for this Fill.

        The FixedCostModel treats reference_price as a
        frictionless midpoint and applies half of the configured
        full spread to each execution side.

    slippage:
        Adverse price-distance contribution from slippage.

    commission:
        Monetary commission charged for this execution.
    """

    reference_price: float
    execution_price: float

    spread_impact: float
    slippage: float

    commission: float

    def __post_init__(self) -> None:
        self._validate_positive(
            "reference_price",
            self.reference_price,
        )

        self._validate_positive(
            "execution_price",
            self.execution_price,
        )

        self._validate_non_negative(
            "spread_impact",
            self.spread_impact,
        )

        self._validate_non_negative(
            "slippage",
            self.slippage,
        )

        self._validate_non_negative(
            "commission",
            self.commission,
        )

    @staticmethod
    def _validate_positive(
        name: str,
        value: Real,
    ) -> None:
        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(
                f"{name} must be a finite positive number"
            )

    @staticmethod
    def _validate_non_negative(
        name: str,
        value: Real,
    ) -> None:
        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(
                f"{name} must be a finite "
                "non-negative number"
            )


@runtime_checkable
class CostModel(Protocol):
    """
    Contract implemented by execution cost models.
    """

    @property
    def instrument(
        self,
    ) -> InstrumentSpecification:
        ...

    def calculate(
        self,
        order: Order,
        *,
        reference_price: float,
    ) -> ExecutionCost:
        ...


class FixedCostModel:
    """
    Deterministic fixed execution-cost model.

    Configuration:

        spread_pips
            Full bid/ask spread expressed in pips.

        slippage_pips
            Adverse slippage applied independently to each Fill.

        commission_per_lot_per_side
            Monetary commission for one lot and one execution
            side.

    Price model:

        spread_distance =
            spread_pips * pip_size

        spread_impact =
            spread_distance / 2

    BUY:

        execution_price =
            reference_price
            + spread_impact
            + slippage

    SELL:

        execution_price =
            reference_price
            - spread_impact
            - slippage

    Thus a round trip with no market movement pays the complete
    configured spread:

        half spread on entry
        +
        half spread on exit
        =
        full spread

    The model does not use historical candle spread fields.
    """

    def __init__(
        self,
        instrument: InstrumentSpecification,
        *,
        spread_pips: float,
        slippage_pips: float,
        commission_per_lot_per_side: float,
    ) -> None:
        if not isinstance(
            instrument,
            InstrumentSpecification,
        ):
            raise TypeError(
                "instrument must be an "
                "InstrumentSpecification"
            )

        self._validate_non_negative(
            "spread_pips",
            spread_pips,
        )

        self._validate_non_negative(
            "slippage_pips",
            slippage_pips,
        )

        self._validate_non_negative(
            "commission_per_lot_per_side",
            commission_per_lot_per_side,
        )

        self._instrument = instrument

        self._spread_pips = float(
            spread_pips
        )

        self._slippage_pips = float(
            slippage_pips
        )

        self._commission_per_lot_per_side = float(
            commission_per_lot_per_side
        )

    @property
    def instrument(
        self,
    ) -> InstrumentSpecification:
        return self._instrument

    @property
    def spread_pips(self) -> float:
        return self._spread_pips

    @property
    def slippage_pips(self) -> float:
        return self._slippage_pips

    @property
    def commission_per_lot_per_side(
        self,
    ) -> float:
        return self._commission_per_lot_per_side

    def calculate(
        self,
        order: Order,
        *,
        reference_price: float,
    ) -> ExecutionCost:
        if not isinstance(
            order,
            Order,
        ):
            raise TypeError(
                "order must be an Order"
            )

        self._validate_positive(
            "reference_price",
            reference_price,
        )

        if (
            order.symbol
            != self._instrument.symbol
        ):
            raise ValueError(
                "order symbol does not match instrument"
            )

        full_spread_distance = (
            self._spread_pips
            * self._instrument.pip_size
        )

        spread_impact = (
            full_spread_distance
            / 2.0
        )

        slippage = (
            self._slippage_pips
            * self._instrument.pip_size
        )

        adverse_price_distance = (
            spread_impact
            + slippage
        )

        if order.side == OrderSide.BUY:
            execution_price = (
                reference_price
                + adverse_price_distance
            )

        elif order.side == OrderSide.SELL:
            execution_price = (
                reference_price
                - adverse_price_distance
            )

        else:
            raise ValueError(
                f"unsupported OrderSide: {order.side}"
            )

        if execution_price <= 0:
            raise ValueError(
                "calculated execution_price must be positive"
            )

        commission = (
            self._commission_per_lot_per_side
            * order.quantity
        )

        return ExecutionCost(
            reference_price=float(
                reference_price
            ),
            execution_price=float(
                execution_price
            ),
            spread_impact=float(
                spread_impact
            ),
            slippage=float(
                slippage
            ),
            commission=float(
                commission
            ),
        )

    @staticmethod
    def _validate_positive(
        name: str,
        value: Real,
    ) -> None:
        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(
                f"{name} must be a finite positive number"
            )

    @staticmethod
    def _validate_non_negative(
        name: str,
        value: Real,
    ) -> None:
        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(
                f"{name} must be a finite "
                "non-negative number"
            )


class ZeroCostModel(FixedCostModel):
    """
    Explicit frictionless cost model.

    Useful for regression tests where costs must intentionally
    be disabled.

    Zero costs are explicit rather than being inferred from
    historical candle data.
    """

    def __init__(
        self,
        instrument: InstrumentSpecification,
    ) -> None:
        super().__init__(
            instrument=instrument,
            spread_pips=0.0,
            slippage_pips=0.0,
            commission_per_lot_per_side=0.0,
        )