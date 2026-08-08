import pandas as pd


FILE = "data/raw/EURUSD/M15.parquet"


def main():
    print("=" * 70)
    print("FOREX BOT - HISTORICAL DATA QUALITY")
    print("=" * 70)

    df = pd.read_parquet(FILE)

    print("\n--- DATASET ---")

    print("Candles:", len(df))
    print("Primeiro:", df["time"].min())
    print("Último:", df["time"].max())

    # ---------------------------------------------------------
    # DUPLICADOS
    # ---------------------------------------------------------

    duplicates = df["time"].duplicated().sum()

    print("\n--- DUPLICADOS ---")
    print("Timestamps duplicados:", duplicates)

    # ---------------------------------------------------------
    # VALORES AUSENTES
    # ---------------------------------------------------------

    print("\n--- NULL VALUES ---")
    print(df.isna().sum())

    # ---------------------------------------------------------
    # OHLC
    # ---------------------------------------------------------

    invalid_ohlc = (
        (df["high"] < df["low"])
        | (df["high"] < df["open"])
        | (df["high"] < df["close"])
        | (df["low"] > df["open"])
        | (df["low"] > df["close"])
    )

    print("\n--- OHLC ---")
    print(
        "Candles OHLC inválidos:",
        invalid_ohlc.sum()
    )

    # ---------------------------------------------------------
    # COBERTURA POR ANO
    # ---------------------------------------------------------

    df["year"] = df["time"].dt.year

    yearly = (
        df
        .groupby("year")
        .size()
    )

    print("\n--- CANDLES POR ANO ---")

    print(yearly)

    # ---------------------------------------------------------
    # GAPS
    # ---------------------------------------------------------

    df = df.sort_values("time").copy()

    df["delta"] = df["time"].diff()
    
    df["previous_time"] = df["time"].shift(1)

    expected = pd.Timedelta(minutes=15)

    gaps = df[
        df["delta"] > expected
    ].copy()


    def crosses_weekend(start, end):
        """
        Retorna True se o intervalo atravessar
        sábado ou domingo.
        """

        if pd.isna(start):
            return False

        days = pd.date_range(
            start=start.normalize(),
            end=end.normalize(),
            freq="D",
            tz="UTC",
        )

        return any(
            day.weekday() >= 5
            for day in days
        )


    gaps["crosses_weekend"] = gaps.apply(
        lambda row: crosses_weekend(
            row["previous_time"],
            row["time"],
        ),
        axis=1,
    )

    weekend_gaps = gaps[
        gaps["crosses_weekend"]
    ]

    intraweek_gaps = gaps[
        ~gaps["crosses_weekend"]
    ]


    print("\n--- GAPS ---")

    print("Total:", len(gaps))

    print(
        "Atravessam fim de semana:",
        len(weekend_gaps)
    )

    print(
        "Inteiramente em dias úteis:",
        len(intraweek_gaps)
    )


    if not intraweek_gaps.empty:

        print(
            "\n--- MAIORES GAPS EM DIAS ÚTEIS ---"
        )

        print(
            intraweek_gaps[
                [
                    "previous_time",
                    "time",
                    "delta",
                ]
            ]
            .sort_values(
                "delta",
                ascending=False,
            )
            .head(30)
            .to_string(index=False)
        )
    print("\n--- REAL VOLUME POR ANO ---")

    real_volume_yearly = (
        df
        .groupby("year")
        .agg(
            candles=("real_volume", "size"),
            real_volume_nonzero=(
                "real_volume",
                lambda x: (x > 0).sum()
            ),
        )
    )

    real_volume_yearly[
        "percent_nonzero"
    ] = (
        real_volume_yearly[
            "real_volume_nonzero"
        ]
        / real_volume_yearly["candles"]
        * 100
    )

    print(real_volume_yearly)

if __name__ == "__main__":
    main()