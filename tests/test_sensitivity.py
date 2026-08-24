from datetime import datetime, timezone
import pandas as pd
import pytest
from backtest.models import Timeframe
from experiments.framework import ExperimentRunner, ExperimentSpec, TemporalSplit
from experiments.sensitivity import ParameterSet, SensitivityRunner, SensitivitySpec

def at(hour): return datetime(2026, 8, 24, hour, tzinfo=timezone.utc)
def data():
    prices=[10,9,8,12,13,12,10,9,8,12,13,12]
    return pd.DataFrame({"time":[at(i) for i in range(12)],"open":prices,"high":prices,"low":prices,"close":prices,"tick_volume":[1]*12})
def base(): return ExperimentSpec("dev","synthetic","EURUSD",Timeframe.H1,TemporalSplit(at(0),at(6),at(6),at(12),3),{"fast_period":2,"slow_period":3})
def spec(): return SensitivitySpec(base(),(ParameterSet({"fast_period":2,"slow_period":3}),ParameterSet({"fast_period":2,"slow_period":4})))

def test_grid_is_deterministic_immutable_and_keeps_individual_fingerprints():
    runner=SensitivityRunner(ExperimentRunner(data()))
    first, summary=runner.run(spec())
    assert first == runner.run(spec())[0] and len(first)==2 and first[0].fingerprint != first[1].fingerprint
    assert 0 <= summary.profitable_run_proportion <= 1 and summary.return_dispersion >= 0
    with pytest.raises(TypeError): spec().parameter_sets[0].strategy_parameters["fast_period"]=9

def test_invalid_duplicate_or_invalid_ema_combinations_are_rejected():
    item=ParameterSet({"fast_period":2,"slow_period":3})
    with pytest.raises(ValueError,match="unique"): SensitivitySpec(base(),(item,item))
    with pytest.raises(ValueError,match="fast_period"): SensitivityRunner(ExperimentRunner(data())).run(SensitivitySpec(base(),(ParameterSet({"fast_period":4,"slow_period":3}),)))

def test_sensitivity_uses_development_only_and_future_changes_do_not_affect_results():
    first,_=SensitivityRunner(ExperimentRunner(data())).run(spec())
    changed=data(); changed.loc[changed.time>=pd.Timestamp(at(6)),["open","high","low","close"]]=999
    second,_=SensitivityRunner(ExperimentRunner(changed)).run(spec())
    assert tuple(item.report for item in first)==tuple(item.report for item in second)
