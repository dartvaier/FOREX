from datetime import datetime, timezone

import math

import pytest

from backtest.models import (
    PositionSide,
    Trade,
)
from backtest.models.enums import ExitReason
from backtest.trade_ledger import TradeLedger
from backtest.trade_metrics import (
    TradeMetrics,
    calculate_trade_metrics,
)


def utc_time(
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026,
        8,
        8,
        hour,
        minute,
        tzinfo=timezone.utc,
    )


def make_trade(
    *,
    number: int,
    net_pnl: float,
    gross_pnl: float | None = None,
) -> Trade:
    return Trade(
        trade_id=f"TRADE-{number}",
        position_id=f"POS-{number}",
        strategy_id="TEST-STRATEGY",
        symbol="EURUSD",
        side=PositionSide.LONG,
        entry_fill_id=f"FILL-ENTRY-{number}",
        exit_fill_id=f"FILL-EXIT-{number}",
        entry_time=utc_time(10, 0),
        exit_time=utc_time(
            10,
            15 + number,
        ),
        entry_price=1.1600,
        exit_price=1.1700,
        quantity=0.01,
        gross_pnl=(
            net_pnl
            if gross_pnl is None
            else gross_pnl
        ),
        net_pnl=net_pnl,
        spread_cost=0.0,
        slippage_cost=0.0,
        commission=0.0,
        bars_held=1,
        exit_reason=ExitReason.STRATEGY_EXIT,
    )


def test_empty_ledger_returns_zero_metrics():
    metrics = calculate_trade_metrics(
        TradeLedger()
    )

    assert metrics == TradeMetrics(
        total_trades=0,
        wins=0,
        losses=0,
        breakevens=0,
        win_rate=0.0,
        gross_profit=0.0,
        gross_loss=0.0,
        profit_factor=0.0,
        net_profit=0.0,
        average_trade=0.0,
        expectancy=0.0,
        average_win=0.0,
        average_loss=0.0,
    )


def test_counts_wins_losses_and_breakevens():
    ledger = TradeLedger()

    results = [
        10.0,
        -5.0,
        0.0,
        20.0,
        -1.0,
    ]

    for number, net_pnl in enumerate(
        results,
        start=1,
    ):
        ledger.append(
            make_trade(
                number=number,
                net_pnl=net_pnl,
            )
        )

    metrics = calculate_trade_metrics(
        ledger
    )

    assert metrics.total_trades == 5
    assert metrics.wins == 2
    assert metrics.losses == 2
    assert metrics.breakevens == 1


def test_win_rate_uses_all_completed_trades():
    ledger = TradeLedger()

    results = [
        10.0,
        5.0,
        -5.0,
        -2.0,
        0.0,
    ]

    for number, net_pnl in enumerate(
        results,
        start=1,
    ):
        ledger.append(
            make_trade(
                number=number,
                net_pnl=net_pnl,
            )
        )

    metrics = calculate_trade_metrics(
        ledger
    )

    # 2 wins / 5 completed trades
    assert metrics.win_rate == pytest.approx(
        40.0
    )


def test_all_winning_trades_have_100_percent_win_rate():
    ledger = TradeLedger()

    for number in range(1, 4):
        ledger.append(
            make_trade(
                number=number,
                net_pnl=10.0,
            )
        )

    metrics = calculate_trade_metrics(
        ledger
    )

    assert metrics.total_trades == 3
    assert metrics.wins == 3

    assert metrics.win_rate == pytest.approx(
        100.0
    )


def test_all_breakevens_have_zero_win_rate():
    ledger = TradeLedger()

    for number in range(1, 4):
        ledger.append(
            make_trade(
                number=number,
                net_pnl=0.0,
            )
        )

    metrics = calculate_trade_metrics(
        ledger
    )

    assert metrics.total_trades == 3
    assert metrics.breakevens == 3

    assert metrics.win_rate == pytest.approx(
        0.0
    )


def test_near_zero_pnl_is_breakeven():
    ledger = TradeLedger()

    ledger.append(
        make_trade(
            number=1,
            net_pnl=1e-13,
        )
    )

    metrics = calculate_trade_metrics(
        ledger
    )

    assert metrics.wins == 0
    assert metrics.losses == 0
    assert metrics.breakevens == 1


def test_classification_uses_net_pnl_not_gross_pnl():
    ledger = TradeLedger()

    # Gross result was positive, but costs made
    # the completed Trade economically negative.
    ledger.append(
        make_trade(
            number=1,
            gross_pnl=10.0,
            net_pnl=-2.0,
        )
    )

    metrics = calculate_trade_metrics(
        ledger
    )

    assert metrics.wins == 0
    assert metrics.losses == 1
    assert metrics.breakevens == 0


def test_requires_trade_ledger():
    with pytest.raises(
        TypeError,
        match="TradeLedger",
    ):
        calculate_trade_metrics(
            object()  # type: ignore[arg-type]
        )
        
def test_calculates_gross_profit_and_gross_loss():
    ledger = TradeLedger()

    results = [
        10.0,
        20.0,
        -5.0,
        -2.0,
        0.0,
    ]

    for number, net_pnl in enumerate(
        results,
        start=1,
    ):
        ledger.append(
            make_trade(
                number=number,
                net_pnl=net_pnl,
            )
        )

    metrics = calculate_trade_metrics(
        ledger
    )

    assert metrics.gross_profit == pytest.approx(
        30.0
    )

    assert metrics.gross_loss == pytest.approx(
        7.0
    )


