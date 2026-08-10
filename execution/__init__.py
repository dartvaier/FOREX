"""
F9 Execution Layer: broker adapter contract, order/fill validation
and position reconciliation.

This package has NO MetaTrader dependency. MT5Execution (a later block)
implements `execution.interface.ExecutionInterface` against the MT5 API;
everything else is pure and testable without a broker connection.

TRADING_ENABLED=false remains the platform default (AGENTS.md §10,
roadmap §81).
"""

from execution.audit_log import (
    AuditEvent,
    AuditLogger,
    event_from_dict,
    event_to_dict,
    make_event,
)
from execution.broker_validation import (
    DemoValidationConfig,
    DemoValidationResult,
    validate_broker_preconditions,
    validate_demo_environment,
)
from execution.fill_validation import (
    FillValidationResult,
    validate_fill,
)
from execution.interface import (
    BrokerAccountState,
    BrokerPosition,
    ExecutionInterface,
    ExecutionReport,
)
from execution.monitoring import (
    ExecutionMetrics,
    latency_seconds,
    slippage_pips,
    update_metrics,
)
from execution.mt5_execution import (
    DEFAULT_MAGIC,
    ExecutionNotEnabledError,
    MT5Execution,
)
from execution.order_validation import (
    OrderValidationConfig,
    OrderValidationResult,
    validate_order,
)
from execution.reconciliation import (
    ReconciliationReport,
    reconcile_balance,
    reconcile_positions,
)

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "BrokerAccountState",
    "BrokerPosition",
    "DEFAULT_MAGIC",
    "DemoValidationConfig",
    "DemoValidationResult",
    "ExecutionInterface",
    "ExecutionMetrics",
    "ExecutionNotEnabledError",
    "ExecutionReport",
    "FillValidationResult",
    "MT5Execution",
    "OrderValidationConfig",
    "OrderValidationResult",
    "ReconciliationReport",
    "event_from_dict",
    "event_to_dict",
    "latency_seconds",
    "make_event",
    "reconcile_balance",
    "reconcile_positions",
    "slippage_pips",
    "update_metrics",
    "validate_broker_preconditions",
    "validate_demo_environment",
    "validate_fill",
    "validate_order",
]
