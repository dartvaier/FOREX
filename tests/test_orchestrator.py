import pytest
from research.orchestrator import *
from research.registry import StrategyRegistry
from research.service import ResearchService
def plan(): return ResearchPlan(*[str(i)*64 for i in range(1,7)])
def test_protocol_order_resume_fingerprint_and_idempotence(tmp_path):
 o=ResearchOrchestrator(ResearchService(StrategyRegistry(tmp_path))); r=o.start(plan()); assert r==o.resume(plan())
 with pytest.raises(ValueError): o.record(r,ResearchStage.EXPERIMENT,plan().experiment_fingerprint,True)
 for stage,field in zip(ResearchOrchestrator.ORDER,["hypothesis_fingerprint","hypothesis_fingerprint","experiment_fingerprint","sensitivity_fingerprint","walk_forward_fingerprint","gate_fingerprint"]): r=o.record(r,stage,getattr(plan(),field),True)
 assert len(r.stages)==6 and r==o.resume(plan())
def test_failure_blocks_and_mismatch_rejected(tmp_path):
 o=ResearchOrchestrator(ResearchService(StrategyRegistry(tmp_path)));r=o.start(plan())
 with pytest.raises(ValueError):o.record(r,ResearchStage.PROPOSAL_VALIDATION,"x",True)
 r=o.record(r,ResearchStage.PROPOSAL_VALIDATION,plan().hypothesis_fingerprint,False)
 with pytest.raises(RuntimeError):o.record(r,ResearchStage.REGISTRATION,plan().hypothesis_fingerprint,True)
