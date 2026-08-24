"""Read-only performance analytics for a completed backtest."""

from dataclasses import dataclass
from math import inf, isfinite, sqrt
from statistics import mean, stdev

from backtest.engine import BacktestResult
from backtest.execution import ExecutionStatus
from backtest.position import PositionSide
from domain.fill import Fill
from domain.order_intent import OrderIntent, OrderSide
from domain.signal import SignalAction


@dataclass(frozen=True, slots=True)
class PerformanceTrade:
    """A fully closed baseline position reconstructed from two executions."""

    entry_fill: Fill
    exit_fill: Fill
    side: PositionSide
    quantity: float
    gross_pnl: float
    net_pnl: float
    commission: float


@dataclass(frozen=True, slots=True)
class PerformanceReport:
    initial_equity: float
    final_equity: float
    equity_curve: tuple[float, ...]
    absolute_return: float
    percentage_return: float
    trades: tuple[PerformanceTrade, ...]
    winning_trades: int
    losing_trades: int
    win_rate: float | None
    gross_profit: float
    gross_loss: float
    profit_factor: float | None
    average_win: float | None
    average_loss: float | None
    payoff_ratio: float | None
    total_commissions: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    maximum_drawdown_absolute: float
    maximum_drawdown_percent: float
    sharpe_ratio: float | None
    periods_per_year: int | None

    @property
    def trade_count(self) -> int:
        return len(self.trades)


class PerformanceAnalytics:
    """Produces deterministic analytics without changing ``BacktestResult``.

    Sharpe is annualized only when ``periods_per_year`` is supplied. It uses
    zero risk-free rate, simple adjacent equity returns and sample standard
    deviation; each adjacent observation is treated as one equal period.
    """

    def __init__(self, *, periods_per_year: int | None = None) -> None:
        if periods_per_year is not None and (not isinstance(periods_per_year, int) or isinstance(periods_per_year, bool) or periods_per_year <= 0):
            raise ValueError("periods_per_year must be a positive integer or None")
        self.periods_per_year = periods_per_year

    def analyze(self, result: BacktestResult) -> PerformanceReport:
        if not isinstance(result, BacktestResult):
            raise TypeError("result must be a BacktestResult")
        equity_curve = (float(result.initial_equity),) + tuple(snapshot.equity for snapshot in result.portfolio_snapshots)
        trades = self._reconstruct_closed_trades(result)
        wins = tuple(trade.net_pnl for trade in trades if trade.net_pnl > 0)
        losses = tuple(-trade.net_pnl for trade in trades if trade.net_pnl < 0)
        gross_profit, gross_loss = sum(wins), sum(losses)
        consecutive_wins, consecutive_losses = self._streaks(trades)
        final_equity = equity_curve[-1]
        profit_factor = None if gross_loss == 0 and gross_profit == 0 else (inf if gross_loss == 0 else gross_profit / gross_loss)
        payoff_ratio = None if not wins and not losses else (inf if wins and not losses else (0.0 if losses and not wins else mean(wins) / mean(losses)))
        return PerformanceReport(
            initial_equity=result.initial_equity,
            final_equity=final_equity,
            equity_curve=equity_curve,
            absolute_return=final_equity - result.initial_equity,
            percentage_return=(final_equity - result.initial_equity) / result.initial_equity * 100,
            trades=trades,
            winning_trades=len(wins), losing_trades=len(losses),
            win_rate=None if not trades else len(wins) / len(trades) * 100,
            gross_profit=gross_profit, gross_loss=gross_loss,
            profit_factor=profit_factor,
            average_win=None if not wins else mean(wins), average_loss=None if not losses else mean(losses), payoff_ratio=payoff_ratio,
            total_commissions=sum(fill.commission for fill in result.fills),
            max_consecutive_wins=consecutive_wins, max_consecutive_losses=consecutive_losses,
            maximum_drawdown_absolute=self._maximum_drawdown(equity_curve)[0],
            maximum_drawdown_percent=self._maximum_drawdown(equity_curve)[1],
            sharpe_ratio=self._sharpe(equity_curve), periods_per_year=self.periods_per_year,
        )

    @staticmethod
    def _reconstruct_closed_trades(result: BacktestResult) -> tuple[PerformanceTrade, ...]:
        orders = {order.order_id: order for order in result.orders}
        open_trade: tuple[OrderIntent, Fill] | None = None
        trades: list[PerformanceTrade] = []
        for execution in result.executions:
            if execution.status is not ExecutionStatus.FILLED:
                continue
            order = orders.get(execution.order_id)
            if order is None:
                raise ValueError("filled execution must have a matching order")
            action = order.metadata.get("risk_action")
            if action in (SignalAction.ENTER_LONG.value, SignalAction.ENTER_SHORT.value):
                if open_trade is not None:
                    raise ValueError("baseline result cannot open more than one position")
                open_trade = (order, execution.fill)
            elif action == SignalAction.EXIT.value:
                if open_trade is None:
                    raise ValueError("baseline result cannot exit without an open position")
                entry_order, entry_fill = open_trade
                if entry_order.quantity != execution.fill.quantity:
                    raise ValueError("baseline result does not support partial closes")
                side = PositionSide.LONG if entry_order.side is OrderSide.BUY else PositionSide.SHORT
                price_difference = execution.fill.execution_price - entry_fill.execution_price
                gross_pnl = price_difference * entry_fill.quantity if side is PositionSide.LONG else -price_difference * entry_fill.quantity
                commission = entry_fill.commission + execution.fill.commission
                trades.append(PerformanceTrade(entry_fill, execution.fill, side, entry_fill.quantity, gross_pnl, gross_pnl - commission, commission))
                open_trade = None
        return tuple(trades)

    @staticmethod
    def _streaks(trades: tuple[PerformanceTrade, ...]) -> tuple[int, int]:
        current_win = current_loss = max_win = max_loss = 0
        for trade in trades:
            if trade.net_pnl > 0:
                current_win, current_loss = current_win + 1, 0
            elif trade.net_pnl < 0:
                current_loss, current_win = current_loss + 1, 0
            else:
                current_win = current_loss = 0
            max_win, max_loss = max(max_win, current_win), max(max_loss, current_loss)
        return max_win, max_loss

    @staticmethod
    def _maximum_drawdown(equity_curve: tuple[float, ...]) -> tuple[float, float]:
        peak, maximum, maximum_percent = equity_curve[0], 0.0, 0.0
        for equity in equity_curve:
            peak = max(peak, equity)
            drawdown = peak - equity
            maximum = max(maximum, drawdown)
            if peak > 0:
                maximum_percent = max(maximum_percent, drawdown / peak * 100)
        return maximum, maximum_percent

    def _sharpe(self, equity_curve: tuple[float, ...]) -> float | None:
        if self.periods_per_year is None or len(equity_curve) < 3:
            return None
        returns = [(current / previous) - 1 for previous, current in zip(equity_curve, equity_curve[1:])]
        if any(not isfinite(value) for value in returns) or stdev(returns) == 0:
            return None
        return mean(returns) / stdev(returns) * sqrt(self.periods_per_year)
