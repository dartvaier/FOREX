from pathlib import Path

import pandas as pd

from data.timeframe_builder import TimeframeBuilder


SOURCE = Path(
    "data/raw/EURUSD/M15.parquet"
)

OUTPUT_DIRECTORY = Path(
    "data/processed/EURUSD"
)


def main():

    print("=" * 70)
    print("FOREX BOT - TIMEFRAME BUILDER")
    print("=" * 70)

    df = pd.read_parquet(SOURCE)

    builder = TimeframeBuilder()

    OUTPUT_DIRECTORY.mkdir(
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
            OUTPUT_DIRECTORY
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
            "Candles:",
            len(result)
        )

        print(
            "Completos:",
            complete
        )

        print(
            "Incompletos:",
            incomplete
        )

        print(
            "Primeiro:",
            result["time"].min()
        )

        print(
            "Último:",
            result["time"].max()
        )

        print(
            "Salvo em:",
            output
        )


if __name__ == "__main__":
    main()