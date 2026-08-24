from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import pytest

from research.value_data import (
    BIS_EER_URL,
    BIS_XRU_URL,
    OECD_PPP_URL,
    VALUE_UNIVERSE,
    WORLD_BANK_INDICATORS,
    derive_price_level,
    download_value_snapshot,
    lag_monthly_panel,
    load_value_snapshot,
    parse_bis_eer,
)
from research.value_data_report import _coverage


def zipped_csv(filename: str, text: str) -> bytes:
    payload = BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(filename, text)
    return payload.getvalue()


def bis_eer_payload() -> bytes:
    header = (
        "FREQ:Frequency,EER_TYPE:Type,EER_BASKET:Basket,"
        "REF_AREA:Reference area,TIME_PERIOD:Time period or range,"
        "OBS_VALUE:Observation Value\n"
    )
    rows = []
    for currency, metadata in VALUE_UNIVERSE.items():
        area = metadata["bis_area"]
        rows.append(f"M: Monthly,R: Real,B: Broad,{area}: Area,2020-01,100.0")
        rows.append(f"M: Monthly,R: Real,B: Broad,{area}: Area,2020-02,101.0")
    rows.append("M: Monthly,N: Nominal,N: Narrow,AU: Area,2020-01,999.0")
    return zipped_csv("WS_EER_csv_flat.csv", header + "\n".join(rows) + "\n")


def bis_xru_payload() -> bytes:
    header = (
        "FREQ:Frequency,REF_AREA:Reference area,CURRENCY:Currency,"
        "COLLECTION:Collection,TIME_PERIOD:Time period or range,"
        "OBS_VALUE:Observation Value\n"
    )
    rows = []
    for currency, metadata in VALUE_UNIVERSE.items():
        area = metadata["bis_area"]
        rows.append(
            f"M: Monthly,{area}: Area,{currency}: Currency,"
            "A: Average of observations through period,2020-01,1.25"
        )
    return zipped_csv("WS_XRU_csv_flat.csv", header + "\n".join(rows) + "\n")


def world_bank_payload(indicator: str) -> bytes:
    rows = [
        {
            "indicator": {"id": indicator, "value": indicator},
            "country": {"id": metadata["wb_country"], "value": currency},
            "countryiso3code": metadata["wb_country"],
            "date": "2020",
            "value": 1.0,
        }
        for currency, metadata in VALUE_UNIVERSE.items()
    ]
    return json.dumps([{"page": 1, "pages": 1, "total": len(rows)}, rows]).encode()


def oecd_payload() -> bytes:
    lines = ["FREQ,REF_AREA,TRANSACTION,UNIT_MEASURE,TIME_PERIOD,OBS_VALUE"]
    for currency, metadata in VALUE_UNIVERSE.items():
        lines.append(
            f"A,{metadata['oecd_area']},PPP_B1GQ,XDC_USD,2020,1.0"
        )
    return ("\n".join(lines) + "\n").encode()


def fake_payloads() -> dict[str, bytes]:
    payloads = {
        BIS_EER_URL: bis_eer_payload(),
        BIS_XRU_URL: bis_xru_payload(),
        OECD_PPP_URL: oecd_payload(),
    }
    for indicator, url in WORLD_BANK_INDICATORS.items():
        payloads[url] = world_bank_payload(indicator)
    return payloads


def test_bis_eer_parser_selects_monthly_real_broad_only():
    parsed = parse_bis_eer(bis_eer_payload())

    assert parsed.shape == (2, len(VALUE_UNIVERSE))
    assert parsed.loc[pd.Timestamp("2020-01-01", tz="UTC"), "AUD"] == 100.0
    assert 999.0 not in parsed.to_numpy()


def test_snapshot_download_hashes_and_loads_all_public_datasets(tmp_path):
    payloads = fake_payloads()
    manifest_path = download_value_snapshot(
        tmp_path,
        fetcher=lambda url: payloads[url],
        retrieved_at=datetime(2026, 8, 22, tzinfo=timezone.utc),
    )
    loaded = load_value_snapshot(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert set(loaded) == {
        "bis_reer_monthly",
        "bis_usd_monthly",
        "world_bank_ppp_annual",
        "world_bank_exchange_rate_annual",
        "oecd_ppp_annual",
    }
    assert all(list(frame.columns) == list(VALUE_UNIVERSE) for frame in loaded.values())
    assert manifest["retrieved_at"] == "2026-08-22T00:00:00+00:00"
    assert all(item["sha256"] for item in manifest["raw_files"])
    assert all(item["sha256"] for item in manifest["normalized_files"])


def test_snapshot_loader_rejects_tampered_normalized_file(tmp_path):
    payloads = fake_payloads()
    manifest_path = download_value_snapshot(
        tmp_path,
        fetcher=lambda url: payloads[url],
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = manifest_path.parent / manifest["normalized_files"][0]["file"]
    target.write_bytes(target.read_bytes() + b"tampered")

    with pytest.raises(ValueError, match="SHA256"):
        load_value_snapshot(manifest_path)


def test_monthly_lag_moves_dates_without_filling_gaps():
    panel = pd.DataFrame(
        {"AUD": [100.0, 102.0]},
        index=pd.to_datetime(["2020-01-01", "2020-03-01"], utc=True),
    )

    lagged = lag_monthly_panel(panel, lag_months=2)

    assert list(lagged.index) == list(
        pd.to_datetime(["2020-03-01", "2020-05-01"], utc=True)
    )
    assert pd.Timestamp("2020-04-01", tz="UTC") not in lagged.index
    assert lagged.iloc[:, 0].tolist() == [100.0, 102.0]


def test_price_level_uses_only_exact_overlapping_years_without_fill():
    ppp = pd.DataFrame(
        {"AUD": [1.5, 1.6]},
        index=pd.to_datetime(["2020-01-01", "2022-01-01"], utc=True),
    )
    exchange = pd.DataFrame(
        {"AUD": [2.0, 4.0]},
        index=pd.to_datetime(["2020-01-01", "2021-01-01"], utc=True),
    )

    price_level = derive_price_level(ppp, exchange)

    assert list(price_level.index) == [pd.Timestamp("2020-01-01", tz="UTC")]
    assert price_level.iloc[0, 0] == pytest.approx(0.75)


def test_coverage_counts_a_missing_period_even_if_absent_for_every_currency():
    panel = pd.DataFrame(
        {currency: [100.0, 102.0] for currency in VALUE_UNIVERSE},
        index=pd.to_datetime(["2020-01-01", "2020-03-01"], utc=True),
    )

    coverage = _coverage(
        panel,
        date_from=pd.Timestamp("2020-01-01", tz="UTC"),
        date_to=pd.Timestamp("2020-04-01", tz="UTC"),
        frequency="MS",
    )

    assert coverage["AUD"]["observations"] == 2
    assert coverage["AUD"]["missing"] == 1
