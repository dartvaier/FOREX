import math
from dataclasses import dataclass, field
from datetime import datetime
from numbers import Real
from types import MappingProxyType
from typing import Any, Mapping

from backtest.models.enums import PositionSide


@dataclass(frozen=True, slots=True)
class Position:
    """
    Immutable snapshot of an open market position.

    FLAT is represented by the absence of a Position
    rather than by a special PositionSide value.

    A Position is created from an entry Fill and remains
    open until the Portfolio converts its closing Fill
    into a completed Trade.

    unrealized_pnl is a monetary value maintained by the
    Portfolio. The Position itself does not calculate PnL.
    """

    position_id: str
    entry_fill_id: str

    symbol: str
    side: PositionSide
    quantity: float

    entry_time: datetime
    entry_price: float

    stop_loss: float | None = None
    take_profit: float | None = None

    unrealized_pnl: float = 0.0

    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.position_id or not self.position_id.strip():
            raise ValueError(
                "position_id must be a non-empty string"
            )

        if (
            not self.entry_fill_id
            or not self.entry_fill_id.strip()
        ):
            raise ValueError(
                "entry_fill_id must be a non-empty string"
            )

        if not self.symbol or not self.symbol.strip():
            raise ValueError(
                "symbol must be a non-empty string"
            )

        if not isinstance(self.side, PositionSide):
            raise TypeError(
                "side must be a PositionSide"
            )

        self._validate_positive_number(
            "quantity",
            self.quantity,
        )

        self._validate_positive_number(
            "entry_price",
            self.entry_price,
        )

        if (
            self.entry_time.tzinfo is None
            or self.entry_time.utcoffset() is None
        ):
            raise ValueError(
                "entry_time must be timezone-aware"
            )

        if self.stop_loss is not None:
            self._validate_positive_number(
                "stop_loss",
                self.stop_loss,
            )

        if self.take_profit is not None:
            self._validate_positive_number(
                "take_profit",
                self.take_profit,
            )

        self._validate_finite_number(
            "unrealized_pnl",
            self.unrealized_pnl,
        )

        if not isinstance(self.metadata, Mapping):
            raise TypeError(
                "metadata must be a mapping"
            )

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
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
    def _validate_finite_number(
        name: str,
        value: Real,
    ) -> None:
        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            raise ValueError(
                f"{name} must be a finite number"
            )