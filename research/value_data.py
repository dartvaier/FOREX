"""Auditable public macro/FX snapshots for future currency-value research."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen
from zipfile import ZipFile

import numpy as np
import pandas as pd


VALUE_UNIVERSE = {
    "AUD": {"bis_area": "AU", "wb_country": "AUS", "oecd_area": "AUS"},
    "BRL": {"bis_area": "BR", "wb_country": "BRA", "oecd_area": "BRA"},
    "CAD": {"bis_area": "CA", "wb_country": "CAN", "oecd_area": "CAN"},
    "CHF": {"bis_area": "CH", "wb_country": "CHE", "oecd_area": "CHE"},
    "CZK": {"bis_area": "CZ", "wb_country": "CZE", "oecd_area": "CZE"},
    "DKK": {"bis_area": "DK", "wb_country": "DNK", "oecd_area": "DNK"},
    "EUR": {"bis_area": "XM", "wb_country": "EMU", "oecd_area": "EA20"},
    "GBP": {"bis_area": "GB", "wb_country": "GBR", "oecd_area": "GBR"},
    "HUF": {"bis_area": "HU", "wb_country": "HUN", "oecd_area": "HUN"},
    "JPY": {"bis_area": "JP", "wb_country": "JPN", "oecd_area": "JPN"},
    "KRW": {"bis_area": "KR", "wb_country": "KOR", "oecd_area": "KOR"},
    "MXN": {"bis_area": "MX", "wb_country": "MEX", "oecd_area": "MEX"},
    "NOK": {"bis_area": "NO", "wb_country": "NOR", "oecd_area": "NOR"},
    "NZD": {"bis_area": "NZ", "wb_country": "NZL", "oecd_area": "NZL"},
    "PLN": {"bis_area": "PL", "wb_country": "POL", "oecd_area": "POL"},
    "SEK": {"bis_area": "SE", "wb_country": "SWE", "oecd_area": "SWE"},
    "SGD": {"bis_area": "SG", "wb_country": "SGP", "oecd_area": "SGP"},
    "TRY": {"bis_area": "TR", "wb_country": "TUR", "oecd_area": "TUR"},
    "USD": {"bis_area": "US", "wb_country": "USA", "oecd_area": "USA"},
    "ZAR": {"bis_area": "ZA", "wb_country": "ZAF", "oecd_area": "ZAF"},
}

BIS_EER_URL = "https://data.bis.org/static/bulk/WS_EER_csv_flat.zip"
BIS_XRU_URL = "https://data.bis.org/static/bulk/WS_XRU_csv_flat.zip"
OECD_PPP_URL = (
    "https://sdmx.oecd.org/public/rest/data/"
    "OECD.SDD.NAD,DSD_NAMAIN10@DF_TABLE4,2.0/"
    "?startPeriod=1990&dimensionAtObservation=AllDimensions"
)

_WB_COUNTRIES = ";".join(
    metadata["wb_country"] for metadata in VALUE_UNIVERSE.values()
)
WORLD_BANK_INDICATORS = {
    indicator: (
        f"https://api.worldbank.org/v2/country/{_WB_COUNTRIES}/indicator/"
        f"{indicator}?format=json&per_page=20000"
    )
    for indicator in ("PA.NUS.PPP", "PA.NUS.FCRF")
}

RAW_SOURCES = {
    "bis_eer": BIS_EER_URL,
    "bis_xru": BIS_XRU_URL,
    "world_bank_ppp": WORLD_BANK_INDICATORS["PA.NUS.PPP"],
    "world_bank_exchange_rate": WORLD_BANK_INDICATORS["PA.NUS.FCRF"],
    "oecd_ppp": OECD_PPP_URL,
}
RAW_FILENAMES = {
    "bis_eer": "bis_eer_bulk.zip",
    "bis_xru": "bis_xru_bulk.zip",
    "world_bank_ppp": "world_bank_ppp.json",
    "world_bank_exchange_rate": "world_bank_exchange_rate.json",
    "oecd_ppp": "oecd_ppp.csv",
}
NORMALIZED_FREQUENCIES = {
    "bis_reer_monthly": "monthly",
    "bis_usd_monthly": "monthly",
    "world_bank_ppp_annual": "annual",
    "world_bank_exchange_rate_annual": "annual",
    "oecd_ppp_annual": "annual",
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def fetch_public_data(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": "FOREX-research/1.0 (auditable snapshot)",
            "Accept": "text/csv, application/json, application/zip",
        },
    )
    with urlopen(request, timeout=120) as response:
        return response.read()


def _read_single_csv_zip(payload: bytes, *, expected_name: str) -> pd.DataFrame:
    try:
        with ZipFile(BytesIO(payload)) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if names != [expected_name]:
                raise ValueError(f"unexpected ZIP members: {names}")
            with archive.open(expected_name) as source:
                return pd.read_csv(source, low_memory=False)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"invalid ZIP payload for {expected_name}") from exc


def _code_before_label(values: pd.Series) -> pd.Series:
    return values.astype("string").str.split(":", n=1).str[0].str.strip()


def _wide_panel(
    frame: pd.DataFrame,
    *,
    source_code_column: str,
    code_to_currency: dict[str, str],
    frequency: str,
) -> pd.DataFrame:
    selected = frame.copy()
    selected["currency"] = selected[source_code_column].map(code_to_currency)
    selected = selected.loc[selected["currency"].notna()].copy()
    if frequency == "monthly":
        selected["observation_date"] = pd.to_datetime(
            selected["TIME_PERIOD"].astype("string") + "-01",
            errors="raise",
            utc=True,
        )
    elif frequency == "annual":
        years = pd.to_numeric(selected["TIME_PERIOD"], errors="raise").astype(int)
        selected["observation_date"] = pd.DatetimeIndex(
            [pd.Timestamp(year=int(year), month=1, day=1, tz="UTC") for year in years]
        )
    else:
        raise ValueError(f"unsupported frequency: {frequency}")
    selected["value"] = pd.to_numeric(selected["OBS_VALUE"], errors="coerce")
    duplicate = selected.duplicated(["observation_date", "currency"], keep=False)
    if duplicate.any():
        raise ValueError("duplicate observations in normalized value data")
    result = selected.pivot(
        index="observation_date",
        columns="currency",
        values="value",
    ).sort_index()
    result.columns.name = None
    return result.reindex(columns=list(VALUE_UNIVERSE)).astype(float)


def parse_bis_eer(payload: bytes) -> pd.DataFrame:
    frame = _read_single_csv_zip(payload, expected_name="WS_EER_csv_flat.csv")
    required = {
        "FREQ:Frequency",
        "EER_TYPE:Type",
        "EER_BASKET:Basket",
        "REF_AREA:Reference area",
        "TIME_PERIOD:Time period or range",
        "OBS_VALUE:Observation Value",
    }
    if not required.issubset(frame.columns):
        raise ValueError("BIS EER payload is missing required columns")
    selected = frame.loc[
        _code_before_label(frame["FREQ:Frequency"]).eq("M")
        & _code_before_label(frame["EER_TYPE:Type"]).eq("R")
        & _code_before_label(frame["EER_BASKET:Basket"]).eq("B")
    ].copy()
    selected["area_code"] = _code_before_label(selected["REF_AREA:Reference area"])
    mapping = {
        metadata["bis_area"]: currency
        for currency, metadata in VALUE_UNIVERSE.items()
    }
    selected = selected.rename(
        columns={
            "TIME_PERIOD:Time period or range": "TIME_PERIOD",
            "OBS_VALUE:Observation Value": "OBS_VALUE",
        }
    )
    return _wide_panel(
        selected,
        source_code_column="area_code",
        code_to_currency=mapping,
        frequency="monthly",
    )


def parse_bis_xru(payload: bytes) -> pd.DataFrame:
    frame = _read_single_csv_zip(payload, expected_name="WS_XRU_csv_flat.csv")
    required = {
        "FREQ:Frequency",
        "REF_AREA:Reference area",
        "COLLECTION:Collection",
        "TIME_PERIOD:Time period or range",
        "OBS_VALUE:Observation Value",
    }
    if not required.issubset(frame.columns):
        raise ValueError("BIS XRU payload is missing required columns")
    selected = frame.loc[
        _code_before_label(frame["FREQ:Frequency"]).eq("M")
        & _code_before_label(frame["COLLECTION:Collection"]).eq("A")
    ].copy()
    selected["area_code"] = _code_before_label(selected["REF_AREA:Reference area"])
    mapping = {
        metadata["bis_area"]: currency
        for currency, metadata in VALUE_UNIVERSE.items()
    }
    selected = selected.rename(
        columns={
            "TIME_PERIOD:Time period or range": "TIME_PERIOD",
            "OBS_VALUE:Observation Value": "OBS_VALUE",
        }
    )
    return _wide_panel(
        selected,
        source_code_column="area_code",
        code_to_currency=mapping,
        frequency="monthly",
    )


def parse_world_bank(payload: bytes, *, indicator: str) -> pd.DataFrame:
    try:
        document = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise ValueError("invalid World Bank JSON") from exc
    if not isinstance(document, list) or len(document) != 2:
        raise ValueError("unexpected World Bank response shape")
    rows = document[1]
    if not isinstance(rows, list):
        raise ValueError("unexpected World Bank observations")
    records = []
    for row in rows:
        row_indicator = str(row.get("indicator", {}).get("id", ""))
        if row_indicator != indicator:
            raise ValueError(f"unexpected World Bank indicator: {row_indicator}")
        records.append(
            {
                "country_code": str(row.get("countryiso3code", "")),
                "TIME_PERIOD": row.get("date"),
                "OBS_VALUE": row.get("value"),
            }
        )
    frame = pd.DataFrame(records)
    mapping = {
        metadata["wb_country"]: currency
        for currency, metadata in VALUE_UNIVERSE.items()
    }
    return _wide_panel(
        frame,
        source_code_column="country_code",
        code_to_currency=mapping,
        frequency="annual",
    )


def parse_oecd_ppp(payload: bytes) -> pd.DataFrame:
    frame = pd.read_csv(BytesIO(payload), low_memory=False)
    required = {
        "FREQ",
        "REF_AREA",
        "TRANSACTION",
        "UNIT_MEASURE",
        "TIME_PERIOD",
        "OBS_VALUE",
    }
    if not required.issubset(frame.columns):
        raise ValueError("OECD PPP payload is missing required columns")
    selected = frame.loc[
        frame["FREQ"].astype("string").eq("A")
        & frame["TRANSACTION"].astype("string").eq("PPP_B1GQ")
        & frame["UNIT_MEASURE"].astype("string").eq("XDC_USD")
    ].copy()
    mapping = {
        metadata["oecd_area"]: currency
        for currency, metadata in VALUE_UNIVERSE.items()
    }
    return _wide_panel(
        selected,
        source_code_column="REF_AREA",
        code_to_currency=mapping,
        frequency="annual",
    )


def _serialize_panel(panel: pd.DataFrame) -> bytes:
    return panel.to_csv(
        index=True,
        index_label="observation_date",
        float_format="%.12g",
        lineterminator="\n",
    ).encode("utf-8")


def _panel_manifest_entry(name: str, filename: str, payload: bytes, panel: pd.DataFrame) -> dict:
    present = [currency for currency in panel.columns if panel[currency].notna().any()]
    return {
        "name": name,
        "file": filename,
        "sha256": sha256_bytes(payload),
        "bytes": len(payload),
        "rows": int(len(panel)),
        "currencies_present": present,
        "currencies_missing": sorted(set(VALUE_UNIVERSE) - set(present)),
        "missing_values": int(panel.isna().sum().sum()),
        "date_from": str(panel.index.min()) if len(panel) else None,
        "date_to": str(panel.index.max()) if len(panel) else None,
        "frequency": NORMALIZED_FREQUENCIES[name],
        "point_in_time": False,
    }


def download_value_snapshot(
    out_dir: Path,
    *,
    fetcher: Callable[[str], bytes] = fetch_public_data,
    retrieved_at: datetime | None = None,
) -> Path:
    """Download, normalize and hash all public H17 input candidates."""
    timestamp = retrieved_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("retrieved_at must be timezone-aware")
    timestamp = timestamp.astimezone(timezone.utc)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_payloads: dict[str, bytes] = {}
    raw_entries = []
    for name, url in RAW_SOURCES.items():
        payload = fetcher(url)
        raw_payloads[name] = payload
        filename = RAW_FILENAMES[name]
        (out_dir / filename).write_bytes(payload)
        raw_entries.append(
            {
                "name": name,
                "url": url,
                "file": filename,
                "sha256": sha256_bytes(payload),
                "bytes": len(payload),
            }
        )

    panels = {
        "bis_reer_monthly": parse_bis_eer(raw_payloads["bis_eer"]),
        "bis_usd_monthly": parse_bis_xru(raw_payloads["bis_xru"]),
        "world_bank_ppp_annual": parse_world_bank(
            raw_payloads["world_bank_ppp"], indicator="PA.NUS.PPP"
        ),
        "world_bank_exchange_rate_annual": parse_world_bank(
            raw_payloads["world_bank_exchange_rate"], indicator="PA.NUS.FCRF"
        ),
        "oecd_ppp_annual": parse_oecd_ppp(raw_payloads["oecd_ppp"]),
    }
    normalized_entries = []
    for name, panel in panels.items():
        filename = f"{name}.csv"
        payload = _serialize_panel(panel)
        (out_dir / filename).write_bytes(payload)
        normalized_entries.append(
            _panel_manifest_entry(name, filename, payload, panel)
        )

    manifest = {
        "dataset": "public currency-value research inputs",
        "retrieved_at": timestamp.isoformat(),
        "universe": list(VALUE_UNIVERSE),
        "point_in_time": False,
        "monthly_reer_availability_lag_months": 2,
        "annual_ppp_availability_policy": None,
        "raw_files": raw_entries,
        "normalized_files": normalized_entries,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest_path


def load_value_snapshot(manifest_path: Path) -> dict[str, pd.DataFrame]:
    """Cryptographically verify raw/derived files and load normalized panels."""
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    expected_names = set(NORMALIZED_FREQUENCIES)
    actual_names = {str(entry.get("name")) for entry in manifest.get("normalized_files", [])}
    if actual_names != expected_names:
        raise ValueError("snapshot normalized dataset mapping is incomplete")

    for entry in [*manifest.get("raw_files", []), *manifest.get("normalized_files", [])]:
        source_path = (base / str(entry["file"])).resolve()
        if not source_path.is_relative_to(base):
            raise ValueError("snapshot path escapes manifest directory")
        payload = source_path.read_bytes()
        if sha256_bytes(payload) != entry.get("sha256"):
            raise ValueError(f"SHA256 mismatch for {source_path.name}")

    panels: dict[str, pd.DataFrame] = {}
    for entry in manifest["normalized_files"]:
        name = str(entry["name"])
        source_path = base / str(entry["file"])
        panel = pd.read_csv(source_path, index_col="observation_date")
        panel.index = pd.to_datetime(panel.index, errors="raise", utc=True)
        if list(panel.columns) != list(VALUE_UNIVERSE):
            raise ValueError(f"unexpected currency mapping for {name}")
        values = panel.apply(pd.to_numeric, errors="coerce").astype(float)
        if not values.index.is_monotonic_increasing or values.index.has_duplicates:
            raise ValueError(f"invalid time index for {name}")
        panels[name] = values
    return panels


def lag_monthly_panel(panel: pd.DataFrame, *, lag_months: int) -> pd.DataFrame:
    """Move observations to a later availability month without filling gaps."""
    if not isinstance(lag_months, int) or lag_months < 0:
        raise ValueError("lag_months must be a non-negative integer")
    if not isinstance(panel.index, pd.DatetimeIndex) or panel.index.tz is None:
        raise ValueError("panel index must be a timezone-aware DatetimeIndex")
    result = panel.copy()
    utc_index = result.index.tz_convert("UTC")
    shifted = [
        pd.Timestamp(
            year=(timestamp + pd.DateOffset(months=lag_months)).year,
            month=(timestamp + pd.DateOffset(months=lag_months)).month,
            day=1,
            tz="UTC",
        )
        for timestamp in utc_index
    ]
    result.index = pd.DatetimeIndex(shifted, name=panel.index.name)
    if result.index.has_duplicates:
        raise ValueError("lagged panel contains duplicate availability months")
    return result.sort_index()


def derive_price_level(
    ppp: pd.DataFrame,
    exchange_rate: pd.DataFrame,
) -> pd.DataFrame:
    """Derive PPP/market-FX price levels on exact overlapping observations."""
    if list(ppp.columns) != list(exchange_rate.columns):
        raise ValueError("PPP and exchange-rate currency mappings must match")
    common_index = ppp.index.intersection(exchange_rate.index)
    numerator = ppp.loc[common_index].astype(float)
    denominator = exchange_rate.loc[common_index].astype(float)
    invalid = denominator.notna() & (
        (denominator <= 0) | ~np.isfinite(denominator.to_numpy())
    )
    if invalid.any().any():
        raise ValueError("exchange rates must be finite and positive when present")
    return numerator / denominator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/external/value/public_snapshot"),
    )
    args = parser.parse_args()
    manifest_path = download_value_snapshot(args.out_dir)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
