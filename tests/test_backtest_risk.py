from datetime import datetime, timezone
import math

import pytest

from backtest.position import Position, PositionSide
from backtest.risk import FixedSizeRiskModel, RiskDecision, RiskLimits, RiskModel
from domain.order_intent import OrderIntent, OrderSide, OrderType
from domain.signal import Signal, SignalAction


TIME = datetime(2026, 8, 24, 10, tzinfo=timezone.utc)


def signal(action: SignalAction, *, identifier: str = "signal", symbol: str = "EURUSD") -> Signal:
    return Signal(identifier, "baseline", symbol, TIME, action)


def position(side: PositionSide = PositionSide.LONG, quantity: float = 0.1) -> Position:
    return Position("EURUSD", side, quantity, 1.2, TIME, "fill-entry")


def model() -> FixedSizeRiskModel:
    return FixedSizeRiskModel(RiskLimits("EURUSD"), fixed_quantity=0.1)


def test_enter_long_and_short_map_to_fixed_sized_buy_and_sell():
    long = model().evaluate(signal(SignalAction.ENTER_LONG))
    short = model().evaluate(signal(SignalAction.ENTER_SHORT, identifier="short"))

    assert long.approved and long.order_intent.side is OrderSide.BUY
    assert short.approved and short.order_intent.side is OrderSide.SELL
    assert long.order_intent.quantity == short.order_intent.quantity == 0.1
    assert long.order_intent.order_type is OrderType.MARKET
    assert long.order_intent.created_at == TIME


def test_hold_creates_no_order():
    decision = model().evaluate(signal(SignalAction.HOLD))
    assert not decision.approved
    assert decision.order_intent is None
    assert "HOLD" in decision.reason


def test_exit_closes_long_with_sell_and_short_with_buy_at_position_size():
    long_exit = model().evaluate(signal(SignalAction.EXIT, identifier="long-exit"), position=position(PositionSide.LONG, 0.3))
    short_exit = model().evaluate(signal(SignalAction.EXIT, identifier="short-exit"), position=position(PositionSide.SHORT, 0.4))

    assert long_exit.approved and long_exit.order_intent.side is OrderSide.SELL
    assert short_exit.approved and short_exit.order_intent.side is OrderSide.BUY
    assert long_exit.order_intent.quantity == 0.3
    assert short_exit.order_intent.quantity == 0.4
    assert long_exit.order_intent.metadata["risk_action"] == SignalAction.EXIT.value


def test_exit_without_position_and_entries_with_position_are_rejected():
    assert not model().evaluate(signal(SignalAction.EXIT)).approved
    assert not model().evaluate(signal(SignalAction.ENTER_LONG), position=position()).approved
    assert not model().evaluate(signal(SignalAction.ENTER_SHORT), position=position()).approved


def test_rejects_signal_and_position_outside_single_symbol_limit():
    assert not model().evaluate(signal(SignalAction.ENTER_LONG, symbol="GBPUSD")).approved
    foreign_position = Position("GBPUSD", PositionSide.LONG, 0.1, 1.2, TIME, "fill")
    assert not model().evaluate(signal(SignalAction.EXIT), position=foreign_position).approved


def test_decisions_are_deterministic_and_model_is_an_abstraction():
    first = model().evaluate(signal(SignalAction.ENTER_LONG))
    second = model().evaluate(signal(SignalAction.ENTER_LONG))
    assert first == second
    assert isinstance(model(), RiskModel)


@pytest.mark.parametrize("field, value", [("symbol", ""), ("max_open_positions", 0), ("max_open_positions", 2), ("max_open_positions", True), ("allow_pyramiding", True), ("allow_hedge", True)])
def test_risk_limits_reject_non_baseline_configuration(field, value):
    with pytest.raises(ValueError):
        RiskLimits("EURUSD", **{field: value}) if field != "symbol" else RiskLimits(value)


@pytest.mark.parametrize("field", ["allow_pyramiding", "allow_hedge"])
def test_risk_limits_requires_boolean_flags(field):
    with pytest.raises(TypeError, match=field):
        RiskLimits("EURUSD", **{field: "false"})


@pytest.mark.parametrize("quantity", [0, -1, math.inf, math.nan, True])
def test_fixed_size_rejects_invalid_quantity(quantity):
    with pytest.raises(ValueError, match="fixed_quantity"):
        FixedSizeRiskModel(RiskLimits("EURUSD"), quantity)


def test_rejects_invalid_model_inputs_and_invalid_risk_decisions():
    with pytest.raises(TypeError, match="signal"):
        model().evaluate(None)
    with pytest.raises(TypeError, match="position"):
        model().evaluate(signal(SignalAction.HOLD), position="flat")
    with pytest.raises(ValueError, match="approved"):
        RiskDecision(True, "approved")
    order = OrderIntent("order", "signal", "EURUSD", OrderSide.BUY, 1, OrderType.MARKET, TIME)
    with pytest.raises(ValueError, match="rejected"):
        RiskDecision(False, "rejected", order)
