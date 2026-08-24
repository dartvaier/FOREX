from argparse import ArgumentParser
from pathlib import Path

import pandas as pd

from data.timeframe_builder import TimeframeBuilder

SUPPORTED_SYMBOLS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "AUDUSD",
    "USDCAD",
    "NZDUSD",
]


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build H1/H4 datasets from M15 raw data "
            "(roadmap §104 multi-symbol)."
        )
    )

    parser.add_argument(
        "--symbol",
        default="EURUSD",
        choices=SUPPORTED_SYMBOLS,
        help="instrument key (default: EURUSD)",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()

    symbol = args.symbol

    source = Path(f"data/raw/{symbol}/M15.parquet")
    output_directory = Path(f"data/processed/{symbol}")

    print("=" * 70)
    print("FOREX BOT - TIMEFRAME BUILDER")
    print("=" * 70)
    print("Símbolo:", symbol)

    df = pd.read_parquet(source)

    builder = TimeframeBuilder()

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    for timeframe in ["H1", "H4"]:

        print(
            f"\nConstruindo {timeframe}..."
        )

        result = builder.build(
            df=df,
            timeframe=timeframe,
        )

        output = (
            output_directory
            / f"{timeframe}.parquet"
        )

        result.to_parquet(
            output,
            index=False,
        )

        complete = int(
            result["complete"].sum()
        )

        incomplete = int(
            (~result["complete"]).sum()
        )

        print(
            f"{timeframe}: {len(result)} candles "
            f"({complete} completos, "
            f"{incomplete} incompletos)"
        )
        print(
            "Salvo:",
            output,
        )


if __name__ == "__main__":
    main()
