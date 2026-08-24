"""Declarative, bounded context for a single research proposal."""
from research.registry import StrategyRegistry


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
        "quality_requirements": {
            "thesis": "State a specific, testable claim; do not present a generic strategy description.",
            "expected_mechanism": "State a plausible market mechanism, not merely that a crossover occurs.",
            "parameter_rationale": "Justify fast and slow periods in relation to the stated mechanism.",
            "falsification": "Give at least one pre-specified quantitative threshold and evaluation horizon; state a valid unit or use a dimensionless ratio.",
            "novelty": "Do not restate or make a cosmetic variation of a Registry hypothesis.",
        },
        "prohibitions": (
            "Do not generate executable code.",
            "Do not claim unprovided external facts or results.",
            "Do not use unregistered indicators, filters, entries or conditions; only the declared EMA crossover may define the hypothesis.",
            "Do not request tools, filesystem, shell, MT5, research runs, gates, or holdout access.",
        ),
        "registry_hypotheses": records,
    }
