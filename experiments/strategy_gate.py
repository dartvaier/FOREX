"""Frozen final-holdout strategy gate; execution is deliberately one-shot."""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Mapping
import pandas as pd
from backtest.models import Timeframe
from backtest.performance import PerformanceReport
from experiments.framework import ExperimentRunner, ExperimentSpec, TemporalSplit

class GateStatus(StrEnum): PASS="PASS"; REJECT="REJECT"; INCONCLUSIVE="INCONCLUSIVE"
@dataclass(frozen=True, slots=True)
class StrategyGateSpec:
    name:str; dataset_id:str; symbol:str; timeframe:Timeframe; holdout_start:datetime; holdout_end:datetime; warmup_bars:int; strategy_parameters:Mapping[str,object]; risk_parameters:Mapping[str,object]=field(default_factory=dict); cost_parameters:Mapping[str,object]=field(default_factory=dict); min_return_percent:float=0; min_profit_factor:float=1; min_sharpe:float=0; max_drawdown_percent:float=20; min_trades:int=1; max_return_degradation:float=100
    def __post_init__(self):
        if not self.holdout_start<self.holdout_end or self.warmup_bars<0 or self.min_trades<0: raise ValueError("invalid holdout or criteria")
        for n in ("strategy_parameters","risk_parameters","cost_parameters"): object.__setattr__(self,n,MappingProxyType(dict(getattr(self,n))))
        json.dumps(self.payload(),sort_keys=True)
    def payload(self): return {"name":self.name,"dataset":self.dataset_id,"symbol":self.symbol,"timeframe":self.timeframe.value,"holdout_start":self.holdout_start.isoformat(),"holdout_end":self.holdout_end.isoformat(),"warmup":self.warmup_bars,"strategy":dict(self.strategy_parameters),"risk":dict(self.risk_parameters),"cost":dict(self.cost_parameters),"criteria":[self.min_return_percent,self.min_profit_factor,self.min_sharpe,self.max_drawdown_percent,self.min_trades,self.max_return_degradation]}
    @property
    def fingerprint(self): return sha256(json.dumps(self.payload(),sort_keys=True,separators=(",",":")).encode()).hexdigest()
@dataclass(frozen=True, slots=True)
class StrategyGateResult:
    spec:StrategyGateSpec; fingerprint:str; status:GateStatus; report:PerformanceReport; reasons:tuple[str,...]; walk_forward_median_return:float; audit:Mapping[str,object]

class StrategyGateRunner:
    """Has no dataframe until the explicitly one-shot final execution call."""
    def __init__(self,spec:StrategyGateSpec,walk_forward_median_return:float): self.spec,self._wf,self._executed=spec,walk_forward_median_return,False
    def evaluate(self,report:PerformanceReport):
        s=self.spec
        if report.trade_count<s.min_trades: status,reasons=GateStatus.INCONCLUSIVE,("insufficient closed trades",)
        else:
            reasons=[]
            if report.percentage_return<s.min_return_percent: reasons.append("return below threshold")
            if report.profit_factor is None or report.profit_factor<s.min_profit_factor: reasons.append("profit factor below threshold")
            if report.sharpe_ratio is None or report.sharpe_ratio<s.min_sharpe: reasons.append("sharpe below threshold")
            if report.maximum_drawdown_percent>s.max_drawdown_percent: reasons.append("drawdown above threshold")
            if self._wf-report.percentage_return>s.max_return_degradation: reasons.append("walk-forward degradation above threshold")
            status=GateStatus.REJECT if reasons else GateStatus.PASS
        audit=MappingProxyType({"spec_fingerprint":s.fingerprint,"holdout_start":s.holdout_start.isoformat(),"holdout_end":s.holdout_end.isoformat(),"executed_once":True})
        return StrategyGateResult(s,s.fingerprint,status,report,tuple(reasons),self._wf,audit)
    def execute_holdout_once(self,dataframe:pd.DataFrame):
        if self._executed: raise RuntimeError("final holdout has already been executed")
        self._executed=True; s=self.spec; frame=dataframe.copy(); frame["time"]=pd.to_datetime(frame["time"],utc=True)
        prior=frame[frame.time<pd.Timestamp(s.holdout_start)]
        if prior.empty: raise ValueError("holdout execution requires prior development data")
        split=TemporalSplit(prior.time.iloc[0].to_pydatetime(),s.holdout_start,s.holdout_start,s.holdout_end,s.warmup_bars)
        exp=ExperimentSpec(s.name,s.dataset_id,s.symbol,s.timeframe,split,s.strategy_parameters,s.risk_parameters,s.cost_parameters)
        return self.evaluate(ExperimentRunner(frame).run(exp).out_of_sample_report)
