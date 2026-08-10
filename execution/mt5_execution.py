"""
MT5Execution: MetaTrader 5 adapter implementing ExecutionInterface.

ENGINEERING ONLY. This adapter is the broker-facing implementation of
the F9 Execution Layer, but it is NEVER active by default:

- `trading_enabled=False` by default; submit()/cancel() raise
  ExecutionNotEnabledError while disabled (AGENTS.md §10, roadmap §81).
- Activating Demo (trading_enabled=True) is a separate, explicit
  operator decision AFTER the layer is validated.
- The MetaTrader5 module is imported lazily; without the package the
  adapter raises a clear error instead of failing at import time.

Read-only calls (fetch_account, fetch_positions, ping) are allowed
while disabled: monitoring the account is safe and does not change
broker state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from backtest.models.enums import (
    OrderSide,
    OrderStatus,
    OrderType,
)
from backtest.models.fill import Fill
from backtest.models.order import Order
from execution.fill_validation import validate_fill
from execution.interface import (
    BrokerAccountState,
    BrokerPosition,
    ExecutionInterface,
    ExecutionReport,
)
from execution.order_validation import (
    OrderValidationConfig,
    validate_order,
)

try:  # pragma: no cover - depends on local MT5 install
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover
    mt5 = None

DEFAULT_MAGIC = 20260810

# MT5 trade request action: immediate market execution
_TRADE_ACTION_DEAL = 1

# Order types: 0 = buy, 1 = sell
_ORDER_TYPE_BUY = 0
_ORDER_TYPE_SELL = 1

# Position side: 0 = buy, 1 = sell
_POSITION_TYPE_BUY = 0

# Successful execution retcode
_RETCODE_DONE = 10009


class ExecutionNotEnabledError(RuntimeError):
    """Raised when an execution call is attempted while trading is disabled."""


class MT5Execution(ExecutionInterface):
    """
    MetaTrader 5 broker adapter.

    Parameters
    ----------
    trading_enabled:
        False by default. Must be explicitly True (Demo activation)
        for submit/cancel to reach the broker.
    validation_config:
        Broker-level order constraints enforced before any send.
    max_slippage_pips:
        Slippage tolerance applied to incoming fills.
    deviation_points:
        Max price deviation (points) sent with the trade request.
    magic:
        Expert advisor magic number for order tagging.
    """

    def __init__(
        self,
        *,
        trading_enabled: bool = False,
        validation_config: OrderValidationConfig | None = None,
        max_slippage_pips: float = 2.0,
        deviation_points: int = 20,
        magic: int = DEFAULT_MAGIC,
    ) -> None:
        self._trading_enabled = bool(trading_enabled)
        self._validation_config = (
            validation_config or OrderValidationConfig()
        )
        self._max_slippage_pips = max_slippage_pips
        self._deviation_points = deviation_points
        self._magic = magic
        self._connected = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_mt5(self) -> None:
        if mt5 is None:
            raise RuntimeError(
                "MetaTrader5 package is not installed; "
                "cannot use MT5Execution"
            )

    def _require_trading(self) -> None:
        if not self._trading_enabled:
            raise ExecutionNotEnabledError(
                "trading is disabled (TRADING_ENABLED=false, "
                "AGENTS.md §10); Demo activation is an explicit "
                "separate decision"
            )

    def _ensure_connected(self) -> None:
        self._require_mt5()

        if not self._connected:
            if not mt5.initialize():  # type: ignore[union-attr]
                error = mt5.last_error()  # type: ignore[union-attr]
                raise RuntimeError(
                    f"MT5 initialize failed: {error}"
                )
            self._connected = True

    @staticmethod
    def _tick_price(symbol: str, side: OrderSide) -> float:
        tick = mt5.symbol_info_tick(symbol)  # type: ignore[union-attr]

        if tick is None:
            raise RuntimeError(
                f"no tick for {symbol}: {mt5.last_error()}"  # type: ignore[union-attr]
            )

        price = tick.ask if side == OrderSide.BUY else tick.bid

        if price is None or price <= 0:
            raise RuntimeError(
                f"invalid {side.value} price for {symbol}: {price}"
            )

        return float(price)

    @staticmethod
    def _order_type(side: OrderSide) -> int:
        return _ORDER_TYPE_BUY if side == OrderSide.BUY else _ORDER_TYPE_SELL

    @staticmethod
    def _to_utc(epoch_seconds: int | None) -> datetime:
        if epoch_seconds is None or epoch_seconds <= 0:
            return datetime.now(timezone.utc)

        return datetime.fromtimestamp(
            float(epoch_seconds),
            tz=timezone.utc,
        )

    # ------------------------------------------------------------------
    # ExecutionInterface
    # ------------------------------------------------------------------

    def submit(self, order: Order) -> ExecutionReport:
        self._require_trading()
        self._require_mt5()

        account = self.fetch_account()

        validation = validate_order(
            order,
            account,
            self._validation_config,
        )

        if not validation.valid:
            return ExecutionReport(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                message="; ".join(validation.errors),
            )

        self._ensure_connected()

        price = self._tick_price(order.symbol, order.side)

        request: dict[str, Any] = {
            "action": _TRADE_ACTION_DEAL,
            "symbol": order.symbol,
            "volume": float(order.quantity),
            "type": self._order_type(order.side),
            "price": price,
            "deviation": self._deviation_points,
            "magic": self._magic,
            "comment": f"signal:{order.signal_id}",
        }

        if order.stop_loss is not None:
            request["sl"] = float(order.stop_loss)

        if order.take_profit is not None:
            request["tp"] = float(order.take_profit)

        filling = getattr(mt5, "ORDER_FILLING_IOC", None)

        if filling is not None:
            request["type_filling"] = filling

        result = mt5.order_send(request)  # type: ignore[union-attr]

        if result is None:
            return ExecutionReport(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                message=(
                    f"order_send returned None: "
                    f"{mt5.last_error()}"  # type: ignore[union-attr]
                ),
            )

        if result.retcode != _RETCODE_DONE:
            return ExecutionReport(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                message=(
                    f"broker retcode {result.retcode}: "
                    f"{result.comment or 'no comment'}"
                ),
                broker_order_id=str(getattr(result, "order", None) or ""),
            )

        fill = Fill(
            fill_id=f"mt5-{result.deal}",
            order_id=order.order_id,
            fill_time=self._to_utc(getattr(result, "time", None)),
            reference_price=price,
            execution_price=float(result.price),
            quantity=float(result.volume),
            spread_impact=0.0,
            slippage=abs(float(result.price) - price),
            commission=0.0,
        )

        fill_validation = validate_fill(
            order,
            fill,
            max_slippage_pips=self._max_slippage_pips,
        )

        if not fill_validation.valid:
            return ExecutionReport(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                message="fill failed validation: " + "; ".join(
                    fill_validation.errors
                ),
                broker_order_id=str(getattr(result, "order", None) or ""),
            )

        return ExecutionReport(
            order_id=order.order_id,
            status=OrderStatus.FILLED,
            message=result.comment or "filled",
            broker_order_id=str(result.order),
            fill=fill,
        )

    def cancel(self, order_id: str) -> ExecutionReport:
        self._require_trading()
        self._require_mt5()
        self._ensure_connected()

        result = mt5.order_delete(order_id)  # type: ignore[union-attr]

        if not result:
            return ExecutionReport(
                order_id=order_id,
                status=OrderStatus.CANCELLED,
                message=(
                    f"order_delete failed: "
                    f"{mt5.last_error()}"  # type: ignore[union-attr]
                ),
            )

        return ExecutionReport(
            order_id=order_id,
            status=OrderStatus.CANCELLED,
            message="cancelled",
        )

    def fetch_account(self) -> BrokerAccountState:
        self._require_mt5()
        self._ensure_connected()

        info = mt5.account_info()  # type: ignore[union-attr]

        if info is None:
            raise RuntimeError(
                f"account_info failed: {mt5.last_error()}"  # type: ignore[union-attr]
            )

        return BrokerAccountState(
            balance=float(info.balance),
            equity=float(info.equity),
            margin_free=float(info.margin_free),
            currency=str(info.currency),
            positions=self.fetch_positions(),
        )

    def fetch_positions(
        self,
        symbol: str | None = None,
    ) -> tuple[BrokerPosition, ...]:
        self._require_mt5()
        self._ensure_connected()

        raw_positions = mt5.positions_get(symbol=symbol)  # type: ignore[union-attr]

        if raw_positions is None:
            raise RuntimeError(
                f"positions_get failed: {mt5.last_error()}"  # type: ignore[union-attr]
            )

        positions: list[BrokerPosition] = []

        for raw in raw_positions:
            positions.append(
                BrokerPosition(
                    identifier=str(raw.ticket),
                    symbol=str(raw.symbol),
                    side=(
                        OrderSide.BUY
                        if raw.type == _POSITION_TYPE_BUY
                        else OrderSide.SELL
                    ),
                    quantity=float(raw.volume),
                    entry_price=float(raw.price_open),
                    open_time=self._to_utc(raw.time),
                    current_price=float(raw.price_current),
                )
            )

        return tuple(positions)

    def ping(self) -> bool:
        self._require_mt5()

        try:
            self._ensure_connected()
            terminal = mt5.terminal_info()  # type: ignore[union-attr]
        except RuntimeError:
            return False

        if terminal is None:
            return False

        return bool(terminal.connected)

    def close(self) -> None:
        if mt5 is None:
            return

        if self._connected:
            mt5.shutdown()  # type: ignore[union-attr]
            self._connected = False


# Convenience re-export of the config type used by the adapter.
__all__ = [
    "ExecutionNotEnabledError",
    "MT5Execution",
    "OrderValidationConfig",
]
