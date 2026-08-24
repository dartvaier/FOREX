"""Pure declarative hypothesis-proposal validation; no execution imports."""
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Mapping
from research.registry import StrategyRegistry
from research.service import StrategySpec
from research.semantics import METRIC_TERMS

class ProposalStatus(StrEnum): ACCEPTED="ACCEPTED"; DUPLICATE="DUPLICATE"; INVALID="INVALID"; UNSUPPORTED_STRATEGY="UNSUPPORTED_STRATEGY"; UNSUPPORTED_METRIC="UNSUPPORTED_METRIC"; SEMANTIC_MISMATCH="SEMANTIC_MISMATCH"; INSUFFICIENT_RATIONALE="INSUFFICIENT_RATIONALE"
@dataclass(frozen=True,slots=True)
class HypothesisProposal:
    title:str; thesis:str; expected_mechanism:str; strategy:object; falsification_criteria:tuple[str,...]; parameter_rationale:tuple[str,...]=(); assumptions:tuple[str,...]=(); tags:tuple[str,...]=(); parent_hypothesis_id:str|None=None; provenance:Mapping[str,object]=field(default_factory=dict)
    def __post_init__(self):
        if not all(isinstance(value,tuple) for value in (self.falsification_criteria,self.parameter_rationale,self.assumptions,self.tags)): raise TypeError("list fields must be tuples")
        object.__setattr__(self,"provenance",MappingProxyType(dict(self.provenance)))
    @property
    def fingerprint(self):
        s=self.strategy
        strategy={} if not isinstance(s,StrategySpec) else {"strategy":s.strategy.value,"symbol":s.symbol,"timeframe":s.timeframe,"parameters":dict(s.parameters)}
        material={"title":self.title,"thesis":self.thesis,"mechanism":self.expected_mechanism,"strategy":strategy,"falsification":self.falsification_criteria,"parameter_rationale":self.parameter_rationale,"assumptions":self.assumptions}
        return sha256(json.dumps(material,sort_keys=True,separators=(",",":")).encode()).hexdigest()
@dataclass(frozen=True,slots=True)
class ProposalValidationResult:
    status:ProposalStatus; fingerprint:str; message:str=""

class HypothesisProposalValidator:
    _UNREGISTERED_INDICATORS=("atr","rsi","macd","bollinger")
    _COUNTERTREND_TERMS=("countertrend","counter-trend","reversal","mean reversion","mean-reversion","opposite direction","fade")
    _UNSUPPORTED_CRITERION_TERMS=("p-value","statistical significance","statistically significant","event study","correlation","probability","pips","reversal")
    def __init__(self,registry:StrategyRegistry): self.registry=registry
    def validate(self,proposal:HypothesisProposal):
        if not isinstance(proposal,HypothesisProposal): return ProposalValidationResult(ProposalStatus.INVALID,"","proposal schema is invalid")
        if not isinstance(proposal.strategy,StrategySpec): return ProposalValidationResult(ProposalStatus.UNSUPPORTED_STRATEGY,proposal.fingerprint,"strategy is not registered")
        proposal_text=" ".join((proposal.thesis,proposal.expected_mechanism,*proposal.assumptions,*proposal.tags)).lower()
        if any(re.search(rf"\b{indicator}\b",proposal_text) for indicator in self._UNREGISTERED_INDICATORS): return ProposalValidationResult(ProposalStatus.UNSUPPORTED_STRATEGY,proposal.fingerprint,"proposal depends on an unregistered indicator")
        if any(term in proposal_text for term in self._COUNTERTREND_TERMS): return ProposalValidationResult(ProposalStatus.SEMANTIC_MISMATCH,proposal.fingerprint,"proposal conflicts with directional trend-following EMA semantics")
        criteria=" ".join(x.lower() for x in proposal.falsification_criteria if isinstance(x,str))
        if any(term in criteria for term in self._UNSUPPORTED_CRITERION_TERMS): return ProposalValidationResult(ProposalStatus.UNSUPPORTED_METRIC,proposal.fingerprint,"falsification depends on an unsupported metric or event study")
        if not all(any(metric in criterion.lower() for metric in METRIC_TERMS) for criterion in proposal.falsification_criteria if isinstance(criterion,str)): return ProposalValidationResult(ProposalStatus.UNSUPPORTED_METRIC,proposal.fingerprint,"falsification must use only measurable pipeline metrics")
        quantitative_falsification=any(any(char.isdigit() for char in criterion) for criterion in proposal.falsification_criteria if isinstance(criterion,str))
        rationale_valid=bool(proposal.parameter_rationale) and all(isinstance(x,str) and len(x.strip())>=15 for x in proposal.parameter_rationale)
        if not all(isinstance(x,str) and len(x.strip())>=10 for x in (proposal.thesis,proposal.expected_mechanism)) or not quantitative_falsification or not rationale_valid: return ProposalValidationResult(ProposalStatus.INSUFFICIENT_RATIONALE,proposal.fingerprint,"thesis, mechanism, parameter rationale and quantitative falsification are required")
        if not proposal.title.strip(): return ProposalValidationResult(ProposalStatus.INVALID,proposal.fingerprint,"title is required")
        if proposal.parent_hypothesis_id:
            try: self.registry.get(proposal.parent_hypothesis_id)
            except KeyError: return ProposalValidationResult(ProposalStatus.INVALID,proposal.fingerprint,"parent hypothesis does not exist")
        for record in self.registry._records.values():
            if record.definition==proposal.thesis and record.symbol==proposal.strategy.symbol and record.timeframe==proposal.strategy.timeframe and dict(record.parameters)==dict(proposal.strategy.parameters): return ProposalValidationResult(ProposalStatus.DUPLICATE,proposal.fingerprint,"materially identical hypothesis exists")
        return ProposalValidationResult(ProposalStatus.ACCEPTED,proposal.fingerprint)
