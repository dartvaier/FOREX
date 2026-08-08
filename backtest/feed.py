from collections.abc import Iterator
from datetime import datetime
from numbers import Integral

import numpy as np
import pandas as pd

from backtest.models.bar import MarketBar
from backtest.models.config import BacktestConfig


class HistoricalBarFeed:
    """
    Immutable historical market-data feed used by the
    BacktestEngine.

    Responsibilities:

    - validate the input DataFrame schema
    - preserve chronological ordering
    - reject duplicate timestamps
    - preserve historical gaps
    - apply the configured evaluation interval
    - apply the incomplete-bar policy
    - convert pandas rows into immutable MarketBar objects

    The original DataFrame is never exposed to Strategy code.

    No sorting, resampling, reindexing, forward filling or
    synthetic candle generation is performed here.
    """

    REQUIRED_COLUMNS = frozenset(
        {
            "time",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
        }
    )

    def __init__(
        self,
        dataframe: pd.DataFrame,
        config: BacktestConfig,
    ) -> None:
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                "dataframe must be a pandas DataFrame"
            )

        if not isinstance(config, BacktestConfig):
            raise TypeError(
                "config must be a BacktestConfig"
            )

        self._config = config
        self._input_row_count = len(dataframe)

        self._bars = self._build_bars(dataframe)

    @property
    def config(self) -> BacktestConfig:
        return self._config

    @property
    def input_row_count(self) -> int:
        """
        Number of rows received from the source DataFrame
        before date-range and incomplete-bar filtering.
        """

        return self._input_row_count

    @property
    def bar_count(self) -> int:
        """
        Number of MarketBars available to the simulation.
        """

        return len(self._bars)

    @property
    def bars(self) -> tuple[MarketBar, ...]:
        return self._bars

    @property
    def bar_starts(self) -> tuple[datetime, ...]:
        """
        Bar timestamps suitable for SimulationClock.
        """

        return tuple(
            bar.time
            for bar in self._bars
        )

    def __len__(self) -> int:
        return len(self._bars)

    def __iter__(self) -> Iterator[MarketBar]:
        return iter(self._bars)

    def _build_bars(
        self,
        dataframe: pd.DataFrame,
    ) -> tuple[MarketBar, ...]:
        self._validate_required_columns(dataframe)

        if dataframe.empty:
            raise ValueError(
                "dataframe cannot be empty"
            )

        has_complete_column = (
            "complete" in dataframe.columns
        )

        selected_bars: list[MarketBar] = []

        previous_time: datetime | None = None

        for row_index, row in enumerate(
            dataframe.itertuples(index=False)
        ):
            bar_time = self._to_python_datetime(
                getattr(row, "time"),
                row_index=row_index,
            )

            if previous_time is not None:
                if bar_time == previous_time:
                    raise ValueError(
                        "dataframe contains duplicate timestamps"
                    )

                if bar_time < previous_time:
                    raise ValueError(
                        "dataframe timestamps must be "
                        "strictly increasing"
                    )

            previous_time = bar_time

            tick_volume = self._validate_tick_volume(
                getattr(row, "tick_volume"),
                row_index=row_index,
            )

            complete = True

            if has_complete_column:
                complete = self._validate_complete(
                    getattr(row, "complete"),
                    row_index=row_index,
                )

            bar = MarketBar(
                time=bar_time,
                open=getattr(row, "open"),
                high=getattr(row, "high"),
                low=getattr(row, "low"),
                close=getattr(row, "close"),
                tick_volume=tick_volume,
                complete=complete,
            )

            if not (
                self._config.date_from
                <= bar.time
                < self._config.date_to
            ):
                continue

            if (
                not self._config.allow_incomplete_bars
                and not bar.complete
            ):
                continue

            selected_bars.append(bar)

        if not selected_bars:
            raise ValueError(
                "no bars available for the configured "
                "backtest period"
            )

        return tuple(selected_bars)

    def _validate_required_columns(
        self,
        dataframe: pd.DataFrame,
    ) -> None:
        missing = sorted(
            self.REQUIRED_COLUMNS
            - set(dataframe.columns)
        )

        if missing:
            raise ValueError(
                "dataframe is missing required columns: "
                + ", ".join(missing)
            )

    @staticmethod
    def _to_python_datetime(
        value: object,
        *,
        row_index: int,
    ) -> datetime:
        if pd.isna(value):
            raise ValueError(
                f"time cannot be null at row {row_index}"
            )

        if isinstance(value, pd.Timestamp):
            value = value.to_pydatetime()

        if not isinstance(value, datetime):
            raise ValueError(
                "time must contain datetime values"
            )

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "time must contain timezone-aware values"
            )

        if value.utcoffset().total_seconds() != 0:
            raise ValueError(
                "time must use UTC"
            )

        return value

    @staticmethod
    def _validate_tick_volume(
        value: object,
        *,
        row_index: int,
    ) -> int:
        if (
            not isinstance(
                value,
                (Integral, np.integer),
            )
            or isinstance(
                value,
                (bool, np.bool_),
            )
            or value < 0
        ):
            raise ValueError(
                "tick_volume must be a non-negative "
                f"integer at row {row_index}"
            )

        return int(value)

    @staticmethod
    def _validate_complete(
        value: object,
        *,
        row_index: int,
    ) -> bool:
        if not isinstance(
            value,
            (bool, np.bool_),
        ):
            raise TypeError(
                "complete must contain boolean values "
                f"at row {row_index}"
            )

        return bool(value)