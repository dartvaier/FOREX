from datetime import datetime, timezone

import pandas as pd
import pytest

from backtest.clock import SimulationClock
from backtest.context import BacktestContext, BacktestContextBuilder
from backtest.costs import ZeroCostModel
from backtest.engine import BacktestEngine
from backtest.feed import HistoricalBarFeed
from backtest.models import (
    BacktestConfig,
    InstrumentSpecification,
    Signal,
    SignalAction,
    Timeframe,
)
from backtest.models.enums import SimulationPhase
from backtest.risk import FixedSizeRiskGate


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


def make_dataframe(
    times: list[str],
    closes: list[float],
    *,
    complete: bool = True,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": pd.to_datetime(
                times,
                utc=True,
            ),
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "tick_volume": [
                1000
                for _ in closes
            ],
            "complete": [
                complete
                for _ in closes
            ],
        }
    )


def make_config(
    timeframe: Timeframe,
) -> BacktestConfig:
    return BacktestConfig(
        symbol="EURUSD",
        timeframe=timeframe,
        date_from=utc_time(8, 0),
        date_to=utc_time(13, 0),
        initial_capital=10000.0,
    )


def make_base_dataframe() -> pd.DataFrame:
    return make_dataframe(
        [
            "2026-08-08T10:00:00Z",
            "2026-08-08T10:15:00Z",
            "2026-08-08T10:30:00Z",
            "2026-08-08T10:45:00Z",
            "2026-08-08T11:45:00Z",
        ],
        [
            1.1000,
            1.1010,
            1.1020,
            1.1030,
            1.1040,
        ],
    )


def make_h1_dataframe() -> pd.DataFrame:
    return make_dataframe(
        [
            "2026-08-08T10:00:00Z",
        ],
        [
            1.1010,
        ],
    )


