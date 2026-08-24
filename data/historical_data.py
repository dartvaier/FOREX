from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from broker.mt5_client import MT5Client


class HistoricalData:
    """
    Responsável por coletar, validar e persistir
    dados históricos de mercado.
    """

    def __init__(
        self,
        client: "MT5Client",
        base_path: str = "data/raw"
    ):
        self.client = client
        self.base_path = Path(base_path)

    def download(
        self,
        symbol: str,
        timeframe,
        date_from: datetime,
        date_to: datetime,
        chunk_days: int = 90,
    ) -> pd.DataFrame:

        if date_from >= date_to:
            raise ValueError(
                "date_from precisa ser anterior a date_to."
        )

        chunks = []

        current_from = date_from

        print(
            f"\n[INFO] Iniciando coleta histórica "
            f"em blocos de {chunk_days} dias..."
        )

        while current_from < date_to:

            current_to = min(
                current_from + timedelta(days=chunk_days),
                date_to
            )

            print(
                f"[DOWNLOAD] "
                f"{current_from.date()} -> "
                f"{current_to.date()}",
                end=""
            )

            try:
                rates = self.client.rates_range(
                    symbol=symbol,
                    timeframe=timeframe,
                    date_from=current_from,
                    date_to=current_to,
                )

            except RuntimeError as exc:
                print(f" | ERRO: {exc}")

                # Não derrubamos toda a coleta por causa
                # de apenas um intervalo.
                current_from = current_to
                continue

            if rates is None or len(rates) == 0:
                print(" | 0 candles")

            else:
                chunk_df = pd.DataFrame(rates)

                chunk_df["time"] = pd.to_datetime(
                    chunk_df["time"],
                    unit="s",
                    utc=True
                )
                
                # Garante que o MT5 realmente devolveu
                # candles pertencentes à janela solicitada.
                chunk_df = chunk_df[
                    (chunk_df["time"] >= current_from)
                    & (chunk_df["time"] < current_to)
                ].copy()

                if chunk_df.empty:
                    print(" | 0 candles válidos")

                else:
                    chunks.append(chunk_df)

                    print(
                        f" | {len(chunk_df)} candles"
                    )

            current_from = current_to

        if not chunks:
            raise RuntimeError(
                f"Nenhum histórico foi encontrado para {symbol}."
            )

        # ---------------------------------------------------------
        # Unir todos os blocos
        # ---------------------------------------------------------

        df = pd.concat(
            chunks,
            ignore_index=True
        )

        columns = [
            "time",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
            "spread",
            "real_volume",
        ]

        df = df[columns]

        # Como copy_rates_range inclui os extremos,
        # duas janelas podem compartilhar uma barra.
        df = (
            df
            .sort_values("time")
            .drop_duplicates(
                subset=["time"],
                keep="first"
            )
            .reset_index(drop=True)
        )

        self.validate(df)

        return df

    def validate(self, df: pd.DataFrame) -> None:

        if df.empty:
            raise ValueError("Dataset vazio.")

        # -----------------------------------------
        # UTC
        # -----------------------------------------
        if df["time"].dt.tz is None:
            raise ValueError(
                "Timestamps não possuem timezone."
            )

        if str(df["time"].dt.tz) != "UTC":
            raise ValueError(
                "Timestamps não estão em UTC."
            )

        # -----------------------------------------
        # Ordem temporal
        # -----------------------------------------
        if not df["time"].is_monotonic_increasing:
            raise ValueError(
                "Dados fora de ordem cronológica."
            )

        # -----------------------------------------
        # Duplicados
        # -----------------------------------------
        duplicates = df["time"].duplicated().sum()

        if duplicates > 0:
            raise ValueError(
                f"Foram encontrados {duplicates} "
                "timestamps duplicados."
            )

        # -----------------------------------------
        # OHLC
        # -----------------------------------------
        if not (df["high"] >= df["low"]).all():
            raise ValueError(
                "Existem candles com High < Low."
            )

        if not (df["high"] >= df["open"]).all():
            raise ValueError(
                "Existem candles com High < Open."
            )

        if not (df["high"] >= df["close"]).all():
            raise ValueError(
                "Existem candles com High < Close."
            )

        if not (df["low"] <= df["open"]).all():
            raise ValueError(
                "Existem candles com Low > Open."
            )

        if not (df["low"] <= df["close"]).all():
            raise ValueError(
                "Existem candles com Low > Close."
            )

        # -----------------------------------------
        # Preços
        # -----------------------------------------
        price_columns = [
            "open",
            "high",
            "low",
            "close",
        ]

        for column in price_columns:

            if not (df[column] > 0).all():
                raise ValueError(
                    f"Preços inválidos em {column}."
                )

    def save(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe_name: str,
    ) -> Path:

        directory = self.base_path / symbol

        directory.mkdir(
            parents=True,
            exist_ok=True
        )

        filepath = directory / (
            f"{timeframe_name}.parquet"
        )

        df.to_parquet(
            filepath,
            index=False
        )

        return filepath

    def load(
        self,
        symbol: str,
        timeframe_name: str,
    ) -> pd.DataFrame:

        filepath = (
            self.base_path
            / symbol
            / f"{timeframe_name}.parquet"
        )

        if not filepath.exists():
            raise FileNotFoundError(
                f"Arquivo não encontrado: {filepath}"
            )

        df = pd.read_parquet(filepath)

        self.validate(df)

        return df
