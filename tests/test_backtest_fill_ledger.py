from datetime import datetime, timezone

import pytest

from backtest.fill_ledger import FillLedger
from backtest.models import Fill


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


def make_fill(
    fill_id: str,
    *,
    order_id: str | None = None,
    fill_time: datetime | None = None,
) -> Fill:
    return Fill(
        fill_id=fill_id,
        order_id=(
            order_id
            if order_id is not None
            else f"ORD-{fill_id}"
        ),
        fill_time=(
            fill_time
            if fill_time is not None
            else utc_time(10, 15)
        ),
        reference_price=1.1600,
        execution_price=1.1601,
        quantity=0.01,
        spread_impact=0.0001,
        slippage=0.0,
        commission=0.035,
    )


def test_ledger_starts_empty():
    ledger = FillLedger()

    assert ledger.count == 0
    assert len(ledger) == 0
    assert ledger.is_empty is True
    assert ledger.fills == ()
    assert ledger.last_fill is None


def test_append_fill():
    ledger = FillLedger()

    fill = make_fill("FILL-001")

    ledger.append(fill)

    assert ledger.count == 1
    assert ledger.is_empty is False
    assert ledger.last_fill == fill
    assert ledger.fills == (fill,)


def test_fills_are_exposed_as_tuple():
    ledger = FillLedger()

    ledger.append(
        make_fill("FILL-001")
    )

    assert isinstance(
        ledger.fills,
        tuple,
    )


def test_preserves_insertion_order():
    ledger = FillLedger()

    first = make_fill(
        "FILL-001",
        fill_time=utc_time(10, 15),
    )

    second = make_fill(
        "FILL-002",
        fill_time=utc_time(10, 30),
    )

    ledger.append(first)
    ledger.append(second)

    assert ledger.fills == (
        first,
        second,
    )


def test_rejects_duplicate_fill_id():
    ledger = FillLedger()

    ledger.append(
        make_fill(
            "FILL-001",
            order_id="ORD-001",
        )
    )

    with pytest.raises(
        ValueError,
        match="duplicate fill_id",
    ):
        ledger.append(
            make_fill(
                "FILL-001",
                order_id="ORD-002",
                fill_time=utc_time(10, 30),
            )
        )


def test_rejects_second_fill_for_same_order():
    ledger = FillLedger()

    ledger.append(
        make_fill(
            "FILL-001",
            order_id="ORD-001",
        )
    )

    with pytest.raises(
        ValueError,
        match="already has a Fill",
    ):
        ledger.append(
            make_fill(
                "FILL-002",
                order_id="ORD-001",
                fill_time=utc_time(10, 30),
            )
        )


def test_rejects_fill_time_regression():
    ledger = FillLedger()

    ledger.append(
        make_fill(
            "FILL-001",
            fill_time=utc_time(10, 30),
        )
    )

    with pytest.raises(
        ValueError,
        match="cannot move backward",
    ):
        ledger.append(
            make_fill(
                "FILL-002",
                fill_time=utc_time(10, 15),
            )
        )


def test_allows_equal_fill_times():
    ledger = FillLedger()

    first = make_fill(
        "FILL-001",
        fill_time=utc_time(10, 15),
    )

    second = make_fill(
        "FILL-002",
        fill_time=utc_time(10, 15),
    )

    ledger.append(first)
    ledger.append(second)

    assert ledger.count == 2


def test_get_returns_fill_by_id():
    ledger = FillLedger()

    fill = make_fill("FILL-001")

    ledger.append(fill)

    assert ledger.get(
        "FILL-001"
    ) == fill


def test_get_returns_none_for_unknown_id():
    ledger = FillLedger()

    assert ledger.get(
        "FILL-UNKNOWN"
    ) is None


def test_get_by_order_id_returns_fill():
    ledger = FillLedger()

    fill = make_fill(
        "FILL-001",
        order_id="ORD-001",
    )

    ledger.append(fill)

    assert ledger.get_by_order_id(
        "ORD-001"
    ) == fill


def test_get_by_order_id_returns_none_when_unknown():
    ledger = FillLedger()

    assert ledger.get_by_order_id(
        "ORD-UNKNOWN"
    ) is None


def test_get_rejects_invalid_fill_id():
    ledger = FillLedger()

    with pytest.raises(
        ValueError,
        match="fill_id",
    ):
        ledger.get("")


def test_get_by_order_id_rejects_invalid_order_id():
    ledger = FillLedger()

    with pytest.raises(
        ValueError,
        match="order_id",
    ):
        ledger.get_by_order_id("   ")


def test_append_requires_fill():
    ledger = FillLedger()

    with pytest.raises(
        TypeError,
        match="Fill",
    ):
        ledger.append(
            object()  # type: ignore[arg-type]
        )


def test_iteration_returns_fills_in_order():
    ledger = FillLedger()

    first = make_fill(
        "FILL-001",
        fill_time=utc_time(10, 15),
    )

    second = make_fill(
        "FILL-002",
        fill_time=utc_time(10, 30),
    )

    ledger.append(first)
    ledger.append(second)

    assert list(ledger) == [
        first,
        second,
    ]