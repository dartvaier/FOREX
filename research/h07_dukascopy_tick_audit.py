"""
H07 GBPUSD Dukascopy tick cost audit.

This is an audit runner, not a live-execution module. It takes exported
Dukascopy/JForex tick CSV files, measures the actual first quoted spread
for H07 weekly-gap events, and re-prices the existing H07 stage-2 trade
simulation with that measured entry spread.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from research.h07_experiment import CANDLES_PER_HOUR, detect_gaps
from research.h07_stage2 import (
    COMMISSION_PIPS,
    EXIT_SPREAD_PIPS,
    SL_FRACTION,
    SLIPPAGE_PIPS,
    TIMEOUT_BARS,
    TP_FRACTION,
    simulate_trade,
)

PIP_SIZE_BY_SYMBOL = {
    "USDJPY": 0.01,
}
DEFAULT_PIP_SIZE = 0.0001
DEFAULT_SYMBOL = "GBPUSD"
TICK_FILE_RE = re.compile(
    r"^(?P<symbol>[A-Z]{6})_Ticks_(?P<start>\d{4}\.\d{2}\.\d{2})_"
    r"(?P<end>\d{4}\.\d{2}\.\d{2})\.csv$"
)


def pip_size_for(symbol: str) -> float:
    return PIP_SIZE_BY_SYMBOL.get(symbol.upper(), DEFAULT_PIP_SIZE)


def read_tick_csv(path: Path, *, pip_size: float = DEFAULT_PIP_SIZE) -> pd.DataFrame:
    """Read a Dukascopy/JForex tick CSV and add spread in pips."""
    frame = pd.read_csv(path)
    frame.columns = [str(column).strip() for column in frame.columns]
    required = {"Time (EET)", "Ask", "Bid"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")

    result = frame.copy()
    result["Time (EET)"] = pd.to_datetime(
        result["Time (EET)"],
        format="%Y.%m.%d %H:%M:%S.%f",
    )
    result["Ask"] = result["Ask"].astype(float)
    result["Bid"] = result["Bid"].astype(float)
    result["spread_pips"] = (result["Ask"] - result["Bid"]) / pip_size
    if (result["spread_pips"] < 0).any():
        raise ValueError(f"{path} contains negative spreads")
    return result


def is_canonical_tick_export(path: Path, *, symbol: str) -> bool:
    """True for the exact JForex tick export filename, excluding duplicates."""
    match = TICK_FILE_RE.match(path.name)
    return bool(match and match.group("symbol") == symbol.upper())


def date_from_tick_filename(path: Path) -> str | None:
    match = TICK_FILE_RE.match(path.name)
    if not match:
        return None
    return match.group("start").replace(".", "-")


def date_range_from_tick_filename(path: Path) -> tuple[str, str] | None:
    match = TICK_FILE_RE.match(path.name)
    if not match:
        return None
    return (
        match.group("start").replace(".", "-"),
        match.group("end").replace(".", "-"),
    )


def h07_events_by_utc_date(
    m15: pd.DataFrame,
    h1: pd.DataFrame,
    *,
    threshold: float,
) -> dict[str, dict[str, Any]]:
    events: dict[str, dict[str, Any]] = {}
    for event in detect_gaps(m15, h1, threshold=threshold):
        timestamp = pd.Timestamp(event["first_ts"])
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("UTC")
        else:
            timestamp = timestamp.tz_convert("UTC")
        events[timestamp.date().isoformat()] = event
    return events


def simulate_h07_event_with_entry_spread(
    event: dict[str, Any],
    m15: pd.DataFrame,
    *,
    entry_spread_pips: float,
    pip_size: float,
) -> dict[str, Any]:
    opens = m15["open"].astype(float).reset_index(drop=True)
    highs = m15["high"].astype(float).reset_index(drop=True)
    lows = m15["low"].astype(float).reset_index(drop=True)
    closes = m15["close"].astype(float).reset_index(drop=True)
    mt5_spreads = (m15["spread"].astype(float) / 10.0).reset_index(drop=True)

    event_index = int(event["first_idx"])
    if event_index + TIMEOUT_BARS >= len(closes):
        raise ValueError("event does not have enough bars for timeout window")

    entry = float(opens.iloc[event_index])
    gap = float(event["gap"])
    gap_abs = abs(gap)
    direction = -1 if gap > 0 else 1
    tp = entry + direction * TP_FRACTION * gap_abs
    sl = entry - direction * SL_FRACTION * gap_abs

    bars = [
        {
            "open": float(opens.iloc[index]),
            "high": float(highs.iloc[index]),
            "low": float(lows.iloc[index]),
            "close": float(closes.iloc[index]),
        }
        for index in range(event_index + 1, event_index + 1 + TIMEOUT_BARS)
    ]
    simulation = simulate_trade(entry, tp, sl, bars, direction)

    extra_cost = EXIT_SPREAD_PIPS + SLIPPAGE_PIPS + COMMISSION_PIPS
    gross_pips = float(simulation["pnl"]) / pip_size
    mt5_entry_spread = float(mt5_spreads.iloc[event_index])
    return {
        "h07_week": event["week"],
        "gap_pips": gap / pip_size,
        "normalized_gap_atr": float(event["normalized"]),
        "direction": direction,
        "entry": entry,
        "tp": tp,
        "sl": sl,
        "exit_reason": simulation["exit_reason"],
        "bars_held": int(simulation["bars_held"]),
        "gross_pips": gross_pips,
        "mt5_entry_spread_pips": mt5_entry_spread,
        "current_model_net_pips": gross_pips - (mt5_entry_spread + extra_cost),
        "dukascopy_tick_net_pips": gross_pips - (entry_spread_pips + extra_cost),
    }


def _excluded_row(
    path: Path,
    *,
    symbol: str,
    date: str | None,
    ticks: int,
    reason: str,
) -> dict[str, Any]:
    return {
        "file": path.name,
        "symbol": symbol.upper(),
        "date": date,
        "weekday": None,
        "ticks": ticks,
        "first_spread_pips": None,
        "median_spread_pips": None,
        "p90_spread_pips": None,
        "max_spread_pips": None,
        "first_15m_median_spread_pips": None,
        "included_h07": False,
        "exclusion_reason": reason,
        "h07_week": None,
        "gap_pips": None,
        "normalized_gap_atr": None,
        "exit_reason": None,
        "bars_held": None,
        "gross_pips": None,
        "mt5_entry_spread_pips": None,
        "current_model_net_pips": None,
        "dukascopy_tick_net_pips": None,
    }


def _audit_tick_group(
    *,
    path: Path,
    symbol: str,
    date: str,
    ticks: pd.DataFrame,
    events_by_date: dict[str, dict[str, Any]],
    m15: pd.DataFrame,
) -> dict[str, Any]:
    pip_size = pip_size_for(symbol)
    first_time = ticks["Time (EET)"].iloc[0]
    first_15m = ticks[ticks["Time (EET)"] < first_time + pd.Timedelta(minutes=15)]

    row: dict[str, Any] = {
        "file": path.name,
        "symbol": symbol.upper(),
        "date": date,
        "weekday": first_time.day_name(),
        "ticks": int(len(ticks)),
        "first_spread_pips": float(ticks["spread_pips"].iloc[0]),
        "median_spread_pips": float(ticks["spread_pips"].median()),
        "p90_spread_pips": float(ticks["spread_pips"].quantile(0.90)),
        "max_spread_pips": float(ticks["spread_pips"].max()),
        "first_15m_median_spread_pips": float(first_15m["spread_pips"].median()),
        "included_h07": False,
        "h07_week": None,
        "gap_pips": None,
        "normalized_gap_atr": None,
        "exit_reason": None,
        "bars_held": None,
        "gross_pips": None,
        "mt5_entry_spread_pips": None,
        "current_model_net_pips": None,
        "dukascopy_tick_net_pips": None,
        "exclusion_reason": "not_h07_event",
    }

    event = events_by_date.get(date)
    if event is not None:
        row.update(
            simulate_h07_event_with_entry_spread(
                event,
                m15,
                entry_spread_pips=row["first_spread_pips"],
                pip_size=pip_size,
            )
        )
        row["included_h07"] = True
        row["exclusion_reason"] = None
    return row


def audit_tick_file(
    path: Path,
    *,
    symbol: str,
    events_by_date: dict[str, dict[str, Any]],
    m15: pd.DataFrame,
) -> list[dict[str, Any]]:
    pip_size = pip_size_for(symbol)
    ticks = read_tick_csv(path, pip_size=pip_size)
    if ticks.empty:
        date_range = date_range_from_tick_filename(path)
        date = date_range[0] if date_range else None
        return [
            _excluded_row(
                path,
                symbol=symbol,
                date=date,
                ticks=0,
                reason="empty_tick_file",
            )
        ]

    rows: list[dict[str, Any]] = []
    dates = ticks["Time (EET)"].dt.date.astype(str)
    for date, group in ticks.groupby(dates, sort=True):
        if date not in events_by_date:
            continue
        rows.append(
            _audit_tick_group(
                path=path,
                symbol=symbol,
                date=date,
                ticks=group.reset_index(drop=True),
                events_by_date=events_by_date,
                m15=m15,
            )
        )

    if not rows:
        first_date = ticks["Time (EET)"].iloc[0].date().isoformat()
        return [
            _excluded_row(
                path,
                symbol=symbol,
                date=first_date,
                ticks=int(len(ticks)),
                reason="no_h07_event_in_file",
            )
        ]
    return rows


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    h07_rows = [row for row in rows if row["included_h07"]]
    by_year: dict[str, list[float]] = {}
    blocks: dict[str, list[float]] = {}
    for row in h07_rows:
        year = int(str(row["date"])[:4])
        net = float(row["dukascopy_tick_net_pips"])
        by_year.setdefault(str(year), []).append(net)
        block = f"{year - (year % 2)}-{year - (year % 2) + 1}"
        blocks.setdefault(block, []).append(net)

    nets = [float(row["dukascopy_tick_net_pips"]) for row in h07_rows]
    first_spreads = [float(row["first_spread_pips"]) for row in h07_rows]
    median_spreads = [float(row["median_spread_pips"]) for row in h07_rows]
    gross = [float(row["gross_pips"]) for row in h07_rows]
    current_model_nets = [
        float(row["current_model_net_pips"]) for row in h07_rows
    ]

    positive = sum(1 for value in nets if value > 0)
    positive_blocks = sum(
        1 for values in blocks.values() if mean(values) is not None and mean(values) > 0
    )
    return {
        "scope": "GBPUSD H07 Dukascopy tick cost audit",
        "n_files": len(rows),
        "n_h07_events": len(h07_rows),
        "excluded_files": [row["file"] for row in rows if not row["included_h07"]],
        "excluded_file_reasons": {
            row["file"]: row.get("exclusion_reason")
            for row in rows
            if not row["included_h07"]
        },
        "mean_first_spread_pips": mean(first_spreads),
        "median_first_spread_pips": median(first_spreads),
        "mean_median_spread_pips": mean(median_spreads),
        "mean_gross_pips": mean(gross),
        "mean_current_model_net_pips": mean(current_model_nets),
        "mean_dukascopy_tick_net_pips": mean(nets),
        "median_dukascopy_tick_net_pips": median(nets),
        "positive_dukascopy_tick_events": positive,
        "positive_dukascopy_tick_rate": positive / len(nets) if nets else None,
        "by_year_mean_dukascopy_tick_net_pips": {
            year: mean(values) for year, values in sorted(by_year.items())
        },
        "by_year_n": {
            year: len(values) for year, values in sorted(by_year.items())
        },
        "blocks_mean_dukascopy_tick_net_pips": {
            block: mean(values) for block, values in sorted(blocks.items())
        },
        "blocks_positive_fraction": (
            positive_blocks / len(blocks) if blocks else None
        ),
        "rows": rows,
    }


def deduplicate_h07_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one included H07 row per date and mark later repeats excluded."""
    seen_dates: set[str] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        if not row["included_h07"]:
            result.append(row)
            continue
        date = str(row["date"])
        if date not in seen_dates:
            seen_dates.add(date)
            result.append(row)
            continue
        duplicate = dict(row)
        duplicate["included_h07"] = False
        duplicate["exclusion_reason"] = "duplicate_h07_date"
        duplicate["dukascopy_tick_net_pips"] = None
        duplicate["current_model_net_pips"] = None
        duplicate["gross_pips"] = None
        result.append(duplicate)
    return result


