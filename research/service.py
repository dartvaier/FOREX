"""Deterministic local tool layer over F5; no LLM, MT5 or broker capability."""
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping
import pandas as pd
from experiments.framework import ExperimentRunner, ExperimentSpec
from experiments.sensitivity import SensitivityRunner, SensitivitySpec
from experiments.walk_forward import WalkForwardRunner, WalkForwardSpec
from experiments.strategy_gate import StrategyGateRunner, StrategyGateSpec
from research.registry import HypothesisRecord, StrategyRegistry

class ToolStatus(StrEnum): SUCCESS="SUCCESS"; REJECTED="REJECTED"; INVALID_REQUEST="INVALID_REQUEST"; DUPLICATE="DUPLICATE"; NOT_FOUND="NOT_FOUND"; EXECUTION_FAILED="EXECUTION_FAILED"
class RegisteredStrategy(StrEnum): EMA_CROSSOVER="EMA_CROSSOVER"
@dataclass(frozen=True,slots=True)
class StrategySpec:
    strategy:RegisteredStrategy; symbol:str; timeframe:str; parameters:Mapping[str,object]
    def __post_init__(self):
        if self.strategy is not RegisteredStrategy.EMA_CROSSOVER or not self.symbol or self.timeframe!="H1": raise ValueError("only declarative EMA_CROSSOVER EURUSD/H1 is supported")
        if not isinstance(self.parameters,Mapping): raise TypeError("parameters must be a mapping")
        object.__setattr__(self,"parameters",MappingProxyType(dict(self.parameters)))
        if set(self.parameters)-{"fast_period","slow_period"}: raise ValueError("arbitrary strategy code or parameters are not allowed")
@dataclass(frozen=True,slots=True)
class ToolResponse:
    status:ToolStatus; fingerprint:str|None=None; value:object|None=None; message:str=""

class ResearchService:
    def __init__(self,registry:StrategyRegistry): self.registry=registry; self._cache={}
    def register_hypothesis(self,record:HypothesisRecord):
        try: return ToolResponse(ToolStatus.SUCCESS,record.fingerprint,self.registry.add(record))
        except ValueError as exc: return ToolResponse(ToolStatus.DUPLICATE,message=str(exc))
    def get_hypothesis(self,hypothesis_id:str):
        try:
            value=self.registry.get(hypothesis_id); return ToolResponse(ToolStatus.SUCCESS,value.fingerprint,value)
        except KeyError: return ToolResponse(ToolStatus.NOT_FOUND,message="hypothesis not found")
    def run_experiment(self,strategy:StrategySpec,spec:ExperimentSpec,dataframe:pd.DataFrame): return self._run("experiment",spec.fingerprint,lambda: ExperimentRunner(dataframe).run(spec),strategy,spec)
    def run_sensitivity(self,strategy:StrategySpec,spec:SensitivitySpec,dataframe:pd.DataFrame): return self._run("sensitivity",spec.fingerprint,lambda: SensitivityRunner(ExperimentRunner(dataframe)).run(spec),strategy,spec.experiment_spec)
    def run_walk_forward(self,strategy:StrategySpec,spec:WalkForwardSpec,dataframe:pd.DataFrame): return self._run("walk_forward",spec.fingerprint,lambda: WalkForwardRunner(dataframe).run(spec),strategy,None)
    def run_gate(self,strategy:StrategySpec,spec:StrategyGateSpec,walk_forward_median_return:float,dataframe:pd.DataFrame): return self._run("gate",spec.fingerprint,lambda: StrategyGateRunner(spec,walk_forward_median_return).execute_holdout_once(dataframe),strategy,None)
    def _run(self,kind,key,operation,strategy,spec):
        if not isinstance(strategy,StrategySpec): return ToolResponse(ToolStatus.INVALID_REQUEST,message="StrategySpec is required")
        if spec is not None and (strategy.symbol!=spec.symbol or dict(strategy.parameters)!=dict(spec.strategy_parameters)): return ToolResponse(ToolStatus.REJECTED,message="StrategySpec does not match frozen experiment")
        cache_key=(kind,key)
        if cache_key in self._cache: return ToolResponse(ToolStatus.SUCCESS,key,self._cache[cache_key],"idempotent cached result")
        try:
            value=operation(); self._cache[cache_key]=value; return ToolResponse(ToolStatus.SUCCESS,key,value)
        except (ValueError,TypeError) as exc: return ToolResponse(ToolStatus.INVALID_REQUEST,message=str(exc))
        except Exception as exc: return ToolResponse(ToolStatus.EXECUTION_FAILED,message=str(exc))
