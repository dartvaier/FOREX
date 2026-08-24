from datetime import datetime, timezone

import pandas as pd
import pytest

from backtest.models import Timeframe
from experiments.framework import ExperimentRunner, ExperimentSpec, TemporalSplit


def at(hour): return datetime(2026, 8, 24, hour, tzinfo=timezone.utc)


def frame():
    times = [at(hour) for hour in (0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12)]
    closes = [10, 9, 8, 12, 13, 12, 10, 9, 8, 12, 13, 12]
    return pd.DataFrame({"time": times, "open": closes, "high": closes, "low": closes, "close": closes, "tick_volume": [1] * len(times)})


def spec(warmup=3):
    return ExperimentSpec("ema-oos", "synthetic-h1", "EURUSD", Timeframe.H1, TemporalSplit(at(0), at(6), at(6), at(13), warmup), {"fast_period": 2, "slow_period": 3}, {"quantity": 1}, {"spread": 0.0})


def test_temporal_split_is_strict_and_immutable():
    with pytest.raises(ValueError, match="chronological"):
        TemporalSplit(at(0), at(6), at(5), at(8))
    subject = spec()
    with pytest.raises(TypeError):
        subject.strategy_parameters["fast_period"] = 99
    assert subject.fingerprint == spec().fingerprint


def test_warmup_precedes_each_window_but_produces_no_trades_or_pnl():
    result = ExperimentRunner(frame()).run(spec())
    test = result.out_of_sample_backtest
    first_close = next(context for context in test.contexts if context.current_bar is not None)
    assert first_close.closed_bars[0].time == at(3)
    assert all(signal.timestamp > at(6) for signal in test.signals)
    assert all(snapshot.timestamp >= at(6) for snapshot in test.portfolio_snapshots)
    assert "warm-up" not in test.signals[0].reason


def test_train_and_test_are_independent_non_overlapping_and_gap_preserving():
    result = ExperimentRunner(frame()).run(spec())
    train, test = result.in_sample_backtest, result.out_of_sample_backtest
    assert all(context.current_bar.time < at(6) for context in train.contexts if context.current_bar)
    assert all(context.current_bar.time >= at(3) for context in test.contexts if context.current_bar)
    assert at(7) not in [bar.time for context in test.contexts for bar in context.closed_bars]
    assert result.in_sample_report is not result.out_of_sample_report


def test_results_are_reproducible_and_future_mutation_cannot_change_train():
    source = frame()
    first = ExperimentRunner(source).run(spec())
    changed = source.copy()
    changed.loc[changed.time >= pd.Timestamp(at(6)), ["open", "high", "low", "close"]] = 9_999
    second = ExperimentRunner(changed).run(spec())
    assert first == ExperimentRunner(source).run(spec())
    assert first.in_sample_report == second.in_sample_report


def test_runner_rejects_unsorted_data_and_empty_windows():
    with pytest.raises(ValueError, match="strictly increasing"):
        ExperimentRunner(frame().iloc[::-1])
    empty = ExperimentSpec("empty", "x", "EURUSD", Timeframe.H1, TemporalSplit(at(0), at(6), at(20), at(21)), {"fast_period": 2, "slow_period": 3})
    with pytest.raises(ValueError, match="no bars"):
        ExperimentRunner(frame()).run(empty)
