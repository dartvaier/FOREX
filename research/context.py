"""Declarative, bounded context for a single research proposal."""
from research.registry import StrategyRegistry
from research.semantics import EMA_CROSSOVER_SEMANTICS, EMA_CROSSOVER_SEMANTICS_VERSION, MEASURABLE_METRICS, METRIC_ALLOWLIST_VERSION


QUALITY_POLICY_VERSION = "F6.8-RESEARCH-QUALITY-V1"


def proposal_context(registry: StrategyRegistry) -> dict:
    """Return registry facts and quality constraints, never capabilities or code."""
    records = [
        {
            "hypothesis_id": record.hypothesis_id,
            "definition": record.definition,
            "symbol": record.symbol,
            "timeframe": record.timeframe,
            "parameters": dict(record.parameters),
            "fingerprint": record.fingerprint,
        }
        for record in sorted(registry._records.values(), key=lambda item: item.hypothesis_id)
    ]
    return {
        "policy_version": QUALITY_POLICY_VERSION,
        "task": "Propose exactly one novel, declarative research hypothesis.",
        "allowed_strategy": {"strategy": "EMA_CROSSOVER", "symbol": "EURUSD", "timeframe": "H1"},
        "catalog_constraints": {"fast_period": "fixed positive integer per StrategySpec/Experiment", "slow_period": "fixed positive integer per StrategySpec/Experiment", "runtime_period_adjustment": "UNSUPPORTED"},
        "strategy_semantics": {"version": EMA_CROSSOVER_SEMANTICS_VERSION, **EMA_CROSSOVER_SEMANTICS},
        "measurable_metrics": {"version": METRIC_ALLOWLIST_VERSION, "allowlist": MEASURABLE_METRICS},
        "falsification_semantics": {
            "meaning": "A criterion is a failure predicate: when metric operator threshold evaluates true, the hypothesis is falsified.",
            "examples": (
                {"metric": "sharpe_ratio", "operator": "LTE", "threshold": 1.2, "scope": "EXPERIMENT"},
                {"metric": "maximum_drawdown_percent", "operator": "GT", "threshold": 20.0, "scope": "GATE"},
            ),
        },
        "market_facts": {
            "eurusd_pip": 0.00010,
            "eurusd_point": 0.00001,
            "historical_gaps": "PRESERVED_NOT_FILLED",
            "continuous_history_assumption": False,
        },
        "quality_requirements": {
            "thesis": "State a specific, testable claim; do not present a generic strategy description.",
            "expected_mechanism": "State a plausible market mechanism, not merely that a crossover occurs.",
            "parameter_rationale": "Justify fast and slow periods in relation to the stated mechanism.",
            "falsification": "Use typed failure predicates: choose the operator so a true comparison falsifies the thesis (for example sharpe_ratio LTE 1.2, not GT 1.2 for a Sharpe-above-1.2 thesis).",
            "executable_semantics": "Use only the registered directional EMA crossover semantics and measurable_metrics allowlist.",
            "novelty": "Do not restate or make a cosmetic variation of a Registry hypothesis.",
        },
        "prohibitions": (
            "Do not generate executable code.",
            "Do not claim unprovided external facts or results.",
            "Do not assume the historical series is continuous or that gaps were filled.",
            "Do not use unregistered indicators, filters, entries or conditions; only the declared EMA crossover may define the hypothesis.",
            "Do not use adaptive, dynamic, volatility-adjusted or regime-dependent EMA periods; both periods are fixed per StrategySpec and Experiment.",
            "Do not request tools, filesystem, shell, MT5, research runs, gates, or holdout access.",
        ),
        "registry_hypotheses": records,
    }
