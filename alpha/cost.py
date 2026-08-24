import math
from dataclasses import dataclass, field
from numbers import Real
from types import MappingProxyType
from typing import Any, Mapping

from alpha.models import AlphaSignal
from alpha.protocol import AlphaModel
from backtest.context import BacktestContext
from backtest.models import Timeframe


@dataclass(frozen=True, slots=True)
class CostGateDecision:
    """
    Immutable audit decision for cost-aware alpha filtering.
    """

    allowed: bool
    reason: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.allowed, bool):
            raise TypeError(
                "allowed must be a bool"
            )

        if (
            not isinstance(self.reason, str)
            or not self.reason.strip()
        ):
            raise ValueError(
                "reason must be a non-empty string"
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


@dataclass(frozen=True, slots=True)
class MinimumExpectedMoveGate:
    """
    Causal economic gate for AlphaSignal objects.

    The gate compares an explicit expected movement estimate,
    expressed in pips, against a configured cost estimate. It
    never reads realized execution cost.
    """

    cost_estimate_pips: float = 3.7
    safety_factor: float = 1.0
    expected_move_key: str = "expected_move_pips"

    def __post_init__(self) -> None:
        _validate_non_negative_number(
            "cost_estimate_pips",
            self.cost_estimate_pips,
        )
        _validate_positive_number(
            "safety_factor",
            self.safety_factor,
        )

        if (
            not isinstance(self.expected_move_key, str)
            or not self.expected_move_key.strip()
        ):
            raise ValueError(
                "expected_move_key must be a non-empty string"
            )

    def evaluate(
        self,
        signal: AlphaSignal,
    ) -> CostGateDecision:
        if not isinstance(signal, AlphaSignal):
            raise TypeError(
                "signal must be an AlphaSignal"
            )

        minimum_required_move_pips = (
            self.cost_estimate_pips
            * self.safety_factor
        )

        base_metadata = {
            "cost_gate": "minimum_expected_move",
            "cost_gate_allowed": False,
            "cost_estimate_pips": self.cost_estimate_pips,
            "cost_safety_factor": self.safety_factor,
            "minimum_required_move_pips": minimum_required_move_pips,
            "expected_move_key": self.expected_move_key,
        }

        if signal.abstained:
            return CostGateDecision(
                allowed=False,
                reason="Alpha signal already abstained",
                metadata={
                    **base_metadata,
                    "cost_gate_skipped": True,
                },
            )

        if self.expected_move_key not in signal.metadata:
            return CostGateDecision(
                allowed=False,
                reason="Missing expected move estimate",
                metadata={
                    **base_metadata,
                    "missing_expected_move": True,
                },
            )

        expected_move_pips = signal.metadata[
            self.expected_move_key
        ]
        _validate_non_negative_number(
            self.expected_move_key,
            expected_move_pips,
        )

        allowed = (
            float(expected_move_pips)
            > minimum_required_move_pips
        )

        if allowed:
            reason = "Expected move exceeds estimated cost"
        else:
            reason = "Expected move does not exceed estimated cost"

        return CostGateDecision(
            allowed=allowed,
            reason=reason,
            metadata={
                **base_metadata,
                "cost_gate_allowed": allowed,
                "expected_move_pips": float(expected_move_pips),
            },
        )


@dataclass(frozen=True, slots=True)
class CostAwareAlphaModel:
    """
    AlphaModel wrapper that abstains when expected move does not
    clear the configured cost hurdle.
    """

    inner: AlphaModel
    gate: MinimumExpectedMoveGate = field(
        default_factory=MinimumExpectedMoveGate
    )

    def __post_init__(self) -> None:
        if not isinstance(self.inner, AlphaModel):
            raise TypeError(
                "inner must satisfy the AlphaModel protocol"
            )

        if not isinstance(
            self.gate,
            MinimumExpectedMoveGate,
        ):
            raise TypeError(
                "gate must be a MinimumExpectedMoveGate"
            )

    @property
    def model_id(self) -> str:
        return self.inner.model_id

    @property
    def closed_bar_limit(self) -> int | None:
        return getattr(
            self.inner,
            "closed_bar_limit",
            None,
        )

    @property
    def higher_timeframe_bar_limits(
        self,
    ) -> dict[Timeframe, int]:
        limits = getattr(
            self.inner,
            "higher_timeframe_bar_limits",
            {},
        )

        if limits is None:
            return {}

        if not isinstance(limits, dict):
            raise TypeError(
                "inner higher_timeframe_bar_limits must be a dict"
            )

        return dict(limits)

    def predict(
        self,
        context: BacktestContext,
    ) -> AlphaSignal:
        signal = self.inner.predict(context)
        decision = self.gate.evaluate(signal)

        metadata = {
            **signal.metadata,
            **decision.metadata,
        }

        if signal.abstained:
            return AlphaSignal.abstain(
                model_id=signal.model_id,
                symbol=signal.symbol,
                timestamp=signal.timestamp,
                reason=signal.reason,
                metadata=metadata,
            )

        if not decision.allowed:
            return AlphaSignal.abstain(
                model_id=signal.model_id,
                symbol=signal.symbol,
                timestamp=signal.timestamp,
                reason=f"Cost gate blocked: {decision.reason}",
                metadata=metadata,
            )

        return AlphaSignal(
            model_id=signal.model_id,
            symbol=signal.symbol,
            timestamp=signal.timestamp,
            value=signal.value,
            confidence=signal.confidence,
            abstained=False,
            reason=signal.reason,
            metadata=metadata,
        )


def expected_move_pips_from_return(
    *,
    reference_price: float,
    expected_return: float,
    pip_size: float,
) -> float:
    _validate_positive_number(
        "reference_price",
        reference_price,
    )
    _validate_finite_number(
        "expected_return",
        expected_return,
    )
    _validate_positive_number(
        "pip_size",
        pip_size,
    )

    return abs(
        float(reference_price)
        * float(expected_return)
    ) / float(pip_size)


def price_distance_pips(
    *,
    price_distance: float,
    pip_size: float,
) -> float:
    _validate_finite_number(
        "price_distance",
        price_distance,
    )
    _validate_positive_number(
        "pip_size",
        pip_size,
    )

    return abs(
        float(price_distance)
    ) / float(pip_size)


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


def _validate_positive_number(
    name: str,
    value: Real,
) -> None:
    _validate_finite_number(
        name,
        value,
    )

    if value <= 0:
        raise ValueError(
            f"{name} must be positive"
        )


def _validate_non_negative_number(
    name: str,
    value: Real,
) -> None:
    _validate_finite_number(
        name,
        value,
    )

    if value < 0:
        raise ValueError(
            f"{name} must be non-negative"
        )