def make_h4_dataframe(
    *,
    complete: bool = True,
) -> pd.DataFrame:
    return make_dataframe(
        [
            "2026-08-08T08:00:00Z",
        ],
        [
            1.0990,
        ],
        complete=complete,
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


def make_builder_and_clock() -> tuple[
    BacktestContextBuilder,
    SimulationClock,
]:
    base_feed = HistoricalBarFeed(
        dataframe=make_base_dataframe(),
        config=make_config(
            Timeframe.M15,
        ),
    )

    h1_feed = HistoricalBarFeed(
        dataframe=make_h1_dataframe(),
        config=make_config(
            Timeframe.H1,
        ),
    )

    h4_feed = HistoricalBarFeed(
        dataframe=make_h4_dataframe(),
        config=make_config(
            Timeframe.H4,
        ),
    )

    clock = SimulationClock(
        bar_starts=base_feed.bar_starts,
        timeframe=Timeframe.M15,
    )

    return (
        BacktestContextBuilder(
            feed=base_feed,
            clock=clock,
            higher_timeframe_feeds={
                Timeframe.H1: h1_feed,
                Timeframe.H4: h4_feed,
            },
        ),
        clock,
    )


def test_context_exposes_higher_timeframe_bars_only_after_close():
    builder, clock = make_builder_and_clock()
    events = list(clock.events())

    context_before_h1_close = builder.build(
        events[5],
    )

    assert context_before_h1_close.current_time == utc_time(
        10,
        45,
    )
    assert (
        context_before_h1_close.timeframe_bars[Timeframe.H1]
        == ()
    )
    assert (
        context_before_h1_close.timeframe_bars[Timeframe.H4]
        == ()
    )

    context_at_h1_close = builder.build(
        events[7],
    )

    assert context_at_h1_close.current_time == utc_time(
        11,
        0,
    )
    assert len(
        context_at_h1_close.timeframe_bars[Timeframe.H1]
    ) == 1
    assert (
        context_at_h1_close.timeframe_bars[Timeframe.H1][0].time
        == utc_time(10, 0)
    )
    assert (
        context_at_h1_close.timeframe_bars[Timeframe.H4]
        == ()
    )

    context_at_h4_close = builder.build(
        events[9],
    )

    assert context_at_h4_close.current_time == utc_time(
        12,
        0,
    )
    assert len(
        context_at_h4_close.timeframe_bars[Timeframe.H4]
    ) == 1
    assert (
        context_at_h4_close.timeframe_bars[Timeframe.H4][0].time
        == utc_time(8, 0)
    )


def test_context_rejects_invalid_timeframe_bars_mapping():
    with pytest.raises(
        TypeError,
        match="timeframe_bars",
    ):
        BacktestContext(
            current_time=utc_time(10, 15),
            phase=SimulationPhase.BAR_CLOSE,
            current_bar_index=0,
            current_bar=None,
            closed_bars=(),
            timeframe_bars=[],  # type: ignore[arg-type]
        )


def test_context_builder_rejects_base_timeframe_as_higher_timeframe():
    base_feed = HistoricalBarFeed(
        dataframe=make_base_dataframe(),
        config=make_config(
            Timeframe.M15,
        ),
    )

    clock = SimulationClock(
        bar_starts=base_feed.bar_starts,
        timeframe=Timeframe.M15,
    )

    with pytest.raises(
        ValueError,
        match="base timeframe",
    ):
        BacktestContextBuilder(
            feed=base_feed,
            clock=clock,
            higher_timeframe_feeds={
                Timeframe.M15: base_feed,
            },
        )


def test_higher_timeframe_feed_filters_incomplete_bars():
    base_feed = HistoricalBarFeed(
        dataframe=make_base_dataframe(),
        config=make_config(
            Timeframe.M15,
        ),
    )

    with pytest.raises(
        ValueError,
        match="no bars available",
    ):
        HistoricalBarFeed(
            dataframe=make_h4_dataframe(
                complete=False,
            ),
            config=make_config(
                Timeframe.H4,
            ),
        )

    clock = SimulationClock(
        bar_starts=base_feed.bar_starts,
        timeframe=Timeframe.M15,
    )

    builder = BacktestContextBuilder(
        feed=base_feed,
        clock=clock,
        higher_timeframe_feeds={},
    )

    context = builder.build(
        list(clock.events())[-1],
    )

    assert context.timeframe_bars == {}


class RecordingMultiTimeframeStrategy:
    strategy_id = "RECORDING-MULTI-TIMEFRAME"
    higher_timeframes = (
        Timeframe.H1,
        Timeframe.H4,
    )

    def __init__(self) -> None:
        self.snapshots = []

    @property
    def closed_bar_limit(self) -> int:
        return 1

    def on_bar(
        self,
        context: BacktestContext,
    ) -> Signal:
        self.snapshots.append(
            {
                "time": context.current_time,
                "h1_count": len(
                    context.timeframe_bars.get(
                        Timeframe.H1,
                        (),
                    )
                ),
                "h4_count": len(
                    context.timeframe_bars.get(
                        Timeframe.H4,
                        (),
                    )
                ),
            }
        )

        return Signal(
            signal_id=f"SIG-{context.current_bar_index}",
            strategy_id=self.strategy_id,
            symbol="EURUSD",
            timestamp=context.current_time,
            action=SignalAction.HOLD,
            reason="Recording context",
        )


def test_backtest_engine_passes_higher_timeframes_to_strategy():
    config = make_config(
        Timeframe.M15,
    )

    instrument = make_instrument()

    engine = BacktestEngine(
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

    strategy = RecordingMultiTimeframeStrategy()

    result = engine.run(
        dataframe=make_base_dataframe(),
        strategy=strategy,
        higher_timeframe_dataframes={
            Timeframe.H1: make_h1_dataframe(),
            Timeframe.H4: make_h4_dataframe(),
        },
    )

    assert result.signals.count == 5
    assert strategy.snapshots[-1] == {
        "time": utc_time(12, 0),
        "h1_count": 1,
        "h4_count": 1,
    }
