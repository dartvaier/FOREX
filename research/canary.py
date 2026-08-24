"""Manual, opt-in real-provider canaries. Never called by CI."""
from dataclasses import asdict,dataclass
from hashlib import sha256
import json
from pathlib import Path
from research.agent import ResearchAssessment
from research.proposal import HypothesisProposalValidator
from research.registry import StrategyRegistry

@dataclass(frozen=True,slots=True)
class CanaryResult: canary_id:str; kind:str; passed:bool; fingerprint:str; summary:dict
class ProviderCanaryRunner:
 def __init__(self,provider,registry:StrategyRegistry,validator:HypothesisProposalValidator,output_root:Path|str="outputs/agent_canary"):
  self.provider,self.registry,self.validator,self.root=provider,registry,validator,Path(output_root)
 def proposal_only(self,canary_id:str):
  self._id(canary_id); context={"hypotheses":[(x.hypothesis_id,x.fingerprint) for x in self.registry._records.values()],"allowed_strategy":"EMA_CROSSOVER EURUSD H1"}
  proposal=self.provider.propose(context); validation=self.validator.validate(proposal)
  summary={"schema_valid":validation.fingerprint==proposal.fingerprint,"decision":validation.status.value,"provider":getattr(self.provider,"telemetry",None).provider if getattr(self.provider,"telemetry",None) else "mock"}
  return self._write(canary_id,"proposal_only",summary,{"proposal":proposal,"validation":validation})
 def assessment_only(self,canary_id:str,facts:dict):
  self._id(canary_id); interpretation=self.provider.assess(facts); assessment=ResearchAssessment(facts,interpretation); preserved=dict(assessment.facts)==facts
  return self._write(canary_id,"assessment_only",{"factual_preservation":preserved,"gate_status":facts.get("gate_status")},{"assessment":assessment})
 def _write(self,canary_id,kind,summary,items):
  payload={"canary_id":canary_id,"kind":kind,"summary":summary,"fingerprints":{k:sha256(repr(v).encode()).hexdigest() for k,v in items.items()}}
  path=self.root/canary_id;path.mkdir(parents=True,exist_ok=True);(path/"summary.json").write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
  return CanaryResult(canary_id,kind,all(bool(x) for x in summary.values() if isinstance(x,bool)),sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest(),summary)
 @staticmethod
 def _id(value):
  if not value or any(x in value for x in "\\/"):raise ValueError("invalid canary id")
