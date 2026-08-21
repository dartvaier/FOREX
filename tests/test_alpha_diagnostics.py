from datetime import datetime, timedelta, timezone

import pytest

from alpha.diagnostics import (
    agreement_rate,
    alpha_direction,
    coverage_rate,
    disagreement_rate,
    signal_turnover_rate,
)
from alpha.ledger import AlphaLedgerRecord


NOW = datetime(
    2026,
    8,
    16,
    12,
    0,
    tzinfo=timezone.utc,
)


def record(
    model_id: str,
    value: float,
    *,
    minutes: int = 0,
    symbol: str = "EURUSD",
    abstained: bool = False,
) -> AlphaLedgerRecord:
    return AlphaLedgerRecord(
        timestamp=NOW + timedelta(minutes=minutes),
        symbol=symbol,
        model_id=model_id,
        value=value,
        abstained=abstained,
    )


def test_alpha_direction_maps_values_to_directions():
    assert alpha_direction(0.2) == 1
    assert alpha_direction(-0.2) == -1
    assert alpha_direction(0.0) == 0


def test_alpha_direction_applies_neutral_threshold():
    assert alpha_direction(0.05, neutral_threshold=0.1) == 0
    assert alpha_direction(0.11, neutral_threshold=0.1) == 1
    assert alpha_direction(-0.11, neutral_threshold=0.1) == -1


def test_coverage_rate_counts_active_records():
    records = (
        record("ema", 0.2),
        record("ema", 0.0, minutes=15, abstained=True),
        record("tsmom", -0.2),
    )

    assert coverage_rate(records) == pytest.approx(2 / 3)
    assert coverage_rate(records, model_id="ema") == pytest.approx(
        0.5
    )
    assert coverage_rate(records, model_id="missing") == 0.0


def test_agreement_rate_counts_matching_active_directions():
    records = (
        record("ema", 0.2),
        record("tsmom", 0.3),
        record("ema", -0.2, minutes=15),
        record("tsmom", 0.3, minutes=15),
    )

    assert agreement_rate(records) == pytest.approx(0.5)
    assert disagreement_rate(records) == pytest.approx(0.5)


def test_agreement_rate_treats_neutral_as_active_direction():
    records = (
        record("ema", 0.0),
        record("tsmom", 0.0),
        record("ema", 0.0, minutes=15),
        record("tsmom", 0.2, minutes=15),
    )

    assert agreement_rate(records) == pytest.approx(0.5)
    assert disagreement_rate(records) == pytest.approx(0.5)


def test_agreement_rate_ignores_abstained_records():
    records = (
        record("ema", 0.2),
        record("tsmom", 0.0, abstained=True),
        record("ema", 0.2, minutes=15),
        record("tsmom", 0.3, minutes=15),
    )

    assert agreement_rate(records) == pytest.approx(1.0)
    assert disagreement_rate(records) == pytest.approx(0.0)


def test_signal_turnover_rate_counts_direction_changes():
    records = (
        record("ema", 0.2),
        record("ema", 0.1, minutes=15),
        record("ema", -0.2, minutes=30),
        record("ema", 0.0, minutes=45),
    )

    assert signal_turnover_rate(records, model_id="ema") == (
        pytest.approx(2 / 3)
    )


def test_signal_turnover_rate_skips_abstentions():
    records = (
        record("ema", 0.2),
        record("ema", 0.0, minutes=15, abstained=True),
        record("ema", -0.2, minutes=30),
    )

    assert signal_turnover_rate(records, model_id="ema") == 1.0


def test_signal_turnover_rate_keeps_models_separate():
    records = (
        record("ema", 0.2),
        record("tsmom", -0.2),
        record("ema", 0.3, minutes=15),
        record("tsmom", -0.3, minutes=15),
    )

    assert signal_turnover_rate(records) == 0.0


def test_diagnostics_validate_inputs():
    with pytest.raises(TypeError, match="records"):
        coverage_rate([])  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="model_id"):
        coverage_rate((), model_id="")

    with pytest.raises(ValueError, match="min_active_models"):
        agreement_rate((), min_active_models=1)

    with pytest.raises(ValueError, match="neutral_threshold"):
        alpha_direction(0.2, neutral_threshold=-0.1)
