from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite

from backtest.clock import SimulationClock
from backtest.context import BacktestContext, BacktestContextBuilder
from backtest.execution import ExecutionResult, ExecutionStatus, SimulatedExecution
from backtest.feed import HistoricalBarFeed
from backtest.portfolio import Portfolio, PortfolioSnapshot
from backtest.position import PositionSide
from backtest.risk import RiskDecision, RiskModel
from backtest.strategy import Strategy
from domain.fill import Fill
from domain.order_intent import OrderIntent, OrderSide
from domain.signal import Signal


@dataclass(frozen=True, slots=True)
class BacktestResult:
    signals: tuple[Signal, ...]
    risk_decisions: tuple[RiskDecision, ...]
    orders: tuple[OrderIntent, ...]
    executions: tuple[ExecutionResult, ...]
    fills: tuple[Fill, ...]
    portfolio_snapshots: tuple[PortfolioSnapshot, ...]
    contexts: tuple[BacktestContext, ...]
    initial_equity: float

    def __post_init__(self) -> None:
        if not isinstance(self.initial_equity, (int, float)) or isinstance(self.initial_equity, bool) or not isfinite(self.initial_equity) or self.initial_equity <= 0:
            raise ValueError("initial_equity must be a positive finite number")


class BacktestEngine:
    def __init__(self, *, feed: HistoricalBarFeed, strategy: Strategy, risk_model: RiskModel, execution: SimulatedExecution, portfolio: Portfolio, context_closed_bar_limit: int | None = None, trading_start: datetime | None = None) -> None:
        if not isinstance(feed, HistoricalBarFeed): raise TypeError("feed must be a HistoricalBarFeed")
        if not isinstance(strategy, Strategy): raise TypeError("strategy must be a Strategy")
        if not isinstance(risk_model, RiskModel): raise TypeError("risk_model must be a RiskModel")
        if not isinstance(execution, SimulatedExecution): raise TypeError("execution must be a SimulatedExecution")
        if not isinstance(portfolio, Portfolio): raise TypeError("portfolio must be a Portfolio")
        if context_closed_bar_limit is not None and (not isinstance(context_closed_bar_limit, int) or isinstance(context_closed_bar_limit, bool) or context_closed_bar_limit <= 0): raise ValueError("context_closed_bar_limit must be a positive integer or None")
        if trading_start is not None and (trading_start.tzinfo is None or trading_start.utcoffset() != timedelta(0)): raise ValueError("trading_start must be timezone-aware UTC")
        if portfolio.symbol != feed.config.symbol: raise ValueError("portfolio symbol must match feed symbol")
        self.feed, self.strategy, self.risk_model, self.execution, self.portfolio = feed, strategy, risk_model, execution, portfolio
        self.context_closed_bar_limit = context_closed_bar_limit
        self.trading_start = trading_start

    def run(self) -> BacktestResult:
        clock = SimulationClock(self.feed.bar_starts, self.feed.config.timeframe)
        builder = BacktestContextBuilder(self.feed, clock)
        signals, decisions, orders, executions, fills, contexts = [], [], [], [], [], []
        pending = None
        for event in clock.events():
            context = builder.build(event, closed_bar_limit=self.context_closed_bar_limit)
            contexts.append(context)
            if event.phase.value == "BAR_OPEN":
                if pending is not None:
                    result = self.execution.execute(pending, feed=self.feed)
                    executions.append(result)
                    if result.status is ExecutionStatus.FILLED:
                        fills.append(result.fill)
                        if pending.metadata.get("risk_action") == "EXIT": self.portfolio.close_position(result.fill)
                        else: self.portfolio.open_position(result.fill, side=PositionSide.LONG if pending.side is OrderSide.BUY else PositionSide.SHORT)
                    pending = None
                continue
            if self.portfolio.position is not None:
                self.portfolio.mark_to_market(timestamp=event.timestamp, price=context.current_bar.close)
            signal = self.strategy.on_bar(context)
            if not isinstance(signal, Signal): raise TypeError("Strategy.on_bar must return a Signal")
            if self.trading_start is not None and context.current_bar.time < self.trading_start:
                continue
            signals.append(signal)
            decision = self.risk_model.evaluate(signal, position=self.portfolio.position)
            decisions.append(decision)
            if decision.approved:
                pending = decision.order_intent
                orders.append(pending)
        if pending is not None:
            executions.append(self.execution.execute(pending, feed=self.feed))
        return BacktestResult(tuple(signals), tuple(decisions), tuple(orders), tuple(executions), tuple(fills), self.portfolio.snapshots, tuple(contexts), self.portfolio.initial_cash)
