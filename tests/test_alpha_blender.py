from datetime import datetime, timedelta, timezone

import pytest

from alpha.blender import WeightedAlphaBlender
from alpha.models import AlphaSignal


NOW = datetime(
    2026,
    8,
    16,
    12,
    0,
    tzinfo=timezone.utc,
)


def alpha_signal(
    model_id,
    value,
    *,
    symbol="EURUSD",
    timestamp=NOW,
    confidence=None,
    abstained=False,
):
    return AlphaSignal(
        model_id=model_id,
        symbol=symbol,
        timestamp=timestamp,
        value=value,
        confidence=confidence,
        abstained=abstained,
    )


def test_weighted_alpha_blender_combines_active_signals():
    blender = WeightedAlphaBlender(
        {
            "ema": 1.0,
            "tsmom": 3.0,
        }
    )

    view = blender.blend(
        (
            alpha_signal("ema", 0.2),
            alpha_signal("tsmom", 0.6),
        )
    )

    assert view.symbol == "EURUSD"
    assert view.timestamp == NOW
    assert view.value == pytest.approx(0.5)
    assert view.abstained is False
    assert view.abstained_models == ()
    assert [
        contribution.model_id
        for contribution in view.contributors
    ] == ["ema", "tsmom"]
    assert view.metadata["method"] == "weighted_mean"
    assert view.metadata["active_model_count"] == 2


def test_weighted_alpha_blender_ignores_abstained_signals():
    blender = WeightedAlphaBlender(
        {
            "breakout": 10.0,
            "tsmom": 1.0,
        }
    )

    view = blender.blend(
        (
            AlphaSignal.abstain(
                model_id="breakout",
                symbol="EURUSD",
                timestamp=NOW,
            ),
            alpha_signal("tsmom", 0.4),
        )
    )

    assert view.value == pytest.approx(0.4)
    assert [
        contribution.model_id
        for contribution in view.contributors
    ] == ["tsmom"]
    assert view.abstained_models == ("breakout",)


def test_weighted_alpha_blender_returns_abstained_view_when_all_abstain():
    blender = WeightedAlphaBlender(
        {
            "breakout": 1.0,
            "range": 1.0,
        }
    )

    view = blender.blend(
        (
            AlphaSignal.abstain(
                model_id="range",
                symbol="EURUSD",
                timestamp=NOW,
            ),
            AlphaSignal.abstain(
                model_id="breakout",
                symbol="EURUSD",
                timestamp=NOW,
            ),
        )
    )

    assert view.value == 0.0
    assert view.contributors == ()
    assert view.abstained_models == ("breakout", "range")
    assert view.abstained is True
    assert view.metadata["active_model_count"] == 0


def test_weighted_alpha_blender_distinguishes_neutral_from_abstention():
    blender = WeightedAlphaBlender(
        {
            "neutral-model": 2.0,
            "inactive-model": 100.0,
        }
    )

    view = blender.blend(
        (
            alpha_signal("neutral-model", 0.0),
            AlphaSignal.abstain(
                model_id="inactive-model",
                symbol="EURUSD",
                timestamp=NOW,
            ),
        )
    )

    assert view.value == 0.0
    assert view.abstained is False
    assert [
        contribution.model_id
        for contribution in view.contributors
    ] == ["neutral-model"]
    assert view.abstained_models == ("inactive-model",)


def test_weighted_alpha_blender_is_deterministic():
    blender = WeightedAlphaBlender(
        {
            "ema": 1.0,
            "regime": 2.0,
            "tsmom": 3.0,
        }
    )

    first = blender.blend(
        (
            alpha_signal("tsmom", 0.6),
            alpha_signal("ema", -0.2),
            AlphaSignal.abstain(
                model_id="regime",
                symbol="EURUSD",
                timestamp=NOW,
            ),
        )
    )
    second = blender.blend(
        (
            AlphaSignal.abstain(
                model_id="regime",
                symbol="EURUSD",
                timestamp=NOW,
            ),
            alpha_signal("ema", -0.2),
            alpha_signal("tsmom", 0.6),
        )
    )

    assert first.value == pytest.approx(second.value)
    assert first.contributors == second.contributors
    assert first.abstained_models == second.abstained_models


@pytest.mark.parametrize(
    "weights",
    [
        {},
        {"ema": 0.0},
        {"ema": -1.0},
        {"ema": float("inf")},
        {"ema": float("nan")},
        {"ema": True},
        {"": 1.0},
    ],
)
def test_weighted_alpha_blender_rejects_invalid_weights(
    weights,
):
    with pytest.raises(ValueError, match="weight|weights"):
        WeightedAlphaBlender(weights)


def test_weighted_alpha_blender_weight_mapping_is_immutable():
    blender = WeightedAlphaBlender(
        {
            "ema": 1.0,
        }
    )

    with pytest.raises(TypeError):
        blender.weights["ema"] = 2.0  # type: ignore[index]


def test_weighted_alpha_blender_requires_matching_symbols():
    blender = WeightedAlphaBlender(
        {
            "ema": 1.0,
            "tsmom": 1.0,
        }
    )

    with pytest.raises(ValueError, match="same symbol"):
        blender.blend(
            (
                alpha_signal("ema", 0.2, symbol="EURUSD"),
                alpha_signal("tsmom", 0.2, symbol="GBPUSD"),
            )
        )


def test_weighted_alpha_blender_requires_matching_timestamps():
    blender = WeightedAlphaBlender(
        {
            "ema": 1.0,
            "tsmom": 1.0,
        }
    )

    with pytest.raises(ValueError, match="same timestamp"):
        blender.blend(
            (
                alpha_signal("ema", 0.2),
                alpha_signal(
                    "tsmom",
                    0.2,
                    timestamp=NOW + timedelta(minutes=15),
                ),
            )
        )


def test_weighted_alpha_blender_requires_known_weight_for_each_signal():
    blender = WeightedAlphaBlender(
        {
            "ema": 1.0,
        }
    )

    with pytest.raises(ValueError, match="missing weight"):
        blender.blend(
            (
                alpha_signal("ema", 0.2),
                alpha_signal("tsmom", 0.2),
            )
        )


def test_weighted_alpha_blender_rejects_duplicate_model_ids():
    blender = WeightedAlphaBlender(
        {
            "ema": 1.0,
        }
    )

    with pytest.raises(ValueError, match="unique model_id"):
        blender.blend(
            (
                alpha_signal("ema", 0.2),
                alpha_signal("ema", 0.4),
            )
        )


def test_weighted_alpha_blender_requires_tuple_of_signals():
    blender = WeightedAlphaBlender(
        {
            "ema": 1.0,
        }
    )

    with pytest.raises(TypeError, match="tuple"):
        blender.blend(
            [
                alpha_signal("ema", 0.2),
            ]  # type: ignore[arg-type]
        )


def test_weighted_alpha_blender_rejects_empty_signal_tuple():
    blender = WeightedAlphaBlender(
        {
            "ema": 1.0,
        }
    )

    with pytest.raises(ValueError, match="signals"):
        blender.blend(())


def test_blended_view_metadata_is_immutable():
    blender = WeightedAlphaBlender(
        {
            "ema": 1.0,
        }
    )

    view = blender.blend(
        (
            alpha_signal("ema", 0.2),
        )
    )

    with pytest.raises(TypeError):
        view.metadata["method"] = "other"  # type: ignore[index]
