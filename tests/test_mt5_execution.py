"""
Unit tests for MT5Execution (F9 broker adapter).

The MetaTrader5 module is replaced by a fake: no real broker is ever
touched. The trading_enabled guard is exercised explicitly.
"""

from types import SimpleNamespace
from datetime import datetime, timezone

import pytest

from backtest.models.enums import OrderSide, OrderStatus, OrderType
from backtest.models.fill import Fill
from backtest.models.order import Order
from execution.interface import BrokerPosition
from execution.mt5_execution import (
    DEFAULT_MAGIC,
    ExecutionNotEnabledError,
    MT5Execution,
)
from execution.order_validation import OrderValidationConfig

UTC_EPOCH = 1786406400  # 2026-08-10 12:00:00 UTC approx


class FakeMT5:
    """Minimal fake of the MetaTrader5 module surface used by the adapter."""

    # Real MT5 API values (docs/25 ES-02): FOK=0, IOC=1, RETURN=2.
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2

    def __init__(self) -> None:
        self.initialize_calls = 0
        self.shutdown_calls = 0
        self.sent_requests: list[dict] = []
        self.tick = SimpleNamespace(bid=1.0998, ask=1.1000)
        self.symbol = SimpleNamespace(
            filling_mode=2,  # IOC bit
            digits=5,  # EURUSD-like
        )
        self.order_send_result = SimpleNamespace(
            retcode=10009,
            comment="done",
            deal=12345,
            order=67890,
            price=1.1000,
            volume=0.1,
            time=UTC_EPOCH,
        )
        self.account = SimpleNamespace(
            balance=10000.0,
            equity=10000.0,
            margin_free=9000.0,
            currency="USD",
            trade_mode=0,  # demo (real MT5 enum)
        )
        self.positions = [
            SimpleNamespace(
                ticket=1,
                symbol="EURUSD",
                type=0,
                volume=0.1,
                price_open=1.0900,
                time=UTC_EPOCH,
                price_current=1.0910,
            )
        ]
        self.terminal = SimpleNamespace(connected=True)
        self.last_error_value = (0, "no error")

    def initialize(self):
        self.initialize_calls += 1
        return True

    def last_error(self):
        return self.last_error_value

    def symbol_info_tick(self, symbol):
        return self.tick

    def symbol_info(self, symbol):
        return self.symbol

    def order_send(self, request):
        self.sent_requests.append(request)
        return self.order_send_result

    def account_info(self):
        return self.account

    def positions_get(self, symbol=None):
        if symbol is None:
            return self.positions
        return [p for p in self.positions if p.symbol == symbol]

    def terminal_info(self):
        return self.terminal

    def shutdown(self):
        self.shutdown_calls += 1


@pytest.fixture
def fake_mt5(monkeypatch):
    fake = FakeMT5()
    monkeypatch.setattr(
        "execution.mt5_execution.mt5",
        fake,
    )
    return fake


