"""
Generate Dukascopy/JForex download windows for H07 weekly-gap events.

The output is an operator checklist: one row per H07 event, with UTC and
JForex local time windows plus the expected CSV filename. It does not
download data and does not run trades.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from research.h07_experiment import detect_gaps
from research.h07_dukascopy_tick_audit import pip_size_for

DEFAULT_SYMBOL = "GBPUSD"
DEFAULT_RAW_DIR = Path("data/external/dukascopy/raw")
JFOREX_ZONE = ZoneInfo("Europe/Helsinki")
TICK_FILE_RE = re.compile(
    r"^(?P<symbol>[A-Z]{6})_Ticks_(?P<start>\d{4}\.\d{2}\.\d{2})_"
    r"(?P<end>\d{4}\.\d{2}\.\d{2})\.csv$"
)


def timestamp_utc(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def expected_tick_filename(symbol: str, start_utc: Any) -> str:
    date = timestamp_utc(start_utc).strftime("%Y.%m.%d")
    return f"{symbol.upper()}_Ticks_{date}_{date}.csv"


def downloaded_dates(raw_dir: Path, *, symbol: str) -> set[str]:
    dates: set[str] = set()
    for path in raw_dir.glob(f"{symbol.upper()}_Ticks_*.csv"):
        match = TICK_FILE_RE.match(path.name)
        if match and match.group("symbol") == symbol.upper():
            start = pd.Timestamp(match.group("start").replace(".", "-"))
            end = pd.Timestamp(match.group("end").replace(".", "-"))
            for day in pd.date_range(start, end, freq="D"):
                dates.add(day.date().isoformat())
    return dates


def window_row(
    event: dict[str, Any],
    *,
    symbol: str,
    downloaded: set[str],
    hours: int,
) -> dict[str, Any]:
    pip_size = pip_size_for(symbol)
    start_utc = timestamp_utc(event["first_ts"])
    end_utc = start_utc + pd.Timedelta(hours=hours)
    start_jforex = start_utc.tz_convert(JFOREX_ZONE)
    end_jforex = end_utc.tz_convert(JFOREX_ZONE)
    date = start_utc.date().isoformat()
    expected_file = expected_tick_filename(symbol, start_utc)

    return {
        "symbol": symbol.upper(),
        "iso_week": event["week"],
        "date_utc": date,
        "downloaded": date in downloaded,
        "expected_file": expected_file,
        "download_start_utc": start_utc.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "download_end_utc": end_utc.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "jforex_start": start_jforex.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "jforex_end": end_jforex.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "jforex_date_from": start_jforex.strftime("%H:%M %d.%m.%Y"),
        "jforex_date_to": end_jforex.strftime("%H:%M %d.%m.%Y"),
        "gap_pips_signed": round(float(event["gap"]) / pip_size, 4),
        "gap_pips_abs": round(abs(float(event["gap"])) / pip_size, 4),
        "normalized_gap_atr": round(float(event["normalized"]), 6),
        "download_granularity": "Ticks / Ask+Bid",
    }


def build_rows(
    events: list[dict[str, Any]],
    *,
    symbol: str,
    raw_dir: Path,
    hours: int,
    missing_only: bool,
    balanced: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict[str, Any]]:
    existing = downloaded_dates(raw_dir, symbol=symbol)
    rows: list[dict[str, Any]] = []
    from_ts = pd.Timestamp(date_from, tz="UTC") if date_from else None
    to_ts = pd.Timestamp(date_to, tz="UTC") if date_to else None

    for event in events:
        start = timestamp_utc(event["first_ts"])
        if from_ts is not None and start < from_ts:
            continue
        if to_ts is not None and start >= to_ts:
            continue
        row = window_row(event, symbol=symbol, downloaded=existing, hours=hours)
        if missing_only and row["downloaded"]:
            continue
        rows.append(row)

    if balanced:
        by_year: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_year.setdefault(str(row["date_utc"])[:4], []).append(row)
        for year_rows in by_year.values():
            year_rows.sort(key=lambda item: item["date_utc"])

        balanced_rows: list[dict[str, Any]] = []
        years = sorted(by_year)
        while any(by_year.values()):
            for year in years:
                if by_year[year]:
                    balanced_rows.append(by_year[year].pop(0))
        rows = balanced_rows
    return rows


def load_h07_events(
    *,
    symbol: str,
    threshold: float,
    m15_path: Path | None = None,
    h1_path: Path | None = None,
) -> list[dict[str, Any]]:
    m15_file = m15_path or Path("data/raw") / symbol.upper() / "M15.parquet"
    h1_file = h1_path or Path("data/processed") / symbol.upper() / "H1.parquet"
    m15 = pd.read_parquet(m15_file)
    h1 = pd.read_parquet(h1_file)
    return detect_gaps(m15, h1, threshold=threshold)


def write_csv(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        out_path.write_text("", encoding="utf-8")
        return
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="H07 Dukascopy window list")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--threshold", type=float, default=0.50)
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--hours", type=int, default=8)
    parser.add_argument("--missing-only", action="store_true")
    parser.add_argument(
        "--balanced",
        action="store_true",
        help="round-robin rows by year, useful for manual download batches",
    )
    parser.add_argument("--date-from", default=None)
    parser.add_argument("--date-to", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    symbol = args.symbol.upper()
    events = load_h07_events(symbol=symbol, threshold=args.threshold)
    rows = build_rows(
        events,
        symbol=symbol,
        raw_dir=Path(args.raw_dir),
        hours=args.hours,
        missing_only=args.missing_only,
        balanced=args.balanced,
        date_from=args.date_from,
        date_to=args.date_to,
    )
    if args.limit is not None:
        rows = rows[: args.limit]

    suffix = "missing" if args.missing_only else "all"
    out_path = (
        Path(args.out)
        if args.out
        else Path("research/reports") / f"h07_dukascopy_windows_{symbol}_{suffix}.csv"
    )
    write_csv(rows, out_path)

    downloaded = sum(1 for row in rows if row["downloaded"])
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write(
        f"H07 Dukascopy windows {symbol}: rows={len(rows)} "
        f"downloaded={downloaded} missing={len(rows) - downloaded}\n"
    )
    out.write(f"csv: {out_path}\n")
    if rows:
        first = rows[0]
        out.write(
            "next: "
            f"{first['expected_file']} | {first['jforex_start']} -> "
            f"{first['jforex_end']}\n"
        )
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
