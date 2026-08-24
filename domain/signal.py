from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class SignalAction(str, Enum):
    ENTER_LONG = "ENTER_LONG"
    ENTER_SHORT = "ENTER_SHORT"
    EXIT = "EXIT"
    HOLD = "HOLD"


def _validate_utc_timestamp(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{field_name} must be in UTC")


@dataclass(frozen=True, slots=True)
class Signal:
    """Strategy output describing intent, not an executable broker order."""

    signal_id: str
    strategy_id: str
    symbol: str
    timestamp: datetime
    action: SignalAction
    reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.signal_id.strip():
            raise ValueError("signal_id must not be empty")
        if not self.strategy_id.strip():
            raise ValueError("strategy_id must not be empty")
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        _validate_utc_timestamp(self.timestamp, "timestamp")
