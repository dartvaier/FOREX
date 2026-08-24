import math

import pytest

from backtest.costs import CostEstimate, CostModel, FixedCostModel, ZeroCostModel
from domain.order_intent import OrderSide


def test_zero_cost_keeps_reference_price_and_all_costs_at_zero():
    estimate = ZeroCostModel().estimate(reference_price=1.2, side=OrderSide.BUY, quantity=2)
    assert estimate == CostEstimate(1.2, 1.2, 0.0, 0.0, 0.0)


def test_fixed_cost_is_adverse_for_buy_and_sell():
    model = FixedCostModel(spread=0.0002, slippage=0.0001, commission_per_unit=3.5)
    buy = model.estimate(reference_price=1.2, side=OrderSide.BUY, quantity=2)
    sell = model.estimate(reference_price=1.2, side=OrderSide.SELL, quantity=2)

    assert buy.execution_price == pytest.approx(1.2002)
    assert sell.execution_price == pytest.approx(1.1998)
    assert buy.spread_impact == sell.spread_impact == pytest.approx(0.0001)
    assert buy.slippage == sell.slippage == pytest.approx(0.0001)
    assert buy.commission == sell.commission == pytest.approx(7.0)


def test_round_trip_charges_full_spread_once_not_twice_per_fill():
    model = FixedCostModel(spread=0.0002)
    buy = model.estimate(reference_price=1.2, side=OrderSide.BUY, quantity=1)
    sell = model.estimate(reference_price=1.2, side=OrderSide.SELL, quantity=1)

    assert buy.execution_price - sell.execution_price == pytest.approx(0.0002)
    assert buy.spread_impact + sell.spread_impact == pytest.approx(0.0002)


def test_model_is_deterministic_and_stateless():
    model = FixedCostModel(spread=0.0002, slippage=0.0001, commission_per_unit=2)
    first = model.estimate(reference_price=1.1, side=OrderSide.BUY, quantity=3)
    second = model.estimate(reference_price=1.1, side=OrderSide.BUY, quantity=3)
    assert first == second


@pytest.mark.parametrize("field", ["spread", "slippage", "commission_per_unit"])
@pytest.mark.parametrize("value", [-1.0, math.inf, math.nan, True])
def test_fixed_cost_rejects_negative_or_non_finite_inputs(field, value):
    with pytest.raises(ValueError, match=field):
        FixedCostModel(**{field: value})


@pytest.mark.parametrize("model", [ZeroCostModel(), FixedCostModel()])
@pytest.mark.parametrize("price, quantity", [(0, 1), (-1, 1), (math.inf, 1), (1, 0), (1, -1), (1, math.nan)])
def test_models_reject_invalid_execution_inputs(model, price, quantity):
    with pytest.raises(ValueError):
        model.estimate(reference_price=price, side=OrderSide.BUY, quantity=quantity)


@pytest.mark.parametrize("model", [ZeroCostModel(), FixedCostModel()])
def test_models_reject_invalid_side(model):
    with pytest.raises(TypeError, match="OrderSide"):
        model.estimate(reference_price=1, side="BUY", quantity=1)


def test_fixed_cost_rejects_sell_execution_price_at_or_below_zero():
    with pytest.raises(ValueError, match="execution_price"):
        FixedCostModel(spread=2).estimate(reference_price=1, side=OrderSide.SELL, quantity=1)


@pytest.mark.parametrize("field", ["reference_price", "execution_price", "spread_impact", "slippage", "commission"])
def test_cost_estimate_validates_its_own_invariants(field):
    values = dict(reference_price=1.0, execution_price=1.0, spread_impact=0.0, slippage=0.0, commission=0.0)
    values[field] = -1.0
    with pytest.raises(ValueError, match=field):
        CostEstimate(**values)


def test_cost_model_is_an_abstraction():
    assert isinstance(ZeroCostModel(), CostModel)
    assert isinstance(FixedCostModel(), CostModel)
