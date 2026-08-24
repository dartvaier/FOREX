from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from alpha.cost import (
    CostAwareAlphaModel,
    CostGateDecision,
    MinimumExpectedMoveGate,
    expected_move_pips_from_return,
    price_distance_pips,
)
from alpha.models import AlphaSignal
from alpha.protocol import AlphaModel


TIMESTAMP = datetime(
    2026,
    8,
    8,
    10,
    tzinfo=timezone.utc,
)


@dataclass(frozen=True, slots=True)
class StaticAlphaModel:
    signal: AlphaSignal

    @property
    def model_id(self) -> str:
        return self.signal.model_id

    @property
    def closed_bar_limit(self) -> int:
        return 5

    def predict(
        self,
        context,
    ) -> AlphaSignal:
        return self.signal


def make_signal(
    *,
    value: float = 0.5,
    expected_move_pips: float | None = 5.0,
    abstained: bool = False,
) -> AlphaSignal:
    metadata = {}

    if expected_move_pips is not None:
        metadata["expected_move_pips"] = expected_move_pips

    if abstained:
        return AlphaSignal.abstain(
            model_id="static-alpha",
            symbol="EURUSD",
            timestamp=TIMESTAMP,
            reason="Warm-up",
            metadata=metadata,
        )

    return AlphaSignal(
        model_id="static-alpha",
        symbol="EURUSD",
        timestamp=TIMESTAMP,
        value=value,
        metadata=metadata,
    )


def test_cost_gate_decision_is_immutable_and_metadata_is_read_only():
    metadata = {
        "expected_move_pips": 5.0,
    }
    decision = CostGateDecision(
        allowed=True,
        reason="Allowed",
        metadata=metadata,
    )

    metadata["expected_move_pips"] = 0.0

    assert decision.metadata["expected_move_pips"] == 5.0

    with pytest.raises(TypeError):
        decision.metadata["expected_move_pips"] = 1.0  # type: ignore[index]


def test_minimum_expected_move_gate_validates_parameters():
    with pytest.raises(ValueError, match="cost_estimate_pips"):
        MinimumExpectedMoveGate(
            cost_estimate_pips=-0.1,
        )

    with pytest.raises(ValueError, match="safety_factor"):
        MinimumExpectedMoveGate(
            safety_factor=0.0,
        )

    with pytest.raises(ValueError, match="expected_move_key"):
        MinimumExpectedMoveGate(
            expected_move_key="",
        )


def test_minimum_expected_move_gate_allows_signal_above_cost_hurdle():
    gate = MinimumExpectedMoveGate(
        cost_estimate_pips=3.7,
        safety_factor=1.1,
    )

    decision = gate.evaluate(
        make_signal(
            expected_move_pips=4.2,
        )
    )

    assert decision.allowed is True
    assert decision.reason == "Expected move exceeds estimated cost"
    assert decision.metadata["expected_move_pips"] == 4.2
    assert decision.metadata["minimum_required_move_pips"] == pytest.approx(
        4.07
    )


def test_minimum_expected_move_gate_blocks_signal_at_cost_hurdle():
    gate = MinimumExpectedMoveGate(
        cost_estimate_pips=3.7,
    )

    decision = gate.evaluate(
        make_signal(
            expected_move_pips=3.7,
        )
    )

    assert decision.allowed is False
    assert (
        decision.reason
        == "Expected move does not exceed estimated cost"
    )
    assert decision.metadata["cost_gate_allowed"] is False


def test_minimum_expected_move_gate_blocks_missing_expected_move():
    decision = MinimumExpectedMoveGate().evaluate(
        make_signal(
            expected_move_pips=None,
        )
    )

    assert decision.allowed is False
    assert decision.reason == "Missing expected move estimate"
    assert decision.metadata["missing_expected_move"] is True


@pytest.mark.parametrize(
    "expected_move_pips",
    [
        -0.1,
        float("inf"),
        float("nan"),
        True,
        "5.0",
    ],
)
def test_minimum_expected_move_gate_rejects_invalid_expected_move(
    expected_move_pips,
):
    with pytest.raises(ValueError, match="expected_move_pips"):
        MinimumExpectedMoveGate().evaluate(
            make_signal(
                expected_move_pips=expected_move_pips,
            )
        )


def test_cost_aware_alpha_model_satisfies_alpha_model_protocol():
    model = CostAwareAlphaModel(
        inner=StaticAlphaModel(
            make_signal()
        )
    )

    assert isinstance(model, AlphaModel)
    assert model.closed_bar_limit == 5


def test_cost_aware_alpha_model_preserves_allowed_signal():
    model = CostAwareAlphaModel(
        inner=StaticAlphaModel(
            make_signal(
                value=0.6,
                expected_move_pips=5.0,
            )
        ),
        gate=MinimumExpectedMoveGate(
            cost_estimate_pips=3.7,
        ),
    )

    signal = model.predict(
        object()
    )

    assert signal.abstained is False
    assert signal.value == 0.6
    assert signal.metadata["cost_gate_allowed"] is True
    assert signal.metadata["cost_estimate_pips"] == 3.7


def test_cost_aware_alpha_model_abstains_when_cost_gate_blocks():
    model = CostAwareAlphaModel(
        inner=StaticAlphaModel(
            make_signal(
                value=0.6,
                expected_move_pips=2.0,
            )
        ),
        gate=MinimumExpectedMoveGate(
            cost_estimate_pips=3.7,
        ),
    )

    signal = model.predict(
        object()
    )

    assert signal.abstained is True
    assert signal.value == 0.0
    assert signal.reason == (
        "Cost gate blocked: Expected move does not exceed "
        "estimated cost"
    )
    assert signal.metadata["expected_move_pips"] == 2.0
    assert signal.metadata["cost_gate_allowed"] is False


def test_cost_aware_alpha_model_preserves_inner_abstention():
    model = CostAwareAlphaModel(
        inner=StaticAlphaModel(
            make_signal(
                abstained=True,
            )
        )
    )

    signal = model.predict(
        object()
    )

    assert signal.abstained is True
    assert signal.reason == "Warm-up"
    assert signal.metadata["cost_gate_skipped"] is True


def test_expected_move_pips_from_return_converts_to_abs_pips():
    assert expected_move_pips_from_return(
        reference_price=1.1020,
        expected_return=-0.001,
        pip_size=0.00010,
    ) == pytest.approx(11.02)


def test_price_distance_pips_converts_to_abs_pips():
    assert price_distance_pips(
        price_distance=-0.00042,
        pip_size=0.00010,
    ) == pytest.approx(4.2)
