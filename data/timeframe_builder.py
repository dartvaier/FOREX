from __future__ import annotations

import pandas as pd


class TimeframeBuilder:
    """
    Constrói timeframes superiores a partir
    de candles M15 previamente validados.
    """

    TIMEFRAMES = {
        "H1": {
            "rule": "1h",
            "expected_bars": 4,
        },
        "H4": {
            "rule": "4h",
            "expected_bars": 16,
        },
    }

    def build(
        self,
        df: pd.DataFrame,
        timeframe: str,
    ) -> pd.DataFrame:

        timeframe = timeframe.upper()

        if timeframe not in self.TIMEFRAMES:
            raise ValueError(
                f"Timeframe não suportado: {timeframe}"
            )

        self._validate_source(df)

        config = self.TIMEFRAMES[timeframe]

        rule = config["rule"]
        expected_bars = config["expected_bars"]

        source = (
            df
            .sort_values("time")
            .copy()
        )

        source = source.set_index("time")

        resampled = source.resample(
            rule,
            label="left",
            closed="left",
            origin="epoch",
        ).agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            tick_volume=("tick_volume", "sum"),
            source_bar_count=("close", "count"),
        )

        # Remove intervalos completamente vazios,
        # como finais de semana.
        resampled = resampled[
            resampled["source_bar_count"] > 0
        ].copy()

        resampled[
            "expected_bar_count"
        ] = expected_bars

        resampled["complete"] = (
            resampled["source_bar_count"]
            == expected_bars
        )

        resampled = (
            resampled
            .reset_index()
            .sort_values("time")
            .reset_index(drop=True)
        )

        self._validate_result(
            resampled
        )

        return resampled

    def _validate_source(
        self,
        df: pd.DataFrame,
    ) -> None:

        required = {
            "time",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
        }

        missing = required - set(df.columns)

        if missing:
            raise ValueError(
                f"Colunas ausentes: {sorted(missing)}"
            )

        if df.empty:
            raise ValueError(
                "Dataset de origem está vazio."
            )

        if df["time"].dt.tz is None:
            raise ValueError(
                "Dataset precisa possuir timezone."
            )

        if str(df["time"].dt.tz) != "UTC":
            raise ValueError(
                "Dataset precisa estar em UTC."
            )

    def _validate_result(
        self,
        df: pd.DataFrame,
    ) -> None:

        if df.empty:
            raise ValueError(
                "Resample resultou em dataset vazio."
            )

        if df["time"].duplicated().any():
            raise ValueError(
                "Timeframe gerado possui timestamps duplicados."
            )

        if not df["time"].is_monotonic_increasing:
            raise ValueError(
                "Timeframe gerado está fora de ordem."
            )

        if not (
            df["high"] >= df["low"]
        ).all():
            raise ValueError(
                "Timeframe contém High < Low."
            )

        if not (
            df["high"] >= df["open"]
        ).all():
            raise ValueError(
                "Timeframe contém High < Open."
            )

        if not (
            df["high"] >= df["close"]
        ).all():
            raise ValueError(
                "Timeframe contém High < Close."
            )

        if not (
            df["low"] <= df["open"]
        ).all():
            raise ValueError(
                "Timeframe contém Low > Open."
            )

        if not (
            df["low"] <= df["close"]
        ).all():
            raise ValueError(
                "Timeframe contém Low > Close."
            )