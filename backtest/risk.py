import math
from dataclasses import dataclass
from numbers import Real

from backtest.models.enums import SignalAction
from backtest.models.instrument import InstrumentSpecification
from backtest.models.signal import Signal


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """
    Immutable result of evaluating a Signal through a
    Risk Gate.

    approved:
        Indicates whether the Risk layer permits the Signal.

    quantity:
        Final approved quantity when sizing is required.

        ENTER_LONG / ENTER_SHORT:
            quantity is provided by the Risk Gate.

        EXIT:
            quantity is intentionally None because the final
            exit quantity belongs to the currently open
            Position.

        HOLD:
            quantity is None because no Order is required.

    reason:
        Human-readable audit explanation.
    """

    signal_id: str
    approved: bool
    quantity: float | None
    reason: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.signal_id, str)
            or not self.signal_id.strip()
        ):
            raise ValueError(
                "signal_id must be a non-empty string"
            )

        if not isinstance(self.approved, bool):
            raise TypeError(
                "approved must be a bool"
            )

        if self.quantity is not None:
            if (
                not isinstance(self.quantity, Real)
                or isinstance(self.quantity, bool)
                or not math.isfinite(self.quantity)
                or self.quantity <= 0
            ):
                raise ValueError(
                    "quantity must be a finite positive "
                    "number or None"
                )

        if (
            not isinstance(self.reason, str)
            or not self.reason.strip()
        ):
            raise ValueError(
                "reason must be a non-empty string"
            )


class FixedSizeRiskGate:
    """
    Minimal deterministic Risk Gate used to validate the
    BacktestEngine infrastructure.

    This is NOT the final Risk Management system.

    The baseline uses one fixed quantity for new positions.

    Responsibilities:

    - validate fixed position size
    - enforce instrument min/max volume
    - approve ENTER_LONG
    - approve ENTER_SHORT
    - allow EXIT to continue without assigning quantity
    - allow HOLD without creating financial exposure

    It does not implement:

    - percentage risk
    - stop-distance sizing
    - volatility sizing
    - portfolio exposure limits
    - drawdown controls
    - leverage controls
    - daily loss limits
    """

    def __init__(
        self,
        instrument: InstrumentSpecification,
        fixed_quantity: float,
    ) -> None:
        if not isinstance(
            instrument,
            InstrumentSpecification,
        ):
            raise TypeError(
                "instrument must be an "
                "InstrumentSpecification"
            )

        if (
            not isinstance(fixed_quantity, Real)
            or isinstance(fixed_quantity, bool)
            or not math.isfinite(fixed_quantity)
            or fixed_quantity <= 0
        ):
            raise ValueError(
                "fixed_quantity must be a finite "
                "positive number"
            )

        if fixed_quantity < instrument.volume_min:
            raise ValueError(
                "fixed_quantity cannot be smaller than "
                "instrument volume_min"
            )

        if fixed_quantity > instrument.volume_max:
            raise ValueError(
                "fixed_quantity cannot be greater than "
                "instrument volume_max"
            )

        self._instrument = instrument
        self._fixed_quantity = float(
            fixed_quantity
        )

    @property
    def instrument(
        self,
    ) -> InstrumentSpecification:
        return self._instrument

    @property
    def fixed_quantity(self) -> float:
        return self._fixed_quantity

    def evaluate(
        self,
        signal: Signal,
    ) -> RiskDecision:
        """
        Evaluate a validated Signal.

        The baseline Risk Gate currently approves all valid
        Signal actions because advanced risk rejection belongs
        to the future Risk Management layer.
        """

        if not isinstance(signal, Signal):
            raise TypeError(
                "signal must be a Signal"
            )

        if signal.symbol != self._instrument.symbol:
            raise ValueError(
                "signal symbol does not match instrument"
            )

        if signal.action == SignalAction.HOLD:
            return RiskDecision(
                signal_id=signal.signal_id,
                approved=True,
                quantity=None,
                reason="HOLD requires no order",
            )

        if signal.action == SignalAction.EXIT:
            return RiskDecision(
                signal_id=signal.signal_id,
                approved=True,
                quantity=None,
                reason=(
                    "EXIT quantity must be resolved from "
                    "the current Position"
                ),
            )

        if signal.action in (
            SignalAction.ENTER_LONG,
            SignalAction.ENTER_SHORT,
        ):
            return RiskDecision(
                signal_id=signal.signal_id,
                approved=True,
                quantity=self._fixed_quantity,
                reason="Approved by FixedSizeRiskGate",
            )

        raise ValueError(
            f"unsupported SignalAction: {signal.action}"
        )