from datetime import datetime, timezone

import MetaTrader5 as mt5

from broker.mt5_client import MT5Client
from data.historical_data import HistoricalData


SYMBOL = "EURUSD"


def main():

    date_from = datetime(
        2015,
        1,
        1,
        tzinfo=timezone.utc
    )

    date_to = datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    )

    print("=" * 70)
    print("FOREX BOT - HISTORICAL DATA")
    print("=" * 70)

    print("\nSímbolo:", SYMBOL)
    print("Timeframe: M15")
    print("De:", date_from)
    print("Até:", date_to)

    with MT5Client() as client:

        history = HistoricalData(client)

        df = history.download(
            symbol=SYMBOL,
            timeframe=mt5.TIMEFRAME_M15,
            date_from=date_from,
            date_to=date_to,
        )

        print("\n--- RESULTADO ---")

        print("Candles:", len(df))
        print("Primeiro:", df.iloc[0]["time"])
        print("Último:", df.iloc[-1]["time"])

        print("\n--- DATASET ---")

        print(df.head())
        print("\n...")
        print(df.tail())

        path = history.save(
            df=df,
            symbol=SYMBOL,
            timeframe_name="M15",
        )

        print("\nArquivo salvo:")
        print(path)


if __name__ == "__main__":
    main()