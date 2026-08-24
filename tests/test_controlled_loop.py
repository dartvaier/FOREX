from research.controlled_loop import *
from research.agent_eval import *
from research.agent import *
from research.registry import StrategyRegistry
from research.proposal import HypothesisProposalValidator
from research.orchestrator import ResearchOrchestrator
from research.service import ResearchService
class Mock(LLMProvider):
 def propose(self,c):return object()
 def assess(self,f):return "x"
def safety():return AgentEvaluator().run(AgentEvalSuite((AgentEvalCase("x","code",GuardrailSeverity.CRITICAL),)))
def test_one_hypothesis_stop_and_resume(tmp_path):
 r=StrategyRegistry(tmp_path);a=ResearchAgent(Mock(),r,HypothesisProposalValidator(r),ResearchOrchestrator(ResearchService(r)));loop=ControlledResearchLoop(a,safety());first=loop.run(ResearchLoopSpec());assert first.reason is ResearchLoopStopReason.INVALID_PROPOSAL and first==loop.run(ResearchLoopSpec())
