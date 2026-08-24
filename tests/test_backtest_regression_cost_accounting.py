from datetime import datetime, timedelta, timezone

import pytest

from backtest.clock import ClockEvent
from backtest.costs import FixedCostModel
from backtest.equity_ledger import (
    EquityLedger,
    EquityPoint,
)
from backtest.execution import SimulatedExecution
from backtest.models import (
    BacktestConfig,
    InstrumentSpecification,
    MarketBar,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Timeframe,
)
from backtest.models.enums import SimulationPhase
from backtest.performance import (
    calculate_performance_summary,
)
from backtest.portfolio import Portfolio
from backtest.trade_factory import TradeFactory
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


def make_instrument() -> InstrumentSpecification:
    return InstrumentSpecification(
        symbol="EURUSD",
        digits=5,
        point=0.00001,
        pip_size=0.00010,
        contract_size=100000,
        volume_min=0.01,
        volume_max=500.0,
        volume_step=0.01,
        tick_size=0.00001,
    )


def make_open_event(
    timestamp: datetime,
    *,
    bar_index: int,
) -> ClockEvent:
    return ClockEvent(
        timestamp=timestamp,
        phase=SimulationPhase.BAR_OPEN,
        bar_index=bar_index,
        bar_start=timestamp,
        bar_close=(
            timestamp
            + timedelta(minutes=15)
        ),
    )


def make_bar(
    timestamp: datetime,
) -> MarketBar:
    return MarketBar(
        time=timestamp,
        open=1.16000,
        high=1.16000,
        low=1.16000,
        close=1.16000,
        tick_volume=1000,
    )


def make_order(
    *,
    order_id: str,
    signal_id: str,
    side: OrderSide,
    timestamp: datetime,
    strategy_id: str | None = None,
) -> Order:
    metadata = {}

    if strategy_id is not None:
        metadata["strategy_id"] = strategy_id

    return Order(
        order_id=order_id,
        signal_id=signal_id,
        symbol="EURUSD",
        side=side,
        quantity=0.10,
        order_type=OrderType.MARKET,
        created_at=timestamp,
        scheduled_for=timestamp,
        status=OrderStatus.PENDING,
        metadata=metadata,
    )


def test_costs_are_applied_once_through_final_performance():
    config = make_config()
    instrument = make_instrument()

    execution = SimulatedExecution(
        config=config,
        cost_model=FixedCostModel(
            instrument=instrument,
            spread_pips=2.0,
            slippage_pips=0.5,
            commission_per_lot_per_side=3.50,
        ),
    )

    portfolio = Portfolio(
        config=config,
        instrument=instrument,
    )

    # -------------------------------------------------
    # 1. INITIAL EQUITY
    # -------------------------------------------------

    equity_ledger = EquityLedger()

    equity_ledger.append(
        EquityPoint(
            timestamp=utc_time(10, 0),
            bar_index=0,
            phase=SimulationPhase.BAR_CLOSE,
            cash=10000.0,
            equity=10000.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
        )
    )

    # -------------------------------------------------
    # 2. LONG ENTRY — STATIC MARKET
    # -------------------------------------------------

    entry_time = utc_time(10, 15)

    entry = execution.execute(
        make_order(
            order_id="ORD-ENTRY",
            signal_id="SIG-ENTRY",
            side=OrderSide.BUY,
            timestamp=entry_time,
            strategy_id="REGRESSION-COSTS",
        ),
        event=make_open_event(
            entry_time,
            bar_index=1,
        ),
        bar=make_bar(entry_time),
    )

    portfolio.apply_execution(entry)

    # Midpoint = 1.16000
    #
    # BUY pays:
    # +1 pip half spread
    # +0.5 pip slippage
    assert entry.fill.execution_price == pytest.approx(
        1.16015
    )

    # -------------------------------------------------
    # 3. EXIT — MARKET MIDPOINT STILL DID NOT MOVE
    # -------------------------------------------------

    exit_time = utc_time(10, 30)

    exit_execution = execution.execute(
        make_order(
            order_id="ORD-EXIT",
            signal_id="SIG-EXIT",
            side=OrderSide.SELL,
            timestamp=exit_time,
        ),
        event=make_open_event(
            exit_time,
            bar_index=2,
        ),
        bar=make_bar(exit_time),
    )

    close_result = portfolio.apply_execution(
        exit_execution
    )

    assert close_result is not None

    assert exit_execution.fill.execution_price == pytest.approx(
        1.15985
    )

    # Spread + slippage are embedded in execution prices.
    assert close_result.gross_pnl == pytest.approx(
        -3.00
    )

    # Commission = 0.35 entry + 0.35 exit.
    assert close_result.commission == pytest.approx(
        0.70
    )

    assert close_result.net_pnl == pytest.approx(
        -3.70
    )

    # -------------------------------------------------
    # 4. POSITION CLOSE → TRADE
    # -------------------------------------------------

    trade = TradeFactory(
        instrument
    ).create_from_bar_indexes(
        close_result,
        entry_bar_index=1,
        exit_bar_index=2,
        exit_phase=SimulationPhase.BAR_OPEN,
    )

    # Audit values:
    #
    # full spread round trip:
    # 2 pips * 100000 * 0.10 = 2.00
    assert trade.spread_cost == pytest.approx(
        2.00
    )

    # 0.5 pip per side = 1 pip round trip:
    # 0.00010 * 100000 * 0.10 = 1.00
    assert trade.slippage_cost == pytest.approx(
        1.00
    )

    assert trade.commission == pytest.approx(
        0.70
    )

    # Critical invariant:
    #
    # spread/slippage MUST NOT be subtracted again.
    assert trade.net_pnl == pytest.approx(
        -3.70
    )

    # -------------------------------------------------
    # 5. TRADE LEDGER
    # -------------------------------------------------

    trade_ledger = TradeLedger()
    trade_ledger.append(trade)

    # Final portfolio is flat.
    assert portfolio.is_flat is True

    equity_ledger.append(
        EquityPoint(
            timestamp=exit_time,
            bar_index=2,
            phase=SimulationPhase.BAR_OPEN,
            cash=portfolio.cash,
            equity=portfolio.equity,
            realized_pnl=portfolio.realized_pnl,
            unrealized_pnl=portfolio.unrealized_pnl,
        )
    )

    # -------------------------------------------------
    # 6. FINAL PERFORMANCE
    # -------------------------------------------------

    summary = calculate_performance_summary(
        config,
        trade_ledger,
        equity_ledger,
    )

    assert summary.final_equity == pytest.approx(
        9996.30
    )

    assert summary.total_return == pytest.approx(
        -3.70
    )

    assert summary.total_return_pct == pytest.approx(
        -0.037
    )

    metrics = summary.trade_metrics

    assert metrics.total_trades == 1
    assert metrics.wins == 0
    assert metrics.losses == 1

    assert metrics.gross_profit == pytest.approx(
        0.0
    )

    assert metrics.gross_loss == pytest.approx(
        3.70
    )

    assert metrics.net_profit == pytest.approx(
        -3.70
    )

    assert metrics.average_trade == pytest.approx(
        -3.70
    )

    assert metrics.expectancy == pytest.approx(
        -3.70
    )

    assert summary.drawdown.max_drawdown == pytest.approx(
        3.70
    )

    assert summary.drawdown.max_drawdown_pct == pytest.approx(
        0.037
    )