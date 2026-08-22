from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data.jforex_importer import (
    JForexImportError,
    import_jforex_directory,
    read_jforex_csv,
)


def _write_csv(
    path: Path,
    *,
    rows: int = 4,
    delimiter: str = ",",
    ask_offset: float = 0.00020,
) -> None:
    lines = [
        delimiter.join(
            [
                "Time (EET)",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume ",
            ]
        )
    ]

    start = pd.Timestamp("2020-01-02 00:00:00")
    is_ask = "Ask" in path.name

    for index in range(rows):
        timestamp = start + pd.Timedelta(minutes=15 * index)
        base = 1.10000 + index * 0.00010
        offset = ask_offset if is_ask else 0.0
        open_ = base + offset
        high = base + 0.00050 + offset
        low = base - 0.00030 + offset
        close = base + 0.00010 + offset

        lines.append(
            delimiter.join(
                [
                    timestamp.strftime("%Y.%m.%d %H:%M:%S"),
                    f"{open_:.5f}",
                    f"{high:.5f}",
                    f"{low:.5f}",
                    f"{close:.5f}",
                    str(100 + index),
                ]
            )
        )

    path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def test_read_jforex_csv_normalizes_columns_and_converts_eet_to_utc(
    tmp_path: Path,
) -> None:
    path = tmp_path / "EURUSD_15 Mins_Bid_2020.01.02_2020.01.02.csv"
    _write_csv(path)

    frame = read_jforex_csv(path)

    assert list(frame.columns) == [
        "time",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
    ]
    assert frame["time"].iloc[0] == pd.Timestamp(
        "2020-01-01 22:00:00",
        tz="UTC",
    )
    assert frame["close"].iloc[0] == pytest.approx(1.10010)


def test_import_directory_combines_bid_ask_into_mid_and_spread_points(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "import"
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    input_dir.mkdir()

    _write_csv(
        input_dir / "EURUSD_15 Mins_Bid_2020.01.02_2020.01.02.csv"
    )
    _write_csv(
        input_dir / "EURUSD_15 Mins_Ask_2020.01.02_2020.01.02.csv"
    )

    results = import_jforex_directory(
        input_dir,
        raw_base_path=raw_dir,
        processed_base_path=processed_dir,
        symbols=("EURUSD",),
        build_timeframes=False,
    )

    assert len(results) == 1
    assert results[0].symbol == "EURUSD"
    assert results[0].rows == 4

    m15 = pd.read_parquet(raw_dir / "EURUSD" / "M15.parquet")

    assert m15["open"].iloc[0] == pytest.approx(1.10010)
    assert m15["close"].iloc[0] == pytest.approx(1.10020)
    assert m15["spread"].iloc[0] == pytest.approx(20.0)
    assert m15["real_volume"].iloc[0] == 0


def test_import_directory_accepts_semicolon_exports(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "import"
    input_dir.mkdir()

    _write_csv(
        input_dir / "EURUSD_15 Mins_Bid_2020.01.02_2020.01.02.csv",
        delimiter=";",
    )
    _write_csv(
        input_dir / "EURUSD_15 Mins_Ask_2020.01.02_2020.01.02.csv",
        delimiter=";",
    )

    results = import_jforex_directory(
        input_dir,
        raw_base_path=tmp_path / "raw",
        processed_base_path=tmp_path / "processed",
        symbols=("EURUSD",),
        build_timeframes=False,
    )

    assert results[0].rows == 4


def test_read_jforex_csv_repairs_rounded_extrema(
    tmp_path: Path,
) -> None:
    path = tmp_path / "EURUSD_15 Mins_Bid_2020.01.02_2020.01.02.csv"
    path.write_text(
        "\n".join(
            [
                "Time (EET),Open,High,Low,Close,Volume ",
                "2020.01.02 00:00:00,1.10000,1.09999,1.09950,1.10010,100",
            ]
        ),
        encoding="utf-8",
    )

    frame = read_jforex_csv(path)

    assert frame["high"].iloc[0] == pytest.approx(1.10010)

    with pytest.raises(
        JForexImportError,
        match="High < Open",
    ):
        read_jforex_csv(path, repair_ohlc=False)


def test_import_directory_rejects_missing_bid_or_ask_pair(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "import"
    input_dir.mkdir()

    _write_csv(
        input_dir / "EURUSD_15 Mins_Bid_2020.01.02_2020.01.02.csv"
    )

    with pytest.raises(
        JForexImportError,
        match="both Bid and Ask",
    ):
        import_jforex_directory(
            input_dir,
            raw_base_path=tmp_path / "raw",
            processed_base_path=tmp_path / "processed",
            symbols=("EURUSD",),
        )


def test_import_directory_rejects_crossed_bid_ask(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "import"
    input_dir.mkdir()

    _write_csv(
        input_dir / "EURUSD_15 Mins_Bid_2020.01.02_2020.01.02.csv"
    )
    _write_csv(
        input_dir / "EURUSD_15 Mins_Ask_2020.01.02_2020.01.02.csv",
        ask_offset=-0.00010,
    )

    with pytest.raises(
        JForexImportError,
        match="Ask open below Bid open",
    ):
        import_jforex_directory(
            input_dir,
            raw_base_path=tmp_path / "raw",
            processed_base_path=tmp_path / "processed",
            symbols=("EURUSD",),
        )


def test_import_directory_repairs_one_point_crossed_close(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "import"
    input_dir.mkdir()

    _write_csv(
        input_dir / "EURUSD_15 Mins_Bid_2020.01.02_2020.01.02.csv",
        rows=1,
    )
    _write_csv(
        input_dir / "EURUSD_15 Mins_Ask_2020.01.02_2020.01.02.csv",
        rows=1,
        ask_offset=0.00020,
    )

    ask_path = input_dir / "EURUSD_15 Mins_Ask_2020.01.02_2020.01.02.csv"
    ask_path.write_text(
        ask_path.read_text(encoding="utf-8").replace(
            "1.10030",
            "1.10009",
        ),
        encoding="utf-8",
    )

    import_jforex_directory(
        input_dir,
        raw_base_path=tmp_path / "raw",
        processed_base_path=tmp_path / "processed",
        symbols=("EURUSD",),
        build_timeframes=False,
    )

    m15 = pd.read_parquet(
        tmp_path / "raw" / "EURUSD" / "M15.parquet"
    )

    assert m15["spread"].iloc[0] == pytest.approx(0.0)


def test_import_directory_can_build_processed_timeframes(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "import"
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    input_dir.mkdir()

    _write_csv(
        input_dir / "EURUSD_15 Mins_Bid_2020.01.02_2020.01.02.csv",
        rows=16,
    )
    _write_csv(
        input_dir / "EURUSD_15 Mins_Ask_2020.01.02_2020.01.02.csv",
        rows=16,
    )

    import_jforex_directory(
        input_dir,
        raw_base_path=raw_dir,
        processed_base_path=processed_dir,
        symbols=("EURUSD",),
    )

    h1 = pd.read_parquet(processed_dir / "EURUSD" / "H1.parquet")
    h4 = pd.read_parquet(processed_dir / "EURUSD" / "H4.parquet")

    assert len(h1) == 4
    assert len(h4) == 2
    assert h1["complete"].all()
    assert int(h4["source_bar_count"].sum()) == 16
