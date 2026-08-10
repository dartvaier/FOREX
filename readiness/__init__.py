"""
F10 Live Readiness: programmatic readiness review, risk limits and
operational safety checks (roadmap §89-91).

No broker and no activation required: everything is pure or derived
from module availability. The Demo activation decision stays with the
operator (TRADING_ENABLED=false remains the default).
"""

from readiness.review import (
    ReadinessItem,
    ReadinessReview,
    ReadinessState,
    collect_module_availability,
    evaluate_readiness,
)
from readiness.risk_limits import (
    RiskLimitConfig,
    RiskLimitsReport,
    evaluate_risk_limits,
    position_size_for_risk,
    risk_amount,
    stop_distance_pips,
)
from readiness.safety import (
    connection_breach_count,
    duplicate_order_ids,
    order_count_per_symbol,
)

__all__ = [
    "ReadinessItem",
    "ReadinessReview",
    "ReadinessState",
    "RiskLimitConfig",
    "RiskLimitsReport",
    "collect_module_availability",
    "connection_breach_count",
    "duplicate_order_ids",
    "evaluate_readiness",
    "evaluate_risk_limits",
    "order_count_per_symbol",
    "position_size_for_risk",
    "risk_amount",
    "stop_distance_pips",
]
