"""Versionable JSON registry; it never executes research components."""
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

class HypothesisStatus(StrEnum): DRAFT="DRAFT"; RESEARCHING="RESEARCHING"; READY_FOR_GATE="READY_FOR_GATE"; PASS="PASS"; REJECT="REJECT"; INCONCLUSIVE="INCONCLUSIVE"; DEPRECATED="DEPRECATED"
@dataclass(frozen=True,slots=True)
class EvidenceReference:
    kind:str; fingerprint:str
    def __post_init__(self):
        if not self.kind or len(self.fingerprint)!=64: raise ValueError("evidence requires kind and SHA-256 fingerprint")
@dataclass(frozen=True,slots=True)
class HypothesisRecord:
    hypothesis_id:str; definition:str; symbol:str; timeframe:str; parameters:Mapping[str,object]=field(default_factory=dict); status:HypothesisStatus=HypothesisStatus.DRAFT; parent_hypothesis_id:str|None=None; evidence:tuple[EvidenceReference,...]=()
    def __post_init__(self):
        if not self.hypothesis_id or not self.definition or not self.symbol or not self.timeframe: raise ValueError("hypothesis identity and definition are required")
        if not isinstance(self.status,HypothesisStatus): raise TypeError("status must be HypothesisStatus")
        object.__setattr__(self,"parameters",MappingProxyType(dict(self.parameters)))
    @property
    def fingerprint(self): return sha256(json.dumps({"definition":self.definition,"symbol":self.symbol,"timeframe":self.timeframe,"parameters":dict(self.parameters)},sort_keys=True,separators=(",",":")).encode()).hexdigest()
@dataclass(frozen=True,slots=True)
class StrategyRecord:
    strategy_id:str; hypothesis_id:str; implementation_fingerprint:str
    def __post_init__(self):
        if not self.strategy_id or not self.hypothesis_id or len(self.implementation_fingerprint)!=64: raise ValueError("invalid strategy record")

class StrategyRegistry:
    _TRANSITIONS={HypothesisStatus.DRAFT:{HypothesisStatus.RESEARCHING,HypothesisStatus.DEPRECATED},HypothesisStatus.RESEARCHING:{HypothesisStatus.READY_FOR_GATE,HypothesisStatus.DEPRECATED},HypothesisStatus.READY_FOR_GATE:{HypothesisStatus.PASS,HypothesisStatus.REJECT,HypothesisStatus.INCONCLUSIVE,HypothesisStatus.DEPRECATED},HypothesisStatus.INCONCLUSIVE:{HypothesisStatus.RESEARCHING,HypothesisStatus.DEPRECATED},HypothesisStatus.PASS:{HypothesisStatus.DEPRECATED},HypothesisStatus.REJECT:{HypothesisStatus.DEPRECATED},HypothesisStatus.DEPRECATED:set()}
    def __init__(self,root:Path|str="research/registry"):
        self.root=Path(root); self.path=self.root/"hypotheses.json"; self._records={}; self._load()
    def _load(self):
        if not self.path.exists(): return
        for raw in json.loads(self.path.read_text(encoding="utf-8")):
            raw["status"]=HypothesisStatus(raw["status"]); raw["evidence"]=tuple(EvidenceReference(**x) for x in raw.get("evidence",[])); self._records[raw["hypothesis_id"]]=HypothesisRecord(**raw)
    def _save(self):
        self.root.mkdir(parents=True,exist_ok=True); rows=[]
        for r in sorted(self._records.values(),key=lambda x:x.hypothesis_id): rows.append({"hypothesis_id":r.hypothesis_id,"definition":r.definition,"symbol":r.symbol,"timeframe":r.timeframe,"parameters":dict(r.parameters),"status":r.status.value,"parent_hypothesis_id":r.parent_hypothesis_id,"evidence":[asdict(x) for x in r.evidence]})
        self.path.write_text(json.dumps(rows,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    def add(self,record:HypothesisRecord):
        if record.hypothesis_id in self._records or any(x.fingerprint==record.fingerprint for x in self._records.values()): raise ValueError("duplicate hypothesis id or fingerprint")
        if record.parent_hypothesis_id and record.parent_hypothesis_id not in self._records: raise ValueError("parent hypothesis does not exist")
        self._records[record.hypothesis_id]=record; self._save(); return record
    def transition(self,hypothesis_id:str,status:HypothesisStatus):
        current=self.get(hypothesis_id)
        if status not in self._TRANSITIONS[current.status]: raise ValueError("invalid status transition")
        updated=HypothesisRecord(current.hypothesis_id,current.definition,current.symbol,current.timeframe,current.parameters,status,current.parent_hypothesis_id,current.evidence); self._records[hypothesis_id]=updated; self._save(); return updated
    def get(self,hypothesis_id):
        if hypothesis_id not in self._records: raise KeyError(hypothesis_id)
        return self._records[hypothesis_id]
    def by_status(self,status): return tuple(x for x in self._records.values() if x.status is status)
    def by_fingerprint(self,fingerprint): return next((x for x in self._records.values() if x.fingerprint==fingerprint),None)
    def lineage(self,hypothesis_id):
        out=[]; seen=set(); current=self.get(hypothesis_id)
        while current:
            if current.hypothesis_id in seen: raise ValueError("lineage cycle detected")
            seen.add(current.hypothesis_id); out.append(current); current=self._records.get(current.parent_hypothesis_id)
        return tuple(reversed(out))
