"""
Unit tests for the F9 Execution Layer: broker interface contract,
order validation, fill validation and position reconciliation.

All tests are pure (no MT5, no network); they run under the standard
"not integration" gate.
"""

from datetime import datetime, timedelta, timezone

import pytest

from backtest.models.enums import OrderSide, OrderStatus, OrderType
from backtest.models.fill import Fill
from backtest.models.order import Order
from execution.fill_validation import validate_fill
from execution.interface import (
    BrokerAccountState,
    BrokerPosition,
    ExecutionInterface,
    ExecutionReport,
)
from execution.order_validation import (
    OrderValidationConfig,
    validate_order,
)
from execution.reconciliation import (
    reconcile_balance,
    reconcile_positions,
)

UTC = timezone.utc
T0 = datetime(2026, 8, 10, 12, 0, 0, tzinfo=UTC)


def make_order(
    *,
    order_id: str = "ORD-1",
    signal_id: str = "SIG-1",
    symbol: str = "EURUSD",
    side: OrderSide = OrderSide.BUY,
    quantity: float = 0.1,
    created_at: datetime = T0,
    stop_loss: float | None = 1.0900,
    take_profit: float | None = 1.1000,
) -> Order:
    return Order(
        order_id=order_id,
        signal_id=signal_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        order_type=OrderType.MARKET,
        created_at=created_at,
        scheduled_for=created_at,
        status=OrderStatus.PENDING,
        stop_loss=stop_loss,
        take_profit=take_profit,
        reason=None,
        metadata={},
    )


def make_fill(
    *,
    fill_id: str = "FILL-1",
    order_id: str = "ORD-1",
    fill_time: datetime = T0 + timedelta(seconds=1),
    reference_price: float = 1.0950,
    execution_price: float = 1.0950,
    quantity: float = 0.1,
    commission: float = 0.35,
) -> Fill:
    return Fill(
        fill_id=fill_id,
        order_id=order_id,
        fill_time=fill_time,
        reference_price=reference_price,
        execution_price=execution_price,
        quantity=quantity,
        spread_impact=0.0002,
        slippage=0.0,
        commission=commission,
    )


def make_account(
    *,
    balance: float = 10000.0,
    equity: float = 10000.0,
    margin_free: float = 10000.0,
    positions: tuple[BrokerPosition, ...] = (),
) -> BrokerAccountState:
    return BrokerAccountState(
        balance=balance,
        equity=equity,
        margin_free=margin_free,
        currency="USD",
        positions=positions,
    )


# ---------------------------------------------------------------------------
# ExecutionInterface contract
# ---------------------------------------------------------------------------


def test_interface_cannot_be_instantiated():
    with pytest.raises(TypeError):
        ExecutionInterface()  # type: ignore[abstract]


class FakeAdapter(ExecutionInterface):
    def submit(self, order):
        raise NotImplementedError

    def cancel(self, order_id):
        raise NotImplementedError

    def fetch_account(self):
        raise NotImplementedError

    def fetch_positions(self, symbol=None):
        raise NotImplementedError

    def ping(self):
        return True

    def close(self):
        pass


def test_interface_accepts_concrete_adapter():
    adapter = FakeAdapter()
    assert adapter.ping() is True


def test_execution_report_filled_requires_fill():
    with pytest.raises(
        ValueError,
        match="must carry a fill",
    ):
        ExecutionReport(
            order_id="ORD-1",
            status=OrderStatus.FILLED,
        )


def test_execution_report_fill_requires_filled_status():
    with pytest.raises(
        ValueError,
        match="non-FILLED",
    ):
        ExecutionReport(
            order_id="ORD-1",
            status=OrderStatus.REJECTED,
            fill=make_fill(),
        )


def test_execution_report_rejected_without_fill_ok():
    report = ExecutionReport(
        order_id="ORD-1",
        status=OrderStatus.REJECTED,
        message="bad volume",
    )

    assert report.status == OrderStatus.REJECTED
    assert report.fill is None


def test_broker_position_validates_quantity():
    with pytest.raises(ValueError, match="quantity"):
        BrokerPosition(
            identifier="TICKET-1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=0.0,
            entry_price=1.0950,
            open_time=T0,
        )


def test_broker_account_validates_negative_margin():
    with pytest.raises(ValueError, match="margin_free"):
        make_account(margin_free=-1.0)


# ---------------------------------------------------------------------------
# Order validation
# ---------------------------------------------------------------------------


def test_valid_order_passes():
    result = validate_order(
        make_order(),
        make_account(),
        OrderValidationConfig(),
    )

    assert result.valid
    assert result.errors == ()


def test_symbol_not_allowed_rejected():
    result = validate_order(
        make_order(symbol="GBPJPY"),
        make_account(),
        OrderValidationConfig(
            allowed_symbols=("EURUSD",),
        ),
    )

    assert not result.valid
    assert any("not in allowed" in error for error in result.errors)


def test_quantity_below_minimum_rejected():
    result = validate_order(
        make_order(quantity=0.001),
        make_account(),
        OrderValidationConfig(min_quantity=0.01),
    )

    assert not result.valid
    assert any("below minimum" in error for error in result.errors)


def test_quantity_above_maximum_rejected():
    result = validate_order(
        make_order(quantity=12.0),
        make_account(),
        OrderValidationConfig(max_quantity=10.0),
    )

    assert not result.valid
    assert any("above maximum" in error for error in result.errors)


