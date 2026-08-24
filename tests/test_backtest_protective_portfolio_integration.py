from datetime import datetime, timedelta, timezone

import pytest

from backtest.clock import ClockEvent
from backtest.costs import ZeroCostModel
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


def make_execution(
    instrument: InstrumentSpecification,
) -> SimulatedExecution:
    return SimulatedExecution(
        config=make_config(),
        cost_model=ZeroCostModel(
            instrument=instrument,
        ),
    )


def open_long_position(
    *,
    execution: SimulatedExecution,
    portfolio: Portfolio,
):
    timestamp = utc_time(10, 15)

    bar = MarketBar(
        time=timestamp,
        open=1.1600,
        high=1.1600,
        low=1.1600,
        close=1.1600,
        tick_volume=1000,
    )

    order = Order(
        order_id="ORD-ENTRY-LONG",
        signal_id="SIG-ENTRY-LONG",
        symbol="EURUSD",
        side=OrderSide.BUY,
        quantity=0.01,
        order_type=OrderType.MARKET,
        created_at=timestamp,
        scheduled_for=timestamp,
        status=OrderStatus.PENDING,
        stop_loss=1.1500,
        take_profit=1.1700,
    )

    result = execution.execute(
        order,
        event=make_open_event(
            timestamp,
            bar_index=1,
        ),
        bar=bar,
    )

    portfolio.apply_execution(result)

    return portfolio.current_position


def test_intrabar_stop_closes_long_position():
    config = make_config()
    instrument = make_instrument()

    execution = make_execution(
        instrument
    )

    portfolio = Portfolio(
        config=config,
        instrument=instrument,
    )

    position = open_long_position(
        execution=execution,
        portfolio=portfolio,
    )

    assert position is not None

    bar = MarketBar(
        time=utc_time(10, 30),
        open=1.1600,
        high=1.1650,
        low=1.1490,
        close=1.1550,
        tick_volume=1200,
    )

    evaluator = ProtectiveExitEvaluator(
        config
    )

    decision = evaluator.evaluate(
        position,
        bar,
    )

    assert decision is not None
    assert (
        decision.exit_reason
        == ExitReason.STOP_LOSS
    )

    fill_time = utc_time(10, 45)

    order = ProtectiveExitOrderFactory(
        config
    ).create(
        position,
        decision,
        execution_time=fill_time,
    )

    result = execution.execute_protective(
        order,
        decision=decision,
        bar=bar,
        fill_time=fill_time,
    )

    close_result = portfolio.apply_execution(
        result,
        exit_reason=decision.exit_reason,
    )

    assert close_result is not None

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

    assert portfolio.is_flat is True

    assert portfolio.cash == pytest.approx(
        9990.0
    )

    assert portfolio.realized_pnl == pytest.approx(
        -10.0
    )


def test_intrabar_take_profit_closes_long_position():
    config = make_config()
    instrument = make_instrument()

    execution = make_execution(
        instrument
    )

    portfolio = Portfolio(
        config=config,
        instrument=instrument,
    )

    position = open_long_position(
        execution=execution,
        portfolio=portfolio,
    )

    assert position is not None

    bar = MarketBar(
        time=utc_time(10, 30),
        open=1.1600,
        high=1.1720,
        low=1.1580,
        close=1.1680,
        tick_volume=1200,
    )

    decision = ProtectiveExitEvaluator(
        config
    ).evaluate(
        position,
        bar,
    )

    assert decision is not None

    assert (
        decision.exit_reason
        == ExitReason.TAKE_PROFIT
    )

    fill_time = utc_time(10, 45)

    order = ProtectiveExitOrderFactory(
        config
    ).create(
        position,
        decision,
        execution_time=fill_time,
    )

    result = execution.execute_protective(
        order,
        decision=decision,
        bar=bar,
        fill_time=fill_time,
    )

    close_result = portfolio.apply_execution(
        result,
        exit_reason=decision.exit_reason,
    )

    assert close_result is not None

    assert (
        close_result.exit_reason
        == ExitReason.TAKE_PROFIT
    )

    assert close_result.exit_price == pytest.approx(
        1.1700
    )

    assert close_result.gross_pnl == pytest.approx(
        10.0
    )

    assert close_result.net_pnl == pytest.approx(
        10.0
    )

    assert portfolio.is_flat is True

    assert portfolio.cash == pytest.approx(
        10010.0
    )
