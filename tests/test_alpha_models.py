from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from alpha.models import AlphaSignal
from alpha.protocol import AlphaModel


NOW = datetime(
    2026,
    8,
    16,
    12,
    0,
    tzinfo=timezone.utc,
)


def test_alpha_signal_is_created_with_valid_data():
    signal = AlphaSignal(
        model_id="tsmom",
        symbol="EURUSD",
        timestamp=NOW,
        value=0.42,
        confidence=0.7,
        reason="Positive normalized momentum",
        metadata={"lookback": 20},
    )

    assert signal.model_id == "tsmom"
    assert signal.symbol == "EURUSD"
    assert signal.timestamp == NOW
    assert signal.value == 0.42
    assert signal.confidence == 0.7
    assert signal.abstained is False
    assert signal.reason == "Positive normalized momentum"
    assert signal.metadata["lookback"] == 20


@pytest.mark.parametrize(
    "value",
    [
        -1.01,
        1.01,
        float("inf"),
        float("-inf"),
        float("nan"),
        True,
    ],
)
def test_alpha_signal_rejects_value_outside_normalized_range(
    value,
):
    with pytest.raises(ValueError, match="value"):
        AlphaSignal(
            model_id="tsmom",
            symbol="EURUSD",
            timestamp=NOW,
            value=value,
        )


@pytest.mark.parametrize(
    "confidence",
    [
        -0.01,
        1.01,
        float("inf"),
        float("-inf"),
        float("nan"),
        True,
    ],
)
def test_alpha_signal_rejects_invalid_confidence(
    confidence,
):
    with pytest.raises(ValueError, match="confidence"):
        AlphaSignal(
            model_id="tsmom",
            symbol="EURUSD",
            timestamp=NOW,
            value=0.25,
            confidence=confidence,
        )


def test_alpha_signal_allows_missing_confidence():
    signal = AlphaSignal(
        model_id="tsmom",
        symbol="EURUSD",
        timestamp=NOW,
        value=0.25,
    )

    assert signal.confidence is None


def test_alpha_signal_requires_timezone_aware_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        AlphaSignal(
            model_id="tsmom",
            symbol="EURUSD",
            timestamp=datetime(2026, 8, 16, 12, 0),
            value=0.25,
        )


def test_alpha_signal_requires_utc_timestamp():
    non_utc = timezone(
        timedelta(hours=-3)
    )

    with pytest.raises(ValueError, match="UTC"):
        AlphaSignal(
            model_id="tsmom",
            symbol="EURUSD",
            timestamp=datetime(
                2026,
                8,
                16,
                12,
                0,
                tzinfo=non_utc,
            ),
            value=0.25,
        )


def test_alpha_signal_requires_non_empty_model_id():
    with pytest.raises(ValueError, match="model_id"):
        AlphaSignal(
            model_id="",
            symbol="EURUSD",
            timestamp=NOW,
            value=0.25,
        )


def test_alpha_signal_requires_non_empty_symbol():
    with pytest.raises(ValueError, match="symbol"):
        AlphaSignal(
            model_id="tsmom",
            symbol="",
            timestamp=NOW,
            value=0.25,
        )


def test_alpha_signal_is_immutable():
    signal = AlphaSignal(
        model_id="tsmom",
        symbol="EURUSD",
        timestamp=NOW,
        value=0.25,
    )

    with pytest.raises(FrozenInstanceError):
        signal.value = 0.5  # type: ignore[misc]


def test_alpha_signal_metadata_is_immutable_and_copied():
    metadata = {"lookback": 20}

    signal = AlphaSignal(
        model_id="tsmom",
        symbol="EURUSD",
        timestamp=NOW,
        value=0.25,
        metadata=metadata,
    )

    metadata["lookback"] = 50

    assert signal.metadata["lookback"] == 20

    with pytest.raises(TypeError):
        signal.metadata["lookback"] = 100  # type: ignore[index]


def test_alpha_signal_abstention_is_explicit():
    signal = AlphaSignal.abstain(
        model_id="range-breakout",
        symbol="EURUSD",
        timestamp=NOW,
        reason="Outside trading window",
    )

    assert signal.value == 0.0
    assert signal.confidence is None
    assert signal.abstained is True
    assert signal.reason == "Outside trading window"


def test_alpha_signal_abstention_requires_zero_value():
    with pytest.raises(ValueError, match="abstained"):
        AlphaSignal(
            model_id="range-breakout",
            symbol="EURUSD",
            timestamp=NOW,
            value=0.25,
            abstained=True,
        )


def test_alpha_model_protocol_accepts_structural_model():
    class StaticAlphaModel:
        @property
        def model_id(self):
            return "static"

        def predict(self, context):
            return AlphaSignal(
                model_id=self.model_id,
                symbol="EURUSD",
                timestamp=NOW,
                value=0.0,
            )

    assert isinstance(StaticAlphaModel(), AlphaModel)
