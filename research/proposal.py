"""Pure declarative hypothesis-proposal validation; no execution imports."""
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Mapping
from research.registry import StrategyRegistry
from research.service import StrategySpec

class ProposalStatus(StrEnum): ACCEPTED="ACCEPTED"; DUPLICATE="DUPLICATE"; INVALID="INVALID"; UNSUPPORTED_STRATEGY="UNSUPPORTED_STRATEGY"; INSUFFICIENT_RATIONALE="INSUFFICIENT_RATIONALE"
@dataclass(frozen=True,slots=True)
class HypothesisProposal:
    title:str; thesis:str; expected_mechanism:str; strategy:object; falsification_criteria:tuple[str,...]; assumptions:tuple[str,...]=(); tags:tuple[str,...]=(); parent_hypothesis_id:str|None=None; provenance:Mapping[str,object]=field(default_factory=dict)
    def __post_init__(self):
        if not isinstance(self.falsification_criteria,tuple) or not isinstance(self.assumptions,tuple) or not isinstance(self.tags,tuple): raise TypeError("list fields must be tuples")
        object.__setattr__(self,"provenance",MappingProxyType(dict(self.provenance)))
    @property
    def fingerprint(self):
        s=self.strategy
        strategy={} if not isinstance(s,StrategySpec) else {"strategy":s.strategy.value,"symbol":s.symbol,"timeframe":s.timeframe,"parameters":dict(s.parameters)}
        material={"title":self.title,"thesis":self.thesis,"mechanism":self.expected_mechanism,"strategy":strategy,"falsification":self.falsification_criteria,"assumptions":self.assumptions}
        return sha256(json.dumps(material,sort_keys=True,separators=(",",":")).encode()).hexdigest()
@dataclass(frozen=True,slots=True)
class ProposalValidationResult:
    status:ProposalStatus; fingerprint:str; message:str=""

class HypothesisProposalValidator:
    def __init__(self,registry:StrategyRegistry): self.registry=registry
    def validate(self,proposal:HypothesisProposal):
        if not isinstance(proposal,HypothesisProposal): return ProposalValidationResult(ProposalStatus.INVALID,"","proposal schema is invalid")
        if not isinstance(proposal.strategy,StrategySpec): return ProposalValidationResult(ProposalStatus.UNSUPPORTED_STRATEGY,proposal.fingerprint,"strategy is not registered")
        if not all(isinstance(x,str) and len(x.strip())>=10 for x in (proposal.thesis,proposal.expected_mechanism)) or not proposal.falsification_criteria: return ProposalValidationResult(ProposalStatus.INSUFFICIENT_RATIONALE,proposal.fingerprint,"thesis, mechanism and falsification are required")
        if not proposal.title.strip(): return ProposalValidationResult(ProposalStatus.INVALID,proposal.fingerprint,"title is required")
        if proposal.parent_hypothesis_id:
            try: self.registry.get(proposal.parent_hypothesis_id)
            except KeyError: return ProposalValidationResult(ProposalStatus.INVALID,proposal.fingerprint,"parent hypothesis does not exist")
        for record in self.registry._records.values():
            if record.definition==proposal.thesis and record.symbol==proposal.strategy.symbol and record.timeframe==proposal.strategy.timeframe and dict(record.parameters)==dict(proposal.strategy.parameters): return ProposalValidationResult(ProposalStatus.DUPLICATE,proposal.fingerprint,"materially identical hypothesis exists")
        return ProposalValidationResult(ProposalStatus.ACCEPTED,proposal.fingerprint)
