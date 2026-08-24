from datetime import datetime,timezone
import pandas as pd
from backtest.models import Timeframe
from experiments.sensitivity import ParameterSet
from experiments.walk_forward import WalkForwardRunner,WalkForwardSpec
def at(h): return datetime(2026,8,24,h,tzinfo=timezone.utc)
def df():
 p=[10,9,8,12,13,12,10,9,8,12,13,12];return pd.DataFrame({"time":[at(i) for i in range(12)],"open":p,"high":p,"low":p,"close":p,"tick_volume":[1]*12})
def spec(): return WalkForwardSpec("wf","x","EURUSD",Timeframe.H1,at(0),at(10),3,2,2,3,(ParameterSet({"fast_period":2,"slow_period":3}),))
def test_folds_are_deterministic_and_holdout_excluded():
 r=WalkForwardRunner(df()); a=r.run(spec()); b=r.run(spec()); assert a==b and all(f.test_end<=at(10) for f in a.folds) and all(x.fold.fingerprint in x.fingerprint or x.fingerprint for x in a.results)
def test_future_holdout_mutation_does_not_change_walk_forward():
 a=WalkForwardRunner(df()).run(spec()); changed=df();changed.loc[changed.time>=pd.Timestamp(at(10)),["open","high","low","close"]]=999; assert a==WalkForwardRunner(changed).run(spec())
