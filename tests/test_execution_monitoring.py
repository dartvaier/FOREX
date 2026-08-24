"""
Unit tests for F9 Logs, Monitoring and Broker/Demo validation.

All pure or file-scoped to a tmp_path: no MT5, no broker, no network.
"""

from datetime import datetime, timedelta, timezone

import pytest

from backtest.models.enums import OrderSide, OrderStatus, OrderType
from backtest.models.fill import Fill
from backtest.models.order import Order
from execution.audit_log import (
    AuditLogger,
    event_from_dict,
    event_to_dict,
    make_event,
)
from execution.broker_validation import (
    DemoValidationConfig,
    validate_broker_preconditions,
    validate_demo_environment,
)
from execution.interface import BrokerAccountState, ExecutionReport
from execution.monitoring import (
    ExecutionMetrics,
    latency_seconds,
    slippage_pips,
    update_metrics,
)
from execution.order_validation import OrderValidationConfig

UTC = timezone.utc
T0 = datetime(2026, 8, 10, 12, 0, 0, tzinfo=UTC)


def make_order(**kwargs) -> Order:
    defaults = dict(
        order_id="ORD-1",
        signal_id="SIG-1",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.1,
        order_type=OrderType.MARKET,
        created_at=T0,
        scheduled_for=T0,
        status=OrderStatus.PENDING,
        stop_loss=1.0900,
        take_profit=1.1100,
        reason=None,
        metadata={},
    )
    defaults.update(kwargs)
    return Order(**defaults)


def make_fill(
    *,
    reference_price: float = 1.0950,
    execution_price: float = 1.0952,
    fill_time: datetime = T0 + timedelta(seconds=2),
    quantity: float = 0.1,
) -> Fill:
    return Fill(
        fill_id="F-1",
        order_id="ORD-1",
        fill_time=fill_time,
        reference_price=reference_price,
        execution_price=execution_price,
        quantity=quantity,
        spread_impact=0.0002,
        slippage=0.0,
        commission=0.35,
    )


def make_account(
    *,
    trade_mode: str = "demo",
    margin_free: float = 10000.0,
    currency: str = "USD",
) -> BrokerAccountState:
    return BrokerAccountState(
        balance=10000.0,
        equity=10000.0,
        margin_free=margin_free,
        currency=currency,
        positions=(),
        trade_mode=trade_mode,
    )


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


def test_make_event_defaults_are_utc_and_uuid():
    event = make_event("ORDER_FILLED", {"order_id": "ORD-1"})

    assert event.event_type == "ORDER_FILLED"
    assert event.event_id
    assert event.timestamp.tzinfo is not None
    assert event.timestamp.utcoffset() is not None
    assert event.payload["order_id"] == "ORD-1"


def test_event_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        make_event(
            "ORDER_FILLED",
            timestamp=datetime(2026, 8, 10, 12, 0, 0),
        )


def test_event_roundtrip_dict():
    event = make_event("RECONCILIATION", {"divergences": 1})

    restored = event_from_dict(event_to_dict(event))

    assert restored.event_id == event.event_id
    assert restored.event_type == event.event_type
    assert restored.timestamp == event.timestamp
    assert restored.payload == event.payload


def test_audit_logger_appends_json_lines(tmp_path):
    path = tmp_path / "audit.jsonl"
    logger = AuditLogger(path)

    logger.log(make_event("ORDER_SUBMITTED", {"order_id": "ORD-1"}))
    logger.log(make_event("ORDER_FILLED", {"order_id": "ORD-1"}))

    events = logger.read_events()

    assert len(events) == 2
    assert events[0].event_type == "ORDER_SUBMITTED"
    assert events[1].event_type == "ORDER_FILLED"

    # JSONL: one object per line
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_audit_logger_empty_when_missing(tmp_path):
    logger = AuditLogger(tmp_path / "missing.jsonl")

    assert logger.read_events() == []


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------


def test_latency_seconds_positive_delta():
    fill_time = T0 + timedelta(seconds=5)

    assert latency_seconds(T0, fill_time) == 5.0


def test_latency_seconds_clamps_negative():
    fill_time = T0 - timedelta(seconds=3)

    assert latency_seconds(T0, fill_time) == 0.0