def make_order(
    *,
    order_id: str = "ORD-1",
    symbol: str = "EURUSD",
    side: OrderSide = OrderSide.BUY,
    quantity: float = 0.1,
    stop_loss: float | None = 1.0900,
    take_profit: float | None = 1.1100,
) -> Order:
    from datetime import datetime, timezone

    created_at = datetime(
        2026,
        8,
        10,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    return Order(
        order_id=order_id,
        signal_id="SIG-1",
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


# ---------------------------------------------------------------------------
# Trading guard (AGENTS.md §10)
# ---------------------------------------------------------------------------


def test_submit_blocked_while_trading_disabled(fake_mt5):
    adapter = MT5Execution()

    with pytest.raises(ExecutionNotEnabledError):
        adapter.submit(make_order())

    assert fake_mt5.sent_requests == []


def test_cancel_blocked_while_trading_disabled(fake_mt5):
    adapter = MT5Execution()

    with pytest.raises(ExecutionNotEnabledError):
        adapter.cancel("ORD-1")

    assert fake_mt5.sent_requests == []


def test_fetch_account_allowed_while_disabled(fake_mt5):
    adapter = MT5Execution()

    account = adapter.fetch_account()

    assert account.balance == 10000.0
    assert account.currency == "USD"


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------


def test_submit_buy_uses_ask_and_builds_request(fake_mt5):
    adapter = MT5Execution(trading_enabled=True)

    report = adapter.submit(
        make_order(
            side=OrderSide.BUY,
            stop_loss=1.0900,
            take_profit=1.1100,
        )
    )

    assert report.status == OrderStatus.FILLED
    assert report.broker_order_id == "67890"
    assert report.fill is not None
    assert report.fill.order_id == "ORD-1"
    assert report.fill.quantity == 0.1

    request = fake_mt5.sent_requests[0]
    assert request["action"] == 1
    assert request["symbol"] == "EURUSD"
    assert request["volume"] == 0.1
    assert request["type"] == 0  # ORDER_TYPE_BUY
    assert request["price"] == 1.1000  # ask
    assert request["sl"] == 1.0900
    assert request["tp"] == 1.1100
    assert request["magic"] == DEFAULT_MAGIC
    # ES-02: type_filling must use the REAL MT5 enum value for IOC (1),
    # not a mock-specific literal. The old mock (FOK=1/IOC=2/RETURN=3)
    # masked a retcode-10030 bug: type_filling==2 is RETURN in the
    # real API, which market orders reject.
    assert request["type_filling"] == fake_mt5.ORDER_FILLING_IOC
    assert request["type_filling"] == 1


def test_submit_sell_uses_bid(fake_mt5):
    adapter = MT5Execution(trading_enabled=True)

    report = adapter.submit(
        make_order(side=OrderSide.SELL),
    )

    assert report.status == OrderStatus.FILLED
    assert fake_mt5.sent_requests[0]["type"] == 1  # ORDER_TYPE_SELL
    assert fake_mt5.sent_requests[0]["price"] == 1.0998  # bid


def test_submit_broker_rejection_returns_rejected_report(fake_mt5):
    fake_mt5.order_send_result = SimpleNamespace(
        retcode=10016,
        comment="Invalid volume",
        deal=0,
        order=0,
        price=0.0,
        volume=0.0,
        time=0,
    )

    adapter = MT5Execution(trading_enabled=True)

    report = adapter.submit(make_order())

    assert report.status == OrderStatus.REJECTED
    assert "10016" in report.message
    assert report.fill is None


def test_submit_validation_rejects_before_broker(fake_mt5):
    adapter = MT5Execution(
        trading_enabled=True,
        validation_config=OrderValidationConfig(max_quantity=1.0),
    )

    report = adapter.submit(make_order(quantity=5.0))

    assert report.status == OrderStatus.REJECTED
    assert "maximum" in report.message
    assert fake_mt5.sent_requests == []


def test_submit_without_mt5_raises(monkeypatch):
    monkeypatch.setattr(
        "execution.mt5_execution.mt5",
        None,
    )

    adapter = MT5Execution(trading_enabled=True)

    with pytest.raises(RuntimeError, match="not installed"):
        adapter.submit(make_order())


def test_fill_time_is_utc_aware(fake_mt5):
    adapter = MT5Execution(trading_enabled=True)

    report = adapter.submit(make_order())

    assert report.fill is not None
    assert report.fill.fill_time.tzinfo is not None
    assert report.fill.fill_time.utcoffset() is not None


def test_close_position_delegates_with_ticket(fake_mt5):
    adapter = MT5Execution(trading_enabled=True)

    position = BrokerPosition(
        identifier="57912767267",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.01,
        entry_price=1.15431,
        open_time=datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc),
    )

    report = adapter.close_position(position)

    assert report.status == OrderStatus.FILLED

    request = fake_mt5.sent_requests[0]
    assert request["type"] == 1  # SELL closes BUY
    assert request["position"] == 57912767267
    assert request["volume"] == 0.01
    assert request["price"] == 1.0998  # bid for SELL
    assert request["symbol"] == "EURUSD"


def test_close_position_blocked_while_disabled(fake_mt5):
    adapter = MT5Execution()

    with pytest.raises(ExecutionNotEnabledError):
        adapter.close_position(
            BrokerPosition(
                identifier="T1",
                symbol="EURUSD",
                side=OrderSide.BUY,
                quantity=0.01,
                entry_price=1.15,
                open_time=datetime(
                    2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc
                ),
            )
        )

    assert fake_mt5.sent_requests == []


# ---------------------------------------------------------------------------
# Cancel / close / ping
# ---------------------------------------------------------------------------


def test_cancel_requires_broker_ticket(fake_mt5):
    """ES-01: non-numeric order ids are rejected before the broker."""
    adapter = MT5Execution(trading_enabled=True)

    report = adapter.cancel("ORD-7")

    assert report.status == OrderStatus.REJECTED
    assert "broker ticket" in report.message
    assert fake_mt5.sent_requests == []


def test_cancel_by_ticket_sends_remove(fake_mt5):
    """ES-01: a numeric broker ticket cancels via TRADE_ACTION_REMOVE."""
    adapter = MT5Execution(trading_enabled=True)

    report = adapter.cancel("57912767267")

    assert report.status == OrderStatus.CANCELLED
    request = fake_mt5.sent_requests[0]
    assert request["action"] == 5
    assert request["order"] == 57912767267
    assert report.broker_order_id == "67890"


def test_cancel_failure_is_rejected_not_cancelled(fake_mt5):
    """ES-01: a failed removal is REJECTED, never reported as CANCELLED."""
    fake_mt5.order_send_result = SimpleNamespace(
        retcode=10030,
        comment="order not found",
        deal=0,
        order=0,
        price=0.0,
        volume=0.0,
        time=0,
    )

    adapter = MT5Execution(trading_enabled=True)

    report = adapter.cancel("12345")

    assert report.status == OrderStatus.REJECTED
    assert "10030" in report.message


def test_close_calls_shutdown(fake_mt5):
    adapter = MT5Execution()

    adapter.fetch_account()  # connects
    adapter.close()

    assert fake_mt5.shutdown_calls == 1


def test_ping_returns_connected(fake_mt5):
    adapter = MT5Execution()

    assert adapter.ping() is True


def test_ping_false_when_terminal_missing(fake_mt5):
    fake_mt5.terminal = None

    adapter = MT5Execution()

    assert adapter.ping() is False


# ---------------------------------------------------------------------------
# Hardening ES-03: demo policy + kill switch on the mandatory path
# ---------------------------------------------------------------------------


def test_submit_real_account_blocked_by_default(fake_mt5):
    """ES-03: a real account cannot execute by accident."""
    fake_mt5.account.trade_mode = 2  # real

    adapter = MT5Execution(trading_enabled=True)

    report = adapter.submit(make_order())

    assert report.status == OrderStatus.REJECTED
    assert "allowed_trade_modes" in report.message
    assert fake_mt5.sent_requests == []


def test_submit_kill_switch_blocks(fake_mt5):
    """ES-03: the kill switch is checked on the submit path."""
    adapter = MT5Execution(
        trading_enabled=True,
        kill_switch=lambda: True,
    )

    report = adapter.submit(make_order())

    assert report.status == OrderStatus.REJECTED
    assert "kill switch" in report.message
    assert fake_mt5.sent_requests == []


def test_close_position_blocked_by_kill_switch(fake_mt5):
    """ES-03: the kill switch gate applies to close too."""
    adapter = MT5Execution(
        trading_enabled=True,
        kill_switch=lambda: True,
    )

    report = adapter.close_position(
        BrokerPosition(
            identifier="T1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=0.01,
            entry_price=1.15,
            open_time=datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc),
        )
    )

    assert report.status == OrderStatus.REJECTED
    assert "kill switch" in report.message
    assert fake_mt5.sent_requests == []


