from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from research.scalping_spread_profile import (
    load_scalping_frame,
    metric_row,
    render_csv,
    session_label,
    spread_profile,
    write_profile,
)


def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2020-01-02 08:00:00+00:00",
                    "2020-01-02 12:00:00+00:00",
                    "2020-01-02 14:00:00+00:00",
                    "2020-01-02 23:00:00+00:00",
                ],
                utc=True,
            ),
            "spread": [4.0, 5.0, 8.0, 20.0],
        }
    )


def test_session_label_uses_real_timezones() -> None:
    assert session_label(
        pd.Timestamp("2020-01-02 08:00:00", tz="UTC")
    ) == "london_morning"
    assert session_label(
        pd.Timestamp("2020-01-02 14:00:00", tz="UTC")
    ) == "london_ny_overlap"
    assert session_label(
        pd.Timestamp("2020-01-02 23:00:00", tz="UTC")
    ) == "off_session"


def test_metric_row_calculates_spread_distribution() -> None:
    row = metric_row(
        pd.Series([0.4, 0.5, 0.8, 2.0]),
        symbol="USDJPY",
        timeframe="M1",
        bucket="all",
        key="all",
    )

    assert row["rows"] == 4
    assert row["spread_pips_median"] == pytest.approx(0.65)
    assert row["spread_pips_p90"] == pytest.approx(1.64)


def test_spread_profile_builds_hour_and_session_rows() -> None:
    profile = spread_profile(
        frame(),
        symbol="USDJPY",
        timeframe="M1",
    )

    rows = profile["rows"]

    assert profile["schema_version"] == "scalping-spread-profile/0.1.0"
    assert rows[0]["bucket"] == "all"
    assert rows[0]["spread_pips_median"] == pytest.approx(0.65)
    assert {
        row["bucket"]
        for row in rows
    } >= {"utc_hour", "london_hour", "ny_hour", "session"}


def test_write_profile_outputs_json_and_csv(tmp_path: Path) -> None:
    profile = spread_profile(
        frame(),
        symbol="USDJPY",
        timeframe="M1",
    )
    json_path, csv_path = write_profile(
        profile,
        out_dir=tmp_path,
    )

    assert json_path.exists()
    assert csv_path.exists()
    assert render_csv(profile["rows"]).startswith("symbol,timeframe,bucket")


def test_load_scalping_frame_reads_expected_location(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    path = raw_dir / "USDJPY" / "M1.parquet"
    path.parent.mkdir(
        parents=True,
    )
    frame().to_parquet(
        path,
        index=False,
    )

    loaded = load_scalping_frame(
        symbol="USDJPY",
        timeframe="M1",
        raw_base_path=raw_dir,
        processed_base_path=tmp_path / "processed",
    )

    assert len(loaded) == 4