def test_slippage_pips_converts_price_delta():
    fill = make_fill(
        reference_price=1.0950,
        execution_price=1.0953,
    )

    assert slippage_pips(fill, pip_size=0.0001) == pytest.approx(3.0)


def test_slippage_pips_rejects_bad_pip_size():
    fill = make_fill()

    with pytest.raises(ValueError, match="pip_size"):
        slippage_pips(fill, pip_size=0.0)


def test_update_metrics_filled():
    report = ExecutionReport(
        order_id="ORD-1",
        status=OrderStatus.FILLED,
        fill=make_fill(),
    )

    metrics = update_metrics(
        ExecutionMetrics(),
        report,
        make_order(),
    )

    assert metrics.total_orders == 1
    assert metrics.filled == 1
    assert metrics.rejected == 0
    assert metrics.avg_latency_seconds == 2.0
    assert metrics.avg_slippage_pips == pytest.approx(2.0)
    assert metrics.rejection_rate == 0.0


def test_update_metrics_rejected():
    report = ExecutionReport(
        order_id="ORD-1",
        status=OrderStatus.REJECTED,
        message="bad volume",
    )

    metrics = update_metrics(
        ExecutionMetrics(),
        report,
        make_order(),
    )

    assert metrics.total_orders == 1
    assert metrics.rejected == 1
    assert metrics.rejection_rate == 1.0
    assert metrics.filled == 0


def test_update_metrics_accumulates_max():
    slow_fill = make_fill(fill_time=T0 + timedelta(seconds=9))
    report = ExecutionReport(
        order_id="ORD-1",
        status=OrderStatus.FILLED,
        fill=slow_fill,
    )

    metrics = update_metrics(
        ExecutionMetrics(),
        report,
        make_order(),
    )

    assert metrics.latency_max_seconds == 9.0
    assert metrics.avg_latency_seconds == 9.0


# ---------------------------------------------------------------------------
# Broker / Demo validation (roadmap §84)
# ---------------------------------------------------------------------------


def test_demo_environment_valid():
    result = validate_demo_environment(
        make_account(),
        DemoValidationConfig(),
    )

    assert result.valid


def test_demo_environment_rejects_real_account():
    result = validate_demo_environment(
        make_account(trade_mode="real"),
        DemoValidationConfig(),
    )

    assert not result.valid
    assert any("demo" in error for error in result.errors)


def test_demo_environment_server_allowlist():
    result = validate_demo_environment(
        make_account(),
        DemoValidationConfig(
            allowed_servers=("Broker-Demo",),
        ),
        server="Other-Server",
    )

    assert not result.valid
    assert any("server" in error for error in result.errors)


def test_demo_environment_min_margin():
    result = validate_demo_environment(
        make_account(margin_free=100.0),
        DemoValidationConfig(min_margin_free=500.0),
    )

    assert not result.valid
    assert any("margin" in error for error in result.errors)


def test_broker_preconditions_ok():
    result = validate_broker_preconditions(
        make_account(),
        make_order(),
        OrderValidationConfig(),
        trading_enabled=True,
        kill_switch_armed=False,
    )

    assert result.valid


def test_broker_preconditions_blocked_when_trading_disabled():
    result = validate_broker_preconditions(
        make_account(),
        make_order(),
        OrderValidationConfig(),
        trading_enabled=False,
        kill_switch_armed=False,
    )

    assert not result.valid
    assert any("TRADING_ENABLED" in error for error in result.errors)


def test_broker_preconditions_blocked_when_kill_switch_armed():
    result = validate_broker_preconditions(
        make_account(),
        make_order(),
        OrderValidationConfig(),
        trading_enabled=True,
        kill_switch_armed=True,
    )

    assert not result.valid
    assert any("kill switch" in error for error in result.errors)


def test_broker_preconditions_symbol_and_quantity():
    result = validate_broker_preconditions(
        make_account(),
        make_order(symbol="GBPJPY", quantity=5.0),
        OrderValidationConfig(
            allowed_symbols=("EURUSD",),
            max_quantity=1.0,
        ),
        trading_enabled=True,
        kill_switch_armed=False,
    )

    assert not result.valid
    assert len(result.errors) == 2
