import math
from dataclasses import dataclass, replace
from datetime import datetime

from backtest.execution import ExecutionResult
from backtest.models.config import BacktestConfig
from backtest.models.enums import (
    ExitReason,
    OrderSide,
    PositionSide,
)
from backtest.models.instrument import InstrumentSpecification
from backtest.models.position import Position


@dataclass(frozen=True, slots=True)
class PositionCloseResult:
    """
    Economic result of closing one Position.

    This is not yet a Trade ledger record.

    Trade creation is deferred because fields such as
    bars_held depend on the future BacktestEngine event
    sequence.
    """

    position: Position

    exit_order_id: str
    exit_fill_id: str

    exit_time: datetime
    exit_price: float

    gross_pnl: float
    net_pnl: float

    commission: float

    exit_reason: ExitReason


class Portfolio:
    """
    Baseline single-position Portfolio.

    Responsibilities:

    - maintain cash
    - maintain equity
    - maintain one current Position
    - calculate unrealized PnL
    - calculate realized PnL
    - open Position from an entry Fill
    - close Position from an opposite Fill

    Baseline assumptions:

    - one symbol
    - one Position at a time
    - full exits only
    - linear FX PnL
    - no automatic reversal
    - execution_price already contains spread/slippage impact
    - commission is monetary and deducted separately

    For the current EURUSD research baseline, PnL is:

        price_difference
        * contract_size
        * quantity

    Account/settlement currency conversion is outside the
    current baseline and must be added before supporting
    instruments whose PnL requires currency conversion.
    """

    def __init__(
        self,
        config: BacktestConfig,
        instrument: InstrumentSpecification,
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
                "instrument must be an "
                "InstrumentSpecification"
            )

        if instrument.symbol != config.symbol:
            raise ValueError(
                "instrument symbol does not match "
                "BacktestConfig"
            )

        self._config = config
        self._instrument = instrument

        self._cash = float(
            config.initial_capital
        )

        self._realized_pnl = 0.0
        self._equity = self._cash

        self._position: Position | None = None

    @property
    def config(self) -> BacktestConfig:
        return self._config

    @property
    def instrument(
        self,
    ) -> InstrumentSpecification:
        return self._instrument

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def equity(self) -> float:
        return self._equity

    @property
    def realized_pnl(self) -> float:
        return self._realized_pnl

    @property
    def unrealized_pnl(self) -> float:
        if self._position is None:
            return 0.0

        return self._position.unrealized_pnl

    @property
    def current_position(
        self,
    ) -> Position | None:
        return self._position

    @property
    def is_flat(self) -> bool:
        return self._position is None

    def apply_execution(
        self,
        result: ExecutionResult,
        *,
        exit_reason: ExitReason = (
            ExitReason.STRATEGY_EXIT
        ),
    ) -> PositionCloseResult | None:
        """
        Apply one successful execution to the Portfolio.

        Flat Portfolio:
            BUY  -> opens LONG
            SELL -> opens SHORT

        Existing LONG:
            SELL -> closes LONG
            BUY  -> rejected

        Existing SHORT:
            BUY  -> closes SHORT
            SELL -> rejected
        """

        if not isinstance(
            result,
            ExecutionResult,
        ):
            raise TypeError(
                "result must be an ExecutionResult"
            )

        if not isinstance(
            exit_reason,
            ExitReason,
        ):
            raise TypeError(
                "exit_reason must be an ExitReason"
            )

        order = result.filled_order
        fill = result.fill

        if order.symbol != self._config.symbol:
            raise ValueError(
                "execution symbol does not match Portfolio"
            )

        if self._position is None:
            self._open_position(
                result
            )

            return None

        return self._close_position(
            result,
            exit_reason=exit_reason,
        )

    def mark_to_market(
        self,
        mark_price: float,
    ) -> float:
        """
        Revalue the current Position using a market price.

        Returns the resulting unrealized PnL.
        """

        if (
            isinstance(mark_price, bool)
            or not isinstance(
                mark_price,
                (int, float),
            )
            or not math.isfinite(mark_price)
            or mark_price <= 0
        ):
            raise ValueError(
                "mark_price must be a finite "
                "positive number"
            )

        if self._position is None:
            self._equity = self._cash

            return 0.0

        unrealized = self._calculate_pnl(
            side=self._position.side,
            entry_price=self._position.entry_price,
            exit_price=float(mark_price),
            quantity=self._position.quantity,
        )

        self._position = replace(
            self._position,
            unrealized_pnl=unrealized,
        )

        self._equity = (
            self._cash
            + unrealized
        )

        return unrealized

    def _open_position(
        self,
        result: ExecutionResult,
    ) -> None:
        order = result.filled_order
        fill = result.fill

        if order.side == OrderSide.BUY:
            position_side = PositionSide.LONG

        elif order.side == OrderSide.SELL:
            position_side = PositionSide.SHORT

        else:
            raise ValueError(
                f"unsupported OrderSide: {order.side}"
            )

        metadata = {
            "entry_order_id": order.order_id,
            "entry_commission": fill.commission,
        }

        strategy_id = order.metadata.get(
            "strategy_id"
        )

        if strategy_id is not None:
            metadata["strategy_id"] = strategy_id

        self._position = Position(
            position_id=(
                f"POS-{fill.fill_id}"
            ),
            entry_fill_id=fill.fill_id,
            symbol=order.symbol,
            side=position_side,
            quantity=fill.quantity,
            entry_time=fill.fill_time,
            entry_price=fill.execution_price,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
            unrealized_pnl=0.0,
            metadata=metadata,
        )

        # Commission is monetary and is charged separately.
        #
        # Spread/slippage are not deducted here because their
        # effect is already reflected in execution_price.
        self._cash -= fill.commission
        self._realized_pnl -= fill.commission

        self._equity = self._cash

    def _close_position(
        self,
        result: ExecutionResult,
        *,
        exit_reason: ExitReason,
    ) -> PositionCloseResult:
        position = self._position

        if position is None:
            raise RuntimeError(
                "cannot close without a Position"
            )

        order = result.filled_order
        fill = result.fill

        if position.side == PositionSide.LONG:
            expected_side = OrderSide.SELL

        elif position.side == PositionSide.SHORT:
            expected_side = OrderSide.BUY

        else:
            raise ValueError(
                f"unsupported PositionSide: "
                f"{position.side}"
            )

        if order.side != expected_side:
            raise ValueError(
                "execution would pyramid the existing "
                "Position"
            )

        if fill.quantity != position.quantity:
            raise ValueError(
                "baseline Portfolio requires full-position "
                "exit quantity"
            )

        gross_pnl = self._calculate_pnl(
            side=position.side,
            entry_price=position.entry_price,
            exit_price=fill.execution_price,
            quantity=position.quantity,
        )

        entry_commission = float(
            position.metadata.get(
                "entry_commission",
                0.0,
            )
        )

        exit_commission = fill.commission

        total_commission = (
            entry_commission
            + exit_commission
        )

        net_pnl = (
            gross_pnl
            - total_commission
        )

        # Entry commission was already deducted when the
        # Position was opened, so only gross PnL and exit
        # commission are applied now.
        self._cash += (
            gross_pnl
            - exit_commission
        )

        self._realized_pnl += (
            gross_pnl
            - exit_commission
        )

        close_result = PositionCloseResult(
            position=position,
            exit_order_id=order.order_id,
            exit_fill_id=fill.fill_id,
            exit_time=fill.fill_time,
            exit_price=fill.execution_price,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            commission=total_commission,
            exit_reason=exit_reason,
        )

        self._position = None
        self._equity = self._cash

        return close_result

    def _calculate_pnl(
        self,
        *,
        side: PositionSide,
        entry_price: float,
        exit_price: float,
        quantity: float,
    ) -> float:
        if side == PositionSide.LONG:
            price_difference = (
                exit_price
                - entry_price
            )

        elif side == PositionSide.SHORT:
            price_difference = (
                entry_price
                - exit_price
            )

        else:
            raise ValueError(
                f"unsupported PositionSide: {side}"
            )

        return (
            price_difference
            * self._instrument.contract_size
            * quantity
        )