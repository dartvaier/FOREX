"""
Structured execution audit log for the F9 Execution Layer.

Every execution-relevant event (order submitted, rejected, filled,
cancelled, reconciliation outcome, activation decisions) is appended
as a JSON line (JSONL) with a UTC-aware timestamp. This is the
audit trail required by roadmap §83 (Logs) and §87 (Demo metrics).

Pure helpers (`make_event`) are testable without files; `AuditLogger`
wraps file appends. Events are never mutated after creation.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def utc_now() -> datetime:
    """Timezone-aware UTC now (repo invariant)."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """An immutable, serialisable execution audit event."""

    event_id: str
    timestamp: datetime
    event_type: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id cannot be empty")

        if not self.event_type:
            raise ValueError("event_type cannot be empty")

        if (
            self.timestamp.tzinfo is None
            or self.timestamp.utcoffset() is None
        ):
            raise ValueError("timestamp must be timezone-aware")


def make_event(
    event_type: str,
    payload: Mapping[str, Any] | None = None,
    *,
    timestamp: datetime | None = None,
    event_id: str | None = None,
) -> AuditEvent:
    """
    Build an AuditEvent with sensible defaults (uuid + UTC now).

    Pure: no file or clock side effects beyond the injected values.
    """
    return AuditEvent(
        event_id=event_id or uuid.uuid4().hex,
        timestamp=timestamp or utc_now(),
        event_type=event_type,
        payload=dict(payload or {}),
    )


def event_to_dict(event: AuditEvent) -> dict[str, Any]:
    """Serialise an event to a JSON-safe dict (UTC ISO timestamps)."""
    return {
        "event_id": event.event_id,
        "timestamp": event.timestamp.isoformat(),
        "event_type": event.event_type,
        "payload": event.payload,
    }


def event_from_dict(
    data: Mapping[str, Any],
) -> AuditEvent:
    """Reconstruct an AuditEvent from a dict (roundtrip for tests)."""
    return AuditEvent(
        event_id=str(data["event_id"]),
        timestamp=datetime.fromisoformat(
            str(data["timestamp"])
        ),
        event_type=str(data["event_type"]),
        payload=dict(data.get("payload") or {}),
    )


class AuditLogger:
    """
    JSONL audit logger.

    Appends one JSON object per line; safe for sequential use.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def log(self, event: AuditEvent) -> None:
        """Append the event as a JSON line."""
        line = json.dumps(
            event_to_dict(event),
            default=str,
        )

        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self._path.open(
            "a",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(line + "\n")

    def read_events(self) -> list[AuditEvent]:
        """Read back every event (test/audit helper)."""
        if not self._path.exists():
            return []

        events: list[AuditEvent] = []

        with self._path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            for line in handle:
                line = line.strip()

                if line:
                    events.append(
                        event_from_dict(json.loads(line))
                    )

        return events
