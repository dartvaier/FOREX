import pytest
from research.proposal import *
from research.registry import HypothesisRecord,StrategyRegistry
from research.service import RegisteredStrategy,StrategySpec
def strategy(): return StrategySpec(RegisteredStrategy.EMA_CROSSOVER,"EURUSD","H1",{"fast_period":2,"slow_period":3})
def proposal(**kw):
    values={"title":"EMA thesis","thesis":"trend persists","expected_mechanism":"persistent repricing","strategy":strategy(),"falsification_criteria":("return below zero",),"provenance":{"source":"paper"}}; values.update(kw); return HypothesisProposal(**values)
def test_acceptance_fingerprint_metadata_and_immutability(tmp_path):
 v=HypothesisProposalValidator(StrategyRegistry(tmp_path)); a=proposal(); b=proposal(provenance={"source":"other"}); assert v.validate(a).status is ProposalStatus.ACCEPTED and a.fingerprint==b.fingerprint
 with pytest.raises(TypeError): a.provenance["x"]=1
def test_duplicate_rationale_unsupported_and_lineage(tmp_path):
 r=StrategyRegistry(tmp_path);r.add(HypothesisRecord("p","trend persists","EURUSD","H1",{"fast_period":2,"slow_period":3}));v=HypothesisProposalValidator(r)
 assert v.validate(proposal()).status is ProposalStatus.DUPLICATE
 assert v.validate(proposal(thesis="bad")).status is ProposalStatus.INSUFFICIENT_RATIONALE
 assert v.validate(HypothesisProposal("x","enough thesis","enough mechanism",object(),("fail",))).status is ProposalStatus.UNSUPPORTED_STRATEGY
 assert v.validate(proposal(parent_hypothesis_id="missing")).status is ProposalStatus.INVALID
