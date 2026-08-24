from datetime import datetime, timezone

from backtest.context import BacktestContext
from backtest.models import (
    MarketBar,
    Signal,
    SignalAction,
)
from backtest.models.enums import SimulationPhase
from backtest.strategy import Strategy


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


def make_closed_context() -> BacktestContext:
    bar = MarketBar(
        time=utc_time(10, 0),
        open=1.1600,
        high=1.1620,
        low=1.1590,
        close=1.1610,
        tick_volume=1000,
    )

    return BacktestContext(
        current_time=utc_time(10, 15),
        phase=SimulationPhase.BAR_CLOSE,
        current_bar_index=0,
        current_bar=bar,
        closed_bars=(bar,),
    )


class DummyHoldStrategy:
    @property
    def strategy_id(self) -> str:
        return "DUMMY-HOLD"

    def on_bar(
        self,
        context: BacktestContext,
    ) -> Signal:
        return Signal(
            signal_id="SIG-001",
            strategy_id=self.strategy_id,
            symbol="EURUSD",
            timestamp=context.current_time,
            action=SignalAction.HOLD,
            reason="No trading condition",
        )


class DummyLongStrategy:
    @property
    def strategy_id(self) -> str:
        return "DUMMY-LONG"

    def on_bar(
        self,
        context: BacktestContext,
    ) -> Signal:
        return Signal(
            signal_id="SIG-002",
            strategy_id=self.strategy_id,
            symbol="EURUSD",
            timestamp=context.current_time,
            action=SignalAction.ENTER_LONG,
            reason="Synthetic test signal",
        )


class MissingOnBar:
    @property
    def strategy_id(self) -> str:
        return "INVALID"


class MissingStrategyId:
    def on_bar(
        self,
        context: BacktestContext,
    ) -> Signal:
        return Signal(
            signal_id="SIG-INVALID",
            strategy_id="INVALID",
            symbol="EURUSD",
            timestamp=context.current_time,
            action=SignalAction.HOLD,
        )


def test_strategy_protocol_supports_structural_typing():
    strategy = DummyHoldStrategy()

    assert isinstance(
        strategy,
        Strategy,
    )


def test_strategy_does_not_require_explicit_inheritance():
    strategy = DummyLongStrategy()

    assert isinstance(
        strategy,
        Strategy,
    )


def test_strategy_protocol_rejects_missing_on_bar():
    strategy = MissingOnBar()

    assert not isinstance(
        strategy,
        Strategy,
    )


def test_strategy_protocol_rejects_missing_strategy_id():
    strategy = MissingStrategyId()

    assert not isinstance(
        strategy,
        Strategy,
    )


def test_strategy_exposes_stable_strategy_id():
    strategy = DummyHoldStrategy()

    assert strategy.strategy_id == "DUMMY-HOLD"


def test_strategy_returns_signal():
    strategy = DummyLongStrategy()

    signal = strategy.on_bar(
        make_closed_context()
    )

    assert isinstance(
        signal,
        Signal,
    )


def test_strategy_can_explicitly_return_hold():
    strategy = DummyHoldStrategy()

    signal = strategy.on_bar(
        make_closed_context()
    )

    assert signal.action == SignalAction.HOLD


def test_strategy_signal_uses_context_time():
    context = make_closed_context()

    signal = DummyLongStrategy().on_bar(
        context
    )

    assert signal.timestamp == context.current_time


def test_strategy_signal_preserves_strategy_identity():
    strategy = DummyLongStrategy()

    signal = strategy.on_bar(
        make_closed_context()
    )

    assert (
        signal.strategy_id
        == strategy.strategy_id
    )


def test_strategy_receives_only_context_interface():
    context = make_closed_context()

    signal = DummyHoldStrategy().on_bar(
        context
    )

    assert signal.action == SignalAction.HOLD

    assert not hasattr(context, "dataframe")
    assert not hasattr(context, "feed")
    assert not hasattr(context, "future_bars")