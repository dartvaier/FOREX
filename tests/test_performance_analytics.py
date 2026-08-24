from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from math import inf, isclose

import pytest

from backtest.engine import BacktestResult
from backtest.execution import ExecutionResult, ExecutionStatus
from backtest.performance import PerformanceAnalytics
from backtest.portfolio import PortfolioSnapshot
from domain.fill import Fill
from domain.order_intent import OrderIntent, OrderSide, OrderType
from domain.signal import SignalAction


def at(hour): return datetime(2026, 8, 24, hour, tzinfo=timezone.utc)


def order(order_id, side, action, quantity=2):
    return OrderIntent(order_id, f"signal-{order_id}", "EURUSD", side, quantity, OrderType.MARKET, at(0), metadata={"risk_action": action.value})


def fill(order_id, hour, price, quantity=2, commission=0):
    return Fill(f"fill-{order_id}", order_id, at(hour), price, price, quantity, commission=commission)


def snapshot(hour, equity):
    return PortfolioSnapshot(at(hour), equity, equity, 0, 0, 0, None)


def result(*, orders=(), executions=(), fills=(), snapshots=(), initial=100):
    return BacktestResult(tuple(), tuple(), tuple(orders), tuple(executions), tuple(fills), tuple(snapshots), tuple(), initial)


def filled(order_id, trade_fill):
    return ExecutionResult(order_id, ExecutionStatus.FILLED, "filled", trade_fill.fill_time, trade_fill)


def test_long_closed_trade_is_reconstructed_from_executions_and_costs_are_net():
    entry, exit = order("entry", OrderSide.BUY, SignalAction.ENTER_LONG), order("exit", OrderSide.SELL, SignalAction.EXIT)
    entry_fill, exit_fill = fill("entry", 1, 10, commission=1), fill("exit", 2, 12, commission=1)
    report = PerformanceAnalytics().analyze(result(orders=(entry, exit), executions=(filled("entry", entry_fill), filled("exit", exit_fill)), fills=(entry_fill, exit_fill), snapshots=(snapshot(1, 99), snapshot(2, 102))))
    trade = report.trades[0]
    assert report.trade_count == report.winning_trades == 1
    assert trade.side.value == "LONG" and trade.gross_pnl == 4 and trade.net_pnl == 2 and trade.commission == 2
    assert report.absolute_return == 2 and report.percentage_return == 2 and report.total_commissions == 2
    assert report.gross_profit == report.average_win == 2 and report.gross_loss == 0
    assert report.profit_factor == report.payoff_ratio == inf and report.win_rate == 100


def test_short_closed_trade_has_the_correct_pnl_direction():
    entry, exit = order("entry", OrderSide.SELL, SignalAction.ENTER_SHORT), order("exit", OrderSide.BUY, SignalAction.EXIT)
    entry_fill, exit_fill = fill("entry", 1, 10), fill("exit", 2, 7)
    report = PerformanceAnalytics().analyze(result(orders=(entry, exit), executions=(filled("entry", entry_fill), filled("exit", exit_fill)), fills=(entry_fill, exit_fill), snapshots=(snapshot(2, 106),)))
    assert report.trades[0].side.value == "SHORT"
    assert report.trades[0].gross_pnl == report.trades[0].net_pnl == 6


def test_open_fill_is_not_mistaken_for_a_closed_trade():
    entry, exit, open_entry = order("entry", OrderSide.BUY, SignalAction.ENTER_LONG), order("exit", OrderSide.SELL, SignalAction.EXIT), order("open", OrderSide.BUY, SignalAction.ENTER_LONG)
    fills = (fill("entry", 1, 10), fill("exit", 2, 11), fill("open", 3, 12))
    report = PerformanceAnalytics().analyze(result(orders=(entry, exit, open_entry), executions=tuple(filled(item.order_id, item) for item in fills), fills=fills, snapshots=(snapshot(3, 102),)))
    assert len(fills) == 3 and report.trade_count == 1 and report.trades[0].net_pnl == 2


def test_zero_trade_and_zero_loss_edge_cases_are_explicit():
    empty = PerformanceAnalytics().analyze(result(snapshots=(snapshot(1, 100),)))
    assert empty.trade_count == 0 and empty.win_rate is None and empty.profit_factor is None
    assert empty.average_win is empty.average_loss is empty.payoff_ratio is None
    assert empty.maximum_drawdown_absolute == empty.maximum_drawdown_percent == 0


def test_drawdown_recovery_and_streaks_have_known_values():
    report = PerformanceAnalytics().analyze(result(snapshots=(snapshot(1, 120), snapshot(2, 90), snapshot(3, 130))))
    assert report.equity_curve == (100.0, 120, 90, 130)
    assert report.absolute_return == 30 and report.percentage_return == 30
    assert report.maximum_drawdown_absolute == 30 and report.maximum_drawdown_percent == 25


def test_winning_and_losing_streaks_are_counted_per_closed_trade():
    orders, fills = [], []
    for number, exit_price in enumerate((11, 12, 9, 8)):
        entry = order(f"entry-{number}", OrderSide.BUY, SignalAction.ENTER_LONG)
        exit = order(f"exit-{number}", OrderSide.SELL, SignalAction.EXIT)
        orders.extend((entry, exit))
        fills.extend((fill(entry.order_id, number * 2 + 1, 10), fill(exit.order_id, number * 2 + 2, exit_price)))
    executions = tuple(filled(item.order_id, item) for item in fills)
    report = PerformanceAnalytics().analyze(result(orders=orders, executions=executions, fills=fills))
    assert report.winning_trades == report.losing_trades == 2
    assert report.max_consecutive_wins == report.max_consecutive_losses == 2
    assert report.gross_profit == report.gross_loss == 6
    assert report.profit_factor == report.payoff_ratio == 1
    assert report.average_win == report.average_loss == 3


def test_sharpe_requires_explicit_annualization_and_handles_zero_variance():
    source = result(snapshots=(snapshot(1, 110), snapshot(2, 132)))
    assert PerformanceAnalytics().analyze(source).sharpe_ratio is None
    assert isclose(PerformanceAnalytics(periods_per_year=4).analyze(source).sharpe_ratio, 4.242640687119285)
    flat = result(snapshots=(snapshot(1, 100), snapshot(2, 100)))
    assert PerformanceAnalytics(periods_per_year=252).analyze(flat).sharpe_ratio is None
    with pytest.raises(ValueError, match="periods_per_year"):
        PerformanceAnalytics(periods_per_year=0)


def test_analytics_is_deterministic_and_does_not_mutate_result():
    source = result(snapshots=(snapshot(1, 90), snapshot(2, 110)))
    before = source
    first, second = PerformanceAnalytics().analyze(source), PerformanceAnalytics().analyze(source)
    assert first == second and source == before
    with pytest.raises(FrozenInstanceError):
        first.final_equity = 0


def test_inconsistent_filled_execution_is_rejected_instead_of_silently_inventing_trade():
    orphan = fill("missing", 1, 10)
    source = result(executions=(filled("missing", orphan),), fills=(orphan,))
    with pytest.raises(ValueError, match="matching order"):
        PerformanceAnalytics().analyze(source)