def open_short_position(
    *,
    execution: SimulatedExecution,
    portfolio: Portfolio,
):
    timestamp = utc_time(10, 15)

    bar = MarketBar(
        time=timestamp,
        open=1.1600,
        high=1.1600,
        low=1.1600,
        close=1.1600,
        tick_volume=1000,
    )

    order = Order(
        order_id="ORD-ENTRY-SHORT",
        signal_id="SIG-ENTRY-SHORT",
        symbol="EURUSD",
        side=OrderSide.SELL,
        quantity=0.01,
        order_type=OrderType.MARKET,
        created_at=timestamp,
        scheduled_for=timestamp,
        status=OrderStatus.PENDING,
        stop_loss=1.1700,
        take_profit=1.1500,
    )

    result = execution.execute(
        order,
        event=make_open_event(
            timestamp,
            bar_index=1,
        ),
        bar=bar,
    )

    portfolio.apply_execution(result)

    return portfolio.current_position

def test_long_gap_through_stop_closes_at_available_open():
    config = make_config()
    instrument = make_instrument()

    execution = make_execution(
        instrument
    )

    portfolio = Portfolio(
        config=config,
        instrument=instrument,
    )

    position = open_long_position(
        execution=execution,
        portfolio=portfolio,
    )

    assert position is not None

    # Stop configurado = 1.1500
    #
    # A próxima barra abre em 1.1450.
    # Portanto não podemos fingir execução em 1.1500.
    bar = MarketBar(
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
        bar,
    )

    assert decision is not None
    assert (
        decision.exit_reason
        == ExitReason.STOP_LOSS
    )

    assert decision.triggered_at_open is True

    assert decision.reference_price == pytest.approx(
        1.1450
    )

    # Como o gap já existe no OPEN,
    # a ordem protetiva é criada e executada
    # naquele mesmo timestamp.
    order = ProtectiveExitOrderFactory(
        config
    ).create(
        position,
        decision,
        execution_time=bar.time,
    )

    result = execution.execute_protective(
        order,
        decision=decision,
        bar=bar,
        fill_time=bar.time,
    )

    close_result = portfolio.apply_execution(
        result,
        exit_reason=decision.exit_reason,
    )

    assert close_result is not None

    assert close_result.exit_reason == (
        ExitReason.STOP_LOSS
    )

    assert close_result.exit_time == bar.time

    assert close_result.exit_price == pytest.approx(
        1.1450
    )

    # LONG:
    #
    # entry = 1.1600
    # exit  = 1.1450
    #
    # -0.0150 * 100000 * 0.01
    # = -15.00
    assert close_result.gross_pnl == pytest.approx(
        -15.0
    )

    assert portfolio.realized_pnl == pytest.approx(
        -15.0
    )

    assert portfolio.cash == pytest.approx(
        9985.0
    )

    assert portfolio.is_flat is True


def test_short_gap_through_stop_closes_at_available_open():
    config = make_config()
    instrument = make_instrument()

    execution = make_execution(
        instrument
    )

    portfolio = Portfolio(
        config=config,
        instrument=instrument,
    )

    position = open_short_position(
        execution=execution,
        portfolio=portfolio,
    )

    assert position is not None

    # SHORT stop = 1.1700
    #
    # Próxima barra abre acima dele em 1.1750.
    bar = MarketBar(
        time=utc_time(10, 30),
        open=1.1750,
        high=1.1800,
        low=1.1720,
        close=1.1780,
        tick_volume=1200,
    )

    decision = ProtectiveExitEvaluator(
        config
    ).evaluate(
        position,
        bar,
    )

    assert decision is not None

    assert (
        decision.exit_reason
        == ExitReason.STOP_LOSS
    )

    assert decision.triggered_at_open is True

    assert decision.reference_price == pytest.approx(
        1.1750
    )

    order = ProtectiveExitOrderFactory(
        config
    ).create(
        position,
        decision,
        execution_time=bar.time,
    )

    result = execution.execute_protective(
        order,
        decision=decision,
        bar=bar,
        fill_time=bar.time,
    )

    close_result = portfolio.apply_execution(
        result,
        exit_reason=decision.exit_reason,
    )

    assert close_result is not None

    assert close_result.exit_time == bar.time

    assert close_result.exit_price == pytest.approx(
        1.1750
    )

    # SHORT:
    #
    # entry = 1.1600
    # exit  = 1.1750
    #
    # (1.1600 - 1.1750)
    # * 100000 * 0.01
    # = -15.00
    assert close_result.gross_pnl == pytest.approx(
        -15.0
    )

    assert portfolio.realized_pnl == pytest.approx(
        -15.0
    )

    assert portfolio.cash == pytest.approx(
        9985.0
    )

    assert portfolio.is_flat is True