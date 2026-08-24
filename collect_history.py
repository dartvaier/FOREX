from argparse import ArgumentParser
from datetime import datetime, timezone

import MetaTrader5 as mt5

from broker.mt5_client import MT5Client
from data.historical_data import HistoricalData

SUPPORTED_SYMBOLS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "AUDUSD",
    "USDCAD",
    "NZDUSD",
]

DEFAULT_DATE_FROM = datetime(
    2015,
    1,
    1,
    tzinfo=timezone.utc,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Download M15 historical data for a symbol "
            "(roadmap §104 multi-symbol)."
        )
    )

    parser.add_argument(
        "--symbol",
        default="EURUSD",
        choices=SUPPORTED_SYMBOLS,
        help="instrument key (default: EURUSD)",
    )

    parser.add_argument(
        "--date-from",
        default=None,
        help="inclusive start, UTC (YYYY-MM-DD); "
        "default 2015-01-01",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()

    symbol = args.symbol

    date_from = (
        datetime.fromisoformat(args.date_from)
        if args.date_from
        else DEFAULT_DATE_FROM
    )

    if date_from.tzinfo is None:
        date_from = date_from.replace(
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

    print("\nSímbolo:", symbol)
    print("Timeframe: M15")
    print("De:", date_from)
    print("Até:", date_to)

    with MT5Client() as client:

        history = HistoricalData(client)

        df = history.download(
            symbol=symbol,
            timeframe=mt5.TIMEFRAME_M15,
            date_from=date_from,
            date_to=date_to,
        )

        print("\n--- RESULTADO ---")

        print("Candles:", len(df))

        if len(df):
            print("Primeiro:", df.iloc[0]["time"])
            print("Último:", df.iloc[-1]["time"])
            print("\n--- DATASET ---")
            print(df.head())
            print("\n...")
            print(df.tail())

        path = history.save(
            df=df,
            symbol=symbol,
            timeframe_name="M15",
        )

        print("\nArquivo salvo:")
        print(path)


if __name__ == "__main__":
    main()
