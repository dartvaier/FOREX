import math
from dataclasses import dataclass, field
from datetime import datetime
from numbers import Real
from types import MappingProxyType
from typing import Any, Mapping

from backtest.models.enums import ExitReason, PositionSide


@dataclass(frozen=True, slots=True)
class Trade:
    """
    Immutable record of a completed trade.

    A Trade links the lifecycle of an opened Position
    to its closing Fill.

    PnL and cost values are stored rather than calculated
    here. Their calculation belongs to Portfolio / accounting
    components.

    Cost fields are monetary audit values.

    The Trade model does not enforce:

        net_pnl =
            gross_pnl
            - spread_cost
            - slippage_cost
            - commission
            + swap

    because some execution models may already embed spread
    and slippage into execution prices.

    The accounting component is responsible for applying
    one consistent convention without double-counting costs.
    """

    trade_id: str
    position_id: str

    strategy_id: str
    symbol: str
    side: PositionSide

    entry_fill_id: str
    exit_fill_id: str

    entry_time: datetime
    exit_time: datetime

    entry_price: float
    exit_price: float

    quantity: float

    gross_pnl: float
    net_pnl: float

    spread_cost: float = 0.0
    slippage_cost: float = 0.0
    commission: float = 0.0
    swap: float = 0.0

    bars_held: int = 0

    exit_reason: ExitReason = ExitReason.STRATEGY_EXIT

    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._validate_non_empty_string(
            "trade_id",
            self.trade_id,
        )

        self._validate_non_empty_string(
            "position_id",
            self.position_id,
        )

        self._validate_non_empty_string(
            "strategy_id",
            self.strategy_id,
        )

        self._validate_non_empty_string(
            "symbol",
            self.symbol,
        )

        self._validate_non_empty_string(
            "entry_fill_id",
            self.entry_fill_id,
        )

        self._validate_non_empty_string(
            "exit_fill_id",
            self.exit_fill_id,
        )

        if not isinstance(self.side, PositionSide):
            raise TypeError(
                "side must be a PositionSide"
            )

        if not isinstance(self.exit_reason, ExitReason):
            raise TypeError(
                "exit_reason must be an ExitReason"
            )

        self._validate_aware_datetime(
            "entry_time",
            self.entry_time,
        )

        self._validate_aware_datetime(
            "exit_time",
            self.exit_time,
        )

        if self.exit_time < self.entry_time:
            raise ValueError(
                "exit_time cannot be earlier than entry_time"
            )

        self._validate_positive_number(
            "entry_price",
            self.entry_price,
        )

        self._validate_positive_number(
            "exit_price",
            self.exit_price,
        )

        self._validate_positive_number(
            "quantity",
            self.quantity,
        )

        self._validate_finite_number(
            "gross_pnl",
            self.gross_pnl,
        )

        self._validate_finite_number(
            "net_pnl",
            self.net_pnl,
        )

        self._validate_non_negative_number(
            "spread_cost",
            self.spread_cost,
        )

        self._validate_non_negative_number(
            "slippage_cost",
            self.slippage_cost,
        )

        self._validate_non_negative_number(
            "commission",
            self.commission,
        )

        self._validate_finite_number(
            "swap",
            self.swap,
        )

        if (
            not isinstance(self.bars_held, int)
            or isinstance(self.bars_held, bool)
            or self.bars_held < 0
        ):
            raise ValueError(
                "bars_held must be a non-negative integer"
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
    def _validate_non_empty_string(
        name: str,
        value: str,
    ) -> None:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{name} must be a non-empty string"
            )

    @staticmethod
    def _validate_aware_datetime(
        name: str,
        value: datetime,
    ) -> None:
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                f"{name} must be timezone-aware"
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