from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from backtest.costs import ZeroCostModel
from backtest.engine import BacktestEngine
from backtest.execution import ExecutionStatus, SimulatedExecution
from backtest.feed import HistoricalBarFeed
from backtest.models import BacktestConfig, Timeframe
from backtest.portfolio import Portfolio
from backtest.risk import FixedSizeRiskModel, RiskLimits
from backtest.strategy import Strategy
from domain.signal import Signal, SignalAction


def at(hour, minute=0): return datetime(2026, 8, 24, hour, minute, tzinfo=timezone.utc)


class Stub(Strategy):
    def __init__(self, actions): self.actions, self.contexts = actions, []
    def on_bar(self, context):
        self.contexts.append(context)
        return Signal(f"s{len(self.contexts)}", "stub", "EURUSD", context.current_time, self.actions[len(self.contexts)-1])


def engine(actions, times=None):
    times = times or [at(10), at(10,15), at(10,30), at(10,45)]
    n=len(times)
    frame=pd.DataFrame({"time":times,"open":[10+i for i in range(n)],"high":[11+i for i in range(n)],"low":[9+i for i in range(n)],"close":[10.5+i for i in range(n)],"tick_volume":[1]*n})
    feed=HistoricalBarFeed(frame,BacktestConfig("EURUSD",Timeframe.M15,at(9),at(12),1000))
    strategy=Stub(actions)
    return BacktestEngine(feed=feed,strategy=strategy,risk_model=FixedSizeRiskModel(RiskLimits("EURUSD"),1),execution=SimulatedExecution(ZeroCostModel()),portfolio=Portfolio(symbol="EURUSD",initial_cash=1000)),strategy


def test_long_exit_flow_is_close_signal_next_open_execution():
    subject,strategy=engine([SignalAction.ENTER_LONG,SignalAction.EXIT,SignalAction.HOLD,SignalAction.HOLD])
    result=subject.run()
    assert [fill.fill_time for fill in result.fills]==[at(10,15),at(10,30)]
    assert result.portfolio_snapshots[-1].position is None
    assert result.portfolio_snapshots[-1].realized_pnl==1
    assert all(context.phase.value=="BAR_CLOSE" for context in strategy.contexts)


def test_short_hold_rejection_and_last_unfilled_are_recorded():
    subject,_=engine([SignalAction.ENTER_SHORT,SignalAction.HOLD,SignalAction.HOLD,SignalAction.EXIT])
    result=subject.run()
    assert result.fills[0].fill_time==at(10,15)
    assert not result.risk_decisions[1].approved
    assert result.executions[-1].status is ExecutionStatus.UNFILLED


def test_gap_and_contexts_preserve_availability_and_determinism():
    first,_=engine([SignalAction.ENTER_LONG,SignalAction.HOLD],[at(10),at(10,30)])
    second,_=engine([SignalAction.ENTER_LONG,SignalAction.HOLD],[at(10),at(10,30)])
    result=first.run()
    assert result==second.run()
    assert result.fills[0].fill_time==at(10,30)
    assert all(bar.time+timedelta(minutes=15)<=context.current_time for context in result.contexts for bar in context.closed_bars)


def test_engine_validates_dependencies():
    subject,_=engine([SignalAction.HOLD]*4)
    with pytest.raises(TypeError,match="strategy"):
        BacktestEngine(feed=subject.feed,strategy=None,risk_model=subject.risk_model,execution=subject.execution,portfolio=subject.portfolio)
    with pytest.raises(ValueError, match="context_closed_bar_limit"):
        BacktestEngine(feed=subject.feed, strategy=subject.strategy, risk_model=subject.risk_model, execution=subject.execution, portfolio=subject.portfolio, context_closed_bar_limit=0)
