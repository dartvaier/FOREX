from datetime import datetime, timezone

import pytest

from backtest.models import (
    BacktestConfig,
    MarketBar,
    Position,
    PositionSide,
    Timeframe,
)
from backtest.models.enums import ExitReason
from backtest.protective_exit import ProtectiveExitEvaluator


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
        date_from=utc_time(10, 0),
        date_to=utc_time(12, 0),
        initial_capital=10000.0,
    )


def make_position(
    side: PositionSide,
    *,
    entry_price: float = 1.1600,
    stop_loss: float | None = None,
    take_profit: float | None = None,
) -> Position:
    return Position(
        position_id="POS-001",
        entry_fill_id="FILL-001",
        symbol="EURUSD",
        side=side,
        quantity=0.01,
        entry_time=utc_time(10, 0),
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        unrealized_pnl=0.0,
    )


def make_bar(
    *,
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> MarketBar:
    return MarketBar(
        time=utc_time(10, 15),
        open=open_price,
        high=high,
        low=low,
        close=close,
        tick_volume=1000,
    )


def test_long_stop_loss_is_triggered():
    evaluator = ProtectiveExitEvaluator(
        make_config()
    )

    position = make_position(
        PositionSide.LONG,
        stop_loss=1.1500,
        take_profit=1.1700,
    )

    bar = make_bar(
        open_price=1.1600,
        high=1.1650,
        low=1.1490,
        close=1.1550,
    )

    decision = evaluator.evaluate(
        position,
        bar,
    )

    assert decision is not None
    assert decision.exit_reason == ExitReason.STOP_LOSS
    assert decision.reference_price == pytest.approx(1.1500)
    assert decision.triggered_at_open is False
    assert decision.ambiguous is False


def test_long_take_profit_is_triggered():
    evaluator = ProtectiveExitEvaluator(
        make_config()
    )

    position = make_position(
        PositionSide.LONG,
        stop_loss=1.1500,
        take_profit=1.1700,
    )

    bar = make_bar(
        open_price=1.1600,
        high=1.1720,
        low=1.1580,
        close=1.1680,
    )

    decision = evaluator.evaluate(
        position,
        bar,
    )

    assert decision is not None
    assert decision.exit_reason == ExitReason.TAKE_PROFIT
    assert decision.reference_price == pytest.approx(1.1700)
    assert decision.triggered_at_open is False
    assert decision.ambiguous is False


def test_short_stop_loss_is_triggered():
    evaluator = ProtectiveExitEvaluator(
        make_config()
    )

    position = make_position(
        PositionSide.SHORT,
        stop_loss=1.1700,
        take_profit=1.1500,
    )

    bar = make_bar(
        open_price=1.1600,
        high=1.1720,
        low=1.1550,
        close=1.1650,
    )

    decision = evaluator.evaluate(
        position,
        bar,
    )

    assert decision is not None
    assert decision.exit_reason == ExitReason.STOP_LOSS
    assert decision.reference_price == pytest.approx(1.1700)
    assert decision.triggered_at_open is False
    assert decision.ambiguous is False


def test_short_take_profit_is_triggered():
    evaluator = ProtectiveExitEvaluator(
        make_config()
    )

    position = make_position(
        PositionSide.SHORT,
        stop_loss=1.1700,
        take_profit=1.1500,
    )

    bar = make_bar(
        open_price=1.1600,
        high=1.1650,
        low=1.1480,
        close=1.1520,
    )

    decision = evaluator.evaluate(
        position,
        bar,
    )

    assert decision is not None
    assert decision.exit_reason == ExitReason.TAKE_PROFIT
    assert decision.reference_price == pytest.approx(1.1500)
    assert decision.triggered_at_open is False
    assert decision.ambiguous is False


def test_long_gap_through_stop_uses_open_price():
    evaluator = ProtectiveExitEvaluator(
        make_config()
    )

    position = make_position(
        PositionSide.LONG,
        stop_loss=1.1500,
        take_profit=1.1700,
    )

    bar = make_bar(
        open_price=1.1450,
        high=1.1500,
        low=1.1400,
        close=1.1480,
    )

    decision = evaluator.evaluate(
        position,
        bar,
    )

    assert decision is not None
    assert decision.exit_reason == ExitReason.STOP_LOSS

    # Gap adverso:
    # não fingimos execução em 1.1500.
    assert decision.reference_price == pytest.approx(1.1450)
    assert decision.triggered_at_open is True
    assert decision.ambiguous is False


def test_short_gap_through_stop_uses_open_price():
    evaluator = ProtectiveExitEvaluator(
        make_config()
    )

    position = make_position(
        PositionSide.SHORT,
        stop_loss=1.1700,
        take_profit=1.1500,
    )

    bar = make_bar(
        open_price=1.1750,
        high=1.1800,
        low=1.1720,
        close=1.1780,
    )

    decision = evaluator.evaluate(
        position,
        bar,
    )

    assert decision is not None
    assert decision.exit_reason == ExitReason.STOP_LOSS
    assert decision.reference_price == pytest.approx(1.1750)
    assert decision.triggered_at_open is True
    assert decision.ambiguous is False


def test_long_ambiguous_bar_uses_worst_case_stop():
    evaluator = ProtectiveExitEvaluator(
        make_config()
    )

    position = make_position(
        PositionSide.LONG,
        stop_loss=1.1500,
        take_profit=1.1700,
    )

    bar = make_bar(
        open_price=1.1600,
        high=1.1720,
        low=1.1480,
        close=1.1610,
    )

    decision = evaluator.evaluate(
        position,
        bar,
    )

    assert decision is not None

    # High tocou target e low tocou stop.
    # Como não conhecemos o caminho intrabar:
    # WORST_CASE -> STOP_LOSS.
    assert decision.exit_reason == ExitReason.STOP_LOSS
    assert decision.reference_price == pytest.approx(1.1500)
    assert decision.ambiguous is True


def test_short_ambiguous_bar_uses_worst_case_stop():
    evaluator = ProtectiveExitEvaluator(
        make_config()
    )

    position = make_position(
        PositionSide.SHORT,
        stop_loss=1.1700,
        take_profit=1.1500,
    )

    bar = make_bar(
        open_price=1.1600,
        high=1.1720,
        low=1.1480,
        close=1.1590,
    )

    decision = evaluator.evaluate(
        position,
        bar,
    )

    assert decision is not None
    assert decision.exit_reason == ExitReason.STOP_LOSS
    assert decision.reference_price == pytest.approx(1.1700)
    assert decision.ambiguous is True


def test_no_protective_level_hit_returns_none():
    evaluator = ProtectiveExitEvaluator(
        make_config()
    )

    position = make_position(
        PositionSide.LONG,
        stop_loss=1.1500,
        take_profit=1.1700,
    )

    bar = make_bar(
        open_price=1.1600,
        high=1.1650,
        low=1.1550,
        close=1.1620,
    )

    assert evaluator.evaluate(
        position,
        bar,
    ) is None


def test_position_without_stop_or_target_returns_none():
    evaluator = ProtectiveExitEvaluator(
        make_config()
    )

    position = make_position(
        PositionSide.LONG,
    )

    bar = make_bar(
        open_price=1.1600,
        high=1.1800,
        low=1.1400,
        close=1.1600,
    )

    assert evaluator.evaluate(
        position,
        bar,
    ) is None

def test_long_gap_through_take_profit_uses_target_price():
    evaluator = ProtectiveExitEvaluator(
        make_config()
    )

    position = make_position(
        PositionSide.LONG,
        stop_loss=1.1500,
        take_profit=1.1700,
    )

    bar = make_bar(
        open_price=1.1750,
        high=1.1800,
        low=1.1730,
        close=1.1780,
    )

    decision = evaluator.evaluate(
        position,
        bar,
    )

    assert decision is not None
    assert decision.exit_reason == ExitReason.TAKE_PROFIT

    # Gap favorável acima do target.
    #
    # Baseline conservador:
    # não concedemos melhoria para 1.1750.
    assert decision.reference_price == pytest.approx(
        1.1700
    )

    assert decision.triggered_at_open is True
    assert decision.ambiguous is False


def test_short_gap_through_take_profit_uses_target_price():
    evaluator = ProtectiveExitEvaluator(
        make_config()
    )

    position = make_position(
        PositionSide.SHORT,
        stop_loss=1.1700,
        take_profit=1.1500,
    )

    bar = make_bar(
        open_price=1.1450,
        high=1.1480,
        low=1.1400,
        close=1.1420,
    )

    decision = evaluator.evaluate(
        position,
        bar,
    )

    assert decision is not None
    assert decision.exit_reason == ExitReason.TAKE_PROFIT

    # Gap favorável abaixo do target.
    #
    # Mesmo assim usamos o target configurado.
    assert decision.reference_price == pytest.approx(
        1.1500
    )

    assert decision.triggered_at_open is True
    assert decision.ambiguous is False