import json
from pathlib import Path

import pandas as pd


DATA_FILE = Path(
    "data/raw/EURUSD/M15.parquet"
)

OUTPUT_FILE = Path(
    "data/metadata/EURUSD_M15.json"
)


def main():

    df = pd.read_parquet(DATA_FILE)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    metadata = {
        "symbol": "EURUSD",
        "timeframe": "M15",

        "source": "MetaQuotes-Demo",

        "timezone": "UTC",

        "first_bar": (
            df["time"]
            .min()
            .isoformat()
        ),

        "last_bar": (
            df["time"]
            .max()
            .isoformat()
        ),

        "bars": len(df),

        "duplicates": int(
            df["time"]
            .duplicated()
            .sum()
        ),

        "missing_values": int(
            df.isna()
            .sum()
            .sum()
        ),

        "spread_field_available": True,

        "spread_reliable_for_execution": False,

        "real_volume_reliable": False,

        "tick_volume_available": True,

        "usage": "development_and_research",

        "notes": [
            "OHLC validated.",
            "Timestamps normalized to UTC.",
            "Historical spread field is inconsistent across periods.",
            "Real volume field changes behavior between 2015-2017 and 2018+.",
            "Dataset contains expected weekend gaps and some intraweek gaps.",
        ],
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print(
        "Metadata salvo em:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()