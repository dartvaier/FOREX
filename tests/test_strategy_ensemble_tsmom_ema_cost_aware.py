from datetime import datetime, timedelta, timezone

import pytest

from alpha.ledger import AlphaLedger
from backtest.context import BacktestContext
from backtest.models import MarketBar, SignalAction
from backtest.models.enums import SimulationPhase
from research.runner import (
    STRATEGY_REGISTRY,
    coerce_strategy_params,
    discover_strategy_class,
)
from strategy import TsmomEmaCostAwareEnsembleStrategy


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


def make_bar(
    index: int,
    close: float,
) -> MarketBar:
    return MarketBar(
        time=utc_time(10)
        + timedelta(minutes=index * 15),
        open=close,
        high=close,
        low=close,
        close=close,
        tick_volume=1000,
    )


def make_context(
    closes: list[float],
) -> BacktestContext:
    bars = tuple(
        make_bar(index, close)
        for index, close in enumerate(closes)
    )
    current_index = len(bars) - 1

    return BacktestContext(
        current_time=(
            utc_time(10)
            + timedelta(
                minutes=(current_index + 1) * 15
            )
        ),
        phase=SimulationPhase.BAR_CLOSE,
        current_bar_index=current_index,
        current_bar=bars[-1],
        closed_bars=bars,
    )


def test_cost_aware_ensemble_validates_parameters():
    with pytest.raises(ValueError, match="pip_size"):
        TsmomEmaCostAwareEnsembleStrategy(
            symbol="EURUSD",
            pip_size=0.0,
        )

    with pytest.raises(ValueError, match="cost_estimate_pips"):
        TsmomEmaCostAwareEnsembleStrategy(
            symbol="EURUSD",
            cost_estimate_pips=-0.1,
        )

    with pytest.raises(ValueError, match="cost_safety_factor"):
        TsmomEmaCostAwareEnsembleStrategy(
            symbol="EURUSD",
            cost_safety_factor=0.0,
        )


def test_cost_aware_ensemble_exposes_default_cost_hurdle():
    strategy = TsmomEmaCostAwareEnsembleStrategy(
        symbol="EURUSD",
    )

    assert strategy.strategy_id == "ENSEMBLE-TSMOM-EMA-COST-AWARE"
    assert strategy.cost_estimate_pips == 3.7
    assert strategy.cost_safety_factor == 1.0


def test_cost_aware_ensemble_enters_when_expected_move_clears_cost():
    ledger = AlphaLedger()
    strategy = TsmomEmaCostAwareEnsembleStrategy(
        symbol="EURUSD",
        tsmom_lookback=3,
        tsmom_score_scale=0.02,
        ema_fast_period=2,
        ema_slow_period=4,
        ema_score_scale=1.0,
        cost_estimate_pips=0.1,
        min_conviction=0.1,
        enter_long=0.25,
        enter_short=-0.25,
        alpha_ledger=ledger,
    )

    signal = strategy.on_bar(
        make_context(
            [
                10.0,
                10.0,
                10.0,
                10.0,
                12.0,
            ]
        )
    )

    assert signal.action == SignalAction.ENTER_LONG
    assert ledger.count == 2
    assert all(
        record.metadata["cost_gate_allowed"] is True
        for record in ledger.records
    )


def test_cost_aware_ensemble_holds_when_all_models_fail_cost_gate():
    ledger = AlphaLedger()
    strategy = TsmomEmaCostAwareEnsembleStrategy(
        symbol="EURUSD",
        tsmom_lookback=3,
        tsmom_score_scale=0.02,
        ema_fast_period=2,
        ema_slow_period=4,
        ema_score_scale=1.0,
        cost_estimate_pips=1_000_000.0,
        min_conviction=0.1,
        enter_long=0.25,
        enter_short=-0.25,
        alpha_ledger=ledger,
    )

    signal = strategy.on_bar(
        make_context(
            [
                10.0,
                10.0,
                10.0,
                10.0,
                12.0,
            ]
        )
    )

    assert signal.action == SignalAction.HOLD
    assert signal.reason == "All alpha models abstained"
    assert signal.metadata["blended_abstained"] is True
    assert ledger.count == 2
    assert all(
        record.abstained is True
        for record in ledger.records
    )
    assert all(
        record.reason
        == (
            "Cost gate blocked: Expected move does not exceed "
            "estimated cost"
        )
        for record in ledger.records
    )


def test_research_runner_discovers_cost_aware_ensemble():
    strategy_class = discover_strategy_class(
        STRATEGY_REGISTRY["ensemble_tsmom_ema_cost_aware"]
    )

    assert strategy_class is TsmomEmaCostAwareEnsembleStrategy


def test_research_runner_coerces_cost_aware_params():
    params = coerce_strategy_params(
        TsmomEmaCostAwareEnsembleStrategy,
        {
            "cost_estimate_pips": "4.2",
            "cost_safety_factor": "1.2",
            "pip_size": "0.01",
            "tsmom_lookback": "12",
        },
    )

    assert params == {
        "cost_estimate_pips": 4.2,
        "cost_safety_factor": 1.2,
        "pip_size": 0.01,
        "tsmom_lookback": 12,
    }