# ---------------------------------------------------------------------------
# Hardening ES-04: a real fill is never downgraded to REJECTED
# ---------------------------------------------------------------------------


def test_fill_outside_tolerance_keeps_filled_and_flags_reconciliation(
    fake_mt5,
):
    """ES-04: broker FILLED + local slippage violation stays FILLED and
    requires reconciliation; the real execution is never erased."""
    fake_mt5.order_send_result = SimpleNamespace(
        retcode=10009,
        comment="done",
        deal=12345,
        order=67890,
        price=1.1020,  # 20 pips above ask 1.1000 -> outside 2-pip tolerance
        volume=0.1,
        time=UTC_EPOCH,
    )

    adapter = MT5Execution(trading_enabled=True)

    report = adapter.submit(make_order())

    assert report.status == OrderStatus.FILLED
    assert report.fill is not None
    assert report.fill.execution_price == 1.1020
    assert report.validation_status == "OUTSIDE_TOLERANCE"
    assert report.requires_reconciliation is True
    assert "OUTSIDE_TOLERANCE" in report.message or "validation" in report.message


# ---------------------------------------------------------------------------
# Hardening ES-05: pip size per instrument on fill validation
# ---------------------------------------------------------------------------


def test_submit_uses_real_pip_size_for_jpy(fake_mt5):
    """ES-05: USDJPY (digits=3, pip=0.01) validates slippage with the
    real pip size, not the 0.0001 default."""
    fake_mt5.symbol.digits = 3  # USDJPY-like
    fake_mt5.tick = SimpleNamespace(bid=110.0000, ask=110.0000)
    fake_mt5.order_send_result = SimpleNamespace(
        retcode=10009,
        comment="done",
        deal=12345,
        order=67890,
        price=110.0099,  # 99 pips under the old 0.0001 pip; <1 pip for JPY
        volume=0.1,
        time=UTC_EPOCH,
    )

    adapter = MT5Execution(trading_enabled=True)

    report = adapter.submit(make_order(symbol="USDJPY"))

    assert report.status == OrderStatus.FILLED
    assert report.requires_reconciliation is False


# ---------------------------------------------------------------------------
# Fetch state
# ---------------------------------------------------------------------------


def test_fetch_positions_maps_side_and_quantity(fake_mt5):
    adapter = MT5Execution()

    positions = adapter.fetch_positions()

    assert len(positions) == 1
    position = positions[0]
    assert position.identifier == "1"
    assert position.symbol == "EURUSD"
    assert position.side == OrderSide.BUY
    assert position.quantity == 0.1
    assert position.entry_price == 1.0900
    assert position.current_price == 1.0910


def test_fetch_positions_sell_side(fake_mt5):
    fake_mt5.positions[0].type = 1

    adapter = MT5Execution()

    positions = adapter.fetch_positions()

    assert positions[0].side == OrderSide.SELL


def test_fetch_account_includes_positions(fake_mt5):
    adapter = MT5Execution()

    account = adapter.fetch_account()

    assert len(account.positions) == 1
    assert account.margin_free == 9000.0