def run(
    *,
    symbol: str,
    raw_dir: Path,
    m15_path: Path,
    h1_path: Path,
    threshold: float,
    out_json: Path,
    out_csv: Path,
) -> dict[str, Any]:
    m15 = pd.read_parquet(m15_path).sort_values("time").reset_index(drop=True)
    h1 = pd.read_parquet(h1_path).sort_values("time").reset_index(drop=True)
    events = h07_events_by_utc_date(m15, h1, threshold=threshold)

    all_paths = sorted(raw_dir.glob(f"{symbol.upper()}_Ticks_*.csv"))
    ignored_files = [
        path.name
        for path in all_paths
        if not is_canonical_tick_export(path, symbol=symbol)
    ]
    rows: list[dict[str, Any]] = []
    for path in all_paths:
        if is_canonical_tick_export(path, symbol=symbol):
            rows.extend(
                audit_tick_file(path, symbol=symbol, events_by_date=events, m15=m15)
            )
    rows = deduplicate_h07_rows(rows)
    summary = summarize_rows(rows)
    summary["ignored_files"] = ignored_files

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=1), encoding="utf-8")

    if rows:
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        fieldnames: list[str] = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        with out_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="H07 Dukascopy tick audit")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument(
        "--raw-dir",
        default="data/external/dukascopy/raw",
    )
    parser.add_argument("--threshold", type=float, default=0.50)
    parser.add_argument("--out-json", default=None)
    parser.add_argument("--out-csv", default=None)
    args = parser.parse_args()

    symbol = args.symbol.upper()
    out_json = (
        Path(args.out_json)
        if args.out_json
        else Path("research/reports") / f"h07_dukascopy_tick_audit_{symbol}.json"
    )
    out_csv = (
        Path(args.out_csv)
        if args.out_csv
        else Path("research/reports") / f"h07_dukascopy_tick_audit_{symbol}.csv"
    )
    summary = run(
        symbol=symbol,
        raw_dir=Path(args.raw_dir),
        m15_path=Path("data/raw") / symbol / "M15.parquet",
        h1_path=Path("data/processed") / symbol / "H1.parquet",
        threshold=args.threshold,
        out_json=out_json,
        out_csv=out_csv,
    )

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write(
        f"H07 Dukascopy tick audit {symbol}: "
        f"events={summary['n_h07_events']} files={summary['n_files']}\n"
    )
    out.write(
        f"net mean={summary['mean_dukascopy_tick_net_pips']:+.2f} pips | "
        f"median={summary['median_dukascopy_tick_net_pips']:+.2f} pips | "
        f"positive={summary['positive_dukascopy_tick_events']}/"
        f"{summary['n_h07_events']}\n"
    )
    out.write(
        f"first spread mean={summary['mean_first_spread_pips']:.2f} pips | "
        f"blocks positive={summary['blocks_positive_fraction']:.2%}\n"
    )
    if summary["excluded_files"]:
        out.write(f"excluded files: {summary['excluded_files']}\n")
    out.write(f"json: {out_json}\n")
    out.write(f"csv: {out_csv}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
