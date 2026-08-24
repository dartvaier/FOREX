"""Fail-closed coordinator for the existing F5/F6 research protocol."""
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from research.service import ResearchService

class ResearchStage(StrEnum): PROPOSAL_VALIDATION="PROPOSAL_VALIDATION"; REGISTRATION="REGISTRATION"; EXPERIMENT="EXPERIMENT"; SENSITIVITY="SENSITIVITY"; WALK_FORWARD="WALK_FORWARD"; STRATEGY_GATE="STRATEGY_GATE"
@dataclass(frozen=True,slots=True)
class ResearchPlan:
    hypothesis_fingerprint:str; strategy_fingerprint:str; experiment_fingerprint:str; sensitivity_fingerprint:str; walk_forward_fingerprint:str; gate_fingerprint:str
    @property
    def fingerprint(self): return sha256(json.dumps({"hypothesis":self.hypothesis_fingerprint,"strategy":self.strategy_fingerprint,"experiment":self.experiment_fingerprint,"sensitivity":self.sensitivity_fingerprint,"walk_forward":self.walk_forward_fingerprint,"gate":self.gate_fingerprint},sort_keys=True).encode()).hexdigest()
@dataclass(frozen=True,slots=True)
class ResearchStageResult:
    stage:ResearchStage; evidence_fingerprint:str; success:bool; message:str=""
@dataclass(frozen=True,slots=True)
class ResearchRun:
    plan:ResearchPlan; stages:tuple[ResearchStageResult,...]=(); blocked:bool=False
    @property
    def fingerprint(self): return sha256((self.plan.fingerprint+"|"+"|".join(x.evidence_fingerprint for x in self.stages)).encode()).hexdigest()

class ResearchOrchestrator:
    ORDER=tuple(ResearchStage)
    def __init__(self,service:ResearchService): self.service=service; self._runs={}
    def start(self,plan:ResearchPlan):
        if not isinstance(plan,ResearchPlan): raise TypeError("plan must be ResearchPlan")
        return self._runs.setdefault(plan.fingerprint,ResearchRun(plan))
    def resume(self,plan:ResearchPlan): return self.start(plan)
    def record(self,run:ResearchRun,stage:ResearchStage,evidence_fingerprint:str,success:bool,message:str=""):
        if run.blocked: raise RuntimeError("run is blocked")
        expected=self.ORDER[len(run.stages)] if len(run.stages)<len(self.ORDER) else None
        if stage is not expected: raise ValueError("stage is out of order or already completed")
        expected_fp=getattr(run.plan,{ResearchStage.PROPOSAL_VALIDATION:"hypothesis_fingerprint",ResearchStage.REGISTRATION:"hypothesis_fingerprint",ResearchStage.EXPERIMENT:"experiment_fingerprint",ResearchStage.SENSITIVITY:"sensitivity_fingerprint",ResearchStage.WALK_FORWARD:"walk_forward_fingerprint",ResearchStage.STRATEGY_GATE:"gate_fingerprint"}[stage])
        if evidence_fingerprint!=expected_fp: raise ValueError("evidence fingerprint does not match frozen plan")
        result=ResearchStageResult(stage,evidence_fingerprint,success,message); updated=ResearchRun(run.plan,run.stages+(result,),not success); self._runs[run.plan.fingerprint]=updated; return updated
