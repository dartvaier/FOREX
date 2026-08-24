from hashlib import sha256
import pytest
from research.registry import *
def rec(i,**kw): return HypothesisRecord(i,"ema","EURUSD","H1",kw.pop("parameters",{"fast":2,"slow":3}),**kw)
def test_registry_persistence_fingerprint_and_lineage(tmp_path):
 r=StrategyRegistry(tmp_path); parent=r.add(rec("a")); child=r.add(rec("b",parameters={"fast":3,"slow":5},parent_hypothesis_id="a")); assert r.lineage("b")== (parent,child) and StrategyRegistry(tmp_path).by_fingerprint(parent.fingerprint)==parent
def test_duplicates_states_immutability_and_evidence(tmp_path):
 r=StrategyRegistry(tmp_path); a=r.add(rec("a",evidence=(EvidenceReference("experiment",sha256(b"x").hexdigest()),)))
 with pytest.raises(ValueError): r.add(rec("b"))
 with pytest.raises(TypeError): a.parameters["fast"]=9
 assert r.transition("a",HypothesisStatus.RESEARCHING).status is HypothesisStatus.RESEARCHING
 with pytest.raises(ValueError): r.transition("a",HypothesisStatus.PASS)
