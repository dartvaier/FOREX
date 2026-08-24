from research.agent import *
from research.proposal import ProposalStatus
from research.registry import StrategyRegistry
from research.proposal import HypothesisProposalValidator
from research.orchestrator import ResearchOrchestrator
class Mock(LLMProvider):
 def propose(self,c): return object()
 def assess(self,f): return "interpretation only"
def test_agent_allowlist_limits_and_assessment_authority(tmp_path):
 registry=StrategyRegistry(tmp_path);agent=ResearchAgent(Mock(),registry,HypothesisProposalValidator(registry),ResearchOrchestrator(__import__('research.service',fromlist=['ResearchService']).ResearchService(registry)))
 assert agent.query_hypotheses()==() and agent.propose().status is ProposalStatus.INVALID
 try: agent.propose();assert False
 except RuntimeError: pass
def test_no_forbidden_provider_surface():
 assert all("MT5" not in name and "Backtest" not in name for name in dir(ResearchAgent))
