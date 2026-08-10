"""
F10 Live Readiness review (roadmap §89-91).

Encodes the Live Readiness Review checklist: every pre-requisite from
§90 (backtest, OOS, cost stress, risk engine, demo validation,
execution validation, monitoring, kill switch, operational procedures)
plus the review dimensions from §91.

The review is computed from a `ReadinessState` snapshot; module
availability is collected programmatically (no broker needed), while
decision flags (trading_enabled, demo_validation_done, ...) are
provided by the operator.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass

# Modules that must be importable for the execution stack to exist.
_REQUIRED_MODULES = (
    "execution.interface",
    "execution.mt5_execution",
    "execution.order_validation",
    "execution.fill_validation",
    "execution.reconciliation",
    "execution.audit_log",
    "execution.monitoring",
    "execution.comparison",
    "execution.broker_validation",
    "backtest.risk",
)


def collect_module_availability() -> dict[str, bool]:
    """Which required modules are importable right now (real evidence)."""
    return {
        module: importlib.util.find_spec(module) is not None
        for module in _REQUIRED_MODULES
    }


@dataclass(frozen=True, slots=True)
class ReadinessState:
    """System snapshot used to evaluate the readiness review."""

    trading_enabled: bool = False
    kill_switch_available: bool = False
    monitoring_available: bool = False
    audit_log_available: bool = False
    execution_adapter_available: bool = False
    reconciliation_available: bool = False
    broker_validation_available: bool = False
    backtest_done: bool = False
    oos_done: bool = False
    cost_stress_done: bool = False
    risk_engine_done: bool = False
    demo_validation_done: bool = False
    ops_procedures_documented: bool = False


@dataclass(frozen=True, slots=True)
class ReadinessItem:
    """One checklist item with its verdict and evidence."""

    category: str
    item_id: str
    description: str
    satisfied: bool
    evidence: str = ""


@dataclass(frozen=True, slots=True)
class ReadinessReview:
    """Full review: items + aggregate verdicts."""

    items: tuple[ReadinessItem, ...]

    @property
    def ready(self) -> bool:
        return all(item.satisfied for item in self.items)

    @property
    def missing_items(self) -> tuple[ReadinessItem, ...]:
        return tuple(
            item for item in self.items if not item.satisfied
        )

    @property
    def missing_categories(self) -> tuple[str, ...]:
        categories: list[str] = []

        for item in self.items:
            if not item.satisfied and (
                item.category not in categories
            ):
                categories.append(item.category)

        return tuple(categories)


# (category, item_id, description, state_field)
_ITEMS_SPEC = (
    (
        "validation",
        "backtest",
        "Robust backtest completed",
        "backtest_done",
    ),
    (
        "validation",
        "oos",
        "Out-of-sample lockbox consulted",
        "oos_done",
    ),
    (
        "validation",
        "cost_stress",
        "Cost stress (1.5x/2.0x) executed",
        "cost_stress_done",
    ),
    (
        "risk",
        "risk_engine",
        "Risk engine validated (sizing + limits)",
        "risk_engine_done",
    ),
    (
        "risk",
        "kill_switch",
        "Kill switch available",
        "kill_switch_available",
    ),
    (
        "execution",
        "adapter",
        "Execution adapter implemented",
        "execution_adapter_available",
    ),
    (
        "execution",
        "order_validation",
        "Order validation enforced before broker",
        "order_validation_available",
    ),
    (
        "execution",
        "fill_validation",
        "Fill validation enforced",
        "fill_validation_available",
    ),
    (
        "execution",
        "reconciliation",
        "Position reconciliation available",
        "reconciliation_available",
    ),
    (
        "execution",
        "broker_validation",
        "Broker/demo validation available",
        "broker_validation_available",
    ),
    (
        "execution",
        "monitoring",
        "Execution monitoring available",
        "monitoring_available",
    ),
    (
        "execution",
        "audit_log",
        "Audit log available",
        "audit_log_available",
    ),
    (
        "execution",
        "demo_validation",
        "Demo validation period completed",
        "demo_validation_done",
    ),
    (
        "operations",
        "trading_flag",
        "Trading flag explicitly enabled (activation decision)",
        "trading_enabled",
    ),
    (
        "operations",
        "ops_procedures",
        "Operational procedures documented",
        "ops_procedures_documented",
    ),
)


def evaluate_readiness(
    state: ReadinessState,
    *,
    module_availability: dict[str, bool] | None = None,
) -> ReadinessReview:
    """
    Evaluate the full readiness review from a system snapshot.

    Module availability is collected live by default (real evidence);
    decision flags come from the provided state.
    """
    availability = (
        module_availability
        if module_availability is not None
        else collect_module_availability()
    )

    # Map spec fields to their evidence source.
    module_map = {
        "kill_switch_available": "backtest.risk",
        "execution_adapter_available": "execution.mt5_execution",
        "order_validation_available": "execution.order_validation",
        "fill_validation_available": "execution.fill_validation",
        "reconciliation_available": "execution.reconciliation",
        "broker_validation_available": "execution.broker_validation",
        "monitoring_available": "execution.monitoring",
        "audit_log_available": "execution.audit_log",
    }

    state_values = {
        field_name: getattr(state, field_name)
        for field_name in (
            "backtest_done",
            "oos_done",
            "cost_stress_done",
            "risk_engine_done",
            "demo_validation_done",
            "trading_enabled",
            "ops_procedures_documented",
        )
    }

    items: list[ReadinessItem] = []

    for category, item_id, description, field in _ITEMS_SPEC:
        if field in module_map:
            satisfied = bool(
                availability.get(module_map[field], False)
            )
            evidence = (
                f"module {module_map[field]} importable"
                if satisfied
                else f"module {module_map[field]} missing"
            )
        else:
            satisfied = bool(state_values.get(field, False))
            evidence = (
                "operator flag set"
                if satisfied
                else "operator flag not set"
            )

        items.append(
            ReadinessItem(
                category=category,
                item_id=item_id,
                description=description,
                satisfied=satisfied,
                evidence=evidence,
            )
        )

    return ReadinessReview(items=tuple(items))
