"""
F9 Execution Layer: broker-facing interface and state types.

This module defines the CONTRACT between the research platform and any
live/demo broker adapter (MT5Execution in a later block). It has NO
MetaTrader dependency: everything here is testable without MT5 and can
be driven by a simulated adapter for engineering tests.

Roadmap §82-83:

    MarketData -> Strategy -> Risk -> MT5Execution -> MetaTrader 5 Demo

TRADING_ENABLED=false remains the platform default (AGENTS.md §10,
roadmap §81); this interface is the engineering surface that a Demo
activation will plug into.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from backtest.models.enums import OrderStatus, OrderSide
from backtest.models.fill import Fill
from backtest.models.order import Order


@dataclass(frozen=True, slots=True)
class BrokerPosition:
    """
    A position as reported by the broker.

    identifier: broker ticket / position id.
    """

    identifier: str
    symbol: str
    side: OrderSide
    quantity: float
    entry_price: float
    open_time: datetime
    current_price: float | None = None

    def __post_init__(self) -> None:
        if not self.identifier:
            raise ValueError("identifier cannot be empty")

        if not self.symbol:
            raise ValueError("symbol cannot be empty")

        if self.quantity <= 0:
            raise ValueError("quantity must be positive")

        if self.entry_price <= 0:
            raise ValueError("entry_price must be positive")

        if self.current_price is not None and self.current_price <= 0:
            raise ValueError("current_price must be positive")


@dataclass(frozen=True, slots=True)
class BrokerAccountState:
    """
    Account snapshot from the broker: balance, equity, free margin
    and the open positions.

    All timestamps are timezone-aware UTC (repo invariant).
    """

    balance: float
    equity: float
    margin_free: float
    currency: str
    positions: tuple[BrokerPosition, ...] = ()
    trade_mode: str = "unknown"

    def __post_init__(self) -> None:
        if self.balance < 0:
            raise ValueError("balance cannot be negative")

        if self.equity < 0:
            raise ValueError("equity cannot be negative")

        if self.margin_free < 0:
            raise ValueError("margin_free cannot be negative")

        if not self.currency:
            raise ValueError("currency cannot be empty")

        if not self.trade_mode:
            raise ValueError("trade_mode cannot be empty")


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    """
    Result of submitting/cancelling an order at the broker.

    status == FILLED implies a fill; a fill attached to a non-FILLED
    report is invalid (caught in __post_init__).
    """

    order_id: str
    status: OrderStatus
    message: str = ""
    broker_order_id: str | None = None
    fill: Fill | None = None

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("order_id cannot be empty")

        if self.status == OrderStatus.FILLED and self.fill is None:
            raise ValueError(
                "FILLED report must carry a fill"
            )

        if self.fill is not None and self.status != OrderStatus.FILLED:
            raise ValueError(
                "fill attached to a non-FILLED report"
            )


class ExecutionInterface(ABC):
    """
    Broker adapter contract.

    Implementations (e.g. MT5Execution) translate these calls to the
    broker API. All methods are synchronous for simplicity; adapters
    that need async wrap their transport internally.
    """

    @abstractmethod
    def submit(self, order: Order) -> ExecutionReport:
        """Submit an order to the broker."""

    @abstractmethod
    def cancel(self, order_id: str) -> ExecutionReport:
        """Cancel a pending order by platform order id."""

    @abstractmethod
    def fetch_account(self) -> BrokerAccountState:
        """Fetch the current account snapshot."""

    @abstractmethod
    def fetch_positions(
        self,
        symbol: str | None = None,
    ) -> tuple[BrokerPosition, ...]:
        """Fetch open positions, optionally filtered by symbol."""

    @abstractmethod
    def ping(self) -> bool:
        """Broker connectivity check."""

    @abstractmethod
    def close(self) -> None:
        """Release adapter resources (disconnect)."""
