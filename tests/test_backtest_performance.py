from datetime import datetime, timezone

import pytest

from backtest.equity_ledger import (
    EquityLedger,
    EquityPoint,
)
from backtest.models import (
    BacktestConfig,
    Timeframe,
)
from backtest.models.enums import SimulationPhase
from backtest.performance import (
    calculate_performance_summary,
)
from backtest.trade_ledger import TradeLedger


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


def make_config() -> BacktestConfig:
    return BacktestConfig(
        symbol="EURUSD",
        timeframe=Timeframe.M15,
        date_from=utc_time(10),
        date_to=utc_time(12),
        initial_capital=10000.0,
    )


def append_equity(
    ledger: EquityLedger,
    *,
    timestamp: datetime,
    bar_index: int,
    equity: float,
) -> None:
    ledger.append(
        EquityPoint(
            timestamp=timestamp,
            bar_index=bar_index,
            phase=SimulationPhase.BAR_CLOSE,
            cash=equity,
            equity=equity,
            realized_pnl=(
                equity - 10000.0
            ),
            unrealized_pnl=0.0,
        )
    )


def test_empty_ledgers_return_initial_capital():
    summary = calculate_performance_summary(
        make_config(),
        TradeLedger(),
        EquityLedger(),
    )

    assert summary.initial_capital == pytest.approx(
        10000.0
    )

    assert summary.final_equity == pytest.approx(
        10000.0
    )

    assert summary.total_return == pytest.approx(
        0.0
    )

    assert summary.total_return_pct == pytest.approx(
        0.0
    )

    assert summary.trade_metrics.total_trades == 0

    assert summary.drawdown.max_drawdown == pytest.approx(
        0.0
    )


def test_summary_uses_last_equity_point():
    ledger = EquityLedger()

    append_equity(
        ledger,
        timestamp=utc_time(10, 15),
        bar_index=0,
        equity=10000.0,
    )

    append_equity(
        ledger,
        timestamp=utc_time(10, 30),
        bar_index=1,
        equity=10250.0,
    )

    summary = calculate_performance_summary(
        make_config(),
        TradeLedger(),
        ledger,
    )

    assert summary.final_equity == pytest.approx(
        10250.0
    )

    assert summary.total_return == pytest.approx(
        250.0
    )

    assert summary.total_return_pct == pytest.approx(
        2.5
    )


def test_summary_supports_negative_return():
    ledger = EquityLedger()

    append_equity(
        ledger,
        timestamp=utc_time(10, 15),
        bar_index=0,
        equity=10000.0,
    )

    append_equity(
        ledger,
        timestamp=utc_time(10, 30),
        bar_index=1,
        equity=9700.0,
    )

    summary = calculate_performance_summary(
        make_config(),
        TradeLedger(),
        ledger,
    )

    assert summary.total_return == pytest.approx(
        -300.0
    )

    assert summary.total_return_pct == pytest.approx(
        -3.0
    )


def test_summary_includes_drawdown():
    ledger = EquityLedger()

    append_equity(
        ledger,
        timestamp=utc_time(10, 15),
        bar_index=0,
        equity=10000.0,
    )

    append_equity(
        ledger,
        timestamp=utc_time(10, 30),
        bar_index=1,
        equity=10500.0,
    )

    append_equity(
        ledger,
        timestamp=utc_time(10, 45),
        bar_index=2,
        equity=10000.0,
    )

    summary = calculate_performance_summary(
        make_config(),
        TradeLedger(),
        ledger,
    )

    assert summary.drawdown.max_drawdown == pytest.approx(
        500.0
    )

    assert summary.drawdown.max_drawdown_pct == pytest.approx(
        500.0 / 10500.0 * 100.0
    )


def test_requires_backtest_config():
    with pytest.raises(
        TypeError,
        match="BacktestConfig",
    ):
        calculate_performance_summary(
            object(),  # type: ignore[arg-type]
            TradeLedger(),
            EquityLedger(),
        )


def test_requires_trade_ledger():
    with pytest.raises(
        TypeError,
        match="TradeLedger",
    ):
        calculate_performance_summary(
            make_config(),
            object(),  # type: ignore[arg-type]
            EquityLedger(),
        )


def test_requires_equity_ledger():
    with pytest.raises(
        TypeError,
        match="EquityLedger",
    ):
        calculate_performance_summary(
            make_config(),
            TradeLedger(),
            object(),  # type: ignore[arg-type]
        )