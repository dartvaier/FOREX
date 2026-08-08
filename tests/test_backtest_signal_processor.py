from datetime import datetime, timezone

import pytest

from backtest.context import BacktestContext
from backtest.models import (
    BacktestConfig,
    MarketBar,
    Signal,
    SignalAction,
    Timeframe,
)
from backtest.models.enums import SimulationPhase
from backtest.signal_processor import SignalProcessor


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


def make_bar() -> MarketBar:
    return MarketBar(
        time=utc_time(10, 0),
        open=1.1600,
        high=1.1620,
        low=1.1590,
        close=1.1610,
        tick_volume=1000,
    )


def make_close_context() -> BacktestContext:
    bar = make_bar()

    return BacktestContext(
        current_time=utc_time(10, 15),
        phase=SimulationPhase.BAR_CLOSE,
        current_bar_index=0,
        current_bar=bar,
        closed_bars=(bar,),
    )


def make_open_context() -> BacktestContext:
    return BacktestContext(
        current_time=utc_time(10, 0),
        phase=SimulationPhase.BAR_OPEN,
        current_bar_index=0,
        current_bar=None,
        closed_bars=(),
    )


class ValidHoldStrategy:
    @property
    def strategy_id(self) -> str:
        return "VALID-HOLD"

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
        )


class ValidLongStrategy:
    @property
    def strategy_id(self) -> str:
        return "VALID-LONG"

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
        )


def test_signal_processor_is_created_with_config():
    config = make_config()

    processor = SignalProcessor(
        config=config,
    )

    assert processor.config is config


def test_signal_processor_requires_config():
    with pytest.raises(
        TypeError,
        match="BacktestConfig",
    ):
        SignalProcessor(
            config=None,  # type: ignore[arg-type]
        )


def test_signal_processor_returns_valid_signal():
    processor = SignalProcessor(
        config=make_config(),
    )

    context = make_close_context()

    signal = processor.process(
        strategy=ValidLongStrategy(),
        context=context,
    )

    assert isinstance(signal, Signal)

    assert signal.action == (
        SignalAction.ENTER_LONG
    )

    assert signal.timestamp == (
        context.current_time
    )


def test_signal_processor_accepts_hold_signal():
    processor = SignalProcessor(
        config=make_config(),
    )

    signal = processor.process(
        strategy=ValidHoldStrategy(),
        context=make_close_context(),
    )

    assert signal.action == SignalAction.HOLD


def test_signal_processor_requires_context():
    processor = SignalProcessor(
        config=make_config(),
    )

    with pytest.raises(
        TypeError,
        match="BacktestContext",
    ):
        processor.process(
            strategy=ValidHoldStrategy(),
            context=None,  # type: ignore[arg-type]
        )


def test_signal_processor_requires_strategy_protocol():
    processor = SignalProcessor(
        config=make_config(),
    )

    with pytest.raises(
        TypeError,
        match="Strategy protocol",
    ):
        processor.process(
            strategy=object(),  # type: ignore[arg-type]
            context=make_close_context(),
        )


def test_signal_processor_only_allows_bar_close():
    processor = SignalProcessor(
        config=make_config(),
    )

    with pytest.raises(
        ValueError,
        match="BAR_CLOSE",
    ):
        processor.process(
            strategy=ValidHoldStrategy(),
            context=make_open_context(),
        )


def test_signal_processor_rejects_none_result():
    class NoneStrategy:
        @property
        def strategy_id(self) -> str:
            return "NONE"

        def on_bar(
            self,
            context: BacktestContext,
        ) -> Signal:
            return None  # type: ignore[return-value]

    processor = SignalProcessor(
        config=make_config(),
    )

    with pytest.raises(
        TypeError,
        match="return a Signal",
    ):
        processor.process(
            strategy=NoneStrategy(),
            context=make_close_context(),
        )


def test_signal_processor_rejects_non_signal_result():
    class InvalidResultStrategy:
        @property
        def strategy_id(self) -> str:
            return "INVALID"

        def on_bar(
            self,
            context: BacktestContext,
        ) -> Signal:
            return "ENTER_LONG"  # type: ignore[return-value]

    processor = SignalProcessor(
        config=make_config(),
    )

    with pytest.raises(
        TypeError,
        match="return a Signal",
    ):
        processor.process(
            strategy=InvalidResultStrategy(),
            context=make_close_context(),
        )


