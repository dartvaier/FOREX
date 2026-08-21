from datetime import datetime, timedelta, timezone

import pytest

from alpha.ledger import AlphaLedger, AlphaLedgerRecord
from alpha.models import AlphaSignal


NOW = datetime(
    2026,
    8,
    16,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_record(
    model_id="tsmom",
    *,
    timestamp=NOW,
    value=0.25,
) -> AlphaLedgerRecord:
    return AlphaLedgerRecord(
        timestamp=timestamp,
        symbol="EURUSD",
        model_id=model_id,
        value=value,
        confidence=0.7,
        abstained=False,
        reason="Synthetic alpha",
        metadata={"lookback": 20},
        blended_value=0.30,
        strategy_decision="ENTER_LONG",
    )


def test_alpha_ledger_record_is_created_with_valid_data():
    record = make_record()

    assert record.timestamp == NOW
    assert record.symbol == "EURUSD"
    assert record.model_id == "tsmom"
    assert record.value == 0.25
    assert record.confidence == 0.7
    assert record.abstained is False
    assert record.reason == "Synthetic alpha"
    assert record.metadata["lookback"] == 20
    assert record.blended_value == 0.30
    assert record.strategy_decision == "ENTER_LONG"


def test_alpha_ledger_record_copies_metadata_and_makes_it_read_only():
    metadata = {
        "lookback": 20,
    }

    record = AlphaLedgerRecord(
        timestamp=NOW,
        symbol="EURUSD",
        model_id="tsmom",
        value=0.25,
        metadata=metadata,
    )

    metadata["lookback"] = 50

    assert record.metadata["lookback"] == 20

    with pytest.raises(TypeError):
        record.metadata["lookback"] = 100  # type: ignore[index]


def test_alpha_ledger_record_can_be_created_from_alpha_signal():
    signal = AlphaSignal(
        model_id="ema",
        symbol="EURUSD",
        timestamp=NOW,
        value=0.4,
        confidence=0.8,
        reason="Trend up",
        metadata={"fast": 20},
    )

    record = AlphaLedgerRecord.from_signal(
        signal,
        blended_value=0.35,
        strategy_decision="ENTER_LONG",
    )

    assert record.model_id == "ema"
    assert record.symbol == "EURUSD"
    assert record.value == 0.4
    assert record.confidence == 0.8
    assert record.reason == "Trend up"
    assert record.metadata["fast"] == 20
    assert record.blended_value == 0.35
    assert record.strategy_decision == "ENTER_LONG"


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("symbol", ""),
        ("model_id", ""),
        ("value", -1.01),
        ("value", 1.01),
        ("value", float("nan")),
        ("confidence", -0.01),
        ("confidence", 1.01),
        ("confidence", float("nan")),
        ("blended_value", -1.01),
        ("blended_value", 1.01),
        ("blended_value", float("nan")),
        ("strategy_decision", ""),
    ],
)
def test_alpha_ledger_record_validates_fields(
    field_name,
    field_value,
):
    kwargs = {
        "timestamp": NOW,
        "symbol": "EURUSD",
        "model_id": "tsmom",
        "value": 0.25,
    }

    kwargs[field_name] = field_value

    with pytest.raises(ValueError, match=field_name):
        AlphaLedgerRecord(**kwargs)


def test_alpha_ledger_record_requires_utc_timestamp():
    non_utc = timezone(
        timedelta(hours=-3)
    )

    with pytest.raises(ValueError, match="UTC"):
        AlphaLedgerRecord(
            timestamp=datetime(
                2026,
                8,
                16,
                12,
                0,
                tzinfo=non_utc,
            ),
            symbol="EURUSD",
            model_id="tsmom",
            value=0.25,
        )


def test_alpha_ledger_record_abstention_requires_zero_value():
    with pytest.raises(ValueError, match="abstained"):
        AlphaLedgerRecord(
            timestamp=NOW,
            symbol="EURUSD",
            model_id="tsmom",
            value=0.25,
            abstained=True,
        )


def test_alpha_ledger_appends_records_in_order():
    ledger = AlphaLedger()
    first = make_record(
        "ema",
        timestamp=NOW,
    )
    second = make_record(
        "tsmom",
        timestamp=NOW + timedelta(minutes=15),
    )

    ledger.append(first)
    ledger.append(second)

    assert ledger.count == 2
    assert ledger.is_empty is False
    assert ledger.records == (first, second)
    assert ledger.last_record == second
    assert len(ledger) == 2
    assert tuple(ledger) == (first, second)


def test_alpha_ledger_append_signal_records_alpha_signal():
    ledger = AlphaLedger()
    signal = AlphaSignal(
        model_id="ema",
        symbol="EURUSD",
        timestamp=NOW,
        value=0.4,
    )

    ledger.append_signal(
        signal,
        blended_value=0.4,
        strategy_decision="ENTER_LONG",
    )

    record = ledger.last_record

    assert record is not None
    assert record.model_id == "ema"
    assert record.blended_value == 0.4
    assert record.strategy_decision == "ENTER_LONG"


def test_alpha_ledger_rejects_duplicate_symbol_timestamp_model():
    ledger = AlphaLedger()

    ledger.append(
        make_record()
    )

    with pytest.raises(ValueError, match="duplicate"):
        ledger.append(
            make_record()
        )


def test_alpha_ledger_rejects_chronological_regression():
    ledger = AlphaLedger()

    ledger.append(
        make_record(
            timestamp=NOW + timedelta(minutes=15)
        )
    )

    with pytest.raises(ValueError, match="timestamp"):
        ledger.append(
            make_record(
                "ema",
                timestamp=NOW,
            )
        )


def test_alpha_ledger_gets_records_by_key():
    ledger = AlphaLedger()
    record = make_record()

    ledger.append(record)

    assert (
        ledger.get(
            symbol="EURUSD",
            timestamp=NOW,
            model_id="tsmom",
        )
        == record
    )
    assert (
        ledger.get(
            symbol="EURUSD",
            timestamp=NOW,
            model_id="ema",
        )
        is None
    )


def test_alpha_ledger_filters_by_model_and_symbol():
    ledger = AlphaLedger()
    first = make_record(
        "ema",
        timestamp=NOW,
    )
    second = make_record(
        "tsmom",
        timestamp=NOW + timedelta(minutes=15),
    )

    ledger.append(first)
    ledger.append(second)

    assert ledger.for_model("ema") == (first,)
    assert ledger.for_symbol("EURUSD") == (
        first,
        second,
    )
