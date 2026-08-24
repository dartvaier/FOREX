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
from typing import Any, Callable, Mapping

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

# MT5 trade request action: remove a pending order (cancel)
_TRADE_ACTION_REMOVE = 5

# Order types: 0 = buy, 1 = sell
_ORDER_TYPE_BUY = 0
_ORDER_TYPE_SELL = 1

# Position side: 0 = buy, 1 = sell
_POSITION_TYPE_BUY = 0

# Successful execution retcode
_RETCODE_DONE = 10009

# MT5 account trade modes: 0 = demo, 1 = contest, 2 = real
_TRADE_MODE_NAMES = {
    0: "demo",
    1: "contest",
    2: "real",
}


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
    allowed_trade_modes:
        Account trade modes permitted on the MUTATING paths. Default
        is only ("demo",): real accounts are rejected unless an
        explicit separate policy opts them in (docs/25 ES-03).
    kill_switch:
        Optional callable returning True when a freeze is active.
        Checked on every mutating path (submit/cancel/close).
    """

    def __init__(
        self,
        *,
        trading_enabled: bool = False,
        validation_config: OrderValidationConfig | None = None,
        max_slippage_pips: float = 2.0,
        deviation_points: int = 20,
        magic: int = DEFAULT_MAGIC,
        allowed_trade_modes: tuple[str, ...] = ("demo",),
        kill_switch: Callable[[], bool] | None = None,
    ) -> None:
        self._trading_enabled = bool(trading_enabled)
        self._validation_config = (
            validation_config or OrderValidationConfig()
        )
        self._max_slippage_pips = max_slippage_pips
        self._deviation_points = deviation_points
        self._magic = magic
        self._allowed_trade_modes = tuple(allowed_trade_modes)
        self._kill_switch = kill_switch
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
    def _filling_mode(symbol: str) -> int | None:
        """
        Filling mode supported by the symbol (bitmask on
        symbol_info().filling_mode: 1=FOK, 2=IOC, 4=RETURN).

        Returns None when the symbol is unknown or exposes no mode.
        """
        info = mt5.symbol_info(symbol)  # type: ignore[union-attr]

        if info is None:
            return None

        mode = getattr(info, "filling_mode", None)

        if not mode:
            return None

        fok = getattr(mt5, "ORDER_FILLING_FOK", 0)  # type: ignore[union-attr]
        ioc = getattr(mt5, "ORDER_FILLING_IOC", 1)  # type: ignore[union-attr]
        ret = getattr(mt5, "ORDER_FILLING_RETURN", 2)  # type: ignore[union-attr]

        if mode & 1:
            return fok

        if mode & 2:
            return ioc

        if mode & 4:
            return ret

        return None

    def _account_mode_policy(self, account: BrokerAccountState) -> str | None:
        """
        Enforce the account trade-mode policy on mutating paths
        (docs/25 ES-03).

        Returns None when the account mode is allowed, or a rejection
        message describing the violation. Default policy allows only
        demo accounts; real accounts require an explicit separate
        policy (allowed_trade_modes) and can never execute by accident.
        """
        if not account.trade_mode or account.trade_mode == "unknown":
            return (
                "broker account trade mode is unknown; "
                "cannot authorize a mutating request"
            )

        if account.trade_mode not in self._allowed_trade_modes:
            allowed = ", ".join(self._allowed_trade_modes) or "<none>"
            return (
                f"account trade_mode={account.trade_mode!r} is not in "
                f"allowed_trade_modes=({allowed}); real trading requires "
                "an explicit separate policy"
            )

        return None

    def _kill_switch_active(self) -> bool:
        if self._kill_switch is None:
            return False

        return bool(self._kill_switch())

    @staticmethod
    def _pip_size(symbol: str) -> float:
        """
        Real pip size for the symbol (docs/25 ES-05).

        Derived from symbol digits: pip = 10 ** -(digits - 1).
        EURUSD (5 digits) -> 0.0001; USDJPY (3 digits) -> 0.01.
        """
        info = mt5.symbol_info(symbol)  # type: ignore[union-attr]

        if info is None:
            raise RuntimeError(
                f"no symbol info for {symbol}: {mt5.last_error()}"  # type: ignore[union-attr]
            )

        digits = getattr(info, "digits", None)

        if not digits or digits <= 0:
            raise RuntimeError(
                f"invalid digits for {symbol}: {digits}"
            )

        return float(10 ** -(digits - 1))

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

        # Hardening ES-03: kill switch + account mode policy are
        # checked on the mandatory path, before any broker mutation.
        if self._kill_switch_active():
            return ExecutionReport(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                message="kill switch is active; order submission blocked",
            )

        mode_error = self._account_mode_policy(account)

        if mode_error is not None:
            return ExecutionReport(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                message=mode_error,
            )

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

        filling = self._filling_mode(order.symbol)

        if filling is not None:
            request["type_filling"] = filling

        result = mt5.order_send(request)  # type: ignore[union-attr]

        translated = self._translate_result(
            order.order_id,
            result,
            price,
        )

        if translated.status != OrderStatus.FILLED:
            return translated

        # Hardening ES-04: a real broker execution is NEVER downgraded
        # to REJECTED by a local validation. Slippage outside tolerance
        # flags the report for reconciliation instead.
        fill_validation = validate_fill(
            order,
            translated.fill,
            max_slippage_pips=self._max_slippage_pips,
            pip_size=self._pip_size(order.symbol),
        )

        if not fill_validation.valid:
            return ExecutionReport(
                order_id=order.order_id,
                status=OrderStatus.FILLED,
                message="filled; local fill validation failed: " + "; ".join(
                    fill_validation.errors
                ),
                broker_order_id=translated.broker_order_id,
                fill=translated.fill,
                validation_status="OUTSIDE_TOLERANCE",
                requires_reconciliation=True,
            )

        return translated

    def cancel(self, order_id: str) -> ExecutionReport:
        """
        Cancel a pending order using the official MT5 surface.

        Hardening ES-01 (docs/25): `mt5.order_delete()` does NOT exist
        in the MetaTrader5 Python API. Cancellation of a pending order
        is a trade request with TRADE_ACTION_REMOVE via order_send().
        `order_id` must be the BROKER TICKET of the pending order.
        """
        self._require_trading()
        self._require_mt5()
        self._ensure_connected()

        try:
            ticket = int(order_id)
        except (TypeError, ValueError):
            return ExecutionReport(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                message=(
                    "cancel requires the broker ticket as order_id "
                    f"(got {order_id!r})"
                ),
            )

        account = self.fetch_account()

        if self._kill_switch_active():
            return ExecutionReport(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                message="kill switch is active; cancel blocked",
            )

        mode_error = self._account_mode_policy(account)

        if mode_error is not None:
            return ExecutionReport(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                message=mode_error,
            )

        request: dict[str, Any] = {
            "action": _TRADE_ACTION_REMOVE,
            "order": ticket,
            "magic": self._magic,
            "comment": f"cancel:{order_id}",
        }

        result = mt5.order_send(request)  # type: ignore[union-attr]

        if result is None or result.retcode != _RETCODE_DONE:
            return ExecutionReport(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                message=(
                    f"cancel failed (retcode "
                    f"{getattr(result, 'retcode', None)}): "
                    f"{getattr(result, 'comment', 'no comment')}"
                ),
                broker_order_id=str(
                    getattr(result, "order", None) or ""
                ),
            )

        return ExecutionReport(
            order_id=order_id,
            status=OrderStatus.CANCELLED,
            message="cancelled",
            broker_order_id=str(
                getattr(result, "order", None) or ""
            ),
        )

    def _translate_result(
        self,
        order_id: str,
        result: Any,
        reference_price: float,
    ) -> ExecutionReport:
        """Translate an order_send result into an ExecutionReport."""
        if result is None:
            return ExecutionReport(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                message=(
                    f"order_send returned None: "
                    f"{mt5.last_error()}"  # type: ignore[union-attr]
                ),
            )

        if result.retcode != _RETCODE_DONE:
            return ExecutionReport(
                order_id=order_id,
                status=OrderStatus.REJECTED,
                message=(
                    f"broker retcode {result.retcode}: "
                    f"{result.comment or 'no comment'}"
                ),
                broker_order_id=str(
                    getattr(result, "order", None) or ""
                ),
            )

        fill = Fill(
            fill_id=f"mt5-{result.deal}",
            order_id=order_id,
            fill_time=self._to_utc(
                getattr(result, "time", None)
            ),
            reference_price=reference_price,
            execution_price=float(result.price),
            quantity=float(result.volume),
            spread_impact=0.0,
            slippage=abs(float(result.price) - reference_price),
            commission=0.0,
        )

        return ExecutionReport(
            order_id=order_id,
            status=OrderStatus.FILLED,
            message=result.comment or "filled",
            broker_order_id=str(result.order),
            fill=fill,
        )

    def close_position(
        self,
        position: BrokerPosition,
    ) -> ExecutionReport:
        """
        Close a specific position by broker ticket (hedging accounts).

        The trade request carries the position identifier so the
        broker closes that exact position instead of opening a
        counter-position.
        """
        self._require_trading()
        self._require_mt5()
        self._ensure_connected()

        account = self.fetch_account()

        # Hardening ES-03: same mandatory gate as submit().
        if self._kill_switch_active():
            return ExecutionReport(
                order_id=position.identifier,
                status=OrderStatus.REJECTED,
                message="kill switch is active; close blocked",
            )

        mode_error = self._account_mode_policy(account)

        if mode_error is not None:
            return ExecutionReport(
                order_id=position.identifier,
                status=OrderStatus.REJECTED,
                message=mode_error,
            )

        close_side = (
            OrderSide.SELL
            if position.side == OrderSide.BUY
            else OrderSide.BUY
        )

        price = self._tick_price(
            position.symbol,
            close_side,
        )

        request: dict[str, Any] = {
            "action": _TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": float(position.quantity),
            "type": self._order_type(close_side),
            "price": price,
            "position": int(position.identifier),
            "deviation": self._deviation_points,
            "magic": self._magic,
            "comment": f"close:{position.identifier}",
        }

        filling = self._filling_mode(position.symbol)

        if filling is not None:
            request["type_filling"] = filling

        result = mt5.order_send(request)  # type: ignore[union-attr]

        return self._translate_result(
            position.identifier,
            result,
            price,
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
            trade_mode=_TRADE_MODE_NAMES.get(
                getattr(info, "trade_mode", None),
                "unknown",
            ),
        )

    def fetch_positions(
        self,
        symbol: str | None = None,
    ) -> tuple[BrokerPosition, ...]:
        self._require_mt5()
        self._ensure_connected()

        if symbol is None:
            raw_positions = mt5.positions_get()  # type: ignore[union-attr]
        else:
            raw_positions = mt5.positions_get(  # type: ignore[union-attr]
                symbol=symbol
            )

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

    def validate_environment(
        self,
        config: DemoValidationConfig | None = None,
        *,
        server: str | None = None,
    ) -> DemoValidationResult:
        """
        Gate for Demo activation (roadmap §84): fetch the account and
        validate demo trade mode, server allowlist and free margin.

        Read-only: safe to call while trading is disabled.
        """
        from execution.broker_validation import (
            DemoValidationConfig,
            DemoValidationResult,
            validate_demo_environment,
        )

        account = self.fetch_account()

        return validate_demo_environment(
            account,
            config or DemoValidationConfig(),
            server=server,
        )

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
