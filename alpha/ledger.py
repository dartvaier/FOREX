import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from types import MappingProxyType
from typing import Any, Mapping

from alpha.models import AlphaSignal


@dataclass(frozen=True, slots=True)
class AlphaLedgerRecord:
    """
    Immutable audit snapshot for one model view at one timestamp.
    """

    timestamp: datetime
    symbol: str
    model_id: str
    value: float
    confidence: float | None = None
    abstained: bool = False
    reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    blended_value: float | None = None
    strategy_decision: str | None = None

    def __post_init__(self) -> None:
        _validate_utc_datetime(
            "timestamp",
            self.timestamp,
        )
        _validate_non_empty_string(
            "symbol",
            self.symbol,
        )
        _validate_non_empty_string(
            "model_id",
            self.model_id,
        )
        _validate_bounded_alpha(
            "value",
            self.value,
        )

        if self.confidence is not None:
            _validate_bounded_unit(
                "confidence",
                self.confidence,
            )

        if not isinstance(self.abstained, bool):
            raise TypeError(
                "abstained must be a bool"
            )

        if self.abstained and self.value != 0.0:
            raise ValueError(
                "abstained alpha records must have value 0.0"
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

        if self.blended_value is not None:
            _validate_bounded_alpha(
                "blended_value",
                self.blended_value,
            )

        if (
            self.strategy_decision is not None
            and (
                not isinstance(self.strategy_decision, str)
                or not self.strategy_decision.strip()
            )
        ):
            raise ValueError(
                "strategy_decision must be a non-empty string or None"
            )

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )

    @classmethod
    def from_signal(
        cls,
        signal: AlphaSignal,
        *,
        blended_value: float | None = None,
        strategy_decision: str | None = None,
    ) -> "AlphaLedgerRecord":
        if not isinstance(signal, AlphaSignal):
            raise TypeError(
                "signal must be an AlphaSignal"
            )

        return cls(
            timestamp=signal.timestamp,
            symbol=signal.symbol,
            model_id=signal.model_id,
            value=signal.value,
            confidence=signal.confidence,
            abstained=signal.abstained,
            reason=signal.reason,
            metadata=signal.metadata,
            blended_value=blended_value,
            strategy_decision=strategy_decision,
        )


class AlphaLedger:
    """
    Ordered ledger of alpha model audit records.

    A model may record at most one alpha view for the same
    symbol and timestamp.
    """

    def __init__(self) -> None:
        self._records: list[AlphaLedgerRecord] = []
        self._keys: set[tuple[str, datetime, str]] = set()

    @property
    def records(self) -> tuple[AlphaLedgerRecord, ...]:
        return tuple(self._records)

    @property
    def count(self) -> int:
        return len(self._records)

    @property
    def is_empty(self) -> bool:
        return not self._records

    @property
    def last_record(self) -> AlphaLedgerRecord | None:
        if not self._records:
            return None

        return self._records[-1]

    def append(
        self,
        record: AlphaLedgerRecord,
    ) -> None:
        if not isinstance(record, AlphaLedgerRecord):
            raise TypeError(
                "record must be an AlphaLedgerRecord"
            )

        key = (
            record.symbol,
            record.timestamp,
            record.model_id,
        )

        if key in self._keys:
            raise ValueError(
                "duplicate alpha record"
            )

        if self._records:
            previous = self._records[-1]

            if record.timestamp < previous.timestamp:
                raise ValueError(
                    "AlphaLedgerRecord timestamp cannot move backward"
                )

        self._records.append(record)
        self._keys.add(key)

    def append_signal(
        self,
        signal: AlphaSignal,
        *,
        blended_value: float | None = None,
        strategy_decision: str | None = None,
    ) -> None:
        self.append(
            AlphaLedgerRecord.from_signal(
                signal,
                blended_value=blended_value,
                strategy_decision=strategy_decision,
            )
        )

    def get(
        self,
        *,
        symbol: str,
        timestamp: datetime,
        model_id: str,
    ) -> AlphaLedgerRecord | None:
        _validate_non_empty_string(
            "symbol",
            symbol,
        )
        _validate_utc_datetime(
            "timestamp",
            timestamp,
        )
        _validate_non_empty_string(
            "model_id",
            model_id,
        )

        for record in self._records:
            if (
                record.symbol == symbol
                and record.timestamp == timestamp
                and record.model_id == model_id
            ):
                return record

        return None

    def for_model(
        self,
        model_id: str,
    ) -> tuple[AlphaLedgerRecord, ...]:
        _validate_non_empty_string(
            "model_id",
            model_id,
        )

        return tuple(
            record
            for record in self._records
            if record.model_id == model_id
        )

    def for_symbol(
        self,
        symbol: str,
    ) -> tuple[AlphaLedgerRecord, ...]:
        _validate_non_empty_string(
            "symbol",
            symbol,
        )

        return tuple(
            record
            for record in self._records
            if record.symbol == symbol
        )

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        return iter(self.records)


def _validate_non_empty_string(
    name: str,
    value: str,
) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{name} must be a non-empty string"
        )


def _validate_utc_datetime(
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


def _validate_bounded_alpha(
    name: str,
    value: float,
) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < -1.0
        or value > 1.0
    ):
        raise ValueError(
            f"{name} must be a number in [-1.0, 1.0]"
        )


def _validate_bounded_unit(
    name: str,
    value: float,
) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0.0
        or value > 1.0
    ):
        raise ValueError(
            f"{name} must be a number in [0.0, 1.0]"
        )
