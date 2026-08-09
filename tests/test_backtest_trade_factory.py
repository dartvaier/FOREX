from datetime import datetime, timezone

from backtest.models.enums import (
    ExitReason,
    SimulationPhase,
)

import pytest

from backtest.models import (
    InstrumentSpecification,
    Position,
    PositionSide,
)
from backtest.models.enums import ExitReason
from backtest.portfolio import PositionCloseResult
from backtest.trade_factory import TradeFactory


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


def make_position(
    *,
    with_strategy: bool = True,
) -> Position:
    metadata = {
        "entry_order_id": "ORD-ENTRY",
        "entry_commission": 0.35,
        "entry_spread_impact": 0.00010,
        "entry_slippage": 0.00005,
    }

    if with_strategy:
        metadata["strategy_id"] = "TEST-STRATEGY"

    return Position(
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
        metadata=metadata,
    )


def make_close_result(
    *,
    position: Position | None = None,
) -> PositionCloseResult:
    return PositionCloseResult(
        position=(
            position
            if position is not None
            else make_position()
        ),
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


def test_trade_factory_creates_trade_from_close_result():
    trade = TradeFactory(
        make_instrument()
    ).create(
        make_close_result(),
        bars_held=3,
    )

    assert trade.trade_id == "TRADE-POS-001"
    assert trade.position_id == "POS-001"

    assert trade.strategy_id == "TEST-STRATEGY"
    assert trade.symbol == "EURUSD"
    assert trade.side == PositionSide.LONG

    assert trade.entry_fill_id == "FILL-ENTRY"
    assert trade.exit_fill_id == "FILL-EXIT"

    assert trade.entry_time == utc_time(10, 15)
    assert trade.exit_time == utc_time(11, 0)

    assert trade.entry_price == pytest.approx(
        1.16015
    )

    assert trade.exit_price == pytest.approx(
        1.16985
    )

    assert trade.quantity == pytest.approx(
        0.01
    )

    assert trade.gross_pnl == pytest.approx(
        9.70
    )

    assert trade.net_pnl == pytest.approx(
        9.00
    )

    assert trade.commission == pytest.approx(
        0.70
    )

    assert trade.bars_held == 3

    assert (
        trade.exit_reason
        == ExitReason.TAKE_PROFIT
    )


def test_trade_factory_converts_spread_to_money():
    trade = TradeFactory(
        make_instrument()
    ).create(
        make_close_result(),
        bars_held=3,
    )

    # 0.00010 + 0.00010
    # = 0.00020
    #
    # 0.00020 * 100000 * 0.01
    # = 0.20
    assert trade.spread_cost == pytest.approx(
        0.20
    )


def test_trade_factory_converts_slippage_to_money():
    trade = TradeFactory(
        make_instrument()
    ).create(
        make_close_result(),
        bars_held=3,
    )

    # 0.00005 + 0.00005
    # = 0.00010
    #
    # 0.00010 * 100000 * 0.01
    # = 0.10
    assert trade.slippage_cost == pytest.approx(
        0.10
    )


def test_trade_factory_does_not_recalculate_net_pnl():
    trade = TradeFactory(
        make_instrument()
    ).create(
        make_close_result(),
        bars_held=3,
    )

    # net_pnl comes from Portfolio accounting.
    #
    # TradeFactory must not subtract spread/slippage
    # again.
    assert trade.net_pnl == pytest.approx(
        9.00
    )


def test_trade_factory_preserves_order_identity():
    trade = TradeFactory(
        make_instrument()
    ).create(
        make_close_result(),
        bars_held=3,
    )

    assert (
        trade.metadata["entry_order_id"]
        == "ORD-ENTRY"
    )

    assert (
        trade.metadata["exit_order_id"]
        == "ORD-EXIT"
    )


def test_trade_factory_requires_strategy_id():
    position = make_position(
        with_strategy=False
    )

    close_result = make_close_result(
        position=position
    )

    with pytest.raises(
        ValueError,
        match="strategy_id",
    ):
        TradeFactory(
            make_instrument()
        ).create(
            close_result,
            bars_held=3,
        )


@pytest.mark.parametrize(
    "bars_held",
    [
        -1,
        True,
    ],
)
def test_trade_factory_rejects_invalid_bars_held(
    bars_held,
):
    with pytest.raises(
        ValueError,
        match="bars_held",
    ):
        TradeFactory(
            make_instrument()
        ).create(
            make_close_result(),
            bars_held=bars_held,
        )

def test_trade_factory_calculates_bars_held_from_bar_indexes():
    trade = TradeFactory(
        make_instrument()
    ).create_from_bar_indexes(
        make_close_result(),
        entry_bar_index=10,
        exit_bar_index=13,
        exit_phase=SimulationPhase.BAR_OPEN,
    )

    # Exposure occurred during bars:
    # 10, 11, 12
    assert trade.bars_held == 3


def test_trade_factory_counts_intrabar_exit_bar():
    trade = TradeFactory(
        make_instrument()
    ).create_from_bar_indexes(
        make_close_result(),
        entry_bar_index=10,
        exit_bar_index=11,
        exit_phase=SimulationPhase.BAR_CLOSE,
    )

    # Exposure:
    # bar 10
    # bar 11 until its close
    assert trade.bars_held == 2