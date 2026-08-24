import pytest
from research.proposal import *
from research.registry import HypothesisRecord,StrategyRegistry
from research.service import RegisteredStrategy,StrategySpec
from research.falsification import FalsificationCriterion,FalsificationMetric,FalsificationOperator,FalsificationScope
def strategy(): return StrategySpec(RegisteredStrategy.EMA_CROSSOVER,"EURUSD","H1",{"fast_period":2,"slow_period":3})
def proposal(**kw):
    values={"title":"EMA thesis","thesis":"trend persists","expected_mechanism":"persistent repricing","strategy":strategy(),"falsification_criteria":(FalsificationCriterion(FalsificationMetric.PERCENTAGE_RETURN,FalsificationOperator.LT,-2.0,FalsificationScope.EXPERIMENT),),"parameter_rationale":("Fast and slow periods separate short and medium horizons",),"provenance":{"source":"paper"}}; values.update(kw); return HypothesisProposal(**values)
def test_acceptance_fingerprint_metadata_and_immutability(tmp_path):
 v=HypothesisProposalValidator(StrategyRegistry(tmp_path)); a=proposal(); b=proposal(provenance={"source":"other"}); assert v.validate(a).status is ProposalStatus.ACCEPTED and a.fingerprint==b.fingerprint
 with pytest.raises(TypeError): a.provenance["x"]=1
def test_duplicate_rationale_unsupported_and_lineage(tmp_path):
 r=StrategyRegistry(tmp_path);r.add(HypothesisRecord("p","trend persists","EURUSD","H1",{"fast_period":2,"slow_period":3}));v=HypothesisProposalValidator(r)
 assert v.validate(proposal()).status is ProposalStatus.DUPLICATE
 assert v.validate(proposal(thesis="bad")).status is ProposalStatus.INSUFFICIENT_RATIONALE
 assert v.validate(proposal(parameter_rationale=())).status is ProposalStatus.INSUFFICIENT_RATIONALE
 assert v.validate(proposal(expected_mechanism="ATR confirms volatility conditions")).status is ProposalStatus.UNSUPPORTED_STRATEGY
 assert v.validate(proposal(thesis="EMA crossover predicts a reversal")).status is ProposalStatus.SEMANTIC_MISMATCH
 assert v.validate(proposal(falsification_criteria=(FalsificationCriterion(FalsificationMetric.MAXIMUM_DRAWDOWN_PERCENT,FalsificationOperator.GT,20,FalsificationScope.EXPERIMENT),))).status is ProposalStatus.DUPLICATE
 assert v.validate(HypothesisProposal("x","enough thesis","enough mechanism",object(),(FalsificationCriterion(FalsificationMetric.PERCENTAGE_RETURN,FalsificationOperator.LT,-1,FalsificationScope.EXPERIMENT),))).status is ProposalStatus.UNSUPPORTED_STRATEGY
 assert v.validate(proposal(parent_hypothesis_id="missing")).status is ProposalStatus.INVALID
def test_typed_falsification_rejects_unknown_operator_threshold_and_scope(tmp_path):
 with pytest.raises(ValueError): FalsificationMetric("p_value")
 with pytest.raises(ValueError): FalsificationOperator("EQ")
 with pytest.raises(ValueError): FalsificationCriterion(FalsificationMetric.SHARPE_RATIO,FalsificationOperator.GT,float("nan"),FalsificationScope.EXPERIMENT)
 with pytest.raises(ValueError): FalsificationCriterion(FalsificationMetric.SHARPE_RATIO,FalsificationOperator.GT,1.0,FalsificationScope.WALK_FORWARD)
 assert HypothesisProposalValidator(StrategyRegistry(tmp_path)).validate(proposal()).status is ProposalStatus.ACCEPTED
