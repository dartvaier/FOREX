from dataclasses import dataclass

import pandas as pd

from backtest.clock import ClockEvent, SimulationClock
from backtest.context import BacktestContextBuilder
from backtest.costs import CostModel
from backtest.equity_ledger import EquityLedger
from backtest.equity_recorder import EquityRecorder
from backtest.execution import ExecutionResult, SimulatedExecution
from backtest.feed import HistoricalBarFeed
from backtest.fill_ledger import FillLedger
from backtest.models.config import BacktestConfig
from backtest.models.enums import (
    EndOfBacktestPolicy,
    ExitReason,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    SimulationPhase,
)
from backtest.models.instrument import InstrumentSpecification
from backtest.models.order import Order
from backtest.order_factory import OrderFactory
from backtest.order_ledger import OrderLedger
from backtest.order_queue import PendingOrderQueue
from backtest.performance import (
    PerformanceSummary,
    calculate_performance_summary,
)
from backtest.portfolio import Portfolio, PositionCloseResult
from backtest.protective_exit import ProtectiveExitEvaluator
from backtest.protective_order import ProtectiveExitOrderFactory
from backtest.risk import FixedSizeRiskGate
from backtest.signal_ledger import SignalLedger
from backtest.signal_processor import SignalProcessor
from backtest.strategy import Strategy
from backtest.trade_factory import TradeFactory
from backtest.trade_ledger import TradeLedger


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """
    Immutable audit bundle produced by one BacktestEngine run.
    """

    config: BacktestConfig
    feed: HistoricalBarFeed
    portfolio: Portfolio

    signals: SignalLedger
    orders: OrderLedger
    fills: FillLedger
    trades: TradeLedger
    equity: EquityLedger

    pending_orders: tuple[Order, ...]
    performance: PerformanceSummary


