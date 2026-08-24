from datetime import datetime,timezone
import pandas as pd, pytest
from backtest.models import Timeframe
from experiments.strategy_gate import *
def at(h): return datetime(2026,8,24,h,tzinfo=timezone.utc)
def spec(): return StrategyGateSpec("gate","x","EURUSD",Timeframe.H1,at(6),at(10),3,{"fast_period":2,"slow_period":3},min_trades=1)
def frame():
 p=[10,9,8,12,13,12,10,9,8,12];return pd.DataFrame({"time":[at(i) for i in range(10)],"open":p,"high":p,"low":p,"close":p,"tick_volume":[1]*10})
def test_fingerprint_immutable_and_one_shot_holdout():
 r=StrategyGateRunner(spec(),0); result=r.execute_holdout_once(frame()); assert result.fingerprint==spec().fingerprint
 with pytest.raises(RuntimeError): r.execute_holdout_once(frame())
 with pytest.raises(TypeError): spec().strategy_parameters["x"]=1
def test_inconclusive_and_reject_decisions():
 r=StrategyGateRunner(spec(),0); report=r.execute_holdout_once(frame()).report
 assert r.evaluate(report).status is GateStatus.INCONCLUSIVE
 assert StrategyGateRunner(StrategyGateSpec("g","x","EURUSD",Timeframe.H1,at(6),at(10),0,{"fast_period":2,"slow_period":3},min_trades=0,min_return_percent=999),0).evaluate(report).status is GateStatus.REJECT
