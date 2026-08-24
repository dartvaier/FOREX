import pytest
import pandas as pd

from research.h07_dukascopy_tick_audit import (
    audit_tick_file,
    deduplicate_h07_rows,
    is_canonical_tick_export,
    read_tick_csv,
    summarize_rows,
)


def test_read_tick_csv_calculates_spread_pips(tmp_path):
    path = tmp_path / "GBPUSD_Ticks_2026.04.13_2026.04.13.csv"
    path.write_text(
        "\n".join(
            [
                "Time (EET),Ask,Bid,AskVolume,BidVolume",
                "2026.04.13 03:00:00.100,1.25010,1.25000,0.9,1.8",
                "2026.04.13 03:00:00.200,1.25008,1.25002,0.9,0.9",
            ]
        ),
        encoding="utf-8",
    )

    ticks = read_tick_csv(path)

    assert list(ticks.columns) == [
        "Time (EET)",
        "Ask",
        "Bid",
        "AskVolume",
        "BidVolume",
        "spread_pips",
    ]
    assert ticks["spread_pips"].tolist() == pytest.approx([1.0, 0.6])


def test_read_tick_csv_rejects_missing_required_columns(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text(
        "Time (EET),Ask\n2026.04.13 03:00:00.100,1.25010\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing columns"):
        read_tick_csv(path)


def test_is_canonical_tick_export_rejects_duplicate_suffix(tmp_path):
    canonical = tmp_path / "GBPUSD_Ticks_2022.01.01_2022.12.31.csv"
    duplicate = tmp_path / "GBPUSD_Ticks_2022.01.03_2022.01.03_(1).csv"

    assert is_canonical_tick_export(canonical, symbol="GBPUSD") is True
    assert is_canonical_tick_export(duplicate, symbol="GBPUSD") is False


def test_audit_tick_file_excludes_empty_tick_file(tmp_path):
    path = tmp_path / "GBPUSD_Ticks_2025.01.05_2025.01.05.csv"
    path.write_text(
        "Time (EET),Ask,Bid,AskVolume,BidVolume\n",
        encoding="utf-8",
    )

    rows = audit_tick_file(
        path,
        symbol="GBPUSD",
        events_by_date={},
        m15=None,  # type: ignore[arg-type]
    )
    row = rows[0]

    assert row["included_h07"] is False
    assert row["exclusion_reason"] == "empty_tick_file"
    assert row["date"] == "2025-01-05"
    assert row["ticks"] == 0


def test_audit_tick_file_splits_multi_day_file_by_h07_date(tmp_path):
    path = tmp_path / "GBPUSD_Ticks_2026.04.13_2026.04.20.csv"
    path.write_text(
        "\n".join(
            [
                "Time (EET),Ask,Bid,AskVolume,BidVolume",
                "2026.04.13 03:00:00.100,1.25010,1.25000,0.9,1.8",
                "2026.04.13 03:00:00.200,1.25008,1.25002,0.9,0.9",
                "2026.04.14 03:00:00.100,1.26010,1.26000,0.9,1.8",
                "2026.04.20 03:00:00.100,1.27005,1.27000,0.9,1.8",
            ]
        ),
        encoding="utf-8",
    )

    m15 = pd.DataFrame(
        {
            "open": [1.2500] * 80,
            "high": [1.2504] * 80,
            "low": [1.2498] * 80,
            "close": [1.2502] * 80,
            "spread": [10] * 80,
        }
    )
    rows = audit_tick_file(
        path,
        symbol="GBPUSD",
        events_by_date={
            "2026-04-13": {
                "week": "2026-W16",
                "first_idx": 0,
                "gap": -0.0020,
                "normalized": 1.0,
            },
            "2026-04-20": {
                "week": "2026-W17",
                "first_idx": 40,
                "gap": -0.0020,
                "normalized": 1.0,
            },
        },
        m15=m15,
    )

    assert [row["date"] for row in rows] == ["2026-04-13", "2026-04-20"]
    assert [row["first_spread_pips"] for row in rows] == pytest.approx([1.0, 0.5])
    assert [row["exclusion_reason"] for row in rows] == [None, None]


def test_summarize_rows_excludes_non_h07_files():
    rows = [
        {
            "file": "GBPUSD_Ticks_2026.04.13_2026.04.13.csv",
            "date": "2026-04-13",
            "included_h07": True,
            "first_spread_pips": 1.0,
            "median_spread_pips": 0.7,
            "gross_pips": 18.0,
            "current_model_net_pips": 15.9,
            "dukascopy_tick_net_pips": 14.9,
        },
        {
            "file": "GBPUSD_Ticks_2026.07.22_2026.07.22.csv",
            "date": "2026-07-22",
            "included_h07": False,
            "first_spread_pips": 0.9,
            "median_spread_pips": 0.7,
            "gross_pips": None,
            "current_model_net_pips": None,
            "dukascopy_tick_net_pips": None,
        },
        {
            "file": "GBPUSD_Ticks_2025.06.23_2025.06.23.csv",
            "date": "2025-06-23",
            "included_h07": True,
            "first_spread_pips": 0.7,
            "median_spread_pips": 0.9,
            "gross_pips": 24.7,
            "current_model_net_pips": 21.0,
            "dukascopy_tick_net_pips": 21.9,
        },
    ]

    summary = summarize_rows(rows)

    assert summary["n_files"] == 3
    assert summary["n_h07_events"] == 2
    assert summary["excluded_files"] == [
        "GBPUSD_Ticks_2026.07.22_2026.07.22.csv"
    ]
    assert summary["mean_dukascopy_tick_net_pips"] == pytest.approx(18.4)
    assert summary["positive_dukascopy_tick_rate"] == 1.0


def test_deduplicate_h07_rows_marks_repeated_date_as_excluded():
    rows = [
        {
            "file": "GBPUSD_Ticks_2025.01.01_2025.12.31.csv",
            "date": "2025-01-06",
            "included_h07": True,
            "dukascopy_tick_net_pips": 1.0,
            "current_model_net_pips": 1.0,
            "gross_pips": 3.0,
        },
        {
            "file": "GBPUSD_Ticks_2025.01.06_2025.01.06.csv",
            "date": "2025-01-06",
            "included_h07": True,
            "dukascopy_tick_net_pips": 2.0,
            "current_model_net_pips": 2.0,
            "gross_pips": 4.0,
        },
    ]

    result = deduplicate_h07_rows(rows)

    assert result[0]["included_h07"] is True
    assert result[1]["included_h07"] is False
    assert result[1]["exclusion_reason"] == "duplicate_h07_date"
    assert result[1]["dukascopy_tick_net_pips"] is None
