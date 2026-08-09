from dataclasses import dataclass

from backtest.drawdown import (
    DrawdownResult,
    calculate_max_drawdown,
)
from backtest.equity_ledger import EquityLedger
from backtest.models.config import BacktestConfig
from backtest.trade_ledger import TradeLedger
from backtest.trade_metrics import (
    TradeMetrics,
    calculate_trade_metrics,
)


@dataclass(frozen=True, slots=True)
class PerformanceSummary:
    initial_capital: float
    final_equity: float
    total_return: float
    total_return_pct: float

    trade_metrics: TradeMetrics
    drawdown: DrawdownResult


def calculate_performance_summary(
    config: BacktestConfig,
    trade_ledger: TradeLedger,
    equity_ledger: EquityLedger,
) -> PerformanceSummary:
    """
    Consolidate completed-trade and equity-curve performance.

    final_equity comes from the last observed EquityPoint.

    If no equity snapshots exist yet, final_equity defaults to
    initial_capital.

    total_return is based on equity:

        final_equity - initial_capital

    This intentionally differs from TradeMetrics.net_profit
    when unrealized PnL still exists.
    """

    if not isinstance(
        config,
        BacktestConfig,
    ):
        raise TypeError(
            "config must be a BacktestConfig"
        )

    if not isinstance(
        trade_ledger,
        TradeLedger,
    ):
        raise TypeError(
            "trade_ledger must be a TradeLedger"
        )

    if not isinstance(
        equity_ledger,
        EquityLedger,
    ):
        raise TypeError(
            "equity_ledger must be an EquityLedger"
        )

    initial_capital = float(
        config.initial_capital
    )

    if equity_ledger.last_point is None:
        final_equity = initial_capital
    else:
        final_equity = float(
            equity_ledger.last_point.equity
        )

    total_return = (
        final_equity
        - initial_capital
    )

    total_return_pct = (
        total_return
        / initial_capital
        * 100.0
    )

    return PerformanceSummary(
        initial_capital=initial_capital,
        final_equity=final_equity,
        total_return=total_return,
        total_return_pct=total_return_pct,
        trade_metrics=calculate_trade_metrics(
            trade_ledger
        ),
        drawdown=calculate_max_drawdown(
            equity_ledger
        ),
    )