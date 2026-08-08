from __future__ import annotations

import MetaTrader5 as mt5
import pandas as pd

from broker.mt5_client import MT5Client


class MarketData:
    """
    Camada responsável por transformar dados brutos
    do broker em dados utilizáveis pelo sistema.
    """

    def __init__(self, client: MT5Client):
        self.client = client

    def get_closed_bars(
        self,
        symbol: str,
        timeframe=mt5.TIMEFRAME_M15,
        count: int = 100
    ) -> pd.DataFrame:

        # start_pos = 1:
        # ignora deliberadamente a barra corrente.
        rates = self.client.rates(
            symbol=symbol,
            timeframe=timeframe,
            start_pos=1,
            count=count
        )

        df = pd.DataFrame(rates)

        if df.empty:
            raise RuntimeError(
                f"Nenhum candle retornado para {symbol}"
            )

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s",
            utc=True
        )

        df = df[
            [
                "time",
                "open",
                "high",
                "low",
                "close",
                "tick_volume",
                "spread",
                "real_volume",
            ]
        ]

        return df.sort_values("time").reset_index(drop=True)

    def get_current_quote(self, symbol: str) -> dict:
        info = self.client.symbol_info(symbol)
        tick = self.client.current_tick(symbol)

        point = info.point

        if info.digits in (3, 5):
            pip_size = point * 10
        else:
            pip_size = point

        spread_price = tick.ask - tick.bid

        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "point": point,
            "pip_size": pip_size,
            "spread_points": spread_price / point,
            "spread_pips": spread_price / pip_size,
        }