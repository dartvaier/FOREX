from research.context import QUALITY_POLICY_VERSION,proposal_context
from research.registry import HypothesisRecord,StrategyRegistry


def test_proposal_context_is_declarative_and_includes_registry_novelty_facts(tmp_path):
    registry=StrategyRegistry(tmp_path)
    registry.add(HypothesisRecord("known","existing thesis","EURUSD","H1",{"fast_period":12,"slow_period":26}))
    context=proposal_context(registry)
    assert context["policy_version"]==QUALITY_POLICY_VERSION
    assert context["registry_hypotheses"][0]["hypothesis_id"]=="known"
    assert "order_send" not in repr(context) and "holdout data" not in repr(context)
