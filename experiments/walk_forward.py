"""Deterministic rolling walk-forward validation with an inaccessible holdout."""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from statistics import median, pstdev
import pandas as pd
from backtest.models import Timeframe
from backtest.performance import PerformanceReport
from experiments.framework import ExperimentRunner, ExperimentSpec, TemporalSplit
from experiments.sensitivity import ParameterSet

@dataclass(frozen=True, slots=True)
class WalkForwardSpec:
    name: str; dataset_id: str; symbol: str; timeframe: Timeframe; development_start: datetime; final_holdout_start: datetime; train_bars: int; test_bars: int; step_bars: int; warmup_bars: int; parameter_sets: tuple[ParameterSet, ...]
    def __post_init__(self):
        if not self.development_start < self.final_holdout_start: raise ValueError("development must end before final holdout")
        if min(self.train_bars,self.test_bars,self.step_bars)<=0 or self.warmup_bars<0 or not self.parameter_sets: raise ValueError("window sizes and parameter sets are required")
    @property
    def fingerprint(self): return sha256(json.dumps({"name":self.name,"dataset":self.dataset_id,"start":self.development_start.isoformat(),"holdout":self.final_holdout_start.isoformat(),"train":self.train_bars,"test":self.test_bars,"step":self.step_bars,"warmup":self.warmup_bars,"parameters":[x.fingerprint for x in self.parameter_sets]},sort_keys=True).encode()).hexdigest()

@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    fold_id: int; train_start: datetime; train_end: datetime; test_start: datetime; test_end: datetime
    @property
    def fingerprint(self): return sha256(f"{self.fold_id}|{self.train_start.isoformat()}|{self.train_end.isoformat()}|{self.test_start.isoformat()}|{self.test_end.isoformat()}".encode()).hexdigest()

@dataclass(frozen=True, slots=True)
class WalkForwardFoldResult:
    fold: WalkForwardFold; parameter_set: ParameterSet; fingerprint: str; report: PerformanceReport
@dataclass(frozen=True, slots=True)
class WalkForwardSummary:
    positive_fold_proportion: float; median_return_percent: float; return_dispersion: float; worst_return_percent: float; median_drawdown_percent: float; worst_drawdown_percent: float
@dataclass(frozen=True, slots=True)
class WalkForwardResult:
    spec: WalkForwardSpec; fingerprint: str; folds: tuple[WalkForwardFold,...]; results: tuple[WalkForwardFoldResult,...]; summary: WalkForwardSummary

class WalkForwardRunner:
    def __init__(self,dataframe:pd.DataFrame):
        self._data=dataframe.copy(); self._data["time"]=pd.to_datetime(self._data["time"],utc=True); self._experiment=ExperimentRunner(self._data)
    def generate_folds(self,spec:WalkForwardSpec):
        times=[x.to_pydatetime() for x in self._data.loc[(self._data.time>=pd.Timestamp(spec.development_start))&(self._data.time<pd.Timestamp(spec.final_holdout_start)),"time"]]
        folds=[]; start=0
        while start+spec.train_bars+spec.test_bars<=len(times):
            a,b=times[start],times[start+spec.train_bars]
            end=(times[start+spec.train_bars+spec.test_bars] if start+spec.train_bars+spec.test_bars<len(times) else spec.final_holdout_start)
            folds.append(WalkForwardFold(len(folds),a,b,b,end)); start+=spec.step_bars
        return tuple(folds)
    def run(self,spec:WalkForwardSpec):
        folds=self.generate_folds(spec); results=[]
        for fold in folds:
            split=TemporalSplit(fold.train_start,fold.train_end,fold.test_start,fold.test_end,spec.warmup_bars)
            for parameters in spec.parameter_sets:
                experiment=ExperimentSpec(f"{spec.name}-{fold.fold_id}",spec.dataset_id,spec.symbol,spec.timeframe,split,parameters.strategy_parameters)
                report=self._experiment.run(experiment).out_of_sample_report
                results.append(WalkForwardFoldResult(fold,parameters,sha256((fold.fingerprint+parameters.fingerprint).encode()).hexdigest(),report))
        values=[x.report.percentage_return for x in results]; dds=[x.report.maximum_drawdown_percent for x in results]
        summary=WalkForwardSummary(sum(x>0 for x in values)/len(values),median(values),pstdev(values),min(values),median(dds),max(dds))
        return WalkForwardResult(spec,spec.fingerprint,folds,tuple(results),summary)
