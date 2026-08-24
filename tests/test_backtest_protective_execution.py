from datetime import datetime, timezone

import pytest

from backtest.costs import (
    FixedCostModel,
    ZeroCostModel,
)
from backtest.execution import SimulatedExecution
from backtest.models import (
    BacktestConfig,
    InstrumentSpecification,
    MarketBar,
    Position,
    PositionSide,
    Timeframe,
)
from backtest.models.enums import ExitReason
from backtest.protective_exit import (
    ProtectiveExitDecision,
)
from backtest.protective_order import (
    ProtectiveExitOrderFactory,
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


def make_position() -> Position:
    return Position(
        position_id="POS-001",
        entry_fill_id="FILL-ENTRY",
        symbol="EURUSD",
        side=PositionSide.LONG,
        quantity=0.10,
        entry_time=utc_time(10),
        entry_price=1.1600,
        stop_loss=1.1500,
        take_profit=1.1700,
        unrealized_pnl=0.0,
    )


def make_bar() -> MarketBar:
    return MarketBar(
        time=utc_time(10, 15),
        open=1.1600,
        high=1.1650,
        low=1.1490,
        close=1.1550,
        tick_volume=1000,
    )


def test_intrabar_stop_uses_decision_reference_price():
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

    decision = ProtectiveExitDecision(
        position_id="POS-001",
        bar_time=utc_time(10, 15),
        exit_reason=ExitReason.STOP_LOSS,
        reference_price=1.1500,
        triggered_at_open=False,
        ambiguous=False,
    )

    fill_time = utc_time(10, 30)

    order = ProtectiveExitOrderFactory(
        config
    ).create(
        make_position(),
        decision,
        execution_time=fill_time,
    )

    result = execution.execute_protective(
        order,
        decision=decision,
        bar=make_bar(),
        fill_time=fill_time,
    )

    assert result.fill.reference_price == pytest.approx(
        1.1500
    )

    # SELL:
    # 1 pip half spread + 0.5 pip slippage.
    assert result.fill.execution_price == pytest.approx(
        1.14985
    )

    assert result.fill.fill_time == utc_time(
        10,
        30,
    )

    assert result.fill.commission == pytest.approx(
        0.35
    )


def test_gap_stop_fills_at_bar_open():
    config = make_config()
    instrument = make_instrument()

    execution = SimulatedExecution(
        config=config,
        cost_model=ZeroCostModel(
            instrument=instrument
        ),
    )

    bar = MarketBar(
        time=utc_time(10, 15),
        open=1.1450,
        high=1.1500,
        low=1.1400,
        close=1.1480,
        tick_volume=1000,
    )

    decision = ProtectiveExitDecision(
        position_id="POS-001",
        bar_time=bar.time,
        exit_reason=ExitReason.STOP_LOSS,
        reference_price=1.1450,
        triggered_at_open=True,
        ambiguous=False,
    )

    order = ProtectiveExitOrderFactory(
        config
    ).create(
        make_position(),
        decision,
        execution_time=bar.time,
    )

    result = execution.execute_protective(
        order,
        decision=decision,
        bar=bar,
        fill_time=bar.time,
    )

    assert result.fill.reference_price == pytest.approx(
        1.1450
    )

    assert result.fill.execution_price == pytest.approx(
        1.1450
    )

    assert result.fill.fill_time == bar.time


def test_open_trigger_cannot_be_delayed_to_bar_close():
    config = make_config()
    instrument = make_instrument()

    execution = SimulatedExecution(
        config=config,
        cost_model=ZeroCostModel(
            instrument=instrument
        ),
    )

    bar = make_bar()

    decision = ProtectiveExitDecision(
        position_id="POS-001",
        bar_time=bar.time,
        exit_reason=ExitReason.STOP_LOSS,
        reference_price=1.1450,
        triggered_at_open=True,
        ambiguous=False,
    )

    fill_time = utc_time(10, 30)

    order = ProtectiveExitOrderFactory(
        config
    ).create(
        make_position(),
        decision,
        execution_time=fill_time,
    )

    with pytest.raises(
        ValueError,
        match="BAR_OPEN",
    ):
        execution.execute_protective(
            order,
            decision=decision,
            bar=bar,
            fill_time=fill_time,
        )