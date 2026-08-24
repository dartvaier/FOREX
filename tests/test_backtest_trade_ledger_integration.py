from datetime import datetime, timezone

import pytest

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


def make_close_result() -> PositionCloseResult:
    position = Position(
        position_id="POS-001",
        entry_fill_id="FILL-ENTRY",
        symbol="EURUSD",
        side=PositionSide.LONG,
        quantity=0.01,
        entry_time=utc_time(10, 15),
        entry_price=1.16015,
        stop_loss=1.1500,
        take_profit=1.1700,
        unrealized_pnl=0.0,
        metadata={
            "strategy_id": "TEST-STRATEGY",
            "entry_order_id": "ORD-ENTRY",
            "entry_commission": 0.35,
            "entry_spread_impact": 0.00010,
            "entry_slippage": 0.00005,
        },
    )

    return PositionCloseResult(
        position=position,
        exit_order_id="ORD-EXIT",
        exit_fill_id="FILL-EXIT",
        exit_time=utc_time(11, 0),
        exit_price=1.16985,
        gross_pnl=9.70,
        net_pnl=9.00,
        commission=0.70,
        entry_spread_impact=0.00010,
        entry_slippage=0.00005,
        exit_spread_impact=0.00010,
        exit_slippage=0.00005,
        exit_reason=ExitReason.TAKE_PROFIT,
    )


def test_completed_position_becomes_ledger_trade():
    instrument = make_instrument()

    factory = TradeFactory(
        instrument
    )

    ledger = TradeLedger()

    close_result = make_close_result()

    trade = factory.create_from_bar_indexes(
        close_result,
        entry_bar_index=10,
        exit_bar_index=13,
        exit_phase=SimulationPhase.BAR_OPEN,
    )

    ledger.append(trade)

    assert ledger.count == 1
    assert ledger.last_trade is trade

    stored = ledger.get(
        trade.trade_id
    )

    assert stored is not None

    assert stored.position_id == "POS-001"
    assert stored.strategy_id == "TEST-STRATEGY"

    assert stored.entry_fill_id == "FILL-ENTRY"
    assert stored.exit_fill_id == "FILL-EXIT"

    assert stored.bars_held == 3

    assert stored.gross_pnl == pytest.approx(
        9.70
    )

    assert stored.net_pnl == pytest.approx(
        9.00
    )

    assert stored.spread_cost == pytest.approx(
        0.20
    )

    assert stored.slippage_cost == pytest.approx(
        0.10
    )

    assert stored.commission == pytest.approx(
        0.70
    )

    assert (
        stored.exit_reason
        == ExitReason.TAKE_PROFIT
    )


def test_trade_ledger_does_not_change_trade_accounting():
    instrument = make_instrument()

    factory = TradeFactory(
        instrument
    )

    trade = factory.create_from_bar_indexes(
        make_close_result(),
        entry_bar_index=10,
        exit_bar_index=13,
        exit_phase=SimulationPhase.BAR_OPEN,
    )

    original_net_pnl = trade.net_pnl
    original_spread_cost = trade.spread_cost
    original_slippage_cost = trade.slippage_cost

    ledger = TradeLedger()
    ledger.append(trade)

    stored = ledger.last_trade

    assert stored is not None

    # Ledger stores the immutable Trade.
    # It does not recalculate accounting.
    assert stored is trade

    assert stored.net_pnl == pytest.approx(
        original_net_pnl
    )

    assert stored.spread_cost == pytest.approx(
        original_spread_cost
    )

    assert stored.slippage_cost == pytest.approx(
        original_slippage_cost
    )