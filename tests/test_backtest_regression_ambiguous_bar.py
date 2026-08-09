from datetime import datetime, timedelta, timezone

import pytest

from backtest.clock import ClockEvent

from backtest.costs import (
    FixedCostModel,
    ZeroCostModel,
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
from backtest.models.enums import (
    ExitReason,
    SimulationPhase,
)
from backtest.portfolio import Portfolio
from backtest.protective_exit import ProtectiveExitEvaluator
from backtest.protective_order import ProtectiveExitOrderFactory


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


def test_ambiguous_bar_closes_long_at_worst_case_stop():
    config = make_config()
    instrument = make_instrument()

    execution = SimulatedExecution(
        config=config,
        cost_model=ZeroCostModel(
            instrument=instrument,
        ),
    )

    portfolio = Portfolio(
        config=config,
        instrument=instrument,
    )

    # -------------------------------------------------
    # 1. OPEN LONG @ 1.1600
    # -------------------------------------------------

    entry_time = utc_time(10, 15)

    entry_bar = MarketBar(
        time=entry_time,
        open=1.1600,
        high=1.1600,
        low=1.1600,
        close=1.1600,
        tick_volume=1000,
    )

    entry_order = Order(
        order_id="ORD-ENTRY",
        signal_id="SIG-ENTRY",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.MARKET,
        created_at=entry_time,
        scheduled_for=entry_time,
        status=OrderStatus.PENDING,
        stop_loss=1.1500,
        take_profit=1.1700,
    )

    entry_result = execution.execute(
        entry_order,
        event=make_open_event(
            entry_time,
            bar_index=1,
        ),
        bar=entry_bar,
    )

    portfolio.apply_execution(
        entry_result
    )

    position = portfolio.current_position

    assert position is not None

    # -------------------------------------------------
    # 2. BAR TOUCHES BOTH SL AND TP
    # -------------------------------------------------

    ambiguous_bar = MarketBar(
        time=utc_time(10, 30),
        open=1.1600,
        high=1.1720,  # touches TP 1.1700
        low=1.1480,   # touches SL 1.1500
        close=1.1610,
        tick_volume=1200,
    )

    decision = ProtectiveExitEvaluator(
        config
    ).evaluate(
        position,
        ambiguous_bar,
    )

    assert decision is not None

    # Unknown intrabar path:
    # WORST_CASE must select Stop Loss.
    assert (
        decision.exit_reason
        == ExitReason.STOP_LOSS
    )

    assert decision.ambiguous is True

    assert decision.reference_price == pytest.approx(
        1.1500
    )

    assert decision.triggered_at_open is False

    # -------------------------------------------------
    # 3. EXECUTE PROTECTIVE EXIT AT BAR CLOSE
    # -------------------------------------------------

    exit_time = utc_time(10, 45)

    exit_order = ProtectiveExitOrderFactory(
        config
    ).create(
        position,
        decision,
        execution_time=exit_time,
    )

    exit_result = execution.execute_protective(
        exit_order,
        decision=decision,
        bar=ambiguous_bar,
        fill_time=exit_time,
    )

    close_result = portfolio.apply_execution(
        exit_result,
        exit_reason=decision.exit_reason,
    )

    assert close_result is not None

    # -------------------------------------------------
    # 4. REGRESSION INVARIANTS
    # -------------------------------------------------

    assert (
        close_result.exit_reason
        == ExitReason.STOP_LOSS
    )

    assert close_result.exit_price == pytest.approx(
        1.1500
    )

    # LONG:
    #
    # entry = 1.1600
    # exit  = 1.1500
    #
    # -0.0100 * 100000 * 0.01
    # = -10.00
    assert close_result.gross_pnl == pytest.approx(
        -10.0
    )

    assert close_result.net_pnl == pytest.approx(
        -10.0
    )

    assert portfolio.cash == pytest.approx(
        9990.0
    )

    assert portfolio.realized_pnl == pytest.approx(
        -10.0
    )

    assert portfolio.is_flat is True
    
def test_gap_through_stop_uses_real_open_before_costs():
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
    # 1. OPEN LONG
    # -------------------------------------------------

    entry_time = utc_time(10, 15)

    entry_bar = MarketBar(
        time=entry_time,
        open=1.1600,
        high=1.1600,
        low=1.1600,
        close=1.1600,
        tick_volume=1000,
    )

    entry_order = Order(
        order_id="ORD-GAP-ENTRY",
        signal_id="SIG-GAP-ENTRY",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.MARKET,
        created_at=entry_time,
        scheduled_for=entry_time,
        status=OrderStatus.PENDING,
        stop_loss=1.1500,
        take_profit=1.1700,
    )

    entry_result = execution.execute(
        entry_order,
        event=make_open_event(
            entry_time,
            bar_index=1,
        ),
        bar=entry_bar,
    )

    portfolio.apply_execution(
        entry_result
    )

    position = portfolio.current_position

    assert position is not None

    # BUY:
    #
    # reference      = 1.16000
    # half spread    = 0.00010
    # slippage       = 0.00005
    #
    # execution      = 1.16015
    assert position.entry_price == pytest.approx(
        1.16015
    )

    # -------------------------------------------------
    # 2. GAP THROUGH STOP
    # -------------------------------------------------

    gap_bar = MarketBar(
        time=utc_time(10, 30),
        open=1.1450,
        high=1.1500,
        low=1.1400,
        close=1.1480,
        tick_volume=1200,
    )

    decision = ProtectiveExitEvaluator(
        config
    ).evaluate(
        position,
        gap_bar,
    )

    assert decision is not None

    assert (
        decision.exit_reason
        == ExitReason.STOP_LOSS
    )

    assert decision.triggered_at_open is True

    # Critical regression:
    #
    # Stop was 1.1500, but market actually opened
    # at 1.1450.
    #
    # The simulator must NOT pretend 1.1500 was
    # available.
    assert decision.reference_price == pytest.approx(
        1.1450
    )

    # -------------------------------------------------
    # 3. COST MODEL STARTS FROM REAL GAP OPEN
    # -------------------------------------------------

    exit_order = ProtectiveExitOrderFactory(
        config
    ).create(
        position,
        decision,
        execution_time=gap_bar.time,
    )

    exit_result = execution.execute_protective(
        exit_order,
        decision=decision,
        bar=gap_bar,
        fill_time=gap_bar.time,
    )

    assert exit_result.fill.reference_price == pytest.approx(
        1.1450
    )

    # SELL:
    #
    # reference      = 1.14500
    # half spread    = 0.00010
    # slippage       = 0.00005
    #
    # execution      = 1.14485
    assert exit_result.fill.execution_price == pytest.approx(
        1.14485
    )

    close_result = portfolio.apply_execution(
        exit_result,
        exit_reason=decision.exit_reason,
    )

    assert close_result is not None

    assert close_result.exit_price == pytest.approx(
        1.14485
    )

    # -------------------------------------------------
    # 4. ACCOUNTING REGRESSION
    # -------------------------------------------------

    # Entry execution = 1.16015
    # Exit execution  = 1.14485
    #
    # Difference:
    # -0.01530
    #
    # -0.01530 * 100000 * 0.01
    # = -15.30 gross PnL
    assert close_result.gross_pnl == pytest.approx(
        -15.30
    )

    # Commission:
    #
    # 3.50 * 0.01 = 0.035 per side
    #
    # total = 0.07
    assert close_result.commission == pytest.approx(
        0.07
    )

    assert close_result.net_pnl == pytest.approx(
        -15.37
    )

    assert portfolio.cash == pytest.approx(
        9984.63
    )

    assert portfolio.realized_pnl == pytest.approx(
        -15.37
    )

    assert portfolio.is_flat is True