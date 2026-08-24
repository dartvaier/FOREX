from dataclasses import dataclass
from datetime import datetime, timedelta

from backtest.models.enums import Timeframe


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Immutable data interval for a backtest, using ``[date_from, date_to)``."""

    symbol: str
    timeframe: Timeframe
    date_from: datetime
    date_to: datetime
    initial_capital: float
    allow_incomplete_bars: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol must be a non-empty string")
        if not isinstance(self.timeframe, Timeframe):
            raise TypeError("timeframe must be a Timeframe")
        for name in ("date_from", "date_to"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() != timedelta(0):
                raise ValueError(f"{name} must be timezone-aware UTC")
        if self.date_to <= self.date_from:
            raise ValueError("date_to must be later than date_from")
        if not isinstance(self.initial_capital, (int, float)) or isinstance(self.initial_capital, bool) or self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if not isinstance(self.allow_incomplete_bars, bool):
            raise TypeError("allow_incomplete_bars must be a bool")
