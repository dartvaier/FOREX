from datetime import datetime, timezone

import pandas as pd
import pytest

from backtest.costs import ZeroCostModel
from backtest.engine import BacktestEngine, BacktestResult
from backtest.models import (
    BacktestConfig,
    ExitReason,
    InstrumentSpecification,
    OrderSide,
    Signal,
    SignalAction,
    Timeframe,
)
from backtest.risk import (
    FixedSizeRiskGate,
    StopBasedRiskGate,
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
        date_from=utc_time(10, 0),
        date_to=utc_time(12, 0),
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


def make_engine() -> BacktestEngine:
    config = make_config()
    instrument = make_instrument()

    return BacktestEngine(
        config=config,
        instrument=instrument,
        cost_model=ZeroCostModel(
            instrument,
        ),
        risk_gate=FixedSizeRiskGate(
            instrument=instrument,
            fixed_quantity=0.01,
        ),
    )


def make_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2026-08-08T10:00:00Z",
                    "2026-08-08T10:15:00Z",
                    "2026-08-08T10:30:00Z",
                ],
                utc=True,
            ),
            "open": [
                1.1600,
                1.1620,
                1.1670,
            ],
            "high": [
                1.1620,
                1.1660,
                1.1690,
            ],
            "low": [
                1.1590,
                1.1610,
                1.1650,
            ],
            "close": [
                1.1610,
                1.1650,
                1.1660,
            ],
            "tick_volume": [
                1000,
                1100,
                1200,
            ],
        }
    )


class LongThenExitStrategy:
    @property
    def strategy_id(self) -> str:
        return "LONG-THEN-EXIT"

    def on_bar(
        self,
        context,
    ) -> Signal:
        if context.current_bar_index == 0:
            action = SignalAction.ENTER_LONG

        elif context.current_bar_index == 1:
            action = SignalAction.EXIT

        else:
            action = SignalAction.HOLD

        return Signal(
            signal_id=(
                f"LONG-{context.current_bar_index}"
            ),
            strategy_id=self.strategy_id,
            symbol="EURUSD",
            timestamp=context.current_time,
            action=action,
        )


class LongOnlyStrategy:
    @property
    def strategy_id(self) -> str:
        return "LONG-ONLY"

    def on_bar(
        self,
        context,
    ) -> Signal:
        action = (
            SignalAction.ENTER_LONG
            if context.current_bar_index == 0
            else SignalAction.HOLD
        )

        return Signal(
            signal_id=(
                f"LONG-ONLY-{context.current_bar_index}"
            ),
            strategy_id=self.strategy_id,
            symbol="EURUSD",
            timestamp=context.current_time,
            action=action,
        )


class LongWithStopStrategy:
    @property
    def strategy_id(self) -> str:
        return "LONG-WITH-STOP"

    def on_bar(
        self,
        context,
    ) -> Signal:
        if context.current_bar_index == 0:
            return Signal(
                signal_id="STOP-ENTRY",
                strategy_id=self.strategy_id,
                symbol="EURUSD",
                timestamp=context.current_time,
                action=SignalAction.ENTER_LONG,
                metadata={
                    "stop_loss": 1.1590,
                    "take_profit": 1.1800,
                },
            )

        return Signal(
            signal_id=(
                f"STOP-HOLD-{context.current_bar_index}"
            ),
            strategy_id=self.strategy_id,
            symbol="EURUSD",
            timestamp=context.current_time,
            action=SignalAction.HOLD,
        )


class LongThenExitWithRiskMetadataStrategy:
    @property
    def strategy_id(self) -> str:
        return "LONG-THEN-EXIT-RISK"

    def on_bar(
        self,
        context,
    ) -> Signal:
        if context.current_bar_index == 0:
            return Signal(
                signal_id="RISK-LONG-0",
                strategy_id=self.strategy_id,
                symbol="EURUSD",
                timestamp=context.current_time,
                action=SignalAction.ENTER_LONG,
                metadata={
                    "entry_price": 1.1620,
                    "stop_loss": 1.1520,
                },
            )

        if context.current_bar_index == 1:
            return Signal(
                signal_id="RISK-EXIT-1",
                strategy_id=self.strategy_id,
                symbol="EURUSD",
                timestamp=context.current_time,
                action=SignalAction.EXIT,
            )

        return Signal(
            signal_id=(
                f"RISK-HOLD-{context.current_bar_index}"
            ),
            strategy_id=self.strategy_id,
            symbol="EURUSD",
            timestamp=context.current_time,
            action=SignalAction.HOLD,
        )


