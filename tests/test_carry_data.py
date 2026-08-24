from __future__ import annotations

from datetime import datetime, timezone
import json

import pandas as pd
import pytest

from research.carry_data import (
    FRED_SERIES_BY_CURRENCY,
    download_rate_snapshot,
    load_rate_snapshot,
    parse_fred_csv,
    require_complete_rate_window,
)


def fred_payload(series_id: str, values: list[tuple[str, str]]) -> bytes:
    lines = [f"observation_date,{series_id}"]
    lines.extend(f"{date},{value}" for date, value in values)
    return ("\n".join(lines) + "\n").encode("utf-8")


def test_parse_fred_csv_preserves_missing_observations():
    parsed = parse_fred_csv(
        fred_payload(
            "TEST",
            [("2020-01-01", "1.25"), ("2020-02-01", ".")],
        ),
        series_id="TEST",
    )

    assert str(parsed.index.tz) == "UTC"
    assert parsed.iloc[0] == pytest.approx(1.25)
    assert pd.isna(parsed.iloc[1])


def test_snapshot_manifest_hashes_and_loads_all_currencies(tmp_path):
    payloads = {
        series_id: fred_payload(
            series_id,
            [("2020-01-01", "1.0"), ("2020-02-01", "2.0")],
        )
        for series_id in FRED_SERIES_BY_CURRENCY.values()
    }

    manifest_path = download_rate_snapshot(
        tmp_path,
        fetcher=lambda url: payloads[url.rsplit("=", 1)[-1]],
        retrieved_at=datetime(2026, 8, 22, tzinfo=timezone.utc),
    )
    loaded = load_rate_snapshot(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert list(loaded.columns) == list(FRED_SERIES_BY_CURRENCY)
    assert loaded.shape == (2, 8)
    assert manifest["retrieved_at"] == "2026-08-22T00:00:00+00:00"
    assert all(item["sha256"] for item in manifest["series"])


def test_snapshot_loader_rejects_tampered_source(tmp_path):
    payloads = {
        series_id: fred_payload(series_id, [("2020-01-01", "1.0")])
        for series_id in FRED_SERIES_BY_CURRENCY.values()
    }
    manifest_path = download_rate_snapshot(
        tmp_path,
        fetcher=lambda url: payloads[url.rsplit("=", 1)[-1]],
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_path = manifest_path.parent / manifest["series"][0]["file"]
    source_path.write_bytes(source_path.read_bytes() + b"tampered")

    with pytest.raises(ValueError, match="SHA256"):
        load_rate_snapshot(manifest_path)


def test_complete_window_rejects_missing_month_without_forward_fill():
    index = pd.to_datetime(
        ["2020-01-01", "2020-03-01"],
        utc=True,
    )
    rates = pd.DataFrame(
        1.0,
        index=index,
        columns=list(FRED_SERIES_BY_CURRENCY),
    )

    with pytest.raises(ValueError, match="missing monthly rates"):
        require_complete_rate_window(
            rates,
            date_from=pd.Timestamp("2020-01-01", tz="UTC"),
            date_to=pd.Timestamp("2020-04-01", tz="UTC"),
        )
