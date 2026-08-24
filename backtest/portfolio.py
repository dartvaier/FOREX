from dataclasses import dataclass
from datetime import datetime, timedelta

from backtest.position import Position, PositionSide
from domain.fill import Fill


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Immutable account state after a fill or mark-to-market event."""

    timestamp: datetime
    cash: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    total_commission: float
    position: Position | None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() != timedelta(0):
            raise ValueError("timestamp must be timezone-aware UTC")
        if abs(self.equity - (self.cash + self.unrealized_pnl)) > 1e-10:
            raise ValueError("equity must equal cash plus unrealized_pnl")


class Portfolio:
    """Single-symbol, one-position accounting ledger.

    It consumes execution results only. The caller supplies ``side`` for an
    opening fill because F5.1 Fill intentionally has no order-side field.
    """

    def __init__(self, *, symbol: str, initial_cash: float) -> None:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("symbol must be a non-empty string")
        if not isinstance(initial_cash, (int, float)) or isinstance(initial_cash, bool) or initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        self.symbol = symbol
        self.initial_cash = float(initial_cash)
        self._cash = float(initial_cash)
        self._realized_pnl = 0.0
        self._total_commission = 0.0
        self._position: Position | None = None
        self._consumed_fill_ids: set[str] = set()
        self._last_timestamp: datetime | None = None
        self._last_mark_price: float | None = None
        self._snapshots: list[PortfolioSnapshot] = []

    @property
    def position(self) -> Position | None:
        return self._position

    @property
    def snapshots(self) -> tuple[PortfolioSnapshot, ...]:
        return tuple(self._snapshots)

    @property
    def cash(self) -> float:
        return self._cash

    def open_position(self, fill: Fill, *, side: PositionSide) -> PortfolioSnapshot:
        self._validate_fill(fill)
        if not isinstance(side, PositionSide):
            raise TypeError("side must be a PositionSide")
        if self._position is not None:
            raise ValueError("baseline Portfolio permits only one open position")
        self._consume(fill)
        self._cash -= fill.commission
        self._total_commission += fill.commission
        self._position = Position(self.symbol, side, fill.quantity, fill.execution_price, fill.fill_time, fill.fill_id, fill.commission)
        self._last_mark_price = fill.execution_price
        return self._record(fill.fill_time)

    def close_position(self, fill: Fill) -> PortfolioSnapshot:
        self._validate_fill(fill)
        if self._position is None:
            raise ValueError("cannot close a flat Portfolio")
        if fill.quantity != self._position.quantity:
            raise ValueError("baseline Portfolio does not support partial closes")
        if fill.fill_time < self._position.entry_time:
            raise ValueError("closing fill cannot precede the opening fill")
        position = self._position
        self._consume(fill)
        gross_pnl = position.gross_unrealized_pnl(fill.execution_price)
        net_pnl = gross_pnl - position.entry_commission - fill.commission
        self._cash += gross_pnl - fill.commission
        self._realized_pnl += net_pnl
        self._total_commission += fill.commission
        self._position = None
        self._last_mark_price = None
        return self._record(fill.fill_time)

    def mark_to_market(self, *, timestamp: datetime, price: float) -> PortfolioSnapshot:
        self._validate_timestamp(timestamp)
        if self._position is None:
            raise ValueError("cannot mark a flat Portfolio")
        if price <= 0:
            raise ValueError("price must be positive")
        if self._last_timestamp is not None and timestamp < self._last_timestamp:
            raise ValueError("snapshot timestamps must be non-decreasing")
        self._last_mark_price = float(price)
        return self._record(timestamp)

    def _validate_fill(self, fill: Fill) -> None:
        if not isinstance(fill, Fill):
            raise TypeError("fill must be a Fill")
        if fill.fill_id in self._consumed_fill_ids:
            raise ValueError("fill_id has already been consumed")
        if self._last_timestamp is not None and fill.fill_time < self._last_timestamp:
            raise ValueError("fill_time must be non-decreasing")

    def _consume(self, fill: Fill) -> None:
        self._consumed_fill_ids.add(fill.fill_id)

    def _record(self, timestamp: datetime) -> PortfolioSnapshot:
        self._validate_timestamp(timestamp)
        unrealized = 0.0 if self._position is None else self._position.gross_unrealized_pnl(self._last_mark_price)
        snapshot = PortfolioSnapshot(timestamp, self._cash, self._cash + unrealized, self._realized_pnl, unrealized, self._total_commission, self._position)
        self._last_timestamp = timestamp
        self._snapshots.append(snapshot)
        return snapshot

    @staticmethod
    def _validate_timestamp(timestamp: datetime) -> None:
        if not isinstance(timestamp, datetime) or timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
            raise ValueError("timestamp must be timezone-aware UTC")
