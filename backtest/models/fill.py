import math
from dataclasses import dataclass
from datetime import datetime
from numbers import Real


@dataclass(frozen=True, slots=True)
class Fill:
    """
    Immutable record of an executed Order.

    A Fill represents actual simulated execution.

    It is distinct from:
    - Signal: strategy intent
    - Order: execution instruction

    Cost conventions used by the baseline:

    reference_price:
        Market/reference price before execution adjustments.

    execution_price:
        Effective simulated execution price after spread
        and slippage adjustments.

    spread_impact:
        Non-negative price-distance contribution attributed
        to spread.

    slippage:
        Non-negative price-distance contribution attributed
        to adverse slippage.

    commission:
        Non-negative monetary commission charged for this fill.

    Spread and slippage stored here are audit fields.
    If their effect is already embedded in execution_price,
    they must not be deducted again from PnL.
    """

    fill_id: str
    order_id: str

    fill_time: datetime

    reference_price: float
    execution_price: float
    quantity: float

    spread_impact: float = 0.0
    slippage: float = 0.0
    commission: float = 0.0

    def __post_init__(self) -> None:
        if not self.fill_id or not self.fill_id.strip():
            raise ValueError(
                "fill_id must be a non-empty string"
            )

        if not self.order_id or not self.order_id.strip():
            raise ValueError(
                "order_id must be a non-empty string"
            )

        if (
            self.fill_time.tzinfo is None
            or self.fill_time.utcoffset() is None
        ):
            raise ValueError(
                "fill_time must be timezone-aware"
            )

        self._validate_positive_number(
            "reference_price",
            self.reference_price,
        )

        self._validate_positive_number(
            "execution_price",
            self.execution_price,
        )

        self._validate_positive_number(
            "quantity",
            self.quantity,
        )

        self._validate_non_negative_number(
            "spread_impact",
            self.spread_impact,
        )

        self._validate_non_negative_number(
            "slippage",
            self.slippage,
        )

        self._validate_non_negative_number(
            "commission",
            self.commission,
        )

    @staticmethod
    def _validate_positive_number(
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
    def _validate_non_negative_number(
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
                f"{name} must be a finite non-negative number"
            )