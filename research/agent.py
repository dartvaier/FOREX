"""Bounded LLM adapter; deliberately no execution, filesystem or broker access."""
from abc import ABC,abstractmethod
from dataclasses import dataclass,field
from enum import StrEnum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Mapping
from research.proposal import HypothesisProposal,HypothesisProposalValidator,ProposalValidationResult,ProposalStatus
from research.context import proposal_context
from research.registry import StrategyRegistry
from research.orchestrator import ResearchOrchestrator,ResearchRun

class AgentCapability(StrEnum): QUERY_HYPOTHESES="QUERY_HYPOTHESES"; SUBMIT_PROPOSAL="SUBMIT_PROPOSAL"; START_RESEARCH_RUN="START_RESEARCH_RUN"; QUERY_RESEARCH_RUN="QUERY_RESEARCH_RUN"; ANALYZE_RESULTS="ANALYZE_RESULTS"
class LLMProvider(ABC):
 @abstractmethod
 def propose(self,context:Mapping[str,object])->object: ...
 @abstractmethod
 def assess(self,facts:Mapping[str,object])->str: ...
@dataclass(frozen=True,slots=True)
class AgentLimits: max_proposals:int=1; max_retries:int=0
@dataclass(frozen=True,slots=True)
class ResearchAssessment:
 facts:Mapping[str,object]; interpretation:str
 def __post_init__(self): object.__setattr__(self,"facts",MappingProxyType(dict(self.facts)))
@dataclass(frozen=True,slots=True)
class AgentRun:
 input_fingerprint:str; output_fingerprint:str; proposal_fingerprint:str|None=None; hypothesis_id:str|None=None; research_run_fingerprint:str|None=None

class ResearchAgent:
 ALLOWLIST=frozenset(AgentCapability)
 def __init__(self,provider:LLMProvider,registry:StrategyRegistry,validator:HypothesisProposalValidator,orchestrator:ResearchOrchestrator,limits:AgentLimits=AgentLimits()): self.provider,self.registry,self.validator,self.orchestrator,self.limits,self._proposals=provider,registry,validator,orchestrator,limits,0
 def query_hypotheses(self,status=None): return tuple(self.registry._records.values() if status is None else self.registry.by_status(status))
 def propose(self):
  if self._proposals>=self.limits.max_proposals: raise RuntimeError("proposal limit reached")
  raw=self.provider.propose(proposal_context(self.registry)); self._proposals+=1
  if not isinstance(raw,HypothesisProposal): return ProposalValidationResult(ProposalStatus.INVALID,"","provider output is not a proposal")
  return self.validator.validate(raw)
 def submit(self,proposal:HypothesisProposal): return self.validator.validate(proposal)
 def start_run(self,plan): return self.orchestrator.start(plan)
 def get_run(self,plan): return self.orchestrator.resume(plan)
 def analyze(self,run:ResearchRun):
  facts={"plan_fingerprint":run.plan.fingerprint,"run_fingerprint":run.fingerprint,"stages":tuple((x.stage.value,x.success,x.evidence_fingerprint) for x in run.stages),"blocked":run.blocked}; text=self.provider.assess(facts); assessment=ResearchAssessment(facts,str(text)); digest=sha256(json.dumps(facts,sort_keys=True,default=str).encode()).hexdigest(); return assessment,AgentRun(digest,sha256((digest+assessment.interpretation).encode()).hexdigest(),research_run_fingerprint=run.fingerprint)
