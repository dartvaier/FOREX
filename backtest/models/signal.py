from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

from backtest.models.enums import SignalAction


@dataclass(frozen=True, slots=True)
class Signal:
    """
    Immutable strategy intent produced after processing
    information available at a specific simulation time.

    A Signal is not an Order and does not guarantee execution.
    """

    signal_id: str
    strategy_id: str
    symbol: str
    timestamp: datetime
    action: SignalAction
    reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.signal_id or not self.signal_id.strip():
            raise ValueError("signal_id must be a non-empty string")

        if not self.strategy_id or not self.strategy_id.strip():
            raise ValueError("strategy_id must be a non-empty string")

        if not self.symbol or not self.symbol.strip():
            raise ValueError("symbol must be a non-empty string")

        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")

        if not isinstance(self.action, SignalAction):
            raise TypeError("action must be a SignalAction")

        if self.reason is not None and not isinstance(self.reason, str):
            raise TypeError("reason must be a string or None")

        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")

        # Store an isolated, read-only copy so external code
        # cannot mutate a Signal after it has been created.
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )