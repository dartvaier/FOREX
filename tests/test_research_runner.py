"""
Unit tests for the research runner cost-stress helpers.

The runner is a CLI orchestration layer; the pure helpers
(validate_cost_multiplier, scale_cost_params) are tested here
without requiring the EURUSD dataset or MetaTrader 5.
"""

import math

import pytest

from research.runner import (
    scale_cost_params,
    validate_cost_multiplier,
)

BASE_COSTS = {
    "spread_pips": 2.0,
    "slippage_pips": 0.5,
    "commission_per_lot_per_side": 3.50,
}


def test_validate_cost_multiplier_accepts_one():
    assert validate_cost_multiplier(1.0) == 1.0


def test_validate_cost_multiplier_accepts_stress_levels():
    assert validate_cost_multiplier(1.5) == 1.5
    assert validate_cost_multiplier(2.0) == 2.0


def test_validate_cost_multiplier_accepts_zero():
    assert validate_cost_multiplier(0.0) == 0.0


@pytest.mark.parametrize(
    "value",
    [
        -0.1,
        float("inf"),
        float("-inf"),
        float("nan"),
        True,
        "2.0",
    ],
)
def test_validate_cost_multiplier_rejects_invalid(value):
    with pytest.raises(
        ValueError,
        match="cost_multiplier",
    ):
        validate_cost_multiplier(value)  # type: ignore[arg-type]


def test_scale_cost_params_one_is_identity():
    scaled = scale_cost_params(
        BASE_COSTS,
        1.0,
    )

    assert scaled == BASE_COSTS


def test_scale_cost_params_one_point_five():
    scaled = scale_cost_params(
        BASE_COSTS,
        1.5,
    )

    assert scaled["spread_pips"] == pytest.approx(3.0)
    assert scaled["slippage_pips"] == pytest.approx(0.75)
    assert scaled["commission_per_lot_per_side"] == (
        pytest.approx(5.25)
    )


def test_scale_cost_params_two():
    scaled = scale_cost_params(
        BASE_COSTS,
        2.0,
    )

    assert scaled["spread_pips"] == pytest.approx(4.0)
    assert scaled["slippage_pips"] == pytest.approx(1.0)
    assert scaled["commission_per_lot_per_side"] == (
        pytest.approx(7.0)
    )


def test_scale_cost_params_zero_zeros_all():
    scaled = scale_cost_params(
        BASE_COSTS,
        0.0,
    )

    assert scaled["spread_pips"] == 0.0
    assert scaled["slippage_pips"] == 0.0
    assert scaled["commission_per_lot_per_side"] == 0.0


def test_scale_cost_params_does_not_mutate_base():
    original = dict(BASE_COSTS)

    scale_cost_params(
        BASE_COSTS,
        2.0,
    )

    assert BASE_COSTS == original


def test_scale_cost_params_rejects_invalid_multiplier():
    with pytest.raises(
        ValueError,
        match="cost_multiplier",
    ):
        scale_cost_params(
            BASE_COSTS,
            -1.0,
        )


def test_scale_cost_params_rejects_non_dict():
    with pytest.raises(
        TypeError,
        match="cost_params",
    ):
        scale_cost_params(
            None,  # type: ignore[arg-type]
            1.0,
        )
