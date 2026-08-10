"""
F9 Execution Layer: broker adapter contract, order/fill validation
and position reconciliation.

This package has NO MetaTrader dependency. MT5Execution (a later block)
implements `execution.interface.ExecutionInterface` against the MT5 API;
everything else is pure and testable without a broker connection.

TRADING_ENABLED=false remains the platform default (AGENTS.md §10,
roadmap §81).
"""

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
    "BrokerAccountState",
    "BrokerPosition",
    "ExecutionInterface",
    "ExecutionReport",
    "FillValidationResult",
    "OrderValidationConfig",
    "OrderValidationResult",
    "ReconciliationReport",
    "reconcile_balance",
    "reconcile_positions",
    "validate_fill",
    "validate_order",
]
