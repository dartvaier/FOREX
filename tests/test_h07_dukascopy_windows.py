from research.h07_dukascopy_windows import (
    build_rows,
    downloaded_dates,
    expected_tick_filename,
    window_row,
)


def test_expected_tick_filename_uses_dukascopy_export_pattern():
    assert (
        expected_tick_filename("gbpusd", "2026-04-13 00:00:00Z")
        == "GBPUSD_Ticks_2026.04.13_2026.04.13.csv"
    )


def test_downloaded_dates_reads_existing_tick_exports(tmp_path):
    (tmp_path / "GBPUSD_Ticks_2026.04.13_2026.04.13.csv").write_text("")
    (tmp_path / "GBPUSD_Ticks_2025.01.01_2025.12.31.csv").write_text("")
    (tmp_path / "EURUSD_Ticks_2026.04.13_2026.04.13.csv").write_text("")
    (tmp_path / "GBPUSD_1 Min_Bid_2026.04.13_2026.04.13.csv").write_text("")

    dates = downloaded_dates(tmp_path, symbol="GBPUSD")

    assert "2026-04-13" in dates
    assert "2025-01-01" in dates
    assert "2025-12-31" in dates
    assert "2024-12-31" not in dates


def test_window_row_converts_utc_to_jforex_time_and_status():
    event = {
        "week": "2026-W16",
        "first_ts": "2026-04-13 00:00:00+00:00",
        "gap": -0.00777,
        "normalized": 1.25,
    }

    row = window_row(
        event,
        symbol="GBPUSD",
        downloaded={"2026-04-13"},
        hours=8,
    )

    assert row["downloaded"] is True
    assert row["expected_file"] == "GBPUSD_Ticks_2026.04.13_2026.04.13.csv"
    assert row["download_start_utc"] == "2026-04-13 00:00:00 UTC"
    assert row["jforex_start"] == "2026-04-13 03:00:00 EEST"
    assert row["jforex_end"] == "2026-04-13 11:00:00 EEST"
    assert row["jforex_date_from"] == "03:00 13.04.2026"
    assert row["jforex_date_to"] == "11:00 13.04.2026"
    assert row["gap_pips_signed"] == -77.7


def test_build_rows_can_return_only_missing_events(tmp_path):
    (tmp_path / "GBPUSD_Ticks_2026.04.13_2026.04.13.csv").write_text("")
    events = [
        {
            "week": "2026-W16",
            "first_ts": "2026-04-13 00:00:00+00:00",
            "gap": -0.00777,
            "normalized": 1.25,
        },
        {
            "week": "2026-W17",
            "first_ts": "2026-04-20 00:00:00+00:00",
            "gap": -0.00361,
            "normalized": 1.1,
        },
    ]

    rows = build_rows(
        events,
        symbol="GBPUSD",
        raw_dir=tmp_path,
        hours=8,
        missing_only=True,
    )

    assert [row["iso_week"] for row in rows] == ["2026-W17"]


def test_build_rows_balanced_round_robins_by_year(tmp_path):
    events = [
        {
            "week": "2025-W01",
            "first_ts": "2025-01-06 00:00:00+00:00",
            "gap": -0.0020,
            "normalized": 1.1,
        },
        {
            "week": "2025-W02",
            "first_ts": "2025-01-13 00:00:00+00:00",
            "gap": -0.0021,
            "normalized": 1.1,
        },
        {
            "week": "2026-W01",
            "first_ts": "2026-01-05 00:00:00+00:00",
            "gap": -0.0030,
            "normalized": 1.2,
        },
        {
            "week": "2026-W02",
            "first_ts": "2026-01-12 00:00:00+00:00",
            "gap": -0.0031,
            "normalized": 1.2,
        },
    ]

    rows = build_rows(
        events,
        symbol="GBPUSD",
        raw_dir=tmp_path,
        hours=8,
        missing_only=False,
        balanced=True,
    )

    assert [row["iso_week"] for row in rows] == [
        "2025-W01",
        "2026-W01",
        "2025-W02",
        "2026-W02",
    ]
