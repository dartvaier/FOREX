import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from numbers import Real
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class AlphaSignal:
    """
    Immutable model view produced from information available
    at a specific simulation time.

    An AlphaSignal is not a trading Signal. It expresses only
    direction and conviction in the normalized range [-1, +1].
    """

    model_id: str
    symbol: str
    timestamp: datetime
    value: float
    confidence: float | None = None
    abstained: bool = False
    reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_non_empty_string(
            "model_id",
            self.model_id,
        )

        _validate_non_empty_string(
            "symbol",
            self.symbol,
        )

        _validate_timezone_aware_datetime(
            "timestamp",
            self.timestamp,
        )

        _validate_bounded_number(
            "value",
            self.value,
            lower=-1.0,
            upper=1.0,
        )

        if self.confidence is not None:
            _validate_bounded_number(
                "confidence",
                self.confidence,
                lower=0.0,
                upper=1.0,
            )

        if not isinstance(self.abstained, bool):
            raise TypeError(
                "abstained must be a bool"
            )

        if self.abstained and self.value != 0.0:
            raise ValueError(
                "abstained alpha signals must have value 0.0"
            )

        if self.reason is not None and not isinstance(
            self.reason,
            str,
        ):
            raise TypeError(
                "reason must be a string or None"
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

    @classmethod
    def abstain(
        cls,
        *,
        model_id: str,
        symbol: str,
        timestamp: datetime,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "AlphaSignal":
        return cls(
            model_id=model_id,
            symbol=symbol,
            timestamp=timestamp,
            value=0.0,
            confidence=None,
            abstained=True,
            reason=reason,
            metadata={} if metadata is None else metadata,
        )


@dataclass(frozen=True, slots=True)
class AlphaContribution:
    """
    Audit record for an active AlphaSignal used in a blended view.
    """

    model_id: str
    value: float
    weight: float
    confidence: float | None = None

    def __post_init__(self) -> None:
        _validate_non_empty_string(
            "model_id",
            self.model_id,
        )

        _validate_bounded_number(
            "value",
            self.value,
            lower=-1.0,
            upper=1.0,
        )

        _validate_positive_number(
            "weight",
            self.weight,
        )

        if self.confidence is not None:
            _validate_bounded_number(
                "confidence",
                self.confidence,
                lower=0.0,
                upper=1.0,
            )


@dataclass(frozen=True, slots=True)
class BlendedAlphaView:
    """
    Immutable weighted view consumed by future ensemble strategies.
    """

    symbol: str
    timestamp: datetime
    value: float
    contributors: tuple[AlphaContribution, ...] = ()
    abstained_models: tuple[str, ...] = ()
    abstained: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_non_empty_string(
            "symbol",
            self.symbol,
        )

        _validate_timezone_aware_datetime(
            "timestamp",
            self.timestamp,
        )

        _validate_bounded_number(
            "value",
            self.value,
            lower=-1.0,
            upper=1.0,
        )

        if not isinstance(self.contributors, tuple):
            raise TypeError(
                "contributors must be a tuple"
            )

        if not all(
            isinstance(contributor, AlphaContribution)
            for contributor in self.contributors
        ):
            raise TypeError(
                "contributors must contain only AlphaContribution "
                "objects"
            )

        if not isinstance(self.abstained_models, tuple):
            raise TypeError(
                "abstained_models must be a tuple"
            )

        for model_id in self.abstained_models:
            _validate_non_empty_string(
                "abstained_models",
                model_id,
            )

        if not isinstance(self.abstained, bool):
            raise TypeError(
                "abstained must be a bool"
            )

        if self.abstained and self.contributors:
            raise ValueError(
                "abstained blended views cannot have contributors"
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


def _validate_non_empty_string(
    name: str,
    value: str,
) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{name} must be a non-empty string"
        )


def _validate_timezone_aware_datetime(
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

    if value.utcoffset() != timedelta(0):
        raise ValueError(
            f"{name} must use UTC"
        )


def _validate_bounded_number(
    name: str,
    value: Real,
    *,
    lower: float,
    upper: float,
) -> None:
    if (
        not isinstance(value, Real)
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < lower
        or value > upper
    ):
        raise ValueError(
            f"{name} must be a finite number in [{lower}, {upper}]"
        )


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
