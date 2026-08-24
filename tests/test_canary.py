from research.canary import ProviderCanaryRunner
from research.registry import StrategyRegistry
from research.proposal import HypothesisProposalValidator,HypothesisProposal
from research.service import StrategySpec,RegisteredStrategy
class Mock:
 def propose(self,c):return HypothesisProposal("title","sufficient thesis","sufficient mechanism",StrategySpec(RegisteredStrategy.EMA_CROSSOVER,"EURUSD","H1",{"fast_period":2,"slow_period":3}),("falsify",))
 def assess(self,f):return "text only"
def test_proposal_and_assessment_canaries_preserve_boundaries(tmp_path):
 r=StrategyRegistry(tmp_path/"registry");c=ProviderCanaryRunner(Mock(),r,HypothesisProposalValidator(r),tmp_path/"out")
 assert c.proposal_only("p").passed and c.assessment_only("a",{"return":1,"gate_status":"PASS"}).passed