class BacktestEngine:
    """
    Coordinates the baseline deterministic bar-by-bar backtest.

    The engine owns orchestration only. Market data validation,
    strategy processing, risk decisions, order creation,
    execution, portfolio accounting, ledgers and performance
    remain delegated to their dedicated components.
    """

    def __init__(
        self,
        *,
        config: BacktestConfig,
        instrument: InstrumentSpecification,
        cost_model: CostModel,
        risk_gate: FixedSizeRiskGate,
    ) -> None:
        if not isinstance(
            config,
            BacktestConfig,
        ):
            raise TypeError(
                "config must be a BacktestConfig"
            )

        if not isinstance(
            instrument,
            InstrumentSpecification,
        ):
            raise TypeError(
                "instrument must be an InstrumentSpecification"
            )

        if not isinstance(
            cost_model,
            CostModel,
        ):
            raise TypeError(
                "cost_model must satisfy the CostModel protocol"
            )

        if not isinstance(
            risk_gate,
            FixedSizeRiskGate,
        ):
            raise TypeError(
                "risk_gate must be a FixedSizeRiskGate"
            )

        if instrument.symbol != config.symbol:
            raise ValueError(
                "instrument symbol does not match BacktestConfig"
            )

        if cost_model.instrument.symbol != config.symbol:
            raise ValueError(
                "cost_model instrument symbol does not match "
                "BacktestConfig"
            )

        if risk_gate.instrument.symbol != config.symbol:
            raise ValueError(
                "risk_gate instrument symbol does not match "
                "BacktestConfig"
            )

        self._config = config
        self._instrument = instrument
        self._cost_model = cost_model
        self._risk_gate = risk_gate

    @property
    def config(self) -> BacktestConfig:
        return self._config

    @property
    def instrument(
        self,
    ) -> InstrumentSpecification:
        return self._instrument

    @property
    def cost_model(self) -> CostModel:
        return self._cost_model

    @property
    def risk_gate(self) -> FixedSizeRiskGate:
        return self._risk_gate

    def run(
        self,
        *,
        dataframe: pd.DataFrame,
        strategy: Strategy,
    ) -> BacktestResult:
        if not isinstance(
            dataframe,
            pd.DataFrame,
        ):
            raise TypeError(
                "dataframe must be a pandas DataFrame"
            )

        if not isinstance(
            strategy,
            Strategy,
        ):
            raise TypeError(
                "strategy must satisfy the Strategy protocol"
            )

        self._reset_strategy(strategy)
        closed_bar_limit = self._strategy_closed_bar_limit(
            strategy
        )

        feed = HistoricalBarFeed(
            dataframe=dataframe,
            config=self._config,
        )

        clock = SimulationClock(
            bar_starts=feed.bar_starts,
            timeframe=self._config.timeframe,
        )

        context_builder = BacktestContextBuilder(
            feed=feed,
            clock=clock,
        )

        signal_processor = SignalProcessor(
            config=self._config,
        )

        order_factory = OrderFactory(
            config=self._config,
        )

        queue = PendingOrderQueue()

        execution = SimulatedExecution(
            config=self._config,
            cost_model=self._cost_model,
        )

        portfolio = Portfolio(
            config=self._config,
            instrument=self._instrument,
        )

        protective_evaluator = ProtectiveExitEvaluator(
            self._config
        )

        protective_order_factory = ProtectiveExitOrderFactory(
            self._config
        )

        trade_factory = TradeFactory(
            self._instrument
        )

        signal_ledger = SignalLedger()
        order_ledger = OrderLedger()
        fill_ledger = FillLedger()
        trade_ledger = TradeLedger()
        equity_ledger = EquityLedger()
        equity_recorder = EquityRecorder(
            equity_ledger
        )

        entry_bar_indexes: dict[str, int] = {}

        for event in clock.events():
            bar = feed.bars[event.bar_index]

            if event.phase == SimulationPhase.BAR_OPEN:
                self._process_pending_orders(
                    event=event,
                    bar=bar,
                    queue=queue,
                    execution=execution,
                    portfolio=portfolio,
                    order_ledger=order_ledger,
                    fill_ledger=fill_ledger,
                    trade_ledger=trade_ledger,
                    trade_factory=trade_factory,
                    entry_bar_indexes=entry_bar_indexes,
                )

                self._process_protective_exit_at_open(
                    event=event,
                    bar=bar,
                    execution=execution,
                    portfolio=portfolio,
                    protective_evaluator=protective_evaluator,
                    protective_order_factory=protective_order_factory,
                    order_ledger=order_ledger,
                    fill_ledger=fill_ledger,
                    trade_ledger=trade_ledger,
                    trade_factory=trade_factory,
                    entry_bar_indexes=entry_bar_indexes,
                )

                equity_recorder.record(
                    event,
                    portfolio,
                )

                continue

            self._process_protective_exit_at_close(
                event=event,
                bar=bar,
                execution=execution,
                portfolio=portfolio,
                protective_evaluator=protective_evaluator,
                protective_order_factory=protective_order_factory,
                order_ledger=order_ledger,
                fill_ledger=fill_ledger,
                trade_ledger=trade_ledger,
                trade_factory=trade_factory,
                entry_bar_indexes=entry_bar_indexes,
            )

            if portfolio.current_position is not None:
                portfolio.mark_to_market(
                    bar.close
                )

            equity_recorder.record(
                event,
                portfolio,
            )

            context = context_builder.build(
                event,
                closed_bar_limit=closed_bar_limit,
            )

            signal = signal_processor.process(
                strategy=strategy,
                context=context,
            )

            signal_ledger.append(signal)

            decision = self._risk_gate.evaluate(
                signal
            )

            order = order_factory.create(
                signal=signal,
                risk_decision=decision,
                current_position=portfolio.current_position,
            )

            if order is None:
                continue

            order_ledger.append(order)

            queue.enqueue(
                order,
                submitted_event=event,
            )

        self._finalize_open_position(
            feed=feed,
            clock=clock,
            execution=execution,
            portfolio=portfolio,
            order_ledger=order_ledger,
            fill_ledger=fill_ledger,
            trade_ledger=trade_ledger,
            trade_factory=trade_factory,
            equity_recorder=equity_recorder,
            entry_bar_indexes=entry_bar_indexes,
        )

        performance = calculate_performance_summary(
            self._config,
            trade_ledger,
            equity_ledger,
        )

        return BacktestResult(
            config=self._config,
            feed=feed,
            portfolio=portfolio,
            signals=signal_ledger,
            orders=order_ledger,
            fills=fill_ledger,
            trades=trade_ledger,
            equity=equity_ledger,
            pending_orders=queue.pending_orders,
            performance=performance,
        )

    @staticmethod
    def _reset_strategy(
        strategy: Strategy,
    ) -> None:
        reset = getattr(
            strategy,
            "reset",
            None,
        )

        if reset is None:
            return

        if not callable(reset):
            raise TypeError(
                "strategy reset attribute must be callable"
            )

        reset()

    @staticmethod
    def _strategy_closed_bar_limit(
        strategy: Strategy,
    ) -> int | None:
        limit = getattr(
            strategy,
            "closed_bar_limit",
            None,
        )

        if limit is None:
            return None

        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit <= 0
        ):
            raise ValueError(
                "strategy closed_bar_limit must be a positive "
                "integer or None"
            )

        return limit

    def _process_pending_orders(
        self,
        *,
        event: ClockEvent,
        bar,
        queue: PendingOrderQueue,
        execution: SimulatedExecution,
        portfolio: Portfolio,
        order_ledger: OrderLedger,
        fill_ledger: FillLedger,
        trade_ledger: TradeLedger,
        trade_factory: TradeFactory,
        entry_bar_indexes: dict[str, int],
    ) -> None:
        for order in queue.pop_eligible(event):
            result = execution.execute(
                order,
                event=event,
                bar=bar,
            )

            self._record_execution(
                result,
                portfolio=portfolio,
                event=event,
                exit_reason=ExitReason.STRATEGY_EXIT,
                order_ledger=order_ledger,
                fill_ledger=fill_ledger,
                trade_ledger=trade_ledger,
                trade_factory=trade_factory,
                entry_bar_indexes=entry_bar_indexes,
            )

    def _process_protective_exit_at_open(
        self,
        *,
        event: ClockEvent,
        bar,
        execution: SimulatedExecution,
        portfolio: Portfolio,
        protective_evaluator: ProtectiveExitEvaluator,
        protective_order_factory: ProtectiveExitOrderFactory,
        order_ledger: OrderLedger,
        fill_ledger: FillLedger,
        trade_ledger: TradeLedger,
        trade_factory: TradeFactory,
        entry_bar_indexes: dict[str, int],
    ) -> None:
        position = portfolio.current_position

        if position is None:
            return

        decision = protective_evaluator.evaluate(
            position,
            bar,
        )

        if (
            decision is None
            or not decision.triggered_at_open
        ):
            return

        order = protective_order_factory.create(
            position,
            decision,
            execution_time=event.timestamp,
        )

        order_ledger.append(order)

        result = execution.execute_protective(
            order,
            decision=decision,
            bar=bar,
            fill_time=event.timestamp,
        )

        self._record_execution(
            result,
            portfolio=portfolio,
            event=event,
            exit_reason=decision.exit_reason,
            order_ledger=order_ledger,
            fill_ledger=fill_ledger,
            trade_ledger=trade_ledger,
            trade_factory=trade_factory,
            entry_bar_indexes=entry_bar_indexes,
        )

    def _process_protective_exit_at_close(
        self,
        *,
        event: ClockEvent,
        bar,
        execution: SimulatedExecution,
        portfolio: Portfolio,
        protective_evaluator: ProtectiveExitEvaluator,
        protective_order_factory: ProtectiveExitOrderFactory,
        order_ledger: OrderLedger,
        fill_ledger: FillLedger,
        trade_ledger: TradeLedger,
        trade_factory: TradeFactory,
        entry_bar_indexes: dict[str, int],
    ) -> None:
        position = portfolio.current_position

        if position is None:
            return

        decision = protective_evaluator.evaluate(
            position,
            bar,
        )

        if (
            decision is None
            or decision.triggered_at_open
        ):
            return

        order = protective_order_factory.create(
            position,
            decision,
            execution_time=event.timestamp,
        )

        order_ledger.append(order)

        result = execution.execute_protective(
            order,
            decision=decision,
            bar=bar,
            fill_time=event.timestamp,
        )

        self._record_execution(
            result,
            portfolio=portfolio,
            event=event,
            exit_reason=decision.exit_reason,
            order_ledger=order_ledger,
            fill_ledger=fill_ledger,
            trade_ledger=trade_ledger,
            trade_factory=trade_factory,
            entry_bar_indexes=entry_bar_indexes,
        )

    def _record_execution(
        self,
        result: ExecutionResult,
        *,
        portfolio: Portfolio,
        event: ClockEvent,
        exit_reason: ExitReason,
        order_ledger: OrderLedger,
        fill_ledger: FillLedger,
        trade_ledger: TradeLedger,
        trade_factory: TradeFactory,
        entry_bar_indexes: dict[str, int],
    ) -> None:
        order_ledger.append(
            result.filled_order
        )

        fill_ledger.append(
            result.fill
        )

        close_result = portfolio.apply_execution(
            result,
            exit_reason=exit_reason,
        )

        if close_result is None:
            position = portfolio.current_position

            if position is None:
                raise RuntimeError(
                    "entry execution did not open a Position"
                )

            entry_bar_indexes[
                position.position_id
            ] = event.bar_index

            return

        self._record_trade(
            close_result=close_result,
            event=event,
            trade_ledger=trade_ledger,
            trade_factory=trade_factory,
            entry_bar_indexes=entry_bar_indexes,
        )

    def _record_trade(
        self,
        *,
        close_result: PositionCloseResult,
        event: ClockEvent,
        trade_ledger: TradeLedger,
        trade_factory: TradeFactory,
        entry_bar_indexes: dict[str, int],
    ) -> None:
        position_id = (
            close_result.position.position_id
        )

        entry_bar_index = entry_bar_indexes.pop(
            position_id
        )

        trade = trade_factory.create_from_bar_indexes(
            close_result,
            entry_bar_index=entry_bar_index,
            exit_bar_index=event.bar_index,
            exit_phase=event.phase,
        )

        trade_ledger.append(
            trade
        )

    def _finalize_open_position(
        self,
        *,
        feed: HistoricalBarFeed,
        clock: SimulationClock,
        execution: SimulatedExecution,
        portfolio: Portfolio,
        order_ledger: OrderLedger,
        fill_ledger: FillLedger,
        trade_ledger: TradeLedger,
        trade_factory: TradeFactory,
        equity_recorder: EquityRecorder,
        entry_bar_indexes: dict[str, int],
    ) -> None:
        if (
            portfolio.current_position is None
            or self._config.end_of_backtest_policy
            == EndOfBacktestPolicy.LEAVE_OPEN
        ):
            return

        if (
            self._config.end_of_backtest_policy
            != EndOfBacktestPolicy.FORCE_CLOSE_AT_FINAL_AVAILABLE_CLOSE
        ):
            raise ValueError(
                "unsupported end_of_backtest_policy"
            )

        final_bar_index = len(feed.bars) - 1
        final_bar = feed.bars[final_bar_index]
        final_timestamp = clock.bar_close_time(
            final_bar.time
        )

        position = portfolio.current_position

        if position is None:
            return

        order = self._create_end_of_backtest_order(
            position=position,
            timestamp=final_timestamp,
        )

        order_ledger.append(order)

        result = execution.execute_at_reference(
            order,
            fill_time=final_timestamp,
            reference_price=final_bar.close,
        )

        final_event = ClockEvent(
            timestamp=final_timestamp,
            phase=SimulationPhase.BAR_CLOSE,
            bar_index=final_bar_index,
            bar_start=final_bar.time,
            bar_close=final_timestamp,
        )

        self._record_execution(
            result,
            portfolio=portfolio,
            event=final_event,
            exit_reason=ExitReason.END_OF_BACKTEST,
            order_ledger=order_ledger,
            fill_ledger=fill_ledger,
            trade_ledger=trade_ledger,
            trade_factory=trade_factory,
            entry_bar_indexes=entry_bar_indexes,
        )

        equity_recorder.record(
            final_event,
            portfolio,
        )

    def _create_end_of_backtest_order(
        self,
        *,
        position,
        timestamp,
    ) -> Order:
        if position.side == PositionSide.LONG:
            side = OrderSide.SELL

        elif position.side == PositionSide.SHORT:
            side = OrderSide.BUY

        else:
            raise ValueError(
                f"unsupported PositionSide: {position.side}"
            )

        return Order(
            order_id=(
                f"ORD-END-{position.position_id}"
            ),
            signal_id=(
                f"SYS-END-{position.position_id}"
            ),
            symbol=position.symbol,
            side=side,
            quantity=position.quantity,
            order_type=OrderType.MARKET,
            created_at=timestamp,
            scheduled_for=timestamp,
            status=OrderStatus.PENDING,
            metadata={
                "end_of_backtest": True,
                "position_id": position.position_id,
                "exit_reason": (
                    ExitReason.END_OF_BACKTEST.value
                ),
            },
        )
