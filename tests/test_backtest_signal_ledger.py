from datetime import datetime, timezone

import pytest

from backtest.models import (
    Signal,
    SignalAction,
)
from backtest.signal_ledger import SignalLedger


def utc_time(
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026,
        8,
        8,
        hour,
        minute,
        tzinfo=timezone.utc,
    )


def make_signal(
    signal_id: str,
    *,
    timestamp: datetime | None = None,
    action: SignalAction = SignalAction.HOLD,
) -> Signal:
    return Signal(
        signal_id=signal_id,
        strategy_id="TEST-STRATEGY",
        symbol="EURUSD",
        timestamp=(
            timestamp
            if timestamp is not None
            else utc_time(10, 15)
        ),
        action=action,
    )


def test_ledger_starts_empty():
    ledger = SignalLedger()

    assert ledger.count == 0
    assert len(ledger) == 0
    assert ledger.is_empty is True
    assert ledger.last_signal is None
    assert ledger.signals == ()


def test_append_signal():
    ledger = SignalLedger()

    signal = make_signal(
        "SIG-001",
        action=SignalAction.ENTER_LONG,
    )

    ledger.append(signal)

    assert ledger.count == 1
    assert ledger.is_empty is False
    assert ledger.last_signal == signal
    assert ledger.signals == (signal,)


def test_signals_are_exposed_as_tuple():
    ledger = SignalLedger()

    ledger.append(
        make_signal("SIG-001")
    )

    assert isinstance(
        ledger.signals,
        tuple,
    )


def test_preserves_insertion_order():
    ledger = SignalLedger()

    first = make_signal(
        "SIG-001",
        timestamp=utc_time(10, 15),
    )

    second = make_signal(
        "SIG-002",
        timestamp=utc_time(10, 30),
    )

    ledger.append(first)
    ledger.append(second)

    assert ledger.signals == (
        first,
        second,
    )


def test_rejects_duplicate_signal_id():
    ledger = SignalLedger()

    ledger.append(
        make_signal("SIG-001")
    )

    with pytest.raises(
        ValueError,
        match="duplicate signal_id",
    ):
        ledger.append(
            make_signal(
                "SIG-001",
                timestamp=utc_time(10, 30),
            )
        )


def test_rejects_timestamp_regression():
    ledger = SignalLedger()

    ledger.append(
        make_signal(
            "SIG-001",
            timestamp=utc_time(10, 30),
        )
    )

    with pytest.raises(
        ValueError,
        match="cannot move backward",
    ):
        ledger.append(
            make_signal(
                "SIG-002",
                timestamp=utc_time(10, 15),
            )
        )


def test_allows_equal_timestamps():
    ledger = SignalLedger()

    first = make_signal(
        "SIG-001",
        timestamp=utc_time(10, 15),
    )

    second = make_signal(
        "SIG-002",
        timestamp=utc_time(10, 15),
    )

    ledger.append(first)
    ledger.append(second)

    assert ledger.count == 2


def test_get_returns_signal_by_id():
    ledger = SignalLedger()

    first = make_signal("SIG-001")
    second = make_signal(
        "SIG-002",
        timestamp=utc_time(10, 30),
    )

    ledger.append(first)
    ledger.append(second)

    assert ledger.get(
        "SIG-002"
    ) == second


def test_get_returns_none_for_unknown_id():
    ledger = SignalLedger()

    ledger.append(
        make_signal("SIG-001")
    )

    assert ledger.get(
        "SIG-UNKNOWN"
    ) is None


@pytest.mark.parametrize(
    "signal_id",
    [
        "",
        "   ",
        None,
        123,
    ],
)
def test_get_rejects_invalid_signal_id(
    signal_id,
):
    ledger = SignalLedger()

    with pytest.raises(
        ValueError,
        match="non-empty string",
    ):
        ledger.get(signal_id)


def test_append_requires_signal():
    ledger = SignalLedger()

    with pytest.raises(
        TypeError,
        match="Signal",
    ):
        ledger.append(
            object()  # type: ignore[arg-type]
        )


def test_iteration_returns_signals_in_order():
    ledger = SignalLedger()

    first = make_signal(
        "SIG-001",
        timestamp=utc_time(10, 15),
    )

    second = make_signal(
        "SIG-002",
        timestamp=utc_time(10, 30),
    )

    ledger.append(first)
    ledger.append(second)

    assert list(ledger) == [
        first,
        second,
    ]