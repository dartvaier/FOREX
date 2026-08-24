"""
Position reconciliation for the F9 Execution Layer.

After each execution cycle the platform must verify that broker state
matches the platform's own expectations (roadmap §83 Position
Reconciliation). This module is pure: it compares expected positions
against broker-reported positions and flags every divergence.

Positions are keyed by (symbol, side) for reconciliation purposes;
the broker ticket id is carried for audit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from execution.interface import BrokerPosition

BALANCE_TOLERANCE = 0.01


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    """Divergences between expected and broker-reported state."""

    missing_positions: tuple[BrokerPosition, ...] = field(
        default_factory=tuple
    )
    unexpected_positions: tuple[BrokerPosition, ...] = field(
        default_factory=tuple
    )
    quantity_mismatches: tuple[tuple[str, str, float, float], ...] = (
        field(default_factory=tuple)
    )

    @property
    def consistent(self) -> bool:
        return not (
            self.missing_positions
            or self.unexpected_positions
            or self.quantity_mismatches
        )

    @property
    def issues(self) -> int:
        return (
            len(self.missing_positions)
            + len(self.unexpected_positions)
            + len(self.quantity_mismatches)
        )


def _key(position: BrokerPosition) -> tuple[str, str]:
    return (position.symbol, position.side.value)


def reconcile_positions(
    expected: Mapping[str, BrokerPosition],
    actual: Mapping[str, BrokerPosition],
) -> ReconciliationReport:
    """
    Compare expected positions (platform ledger) with broker-reported
    positions.

    Maps are keyed by (symbol, side) as "SYMBOL:SIDE".
    """
    missing: list[BrokerPosition] = []
    unexpected: list[BrokerPosition] = []
    mismatches: list[tuple[str, str, float, float]] = []

    for key, expected_position in expected.items():
        actual_position = actual.get(key)

        if actual_position is None:
            missing.append(expected_position)
            continue

        if abs(
            actual_position.quantity - expected_position.quantity
        ) > 1e-9:
            mismatches.append(
                (
                    key,
                    actual_position.identifier,
                    expected_position.quantity,
                    actual_position.quantity,
                )
            )

    for key, actual_position in actual.items():
        if key not in expected:
            unexpected.append(actual_position)

    return ReconciliationReport(
        missing_positions=tuple(missing),
        unexpected_positions=tuple(unexpected),
        quantity_mismatches=tuple(mismatches),
    )


def reconcile_balance(
    expected_balance: float,
    actual_balance: float,
    *,
    tolerance: float = BALANCE_TOLERANCE,
) -> bool:
    """True when the broker balance matches the expected within tolerance."""
    return abs(expected_balance - actual_balance) <= tolerance