def test_calculates_profit_factor():
    ledger = TradeLedger()

    results = [
        20.0,
        10.0,
        -5.0,
        -5.0,
    ]

    for number, net_pnl in enumerate(
        results,
        start=1,
    ):
        ledger.append(
            make_trade(
                number=number,
                net_pnl=net_pnl,
            )
        )

    metrics = calculate_trade_metrics(
        ledger
    )

    # 30 / 10
    assert metrics.profit_factor == pytest.approx(
        3.0
    )


def test_profit_factor_is_infinite_without_losses():
    ledger = TradeLedger()

    ledger.append(
        make_trade(
            number=1,
            net_pnl=10.0,
        )
    )

    ledger.append(
        make_trade(
            number=2,
            net_pnl=20.0,
        )
    )

    metrics = calculate_trade_metrics(
        ledger
    )

    assert math.isinf(
        metrics.profit_factor
    )


def test_profit_factor_is_zero_without_profit():
    ledger = TradeLedger()

    ledger.append(
        make_trade(
            number=1,
            net_pnl=-10.0,
        )
    )

    metrics = calculate_trade_metrics(
        ledger
    )

    assert metrics.gross_profit == 0.0

    assert metrics.gross_loss == pytest.approx(
        10.0
    )

    assert metrics.profit_factor == 0.0
    
def test_calculates_net_profit():
    ledger = TradeLedger()

    results = [
        20.0,
        10.0,
        -5.0,
        -2.0,
    ]

    for number, net_pnl in enumerate(
        results,
        start=1,
    ):
        ledger.append(
            make_trade(
                number=number,
                net_pnl=net_pnl,
            )
        )

    metrics = calculate_trade_metrics(
        ledger
    )

    # 30 profit - 7 loss
    assert metrics.net_profit == pytest.approx(
        23.0
    )


def test_calculates_average_trade():
    ledger = TradeLedger()

    results = [
        20.0,
        10.0,
        -5.0,
        -5.0,
        0.0,
    ]

    for number, net_pnl in enumerate(
        results,
        start=1,
    ):
        ledger.append(
            make_trade(
                number=number,
                net_pnl=net_pnl,
            )
        )

    metrics = calculate_trade_metrics(
        ledger
    )

    # Net profit = 20
    # Trades     = 5
    #
    # 20 / 5 = 4
    assert metrics.average_trade == pytest.approx(
        4.0
    )


def test_calculates_monetary_expectancy():
    ledger = TradeLedger()

    results = [
        20.0,
        10.0,
        -5.0,
        -5.0,
        0.0,
    ]

    for number, net_pnl in enumerate(
        results,
        start=1,
    ):
        ledger.append(
            make_trade(
                number=number,
                net_pnl=net_pnl,
            )
        )

    metrics = calculate_trade_metrics(
        ledger
    )

    # Average win:
    # 30 / 2 = 15
    #
    # Average loss:
    # 10 / 2 = 5
    #
    # P(win)  = 2 / 5
    # P(loss) = 2 / 5
    #
    # expectancy =
    # 0.4 * 15 - 0.4 * 5
    # = 4
    assert metrics.expectancy == pytest.approx(
        4.0
    )


def test_expectancy_matches_average_trade():
    ledger = TradeLedger()

    results = [
        12.0,
        -7.0,
        3.0,
        0.0,
        -2.0,
    ]

    for number, net_pnl in enumerate(
        results,
        start=1,
    ):
        ledger.append(
            make_trade(
                number=number,
                net_pnl=net_pnl,
            )
        )

    metrics = calculate_trade_metrics(
        ledger
    )

    assert metrics.expectancy == pytest.approx(
        metrics.average_trade
    )


def test_empty_ledger_has_zero_average_and_expectancy():
    metrics = calculate_trade_metrics(
        TradeLedger()
    )

    assert metrics.net_profit == 0.0
    assert metrics.average_trade == 0.0
    assert metrics.expectancy == 0.0
    
def test_calculates_average_win_and_average_loss():
    ledger = TradeLedger()

    results = [
        20.0,
        10.0,
        -8.0,
        -2.0,
        0.0,
    ]

    for number, net_pnl in enumerate(
        results,
        start=1,
    ):
        ledger.append(
            make_trade(
                number=number,
                net_pnl=net_pnl,
            )
        )

    metrics = calculate_trade_metrics(
        ledger
    )

    # Wins:
    # 20 + 10 = 30
    # 30 / 2 = 15
    assert metrics.average_win == pytest.approx(
        15.0
    )

    # Losses:
    # 8 + 2 = 10
    # 10 / 2 = 5
    assert metrics.average_loss == pytest.approx(
        5.0
    )
    
def test_average_win_and_loss_are_zero_when_absent():
    winning_ledger = TradeLedger()

    winning_ledger.append(
        make_trade(
            number=1,
            net_pnl=10.0,
        )
    )

    winning_metrics = calculate_trade_metrics(
        winning_ledger
    )

    assert winning_metrics.average_win == pytest.approx(
        10.0
    )

    assert winning_metrics.average_loss == pytest.approx(
        0.0
    )

    losing_ledger = TradeLedger()

    losing_ledger.append(
        make_trade(
            number=2,
            net_pnl=-7.0,
        )
    )

    losing_metrics = calculate_trade_metrics(
        losing_ledger
    )

    assert losing_metrics.average_win == pytest.approx(
        0.0
    )

    assert losing_metrics.average_loss == pytest.approx(
        7.0
    )