def test_insufficient_margin_rejected():
    result = validate_order(
        make_order(quantity=1.0),
        make_account(margin_free=50.0),
        OrderValidationConfig(margin_per_lot=100.0),
    )

    assert not result.valid
    assert any("margin" in error for error in result.errors)


def test_stop_loss_equal_take_profit_rejected():
    result = validate_order(
        make_order(stop_loss=1.0950, take_profit=1.0950),
        make_account(),
        OrderValidationConfig(),
    )

    assert not result.valid
    assert any("cannot be equal" in error for error in result.errors)


def test_require_stop_loss_enforced():
    result = validate_order(
        make_order(stop_loss=None),
        make_account(),
        OrderValidationConfig(require_stop_loss=True),
    )

    assert not result.valid
    assert any("stop_loss is required" in error for error in result.errors)


def test_missing_stop_loss_warns_by_default():
    result = validate_order(
        make_order(stop_loss=None),
        make_account(),
        OrderValidationConfig(),
    )

    assert result.valid
    assert any("no stop_loss" in warning for warning in result.warnings)


def test_multiple_violations_collected():
    result = validate_order(
        make_order(quantity=20.0, symbol="XAUUSD"),
        make_account(margin_free=10.0),
        OrderValidationConfig(
            allowed_symbols=("EURUSD",),
            max_quantity=5.0,
            margin_per_lot=100.0,
        ),
    )

    assert not result.valid
    assert len(result.errors) >= 3


# ---------------------------------------------------------------------------
# Fill validation
# ---------------------------------------------------------------------------


def test_valid_fill_passes():
    order = make_order()
    fill = make_fill()

    result = validate_fill(
        order,
        fill,
        max_slippage_pips=2.0,
        pip_size=0.0001,
    )

    assert result.valid


def test_fill_order_id_mismatch_rejected():
    fill = make_fill(order_id="ORD-999")

    result = validate_fill(
        make_order(),
        fill,
        max_slippage_pips=2.0,
        pip_size=0.0001,
    )

    assert not result.valid
    assert any("order_id" in error for error in result.errors)


def test_fill_quantity_mismatch_rejected():
    fill = make_fill(quantity=0.05)

    result = validate_fill(
        make_order(quantity=0.1),
        fill,
        max_slippage_pips=2.0,
        pip_size=0.0001,
    )

    assert not result.valid
    assert any("quantity" in error for error in result.errors)


def test_fill_before_order_creation_rejected():
    fill = make_fill(
        fill_time=T0 - timedelta(minutes=1),
    )

    result = validate_fill(
        make_order(),
        fill,
        max_slippage_pips=2.0,
        pip_size=0.0001,
    )

    assert not result.valid
    assert any("causal" in error for error in result.errors)


def test_fill_excessive_slippage_rejected():
    fill = make_fill(
        reference_price=1.0950,
        execution_price=1.0960,
    )

    result = validate_fill(
        make_order(),
        fill,
        max_slippage_pips=2.0,
        pip_size=0.0001,
    )

    # 10 pips of slippage > 2 pips tolerance
    assert not result.valid
    assert any("slippage" in error for error in result.errors)


def test_fill_slippage_within_tolerance_passes():
    fill = make_fill(
        reference_price=1.0950,
        execution_price=1.0951,
    )

    result = validate_fill(
        make_order(),
        fill,
        max_slippage_pips=2.0,
        pip_size=0.0001,
    )

    assert result.valid


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------


def position(
    identifier: str,
    quantity: float,
    symbol: str = "EURUSD",
    side: OrderSide = OrderSide.BUY,
) -> BrokerPosition:
    return BrokerPosition(
        identifier=identifier,
        symbol=symbol,
        side=side,
        quantity=quantity,
        entry_price=1.0950,
        open_time=T0,
    )


def test_reconcile_identical_positions_consistent():
    expected = {"EURUSD:BUY": position("T1", 0.1)}
    actual = {"EURUSD:BUY": position("T1", 0.1)}

    report = reconcile_positions(expected, actual)

    assert report.consistent
    assert report.issues == 0


def test_reconcile_missing_position():
    expected = {"EURUSD:BUY": position("T1", 0.1)}

    report = reconcile_positions(expected, {})

    assert not report.consistent
    assert len(report.missing_positions) == 1


def test_reconcile_unexpected_position():
    actual = {"EURUSD:SELL": position("T9", 0.1, side=OrderSide.SELL)}

    report = reconcile_positions({}, actual)

    assert not report.consistent
    assert len(report.unexpected_positions) == 1


def test_reconcile_quantity_mismatch():
    expected = {"EURUSD:BUY": position("T1", 0.1)}
    actual = {"EURUSD:BUY": position("T1", 0.2)}

    report = reconcile_positions(expected, actual)

    assert not report.consistent
    assert len(report.quantity_mismatches) == 1

    key, ticket, expected_qty, actual_qty = (
        report.quantity_mismatches[0]
    )
    assert key == "EURUSD:BUY"
    assert expected_qty == 0.1
    assert actual_qty == 0.2


def test_reconcile_balance_within_tolerance():
    assert reconcile_balance(10000.0, 10000.005) is True


def test_reconcile_balance_outside_tolerance():
    assert reconcile_balance(10000.0, 10000.50) is False
