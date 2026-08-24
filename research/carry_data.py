"""Auditable OECD/FRED call-money rate snapshots for H16 research."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

import pandas as pd


FRED_SERIES_BY_CURRENCY = {
    "AUD": "IRSTCI01AUM156N",
    "CAD": "IRSTCI01CAM156N",
    "CHF": "IRSTCI01CHM156N",
    "EUR": "IRSTCI01EZM156N",
    "GBP": "IRSTCI01GBM156N",
    "JPY": "IRSTCI01JPM156N",
    "NZD": "IRSTCI01NZM156N",
    "USD": "IRSTCI01USM156N",
}
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def parse_fred_csv(payload: bytes, *, series_id: str) -> pd.Series:
    """Parse one FRED CSV without concealing missing observations."""
    frame = pd.read_csv(BytesIO(payload), dtype=str)
    expected_columns = ["observation_date", series_id]
    if list(frame.columns) != expected_columns:
        raise ValueError(
            f"unexpected FRED columns for {series_id}: {list(frame.columns)}"
        )
    dates = pd.to_datetime(frame["observation_date"], errors="raise", utc=True)
    if dates.duplicated().any():
        raise ValueError(f"duplicate FRED dates for {series_id}")
    raw_values = frame[series_id]
    values = pd.to_numeric(raw_values.replace(".", pd.NA), errors="coerce")
    invalid = values.isna() & ~raw_values.isin(["."]) & raw_values.notna()
    if invalid.any():
        raise ValueError(f"invalid FRED values for {series_id}")
    result = pd.Series(
        values.astype(float).to_numpy(),
        index=pd.DatetimeIndex(dates),
        name=series_id,
    ).sort_index()
    if not result.index.is_monotonic_increasing:
        raise ValueError(f"unsorted FRED dates for {series_id}")
    return result


def fetch_fred_csv(url: str) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": "FOREX-research/1.0 (auditable snapshot)"},
    )
    with urlopen(request, timeout=30) as response:
        return response.read()


def download_rate_snapshot(
    out_dir: Path,
    *,
    fetcher: Callable[[str], bytes] = fetch_fred_csv,
    retrieved_at: datetime | None = None,
) -> Path:
    """Download the fixed H16 universe and write a hashed manifest."""
    timestamp = retrieved_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("retrieved_at must be timezone-aware")
    timestamp = timestamp.astimezone(timezone.utc)
    out_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for currency, series_id in FRED_SERIES_BY_CURRENCY.items():
        url = FRED_CSV_URL.format(series_id=series_id)
        payload = fetcher(url)
        parsed = parse_fred_csv(payload, series_id=series_id)
        filename = f"{currency}_{series_id}.csv"
        (out_dir / filename).write_bytes(payload)
        entries.append(
            {
                "currency": currency,
                "series_id": series_id,
                "url": url,
                "file": filename,
                "sha256": sha256_bytes(payload),
                "rows": int(len(parsed)),
                "missing": int(parsed.isna().sum()),
                "date_from": str(parsed.index.min()),
                "date_to": str(parsed.index.max()),
            }
        )

    manifest = {
        "dataset": "OECD/FRED monthly call-money interbank rates",
        "retrieved_at": timestamp.isoformat(),
        "frequency": "monthly",
        "units": "percent_per_annum",
        "point_in_time": False,
        "publication_lag_policy_months": 1,
        "series": entries,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest_path


def load_rate_snapshot(manifest_path: Path) -> pd.DataFrame:
    """Load and cryptographically verify a local H16 rate snapshot."""
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    series_by_currency: dict[str, pd.Series] = {}
    for entry in manifest.get("series", []):
        currency = str(entry["currency"])
        expected_series = FRED_SERIES_BY_CURRENCY.get(currency)
        if expected_series != entry.get("series_id"):
            raise ValueError(f"unexpected series mapping for {currency}")
        source_path = (base / str(entry["file"])).resolve()
        if not source_path.is_relative_to(base):
            raise ValueError("snapshot source path escapes manifest directory")
        payload = source_path.read_bytes()
        if sha256_bytes(payload) != entry.get("sha256"):
            raise ValueError(f"SHA256 mismatch for {source_path.name}")
        series_by_currency[currency] = parse_fred_csv(
            payload,
            series_id=expected_series,
        ).rename(currency)

    if set(series_by_currency) != set(FRED_SERIES_BY_CURRENCY):
        missing = sorted(set(FRED_SERIES_BY_CURRENCY) - set(series_by_currency))
        raise ValueError(f"snapshot is missing currencies: {missing}")
    return pd.concat(
        [series_by_currency[currency] for currency in FRED_SERIES_BY_CURRENCY],
        axis=1,
        join="outer",
    ).sort_index()


def require_complete_rate_window(
    rates: pd.DataFrame,
    *,
    date_from: pd.Timestamp,
    date_to: pd.Timestamp,
) -> pd.DataFrame:
    """Return a complete monthly window or fail; never forward-fill."""
    if date_from.tz is None or date_to.tz is None:
        raise ValueError("rate window boundaries must be timezone-aware")
    utc_start = date_from.astimezone(timezone.utc)
    utc_end = date_to.astimezone(timezone.utc)
    start = pd.Timestamp(
        year=utc_start.year,
        month=utc_start.month,
        day=1,
        tz="UTC",
    )
    exclusive_end = pd.Timestamp(
        year=utc_end.year,
        month=utc_end.month,
        day=1,
        tz="UTC",
    )
    expected = pd.date_range(
        start=start,
        end=exclusive_end - pd.offsets.MonthBegin(1),
        freq="MS",
        tz="UTC",
    )
    required_columns = list(FRED_SERIES_BY_CURRENCY)
    missing_columns = set(required_columns) - set(rates.columns)
    if missing_columns:
        raise ValueError(f"missing rate currencies: {sorted(missing_columns)}")
    window = rates.reindex(expected)[required_columns]
    incomplete = window.index[window.isna().any(axis=1)]
    if len(incomplete):
        labels = ", ".join(timestamp.strftime("%Y-%m") for timestamp in incomplete)
        raise ValueError(f"missing monthly rates: {labels}")
    return window


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/external/carry/fred_call_money"),
    )
    args = parser.parse_args()
    manifest_path = download_rate_snapshot(args.out_dir)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
