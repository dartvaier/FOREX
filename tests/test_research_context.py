from research.context import QUALITY_POLICY_VERSION,proposal_context
from research.registry import HypothesisRecord,StrategyRegistry


def test_proposal_context_is_declarative_and_includes_registry_novelty_facts(tmp_path):
    registry=StrategyRegistry(tmp_path)
    registry.add(HypothesisRecord("known","existing thesis","EURUSD","H1",{"fast_period":12,"slow_period":26}))
    context=proposal_context(registry)
    assert context["policy_version"]==QUALITY_POLICY_VERSION
    assert context["registry_hypotheses"][0]["hypothesis_id"]=="known"
    assert context["market_facts"]=={"eurusd_pip":0.00010,"eurusd_point":0.00001,"historical_gaps":"PRESERVED_NOT_FILLED","continuous_history_assumption":False}
    assert context["strategy_semantics"]["fast_crosses_above_slow"]=="ENTER_LONG"
    assert "percentage_return" in context["measurable_metrics"]["allowlist"]
    assert "order_send" not in repr(context) and "holdout data" not in repr(context)
