from datetime import datetime, timezone

from backtest.models import (
    InstrumentSpecification,
    Position,
    PositionSide,
)
from backtest.models.enums import (
    ExitReason,
    SimulationPhase,
)
from backtest.portfolio import PositionCloseResult
from backtest.trade_factory import TradeFactory


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


def test_weekend_gap_does_not_create_fictitious_bars_held():
    entry_time = datetime(
        2026,
        8,
        7,
        21,
        45,
        tzinfo=timezone.utc,
    )

    exit_time = datetime(
        2026,
        8,
        9,
        22,
        0,
        tzinfo=timezone.utc,
    )

    position = Position(
        position_id="POS-GAP",
        entry_fill_id="FILL-ENTRY-GAP",
        symbol="EURUSD",
        side=PositionSide.LONG,
        quantity=0.01,
        entry_time=entry_time,
        entry_price=1.1600,
        stop_loss=None,
        take_profit=None,
        unrealized_pnl=0.0,
        metadata={
            "strategy_id": "REGRESSION-GAP",
            "entry_order_id": "ORD-ENTRY-GAP",
            "entry_commission": 0.0,
            "entry_spread_impact": 0.0,
            "entry_slippage": 0.0,
        },
    )

    close_result = PositionCloseResult(
        position=position,
        exit_order_id="ORD-EXIT-GAP",
        exit_fill_id="FILL-EXIT-GAP",
        exit_time=exit_time,
        exit_price=1.1610,
        gross_pnl=1.0,
        net_pnl=1.0,
        commission=0.0,
        entry_spread_impact=0.0,
        entry_slippage=0.0,
        exit_spread_impact=0.0,
        exit_slippage=0.0,
        exit_reason=ExitReason.STRATEGY_EXIT,
    )

    trade = TradeFactory(
        make_instrument()
    ).create_from_bar_indexes(
        close_result,
        entry_bar_index=100,
        exit_bar_index=101,
        exit_phase=SimulationPhase.BAR_OPEN,
    )

    # Although more than two days passed on the wall clock,
    # only one observed bar separated entry and exit.
    assert trade.bars_held == 1

    assert trade.entry_time == entry_time
    assert trade.exit_time == exit_time