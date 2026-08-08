from datetime import datetime, timezone

import pytest

from backtest.costs import (
    CostModel,
    ExecutionCost,
    FixedCostModel,
    ZeroCostModel,
)
from backtest.models import (
    InstrumentSpecification,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)


def timestamp():
    return datetime(
        2026,
        8,
        8,
        10,
        15,
        tzinfo=timezone.utc,
    )


def make_instrument(
    symbol: str = "EURUSD",
) -> InstrumentSpecification:
    return InstrumentSpecification(
        symbol=symbol,
        digits=5,
        point=0.00001,
        pip_size=0.00010,
        contract_size=100000,
        volume_min=0.01,
        volume_max=500.0,
        volume_step=0.01,
        tick_size=0.00001,
    )


def make_order(
    side: OrderSide,
    *,
    quantity: float = 0.10,
    symbol: str = "EURUSD",
) -> Order:
    return Order(
        order_id="ORD-001",
        signal_id="SIG-001",
        symbol=symbol,
        side=side,
        quantity=quantity,
        order_type=OrderType.MARKET,
        created_at=timestamp(),
        scheduled_for=timestamp(),
        status=OrderStatus.PENDING,
    )


def make_cost_model() -> FixedCostModel:
    return FixedCostModel(
        instrument=make_instrument(),
        spread_pips=2.0,
        slippage_pips=0.5,
        commission_per_lot_per_side=3.50,
    )


def test_fixed_cost_model_satisfies_protocol():
    model = make_cost_model()

    assert isinstance(
        model,
        CostModel,
    )


def test_fixed_cost_model_preserves_configuration():
    instrument = make_instrument()

    model = FixedCostModel(
        instrument=instrument,
        spread_pips=2.0,
        slippage_pips=0.5,
        commission_per_lot_per_side=3.50,
    )

    assert model.instrument is instrument
    assert model.spread_pips == 2.0
    assert model.slippage_pips == 0.5

    assert (
        model.commission_per_lot_per_side
        == 3.50
    )


def test_buy_cost_is_adverse_to_reference_price():
    cost = make_cost_model().calculate(
        make_order(
            OrderSide.BUY
        ),
        reference_price=1.16000,
    )

    assert cost.reference_price == pytest.approx(
        1.16000
    )

    assert cost.spread_impact == pytest.approx(
        0.00010
    )

    assert cost.slippage == pytest.approx(
        0.00005
    )

    assert cost.execution_price == pytest.approx(
        1.16015
    )


def test_sell_cost_is_adverse_to_reference_price():
    cost = make_cost_model().calculate(
        make_order(
            OrderSide.SELL
        ),
        reference_price=1.16000,
    )

    assert cost.execution_price == pytest.approx(
        1.15985
    )

    assert cost.spread_impact == pytest.approx(
        0.00010
    )

    assert cost.slippage == pytest.approx(
        0.00005
    )


def test_commission_scales_with_quantity():
    cost = make_cost_model().calculate(
        make_order(
            OrderSide.BUY,
            quantity=0.10,
        ),
        reference_price=1.16000,
    )

    assert cost.commission == pytest.approx(
        0.35
    )


def test_one_lot_commission():
    cost = make_cost_model().calculate(
        make_order(
            OrderSide.BUY,
            quantity=1.0,
        ),
        reference_price=1.16000,
    )

    assert cost.commission == pytest.approx(
        3.50
    )


def test_zero_cost_model_has_no_price_impact():
    model = ZeroCostModel(
        instrument=make_instrument()
    )

    cost = model.calculate(
        make_order(
            OrderSide.BUY
        ),
        reference_price=1.16000,
    )

    assert cost.reference_price == pytest.approx(
        1.16000
    )

    assert cost.execution_price == pytest.approx(
        1.16000
    )

    assert cost.spread_impact == 0.0
    assert cost.slippage == 0.0
    assert cost.commission == 0.0


def test_zero_cost_model_sell_is_also_frictionless():
    model = ZeroCostModel(
        instrument=make_instrument()
    )

    cost = model.calculate(
        make_order(
            OrderSide.SELL
        ),
        reference_price=1.16000,
    )

    assert cost.execution_price == pytest.approx(
        1.16000
    )


def test_cost_model_does_not_use_order_metadata_for_costs():
    order = Order(
        order_id="ORD-001",
        signal_id="SIG-001",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.10,
        order_type=OrderType.MARKET,
        created_at=timestamp(),
        scheduled_for=timestamp(),
        status=OrderStatus.PENDING,
        metadata={
            "historical_spread": 99999,
        },
    )

    cost = make_cost_model().calculate(
        order,
        reference_price=1.16000,
    )

    assert cost.spread_impact == pytest.approx(
        0.00010
    )


def test_cost_model_requires_instrument():
    with pytest.raises(
        TypeError,
        match="InstrumentSpecification",
    ):
        FixedCostModel(
            instrument=None,  # type: ignore[arg-type]
            spread_pips=2.0,
            slippage_pips=0.5,
            commission_per_lot_per_side=3.50,
        )


@pytest.mark.parametrize(
    "value",
    [
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
        True,
    ],
)
def test_cost_model_rejects_invalid_spread(
    value,
):
    with pytest.raises(
        ValueError,
        match="spread_pips",
    ):
        FixedCostModel(
            instrument=make_instrument(),
            spread_pips=value,
            slippage_pips=0.0,
            commission_per_lot_per_side=0.0,
        )


@pytest.mark.parametrize(
    "value",
    [
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
        True,
    ],
)
def test_cost_model_rejects_invalid_slippage(
    value,
):
    with pytest.raises(
        ValueError,
        match="slippage_pips",
    ):
        FixedCostModel(
            instrument=make_instrument(),
            spread_pips=0.0,
            slippage_pips=value,
            commission_per_lot_per_side=0.0,
        )


@pytest.mark.parametrize(
    "value",
    [
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
        True,
    ],
)
def test_cost_model_rejects_invalid_commission(
    value,
):
    with pytest.raises(
        ValueError,
        match="commission_per_lot_per_side",
    ):
        FixedCostModel(
            instrument=make_instrument(),
            spread_pips=0.0,
            slippage_pips=0.0,
            commission_per_lot_per_side=value,
        )


@pytest.mark.parametrize(
    "reference_price",
    [
        0,
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
        True,
    ],
)
def test_cost_model_requires_valid_reference_price(
    reference_price,
):
    with pytest.raises(
        ValueError,
        match="reference_price",
    ):
        make_cost_model().calculate(
            make_order(
                OrderSide.BUY
            ),
            reference_price=reference_price,
        )


def test_cost_model_requires_order():
    with pytest.raises(
        TypeError,
        match="Order",
    ):
        make_cost_model().calculate(
            object(),  # type: ignore[arg-type]
            reference_price=1.16000,
        )


def test_cost_model_rejects_symbol_mismatch():
    model = FixedCostModel(
        instrument=make_instrument(
            symbol="EURUSD"
        ),
        spread_pips=2.0,
        slippage_pips=0.5,
        commission_per_lot_per_side=3.50,
    )

    order = make_order(
        OrderSide.BUY,
        symbol="GBPUSD",
    )

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        model.calculate(
            order,
            reference_price=1.16000,
        )


def test_execution_cost_is_immutable():
    cost = ExecutionCost(
        reference_price=1.16000,
        execution_price=1.16015,
        spread_impact=0.00010,
        slippage=0.00005,
        commission=0.35,
    )

    with pytest.raises(AttributeError):
        cost.execution_price = 1.20  # type: ignore[misc]