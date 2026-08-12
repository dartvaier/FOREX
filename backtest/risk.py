import math
from dataclasses import dataclass
from datetime import date, timezone
from numbers import Real
from typing import Protocol, runtime_checkable

from backtest.equity_ledger import EquityPoint
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


@runtime_checkable
class RiskGate(Protocol):
    """
    Contract for components that approve/reject Signals and
    assign final entry quantity.
    """

    @property
    def instrument(
        self,
    ) -> InstrumentSpecification:
        ...

    def evaluate(
        self,
        signal: Signal,
    ) -> RiskDecision:
        ...


class VolumeRules:
    """
    Instrument volume validation and step normalization.
    """

    def __init__(
        self,
        instrument: InstrumentSpecification,
    ) -> None:
        if not isinstance(
            instrument,
            InstrumentSpecification,
        ):
            raise TypeError(
                "instrument must be an "
                "InstrumentSpecification"
            )

        self._instrument = instrument

    @property
    def instrument(
        self,
    ) -> InstrumentSpecification:
        return self._instrument

    def validate(
        self,
        quantity: float,
        *,
        name: str = "quantity",
    ) -> float:
        self._validate_positive_finite(
            name,
            quantity,
        )

        if quantity < self._instrument.volume_min:
            raise ValueError(
                f"{name} cannot be smaller than "
                "instrument volume_min"
            )

        if quantity > self._instrument.volume_max:
            raise ValueError(
                f"{name} cannot be greater than "
                "instrument volume_max"
            )

        if not self.is_step_aligned(quantity):
            raise ValueError(
                f"{name} must respect instrument volume_step"
            )

        return float(quantity)

    def normalize_down(
        self,
        quantity: float,
    ) -> float:
        self._validate_positive_finite(
            "quantity",
            quantity,
        )

        capped = min(
            quantity,
            self._instrument.volume_max,
        )

        steps = math.floor(
            (
                capped
                + self._epsilon()
            )
            / self._instrument.volume_step
        )

        normalized = (
            steps
            * self._instrument.volume_step
        )

        return round(
            normalized,
            self._decimal_places(),
        )

    def is_step_aligned(
        self,
        quantity: float,
    ) -> bool:
        if (
            not isinstance(quantity, Real)
            or isinstance(quantity, bool)
            or not math.isfinite(quantity)
        ):
            return False

        ratio = (
            quantity
            / self._instrument.volume_step
        )

        return math.isclose(
            ratio,
            round(ratio),
            rel_tol=0.0,
            abs_tol=1e-9,
        )

    def _decimal_places(self) -> int:
        step_text = f"{self._instrument.volume_step:.10f}"

        return len(
            step_text.rstrip("0").split(".")[-1]
        )

    def _epsilon(self) -> float:
        return self._instrument.volume_step * 1e-9

    @staticmethod
    def _validate_positive_finite(
        name: str,
        value: float,
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

        self._volume_rules = VolumeRules(
            instrument
        )

        self._volume_rules.validate(
            fixed_quantity,
            name="fixed_quantity",
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


class StopBasedRiskGate:
    """
    Risk Gate that sizes entries from explicit stop distance.

    Required entry Signal metadata:

    - entry_price
    - stop_loss

    The approved quantity is floored to the instrument
    volume_step and capped by instrument.volume_max and an
    optional max_quantity.
    """

    def __init__(
        self,
        *,
        instrument: InstrumentSpecification,
        account_equity: float,
        risk_fraction: float,
        max_quantity: float | None = None,
    ) -> None:
        if not isinstance(
            instrument,
            InstrumentSpecification,
        ):
            raise TypeError(
                "instrument must be an "
                "InstrumentSpecification"
            )

        self._validate_positive_finite(
            "account_equity",
            account_equity,
        )

        self._validate_positive_finite(
            "risk_fraction",
            risk_fraction,
        )

        if risk_fraction > 1.0:
            raise ValueError(
                "risk_fraction cannot be greater than 1.0"
            )

        if max_quantity is not None:
            self._validate_positive_finite(
                "max_quantity",
                max_quantity,
            )

        self._instrument = instrument
        self._account_equity = float(account_equity)
        self._risk_fraction = float(risk_fraction)
        self._max_quantity = (
            None
            if max_quantity is None
            else float(max_quantity)
        )
        self._volume_rules = VolumeRules(
            instrument
        )

    @property
    def instrument(
        self,
    ) -> InstrumentSpecification:
        return self._instrument

    @property
    def account_equity(self) -> float:
        return self._account_equity

    @property
    def risk_fraction(self) -> float:
        return self._risk_fraction

    @property
    def max_quantity(self) -> float | None:
        return self._max_quantity

    def evaluate(
        self,
        signal: Signal,
    ) -> RiskDecision:
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

        if signal.action not in (
            SignalAction.ENTER_LONG,
            SignalAction.ENTER_SHORT,
        ):
            raise ValueError(
                f"unsupported SignalAction: {signal.action}"
            )

        entry_price = self._metadata_price(
            signal,
            "entry_price",
        )

        stop_loss = self._metadata_price(
            signal,
            "stop_loss",
        )

        if entry_price is None:
            return self._reject(
                signal,
                "entry_price metadata is required",
            )

        if stop_loss is None:
            return self._reject(
                signal,
                "stop_loss metadata is required",
            )

        if (
            signal.action == SignalAction.ENTER_LONG
            and stop_loss >= entry_price
        ):
            return self._reject(
                signal,
                "long stop_loss must be below entry_price",
            )

        if (
            signal.action == SignalAction.ENTER_SHORT
            and stop_loss <= entry_price
        ):
            return self._reject(
                signal,
                "short stop_loss must be above entry_price",
            )

        stop_distance = abs(
            entry_price
            - stop_loss
        )

        risk_per_lot = (
            stop_distance
            * self._instrument.contract_size
        )

        if risk_per_lot <= 0:
            return self._reject(
                signal,
                "stop distance produced zero risk",
            )

        risk_amount = (
            self._account_equity
            * self._risk_fraction
        )

        raw_quantity = risk_amount / risk_per_lot

        if self._max_quantity is not None:
            raw_quantity = min(
                raw_quantity,
                self._max_quantity,
            )

        quantity = self._volume_rules.normalize_down(
            raw_quantity
        )

        if quantity < self._instrument.volume_min:
            return self._reject(
                signal,
                "calculated quantity is below volume_min",
            )

        return RiskDecision(
            signal_id=signal.signal_id,
            approved=True,
            quantity=quantity,
            reason=(
                "Approved by StopBasedRiskGate "
                f"risk_fraction={self._risk_fraction}"
            ),
        )

    def _reject(
        self,
        signal: Signal,
        reason: str,
    ) -> RiskDecision:
        return RiskDecision(
            signal_id=signal.signal_id,
            approved=False,
            quantity=None,
            reason=reason,
        )

    @staticmethod
    def _metadata_price(
        signal: Signal,
        key: str,
    ) -> float | None:
        value = signal.metadata.get(key)

        if value is None:
            return None

        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value <= 0
        ):
            return None

        return float(value)

    @staticmethod
    def _validate_positive_finite(
        name: str,
        value: float,
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


class ExposureLimitRiskGate:
    """
    Risk Gate wrapper that rejects entries above exposure
    limits after another RiskGate has approved and sized them.

    Supported limits:

    - max_quantity
    - max_notional

    Notional exposure uses:

        entry_price * contract_size * quantity

    therefore max_notional checks require entry_price metadata
    on entry Signals.
    """

    def __init__(
        self,
        *,
        inner: RiskGate,
        max_quantity: float | None = None,
        max_notional: float | None = None,
    ) -> None:
        if not isinstance(
            inner,
            RiskGate,
        ):
            raise TypeError(
                "inner must satisfy the RiskGate protocol"
            )

        if (
            max_quantity is None
            and max_notional is None
        ):
            raise ValueError(
                "at least one exposure limit is required"
            )

        if max_quantity is not None:
            self._validate_positive_finite(
                "max_quantity",
                max_quantity,
            )

        if max_notional is not None:
            self._validate_positive_finite(
                "max_notional",
                max_notional,
            )

        self._inner = inner
        self._max_quantity = (
            None
            if max_quantity is None
            else float(max_quantity)
        )
        self._max_notional = (
            None
            if max_notional is None
            else float(max_notional)
        )

    @property
    def inner(self) -> RiskGate:
        return self._inner

    @property
    def instrument(
        self,
    ) -> InstrumentSpecification:
        return self._inner.instrument

    @property
    def max_quantity(self) -> float | None:
        return self._max_quantity

    @property
    def max_notional(self) -> float | None:
        return self._max_notional

    def observe_equity(
        self,
        point: EquityPoint,
    ) -> None:
        """
        Propagate the equity observation to the inner gate
        (docs/25 RC-01): wrappers must receive equity
        independently of the composition chain.
        """
        if not isinstance(
            point,
            EquityPoint,
        ):
            raise TypeError(
                "point must be an EquityPoint"
            )

        inner_observer = getattr(
            self._inner,
            "observe_equity",
            None,
        )

        if callable(inner_observer):
            inner_observer(point)

    def evaluate(
        self,
        signal: Signal,
    ) -> RiskDecision:
        decision = self._inner.evaluate(signal)

        if not decision.approved:
            return decision

        if signal.action in (
            SignalAction.HOLD,
            SignalAction.EXIT,
        ):
            return decision

        if signal.action not in (
            SignalAction.ENTER_LONG,
            SignalAction.ENTER_SHORT,
        ):
            raise ValueError(
                f"unsupported SignalAction: {signal.action}"
            )

        if decision.quantity is None:
            return self._reject(
                decision,
                "approved entry requires quantity",
            )

        if (
            self._max_quantity is not None
            and decision.quantity > self._max_quantity
        ):
            return self._reject(
                decision,
                "quantity exceeds max_quantity exposure limit",
            )

        if self._max_notional is not None:
            entry_price = StopBasedRiskGate._metadata_price(
                signal,
                "entry_price",
            )

            if entry_price is None:
                return self._reject(
                    decision,
                    "entry_price metadata is required for "
                    "max_notional exposure limit",
                )

            notional = (
                entry_price
                * self.instrument.contract_size
                * decision.quantity
            )

            if notional > self._max_notional:
                return self._reject(
                    decision,
                    "notional exposure exceeds max_notional",
                )

        return RiskDecision(
            signal_id=decision.signal_id,
            approved=True,
            quantity=decision.quantity,
            reason=(
                f"{decision.reason}; approved by "
                "ExposureLimitRiskGate"
            ),
        )

    @staticmethod
    def _reject(
        decision: RiskDecision,
        reason: str,
    ) -> RiskDecision:
        return RiskDecision(
            signal_id=decision.signal_id,
            approved=False,
            quantity=None,
            reason=reason,
        )

    @staticmethod
    def _validate_positive_finite(
        name: str,
        value: float,
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


class DailyLossRiskGate:
    """
    Risk Gate wrapper that rejects new entries after the
    observed daily equity loss reaches a configured limit.

    The gate is stateful. The BacktestEngine updates it with
    EquityPoint snapshots through observe_equity().

    Supported limits:

    - max_daily_loss
    - max_daily_loss_fraction

    The daily boundary is UTC.
    """

    def __init__(
        self,
        *,
        inner: RiskGate,
        max_daily_loss: float | None = None,
        max_daily_loss_fraction: float | None = None,
    ) -> None:
        if not isinstance(
            inner,
            RiskGate,
        ):
            raise TypeError(
                "inner must satisfy the RiskGate protocol"
            )

        if (
            max_daily_loss is None
            and max_daily_loss_fraction is None
        ):
            raise ValueError(
                "at least one daily loss limit is required"
            )

        if max_daily_loss is not None:
            self._validate_positive_finite(
                "max_daily_loss",
                max_daily_loss,
            )

        if max_daily_loss_fraction is not None:
            self._validate_positive_finite(
                "max_daily_loss_fraction",
                max_daily_loss_fraction,
            )

            if max_daily_loss_fraction > 1.0:
                raise ValueError(
                    "max_daily_loss_fraction cannot be "
                    "greater than 1.0"
                )

        self._inner = inner
        self._max_daily_loss = (
            None
            if max_daily_loss is None
            else float(max_daily_loss)
        )
        self._max_daily_loss_fraction = (
            None
            if max_daily_loss_fraction is None
            else float(max_daily_loss_fraction)
        )
        self._current_day: date | None = None
        self._day_start_equity: float | None = None
        self._latest_equity: float | None = None
        self._locked = False

    @property
    def inner(self) -> RiskGate:
        return self._inner

    @property
    def instrument(
        self,
    ) -> InstrumentSpecification:
        return self._inner.instrument

    @property
    def max_daily_loss(self) -> float | None:
        return self._max_daily_loss

    @property
    def max_daily_loss_fraction(self) -> float | None:
        return self._max_daily_loss_fraction

    @property
    def current_day(self) -> date | None:
        return self._current_day

    @property
    def day_start_equity(self) -> float | None:
        return self._day_start_equity

    @property
    def latest_equity(self) -> float | None:
        return self._latest_equity

    @property
    def daily_loss(self) -> float:
        if (
            self._day_start_equity is None
            or self._latest_equity is None
        ):
            return 0.0

        return max(
            0.0,
            self._day_start_equity
            - self._latest_equity,
        )

    @property
    def daily_loss_fraction(self) -> float:
        if (
            self._day_start_equity is None
            or self._day_start_equity <= 0
        ):
            return 0.0

        return (
            self.daily_loss
            / self._day_start_equity
        )

    @property
    def is_locked(self) -> bool:
        return self._locked

    def observe_equity(
        self,
        point: EquityPoint,
    ) -> None:
        if not isinstance(
            point,
            EquityPoint,
        ):
            raise TypeError(
                "point must be an EquityPoint"
            )

        point_day = (
            point.timestamp
            .astimezone(timezone.utc)
            .date()
        )

        if point_day != self._current_day:
            self._current_day = point_day
            self._day_start_equity = point.equity
            self._latest_equity = point.equity
            self._locked = False
            return

        self._latest_equity = point.equity

        if self._breached_limit():
            self._locked = True

    def evaluate(
        self,
        signal: Signal,
    ) -> RiskDecision:
        decision = self._inner.evaluate(signal)

        if not decision.approved:
            return decision

        if signal.action in (
            SignalAction.HOLD,
            SignalAction.EXIT,
        ):
            return decision

        if signal.action not in (
            SignalAction.ENTER_LONG,
            SignalAction.ENTER_SHORT,
        ):
            raise ValueError(
                f"unsupported SignalAction: {signal.action}"
            )

        if self._current_day is None:
            return self._reject(
                decision,
                "equity snapshot is required for "
                "DailyLossRiskGate",
            )

        if self._locked:
            return self._reject(
                decision,
                "daily loss limit reached",
            )

        return RiskDecision(
            signal_id=decision.signal_id,
            approved=True,
            quantity=decision.quantity,
            reason=(
                f"{decision.reason}; approved by "
                "DailyLossRiskGate"
            ),
        )

    def _breached_limit(self) -> bool:
        if (
            self._max_daily_loss is not None
            and self.daily_loss >= self._max_daily_loss
        ):
            return True

        if (
            self._max_daily_loss_fraction is not None
            and self.daily_loss_fraction
            >= self._max_daily_loss_fraction
        ):
            return True

        return False

    @staticmethod
    def _reject(
        decision: RiskDecision,
        reason: str,
    ) -> RiskDecision:
        return RiskDecision(
            signal_id=decision.signal_id,
            approved=False,
            quantity=None,
            reason=reason,
        )

    @staticmethod
    def _validate_positive_finite(
        name: str,
        value: float,
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


class DrawdownRiskGate:
    """
    Risk Gate wrapper that rejects new entries when the
    observed peak-to-current equity drawdown reaches a
    configured limit.

    The gate is stateful. The BacktestEngine updates it with
    EquityPoint snapshots through observe_equity().

    Supported limits:

    - max_drawdown
    - max_drawdown_pct

    The drawdown is dynamic: entries are unlocked when equity
    recovers and the drawdown falls below the configured limit.

    Unlike DailyLossRiskGate, the peak equity is tracked across
    the entire simulation (all-time high), not reset daily.

    HOLD and EXIT signals are always allowed regardless of
    drawdown state, because they do not increase financial
    exposure.
    """

    def __init__(
        self,
        *,
        inner: RiskGate,
        max_drawdown: float | None = None,
        max_drawdown_pct: float | None = None,
    ) -> None:
        if not isinstance(
            inner,
            RiskGate,
        ):
            raise TypeError(
                "inner must satisfy the RiskGate protocol"
            )

        if (
            max_drawdown is None
            and max_drawdown_pct is None
        ):
            raise ValueError(
                "at least one drawdown limit is required"
            )

        if max_drawdown is not None:
            self._validate_positive_finite(
                "max_drawdown",
                max_drawdown,
            )

        if max_drawdown_pct is not None:
            self._validate_positive_finite(
                "max_drawdown_pct",
                max_drawdown_pct,
            )

            if max_drawdown_pct > 100.0:
                raise ValueError(
                    "max_drawdown_pct cannot be greater than "
                    "100.0"
                )

        self._inner = inner
        self._max_drawdown = (
            None
            if max_drawdown is None
            else float(max_drawdown)
        )
        self._max_drawdown_pct = (
            None
            if max_drawdown_pct is None
            else float(max_drawdown_pct)
        )
        self._peak_equity: float | None = None
        self._current_equity: float | None = None
        self._locked = False

    @property
    def inner(self) -> RiskGate:
        return self._inner

    @property
    def instrument(
        self,
    ) -> InstrumentSpecification:
        return self._inner.instrument

    @property
    def max_drawdown(self) -> float | None:
        return self._max_drawdown

    @property
    def max_drawdown_pct(self) -> float | None:
        return self._max_drawdown_pct

    @property
    def peak_equity(self) -> float | None:
        return self._peak_equity

    @property
    def current_equity(self) -> float | None:
        return self._current_equity

    @property
    def current_drawdown(self) -> float:
        if (
            self._peak_equity is None
            or self._current_equity is None
        ):
            return 0.0

        return max(
            0.0,
            self._peak_equity
            - self._current_equity,
        )

    @property
    def current_drawdown_pct(self) -> float:
        if (
            self._peak_equity is None
            or self._peak_equity <= 0
        ):
            return 0.0

        return (
            self.current_drawdown
            / self._peak_equity
            * 100.0
        )

    @property
    def is_locked(self) -> bool:
        return self._locked

    def observe_equity(
        self,
        point: EquityPoint,
    ) -> None:
        if not isinstance(
            point,
            EquityPoint,
        ):
            raise TypeError(
                "point must be an EquityPoint"
            )

        self._current_equity = point.equity

        if (
            self._peak_equity is None
            or point.equity > self._peak_equity
        ):
            self._peak_equity = point.equity
            self._locked = False
            return

        if self._breached_limit():
            self._locked = True
        else:
            self._locked = False

    def evaluate(
        self,
        signal: Signal,
    ) -> RiskDecision:
        decision = self._inner.evaluate(signal)

        if not decision.approved:
            return decision

        if signal.action in (
            SignalAction.HOLD,
            SignalAction.EXIT,
        ):
            return decision

        if signal.action not in (
            SignalAction.ENTER_LONG,
            SignalAction.ENTER_SHORT,
        ):
            raise ValueError(
                f"unsupported SignalAction: {signal.action}"
            )

        if self._peak_equity is None:
            return self._reject(
                decision,
                "equity snapshot is required for "
                "DrawdownRiskGate",
            )

        if self._locked:
            return self._reject(
                decision,
                "drawdown limit reached",
            )

        return RiskDecision(
            signal_id=decision.signal_id,
            approved=True,
            quantity=decision.quantity,
            reason=(
                f"{decision.reason}; approved by "
                "DrawdownRiskGate"
            ),
        )

    def _breached_limit(self) -> bool:
        if (
            self._max_drawdown is not None
            and self.current_drawdown >= self._max_drawdown
        ):
            return True

        if (
            self._max_drawdown_pct is not None
            and self.current_drawdown_pct
            >= self._max_drawdown_pct
        ):
            return True

        return False

    @staticmethod
    def _reject(
        decision: RiskDecision,
        reason: str,
    ) -> RiskDecision:
        return RiskDecision(
            signal_id=decision.signal_id,
            approved=False,
            quantity=None,
            reason=reason,
        )

    @staticmethod
    def _validate_positive_finite(
        name: str,
        value: float,
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


class KillSwitchRiskGate:
    """
    Risk Gate wrapper that blocks execution when armed.

    The kill switch is an independent safety mechanism: once
    triggered through kill(), it stays active until an explicit
    operator reset() call. It is a latch, not a dynamic guard.

    Supported modes:

    - SOFT (default):
        ENTER_LONG / ENTER_SHORT are rejected while active.
        HOLD and EXIT pass through, so existing exposure can
        still be reduced or closed.

    - HARD (freeze_all_orders=True):
        ENTER_LONG / ENTER_SHORT and EXIT are rejected while
        active (full freeze). HOLD always passes because it
        produces no Order.

    Hardening RC-02 (docs/25): HARD is an EXCEPTIONAL operational
    freeze. It may only be enabled explicitly (default is SOFT /
    exposure-reducing), requires operator justification and must
    never be activated implicitly.

    While inactive, the gate delegates to the inner RiskGate
    without altering its decisions.

    This satisfies ADR-045: a kill switch independent of the
    Strategy that can block execution even when the Strategy
    is functioning normally.
    """

    def __init__(
        self,
        *,
        inner: RiskGate,
        freeze_all_orders: bool | None = None,
        block_exits: bool | None = None,
    ) -> None:
        if not isinstance(
            inner,
            RiskGate,
        ):
            raise TypeError(
                "inner must satisfy the RiskGate protocol"
            )

        if (
            freeze_all_orders is not None
            and block_exits is not None
        ):
            raise ValueError(
                "pass either freeze_all_orders or the deprecated "
                "block_exits, not both"
            )

        effective = (
            freeze_all_orders
            if freeze_all_orders is not None
            else block_exits
        )

        if effective is None:
            effective = False

        if not isinstance(
            effective,
            bool,
        ):
            raise TypeError(
                "freeze_all_orders must be a bool"
            )

        self._inner = inner
        self._freeze_all_orders = effective
        self._active = False

    @property
    def inner(self) -> RiskGate:
        return self._inner

    @property
    def instrument(
        self,
    ) -> InstrumentSpecification:
        return self._inner.instrument

    @property
    def freeze_all_orders(self) -> bool:
        return self._freeze_all_orders

    @property
    def block_exits(self) -> bool:
        """Deprecated alias of freeze_all_orders (docs/25 RC-02)."""
        return self._freeze_all_orders

    @property
    def is_active(self) -> bool:
        return self._active

    def observe_equity(
        self,
        point: EquityPoint,
    ) -> None:
        """
        Propagate the equity observation to the inner gate
        (docs/25 RC-01): wrappers must receive equity
        independently of the composition chain.
        """
        if not isinstance(
            point,
            EquityPoint,
        ):
            raise TypeError(
                "point must be an EquityPoint"
            )

        inner_observer = getattr(
            self._inner,
            "observe_equity",
            None,
        )

        if callable(inner_observer):
            inner_observer(point)

    def kill(self) -> None:
        """
        Arm the kill switch (latch).

        Once armed, the switch stays active until reset() is
        called by the operator. No equity observation is
        required: the switch is manual by design.
        """
        self._active = True

    def reset(self) -> None:
        """
        Disarm the kill switch (operator action).

        After reset, the gate delegates to the inner RiskGate
        again without blocking.
        """
        self._active = False

    def evaluate(
        self,
        signal: Signal,
    ) -> RiskDecision:
        decision = self._inner.evaluate(signal)

        if not decision.approved:
            return decision

        if signal.action == SignalAction.HOLD:
            return decision

        if signal.action not in (
            SignalAction.ENTER_LONG,
            SignalAction.ENTER_SHORT,
            SignalAction.EXIT,
        ):
            raise ValueError(
                f"unsupported SignalAction: {signal.action}"
            )

        if not self._active:
            return RiskDecision(
                signal_id=decision.signal_id,
                approved=True,
                quantity=decision.quantity,
                reason=(
                    f"{decision.reason}; approved by "
                    "KillSwitchRiskGate"
                ),
            )

        if signal.action in (
            SignalAction.ENTER_LONG,
            SignalAction.ENTER_SHORT,
        ):
            return self._reject(
                decision,
                "kill switch active",
            )

        if self._freeze_all_orders:
            return self._reject(
                decision,
                "kill switch active (hard mode blocks exits)",
            )

        return decision

    @staticmethod
    def _reject(
        decision: RiskDecision,
        reason: str,
    ) -> RiskDecision:
        return RiskDecision(
            signal_id=decision.signal_id,
            approved=False,
            quantity=None,
            reason=reason,
        )
