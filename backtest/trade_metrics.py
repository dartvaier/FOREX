import math
from dataclasses import dataclass

from backtest.trade_ledger import TradeLedger


@dataclass(frozen=True, slots=True)
class TradeMetrics:
    total_trades: int

    wins: int
    losses: int
    breakevens: int

    win_rate: float

    gross_profit: float
    gross_loss: float
    profit_factor: float
    
    net_profit: float
    average_trade: float
    expectancy: float


def calculate_trade_metrics(
    ledger: TradeLedger,
) -> TradeMetrics:
    """
    Calculate basic completed-trade statistics.

    Classification uses net_pnl:

        net_pnl > 0  -> win
        net_pnl < 0  -> loss
        net_pnl ~= 0 -> breakeven

    win_rate uses all completed Trades as denominator:

        wins / total_trades * 100

    Therefore breakeven Trades remain part of the total.
    """

    if not isinstance(
        ledger,
        TradeLedger,
    ):
        raise TypeError(
            "ledger must be a TradeLedger"
        )

    wins = 0
    losses = 0
    breakevens = 0
    gross_profit = 0.0
    gross_loss = 0.0

    for trade in ledger:
        net_pnl = trade.net_pnl

        if math.isclose(
            net_pnl,
            0.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            breakevens += 1

        elif net_pnl > 0:
            wins += 1
            gross_profit += net_pnl

        else:
            losses += 1
            gross_loss += abs(net_pnl)
        
    total_trades = len(ledger)

    if total_trades == 0:
        win_rate = 0.0

    else:
        win_rate = (
            wins
            / total_trades
            * 100.0
        )
    
    if gross_loss > 0:
        profit_factor = (
            gross_profit
            / gross_loss
        )

    elif gross_profit > 0:
        profit_factor = math.inf

    else:
        profit_factor = 0.0
        
    net_profit = (
        gross_profit
        - gross_loss
    )

    if total_trades > 0:
        average_trade = (
            net_profit
            / total_trades
        )
    else:
        average_trade = 0.0
        
    if wins > 0:
        average_win = (
            gross_profit
            / wins
        )
    else:
        average_win = 0.0

    if losses > 0:
        average_loss = (
            gross_loss
            / losses
        )
    else:
        average_loss = 0.0

    if total_trades > 0:
        win_probability = (
            wins
            / total_trades
        )

        loss_probability = (
            losses
            / total_trades
        )

        expectancy = (
            win_probability
            * average_win
            - loss_probability
            * average_loss
        )
    else:
        expectancy = 0.0

    return TradeMetrics(
        total_trades=total_trades,
        wins=wins,
        losses=losses,
        breakevens=breakevens,
        win_rate=win_rate,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
        net_profit=net_profit,
        average_trade=average_trade,
        expectancy=expectancy,
    )