"""
Operational safety helpers for F10 Live Readiness (roadmap §91):

    connection failures and duplicate orders.

Pure detection helpers used by the operational procedures.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable


def duplicate_order_ids(
    order_ids: Iterable[str],
) -> tuple[str, ...]:
    """
    Order ids that appear more than once (duplicate order protection).

    Returns a tuple of duplicated ids, ordered by first occurrence.
    """
    seen: set[str] = set()
    duplicates: list[str] = []

    for order_id in order_ids:
        if order_id in seen and order_id not in duplicates:
            duplicates.append(order_id)

        seen.add(order_id)

    return tuple(duplicates)


def connection_breach_count(
    heartbeats: Iterable[bool],
) -> int:
    """
    Number of consecutive failed heartbeats at the end of the stream.

    A trailing run of False values means the connection is currently
    down; the count drives the reconnection policy.
    """
    count = 0

    for heartbeat in reversed(list(heartbeats)):
        if not heartbeat:
            count += 1
        else:
            break

    return count


def order_count_per_symbol(
    orders: Iterable[str],
) -> dict[str, int]:
    """Count orders per symbol (turnover monitoring)."""
    return dict(Counter(orders))
