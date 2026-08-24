"""One-hypothesis offline research loop with mandatory stop."""
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from research.agent import ResearchAgent
from research.agent_eval import AgentSafetyReport
from research.proposal import ProposalStatus

class ResearchLoopStatus(StrEnum): STOPPED="STOPPED"; BLOCKED="BLOCKED"; FAILED="FAILED"
class ResearchLoopStopReason(StrEnum): ONE_HYPOTHESIS_COMPLETE="ONE_HYPOTHESIS_COMPLETE"; GUARDRAIL_BLOCK="GUARDRAIL_BLOCK"; INVALID_PROPOSAL="INVALID_PROPOSAL"; DUPLICATE="DUPLICATE"; BUDGET_EXHAUSTED="BUDGET_EXHAUSTED"; INTERMEDIATE_FAILURE="INTERMEDIATE_FAILURE"
@dataclass(frozen=True,slots=True)
class ResearchLoopSpec:
    max_hypotheses:int=1; max_proposals:int=1; max_retries:int=0
    def __post_init__(self):
        if (self.max_hypotheses,self.max_proposals,self.max_retries)!=(1,1,0): raise ValueError("F6.6 permits exactly one hypothesis, proposal and no retries")
    @property
    def fingerprint(self): return sha256(json.dumps((self.max_hypotheses,self.max_proposals,self.max_retries)).encode()).hexdigest()
@dataclass(frozen=True,slots=True)
class ResearchLoopRun: spec:ResearchLoopSpec; attempts:int=0; stopped:bool=False
@dataclass(frozen=True,slots=True)
class ResearchLoopResult: run:ResearchLoopRun; status:ResearchLoopStatus; reason:ResearchLoopStopReason; references:dict[str,str]
class ControlledResearchLoop:
 def __init__(self,agent:ResearchAgent,safety:AgentSafetyReport): self.agent,self.safety,self._cache=agent,safety,{}
 def run(self,spec:ResearchLoopSpec):
  if spec.fingerprint in self._cache:return self._cache[spec.fingerprint]
  run=ResearchLoopRun(spec)
  if not self.safety.passed:
   result=ResearchLoopResult(run,ResearchLoopStatus.BLOCKED,ResearchLoopStopReason.GUARDRAIL_BLOCK,{})
  else:
   try: validation=self.agent.propose();run=ResearchLoopRun(spec,1,True)
   except RuntimeError: result=ResearchLoopResult(run,ResearchLoopStatus.STOPPED,ResearchLoopStopReason.BUDGET_EXHAUSTED,{})
   else:
    reason={ProposalStatus.DUPLICATE:ResearchLoopStopReason.DUPLICATE}.get(validation.status,ResearchLoopStopReason.INVALID_PROPOSAL)
    if validation.status is ProposalStatus.ACCEPTED: reason=ResearchLoopStopReason.ONE_HYPOTHESIS_COMPLETE
    result=ResearchLoopResult(run,ResearchLoopStatus.STOPPED,reason,{"proposal_fingerprint":validation.fingerprint})
  self._cache[spec.fingerprint]=result;return result
