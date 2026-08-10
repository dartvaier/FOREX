"""
Broker / Demo-only validation for the F9 Execution Layer.

Roadmap §84: before ANY order_send the platform must validate demo
account, server, symbol, trade mode, quantity, risk engine,
TRADING_ENABLED and kill switch.

This module implements the pure, broker-independent checks. The
operator-facing `validate_demo_environment` gates Demo activation;
`validate_broker_preconditions` is the last-line check right before
submission.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backtest.models.order import Order
from execution.interface import BrokerAccountState
from execution.order_validation import OrderValidationConfig

# MT5 account trade modes (roadmap §84: only demo is acceptable
# for the F9 validation phase).
TRADE_MODE_DEMO = "demo"
TRADE_MODE_REAL = "real"
ALLOWED_DEMO_MODES: tuple[str, ...] = (TRADE_MODE_DEMO,)


@dataclass(frozen=True, slots=True)
class DemoValidationConfig:
    """Constraints for the demo environment gate."""

    allowed_servers: tuple[str, ...] = ()
    allowed_symbols: tuple[str, ...] = ()
    min_margin_free: float = 0.0
    require_trade_mode_demo: bool = True


@dataclass(frozen=True, slots=True)
class DemoValidationResult:
    """Verdict of the demo environment validation."""

    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)

    def __bool__(self) -> bool:
        return self.valid


def validate_demo_environment(
    account: BrokerAccountState,
    config: DemoValidationConfig,
    *,
    server: str | None = None,
) -> DemoValidationResult:
    """
    Validate that the connected account is a safe demo environment.

    Checks trade mode (default: must be demo), server allowlist and
    minimum free margin.
    """
    errors: list[str] = []

    if config.require_trade_mode_demo and (
        account.trade_mode not in ALLOWED_DEMO_MODES
    ):
        errors.append(
            f"account trade_mode {account.trade_mode!r} is not "
            "a demo account; only demo is allowed for F9 validation"
        )

    if config.allowed_servers and (
        server is None or server not in config.allowed_servers
    ):
        errors.append(
            f"server {server!r} not in allowed servers"
        )

    if account.margin_free < config.min_margin_free:
        errors.append(
            f"free margin {account.margin_free:.2f} below minimum "
            f"{config.min_margin_free:.2f}"
        )

    return DemoValidationResult(
        valid=not errors,
        errors=tuple(errors),
    )


def validate_broker_preconditions(
    account: BrokerAccountState,
    order: Order,
    config: OrderValidationConfig,
    *,
    trading_enabled: bool,
    kill_switch_armed: bool,
) -> DemoValidationResult:
    """
    Last-line check right before submission (roadmap §84):

    - TRADING_ENABLED must be true (activation decision);
    - kill switch must NOT be armed;
    - symbol must be allowed (when config restricts);
    - quantity must be within [min, max];
    - order must carry a stop loss (when required by config).
    """
    errors: list[str] = []

    if not trading_enabled:
        errors.append(
            "TRADING_ENABLED is false; execution is disabled "
            "(AGENTS.md §10)"
        )

    if kill_switch_armed:
        errors.append("kill switch is armed; execution blocked")

    if config.allowed_symbols and (
        order.symbol not in config.allowed_symbols
    ):
        errors.append(
            f"symbol {order.symbol!r} not in allowed symbols"
        )

    if order.quantity < config.min_quantity:
        errors.append(
            f"quantity below minimum ({config.min_quantity})"
        )

    if order.quantity > config.max_quantity:
        errors.append(
            f"quantity above maximum ({config.max_quantity})"
        )

    if config.require_stop_loss and order.stop_loss is None:
        errors.append("stop_loss is required")

    return DemoValidationResult(
        valid=not errors,
        errors=tuple(errors),
    )