def test_engine_runs_strategy_to_performance_summary():
    result = make_engine().run(
        dataframe=make_dataframe(),
        strategy=LongThenExitStrategy(),
    )

    assert isinstance(
        result,
        BacktestResult,
    )

    assert result.signals.count == 3
    assert result.orders.count == 2
    assert result.orders.history_count == 4
    assert result.fills.count == 2
    assert result.trades.count == 1
    assert result.equity.count == 6
    assert result.pending_orders == ()

    trade = result.trades.last_trade

    assert trade is not None
    assert trade.net_pnl == pytest.approx(
        5.0
    )
    assert trade.bars_held == 1
    assert (
        trade.exit_reason
        == ExitReason.STRATEGY_EXIT
    )

    assert result.portfolio.is_flat is True


def test_engine_accepts_stop_based_risk_gate():
    config = make_config()
    instrument = make_instrument()

    engine = BacktestEngine(
        config=config,
        instrument=instrument,
        cost_model=ZeroCostModel(
            instrument,
        ),
        risk_gate=StopBasedRiskGate(
            instrument=instrument,
            account_equity=10000.0,
            risk_fraction=0.01,
        ),
    )

    result = engine.run(
        dataframe=make_dataframe(),
        strategy=LongThenExitWithRiskMetadataStrategy(),
    )

    assert result.trades.count == 1
    assert result.trades.last_trade is not None
    assert result.trades.last_trade.quantity == pytest.approx(
        0.10
    )
    assert result.trades.last_trade.net_pnl == pytest.approx(
        50.0
    )
    assert result.portfolio.cash == pytest.approx(
        10050.0
    )

    assert result.performance.final_equity == pytest.approx(
        10050.0
    )
    assert result.performance.total_return == pytest.approx(
        50.0
    )
    assert (
        result.performance.trade_metrics.total_trades
        == 1
    )


def test_engine_forces_open_position_closed_at_final_close():
    result = make_engine().run(
        dataframe=make_dataframe(),
        strategy=LongOnlyStrategy(),
    )

    assert result.pending_orders == ()
    assert result.portfolio.is_flat is True
    assert result.orders.count == 2
    assert result.fills.count == 2
    assert result.trades.count == 1

    trade = result.trades.last_trade

    assert trade is not None
    assert (
        trade.exit_reason
        == ExitReason.END_OF_BACKTEST
    )
    assert trade.exit_price == pytest.approx(
        1.1660
    )
    assert trade.net_pnl == pytest.approx(
        4.0
    )
    assert trade.bars_held == 2

    assert result.performance.final_equity == pytest.approx(
        10004.0
    )


def test_engine_executes_protective_stop_from_signal_metadata():
    dataframe = make_dataframe()

    dataframe.loc[
        1,
        "low",
    ] = 1.1580

    dataframe.loc[
        1,
        "close",
    ] = 1.1600

    result = make_engine().run(
        dataframe=dataframe,
        strategy=LongWithStopStrategy(),
    )

    entry_order = result.orders.orders[0]
    protective_order = result.orders.orders[1]

    assert entry_order.stop_loss == pytest.approx(
        1.1590
    )
    assert entry_order.take_profit == pytest.approx(
        1.1800
    )

    assert protective_order.side == OrderSide.SELL
    assert (
        protective_order.metadata["protective_exit"]
        is True
    )

    trade = result.trades.last_trade

    assert trade is not None
    assert (
        trade.exit_reason
        == ExitReason.STOP_LOSS
    )
    assert trade.exit_price == pytest.approx(
        1.1590
    )
    assert trade.net_pnl == pytest.approx(
        -3.0
    )
    assert trade.bars_held == 1

    assert result.performance.final_equity == pytest.approx(
        9997.0
    )
