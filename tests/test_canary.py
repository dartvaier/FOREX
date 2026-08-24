from research.canary import ProviderCanaryRunner
from research.ollama_provider import OllamaErrorCode,OllamaProviderError
from research.registry import StrategyRegistry
from research.proposal import HypothesisProposalValidator,HypothesisProposal
from research.service import StrategySpec,RegisteredStrategy
import json
class Mock:
 def propose(self,c):return HypothesisProposal("title","sufficient thesis","sufficient mechanism",StrategySpec(RegisteredStrategy.EMA_CROSSOVER,"EURUSD","H1",{"fast_period":2,"slow_period":3}),("net return below 0.0 over six months",),("Periods separate short and medium trend horizons",))
 def assess(self,f):return "text only"
class FailedProvider:
 def propose(self,c):raise OllamaProviderError(OllamaErrorCode.TIMEOUT,"deadline")
 def assess(self,f):raise OllamaProviderError(OllamaErrorCode.TIMEOUT,"deadline")
class MutatingProvider:
 def propose(self,c):raise AssertionError("not used")
 def assess(self,f):f["gate_status"]="REJECT";return "interpretation only"
def test_proposal_and_assessment_canaries_preserve_boundaries(tmp_path):
 r=StrategyRegistry(tmp_path/"registry");c=ProviderCanaryRunner(Mock(),r,HypothesisProposalValidator(r),tmp_path/"out")
 assert c.proposal_only("p").passed and c.assessment_only("a",{"return":1,"gate_status":"PASS"}).passed
 assert json.loads((tmp_path/"out"/"p"/"proposal.json").read_text())["strategy"]["strategy"]=="EMA_CROSSOVER"
 assert json.loads((tmp_path/"out"/"p"/"validation.json").read_text())["status"]=="ACCEPTED"
 assert json.loads((tmp_path/"out"/"p"/"human_review.json").read_text())["research_authorization"]=="NOT_AUTHORIZED"
def test_provider_failure_is_audited_and_fails_closed(tmp_path):
 r=StrategyRegistry(tmp_path/"registry");result=ProviderCanaryRunner(FailedProvider(),r,HypothesisProposalValidator(r),tmp_path/"out").proposal_only("failed")
 assert not result.passed and json.loads((tmp_path/"out"/"failed"/"error.json").read_text())["code"]=="TIMEOUT"
def test_assessment_rejects_mutated_facts_and_retains_original_snapshot(tmp_path):
 r=StrategyRegistry(tmp_path/"registry");facts={"gate_status":"PASS","metrics":{"sharpe":1.25}};result=ProviderCanaryRunner(MutatingProvider(),r,HypothesisProposalValidator(r),tmp_path/"out").assessment_only("mutated",facts)
 assert not result.passed and json.loads((tmp_path/"out"/"mutated"/"facts.json").read_text())["gate_status"]=="PASS"
