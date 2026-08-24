from research.canary import ProviderCanaryRunner
from research.ollama_provider import OllamaErrorCode,OllamaProviderError
from research.registry import StrategyRegistry
from research.proposal import HypothesisProposalValidator,HypothesisProposal
from research.service import StrategySpec,RegisteredStrategy
import json
class Mock:
 def propose(self,c):return HypothesisProposal("title","sufficient thesis","sufficient mechanism",StrategySpec(RegisteredStrategy.EMA_CROSSOVER,"EURUSD","H1",{"fast_period":2,"slow_period":3}),("falsify",))
 def assess(self,f):return "text only"
class FailedProvider:
 def propose(self,c):raise OllamaProviderError(OllamaErrorCode.TIMEOUT,"deadline")
 def assess(self,f):raise OllamaProviderError(OllamaErrorCode.TIMEOUT,"deadline")
def test_proposal_and_assessment_canaries_preserve_boundaries(tmp_path):
 r=StrategyRegistry(tmp_path/"registry");c=ProviderCanaryRunner(Mock(),r,HypothesisProposalValidator(r),tmp_path/"out")
 assert c.proposal_only("p").passed and c.assessment_only("a",{"return":1,"gate_status":"PASS"}).passed
 assert json.loads((tmp_path/"out"/"p"/"proposal.json").read_text())["strategy"]["strategy"]=="EMA_CROSSOVER"
 assert json.loads((tmp_path/"out"/"p"/"validation.json").read_text())["status"]=="ACCEPTED"
def test_provider_failure_is_audited_and_fails_closed(tmp_path):
 r=StrategyRegistry(tmp_path/"registry");result=ProviderCanaryRunner(FailedProvider(),r,HypothesisProposalValidator(r),tmp_path/"out").proposal_only("failed")
 assert not result.passed and json.loads((tmp_path/"out"/"failed"/"error.json").read_text())["code"]=="TIMEOUT"