def test_signal_processor_rejects_wrong_strategy_id():
    class WrongIdentityStrategy:
        @property
        def strategy_id(self) -> str:
            return "STRATEGY-A"

        def on_bar(
            self,
            context: BacktestContext,
        ) -> Signal:
            return Signal(
                signal_id="SIG-001",
                strategy_id="STRATEGY-B",
                symbol="EURUSD",
                timestamp=context.current_time,
                action=SignalAction.HOLD,
            )

    processor = SignalProcessor(
        config=make_config(),
    )

    with pytest.raises(
        ValueError,
        match="strategy_id",
    ):
        processor.process(
            strategy=WrongIdentityStrategy(),
            context=make_close_context(),
        )


def test_signal_processor_rejects_wrong_symbol():
    class WrongSymbolStrategy:
        @property
        def strategy_id(self) -> str:
            return "WRONG-SYMBOL"

        def on_bar(
            self,
            context: BacktestContext,
        ) -> Signal:
            return Signal(
                signal_id="SIG-001",
                strategy_id=self.strategy_id,
                symbol="GBPUSD",
                timestamp=context.current_time,
                action=SignalAction.HOLD,
            )

    processor = SignalProcessor(
        config=make_config(),
    )

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        processor.process(
            strategy=WrongSymbolStrategy(),
            context=make_close_context(),
        )


def test_signal_processor_rejects_future_timestamp():
    class FutureSignalStrategy:
        @property
        def strategy_id(self) -> str:
            return "FUTURE"

        def on_bar(
            self,
            context: BacktestContext,
        ) -> Signal:
            return Signal(
                signal_id="SIG-001",
                strategy_id=self.strategy_id,
                symbol="EURUSD",
                timestamp=utc_time(10, 30),
                action=SignalAction.ENTER_LONG,
            )

    processor = SignalProcessor(
        config=make_config(),
    )

    with pytest.raises(
        ValueError,
        match="timestamp",
    ):
        processor.process(
            strategy=FutureSignalStrategy(),
            context=make_close_context(),
        )


def test_signal_processor_rejects_past_timestamp():
    class PastSignalStrategy:
        @property
        def strategy_id(self) -> str:
            return "PAST"

        def on_bar(
            self,
            context: BacktestContext,
        ) -> Signal:
            return Signal(
                signal_id="SIG-001",
                strategy_id=self.strategy_id,
                symbol="EURUSD",
                timestamp=utc_time(10, 0),
                action=SignalAction.HOLD,
            )

    processor = SignalProcessor(
        config=make_config(),
    )

    with pytest.raises(
        ValueError,
        match="timestamp",
    ):
        processor.process(
            strategy=PastSignalStrategy(),
            context=make_close_context(),
        )


def test_signal_processor_rejects_empty_strategy_id():
    class EmptyIdStrategy:
        @property
        def strategy_id(self) -> str:
            return ""

        def on_bar(
            self,
            context: BacktestContext,
        ) -> Signal:
            return Signal(
                signal_id="SIG-001",
                strategy_id="PLACEHOLDER",
                symbol="EURUSD",
                timestamp=context.current_time,
                action=SignalAction.HOLD,
            )

    processor = SignalProcessor(
        config=make_config(),
    )

    with pytest.raises(
        ValueError,
        match="strategy_id",
    ):
        processor.process(
            strategy=EmptyIdStrategy(),
            context=make_close_context(),
        )


def test_strategy_exception_is_not_swallowed():
    class BrokenStrategy:
        @property
        def strategy_id(self) -> str:
            return "BROKEN"

        def on_bar(
            self,
            context: BacktestContext,
        ) -> Signal:
            raise RuntimeError(
                "synthetic strategy failure"
            )

    processor = SignalProcessor(
        config=make_config(),
    )

    with pytest.raises(
        RuntimeError,
        match="synthetic strategy failure",
    ):
        processor.process(
            strategy=BrokenStrategy(),
            context=make_close_context(),
        )