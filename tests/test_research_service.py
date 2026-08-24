from datetime import datetime,timezone
import pandas as pd
from backtest.models import Timeframe
from experiments.framework import ExperimentSpec,TemporalSplit
from research.registry import HypothesisRecord,StrategyRegistry
from research.service import *
def at(h): return datetime(2026,8,24,h,tzinfo=timezone.utc)
def frame():
 p=[10,9,8,12,13,12,10,9];return pd.DataFrame({"time":[at(i) for i in range(8)],"open":p,"high":p,"low":p,"close":p,"tick_volume":[1]*8})
def strategy(): return StrategySpec(RegisteredStrategy.EMA_CROSSOVER,"EURUSD","H1",{"fast_period":2,"slow_period":3})
def spec(): return ExperimentSpec("x","d","EURUSD",Timeframe.H1,TemporalSplit(at(0),at(4),at(4),at(8),3),{"fast_period":2,"slow_period":3})
def test_registry_responses_and_no_arbitrary_code(tmp_path):
 s=ResearchService(StrategyRegistry(tmp_path)); h=HypothesisRecord("a","ema","EURUSD","H1",{"fast":2})
 assert s.register_hypothesis(h).status is ToolStatus.SUCCESS and s.register_hypothesis(h).status is ToolStatus.DUPLICATE and s.get_hypothesis("x").status is ToolStatus.NOT_FOUND
 try: StrategySpec(RegisteredStrategy.EMA_CROSSOVER,"EURUSD","H1",{"code":"import MT5"}); assert False
 except ValueError: pass
def test_experiment_is_deterministic_idempotent_and_validated(tmp_path):
 s=ResearchService(StrategyRegistry(tmp_path)); first=s.run_experiment(strategy(),spec(),frame()); second=s.run_experiment(strategy(),spec(),frame()); assert first.status is ToolStatus.SUCCESS and second.message and first.value==second.value
 assert s.run_experiment(StrategySpec(RegisteredStrategy.EMA_CROSSOVER,"EURUSD","H1",{"fast_period":3,"slow_period":4}),spec(),frame()).status is ToolStatus.REJECTED
