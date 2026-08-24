from collections.abc import Iterator
from datetime import datetime
from numbers import Integral

import pandas as pd

from backtest.models.bar import MarketBar
from backtest.models.config import BacktestConfig


class HistoricalBarFeed:
    """Validated immutable bars; never exposes its source DataFrame to Strategy code."""

    _REQUIRED = frozenset({"time", "open", "high", "low", "close", "tick_volume"})

    def __init__(self, dataframe: pd.DataFrame, config: BacktestConfig) -> None:
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("dataframe must be a pandas DataFrame")
        if not isinstance(config, BacktestConfig):
            raise TypeError("config must be a BacktestConfig")
        missing = self._REQUIRED - set(dataframe.columns)
        if missing:
            raise ValueError("dataframe is missing required columns: " + ", ".join(sorted(missing)))
        self.config = config
        bars: list[MarketBar] = []
        previous: datetime | None = None
        for index, row in enumerate(dataframe.itertuples(index=False)):
            time = getattr(row, "time")
            if isinstance(time, pd.Timestamp):
                time = time.to_pydatetime()
            if not isinstance(time, datetime) or time.tzinfo is None or time.utcoffset() is None:
                raise ValueError(f"time must be timezone-aware at row {index}")
            if time.utcoffset().total_seconds() != 0:
                raise ValueError("time must use UTC")
            if previous is not None and time <= previous:
                raise ValueError("dataframe timestamps must be strictly increasing")
            previous = time
            volume = getattr(row, "tick_volume")
            if not isinstance(volume, Integral) or isinstance(volume, bool) or volume < 0:
                raise ValueError("tick_volume must be a non-negative integer")
            complete = getattr(row, "complete", True)
            bar = MarketBar(time, getattr(row, "open"), getattr(row, "high"), getattr(row, "low"), getattr(row, "close"), int(volume), complete)
            if config.date_from <= time < config.date_to and (config.allow_incomplete_bars or bar.complete):
                bars.append(bar)
        if not bars:
            raise ValueError("no bars available for the configured backtest period")
        self.bars = tuple(bars)
        self.bar_starts = tuple(bar.time for bar in self.bars)

    def __len__(self) -> int:
        return len(self.bars)

    def __iter__(self) -> Iterator[MarketBar]:
        return iter(self.bars)
