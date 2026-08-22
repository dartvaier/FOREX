from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from backtest.instruments import MAJOR_SYMBOLS, instrument_specification
from data.historical_data import HistoricalData
from data.timeframe_builder import TimeframeBuilder


class JForexImportError(ValueError):
    """Raised when a JForex export cannot be imported safely."""


@dataclass(frozen=True, slots=True)
class JForexImportResult:
    symbol: str
    m15_path: Path
    h1_path: Path | None
    h4_path: Path | None
    rows: int
    first_time: pd.Timestamp
    last_time: pd.Timestamp


def read_jforex_csv(
    path: Path,
    *,
    source_timezone: str = "Europe/Helsinki",
    repair_ohlc: bool = True,
) -> pd.DataFrame:
    """
    Read one JForex OHLC CSV and normalize it to internal columns.

    JForex exports used here are Bid/Ask files with columns similar to:

        Time (EET),Open,High,Low,Close,Volume
    """

    path = Path(path)
    delimiter = _detect_delimiter(path)

    frame = pd.read_csv(path, sep=delimiter)
    frame = _rename_columns(frame)

    time_column = _find_time_column(frame)
    required = {"open", "high", "low", "close"}
    missing = required - set(frame.columns)

    if missing:
        raise JForexImportError(
            f"{path.name}: missing columns {sorted(missing)}"
        )

    output = pd.DataFrame()
    output["time"] = _parse_time(
        frame[time_column],
        source_timezone=source_timezone,
    )

    for column in ["open", "high", "low", "close"]:
        output[column] = pd.to_numeric(
            frame[column],
            errors="raise",
        )

    volume_column = _find_optional_column(
        frame,
        ["volume", "tick_volume"],
    )
    output["tick_volume"] = (
        pd.to_numeric(frame[volume_column], errors="raise")
        if volume_column is not None
        else 0.0
    )

    output = (
        output
        .sort_values("time")
        .drop_duplicates(subset=["time"], keep="last")
        .reset_index(drop=True)
    )

    if repair_ohlc:
        output = _repair_ohlc_extrema(output)

    _validate_ohlc(output, label=path.name)
    return output


def import_jforex_directory(
    input_dir: Path,
    *,
    raw_base_path: Path = Path("data/raw"),
    processed_base_path: Path = Path("data/processed"),
    symbols: tuple[str, ...] | list[str] | None = None,
    source_timezone: str = "Europe/Helsinki",
    build_timeframes: bool = True,
    repair_ohlc: bool = True,
) -> list[JForexImportResult]:
    input_dir = Path(input_dir)

    if not input_dir.exists():
        raise JForexImportError(
            f"input directory does not exist: {input_dir}"
        )

    requested_symbols = (
        tuple(symbol.upper() for symbol in symbols)
        if symbols is not None
        else MAJOR_SYMBOLS
    )

    unsupported = sorted(set(requested_symbols) - set(MAJOR_SYMBOLS))
    if unsupported:
        raise JForexImportError(
            f"unsupported symbols: {unsupported}"
        )

    files = _collect_jforex_files(
        input_dir,
        requested_symbols=requested_symbols,
    )

    results: list[JForexImportResult] = []

    for symbol in requested_symbols:
        if symbol not in files:
            continue

        bid_path = files[symbol].get("bid")
        ask_path = files[symbol].get("ask")

        if bid_path is None or ask_path is None:
            raise JForexImportError(
                f"{symbol}: both Bid and Ask M15 CSV files are required"
            )

        bid = read_jforex_csv(
            bid_path,
            source_timezone=source_timezone,
            repair_ohlc=repair_ohlc,
        )
        ask = read_jforex_csv(
            ask_path,
            source_timezone=source_timezone,
            repair_ohlc=repair_ohlc,
        )

        m15 = _combine_bid_ask(
            symbol=symbol,
            bid=bid,
            ask=ask,
        )

        validator = HistoricalData(
            client=None,  # type: ignore[arg-type]
            base_path=str(raw_base_path),
        )
        validator.validate(m15)
        m15_path = validator.save(
            m15,
            symbol=symbol,
            timeframe_name="M15",
        )

        h1_path: Path | None = None
        h4_path: Path | None = None

        if build_timeframes:
            h1_path, h4_path = _build_processed_timeframes(
                symbol=symbol,
                m15=m15,
                processed_base_path=processed_base_path,
            )

        results.append(
            JForexImportResult(
                symbol=symbol,
                m15_path=m15_path,
                h1_path=h1_path,
                h4_path=h4_path,
                rows=len(m15),
                first_time=m15["time"].iloc[0],
                last_time=m15["time"].iloc[-1],
            )
        )

    if not results:
        raise JForexImportError(
            f"no supported JForex M15 Bid/Ask files found in {input_dir}"
        )

    return results


def _detect_delimiter(path: Path) -> str:
    first_line = path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    ).splitlines()[0]

    candidates = [",", ";", "\t"]
    return max(
        candidates,
        key=first_line.count,
    )


def _rename_columns(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = {
        column: _canonical_column_name(str(column))
        for column in frame.columns
    }
    return frame.rename(columns=renamed)


def _canonical_column_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def _find_time_column(frame: pd.DataFrame) -> str:
    for column in frame.columns:
        if column == "time" or column.startswith("time_"):
            return column

    for candidate in ["datetime", "date", "timestamp"]:
        if candidate in frame.columns:
            return candidate

    raise JForexImportError("missing time column")


def _find_optional_column(
    frame: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    return None


def _parse_time(
    values: pd.Series,
    *,
    source_timezone: str,
) -> pd.Series:
    parsed = pd.to_datetime(
        values.astype(str).str.strip(),
        format="%Y.%m.%d %H:%M:%S",
        errors="coerce",
    )

    if parsed.isna().any():
        bad_rows = int(parsed.isna().sum())
        raise JForexImportError(
            f"could not parse {bad_rows} timestamp values"
        )

    if source_timezone.upper() in {"UTC", "GMT"}:
        localized = parsed.dt.tz_localize("UTC")
    else:
        localized = parsed.dt.tz_localize(
            ZoneInfo(source_timezone),
            ambiguous="raise",
            nonexistent="raise",
        )

    return localized.dt.tz_convert("UTC")


def _validate_ohlc(
    frame: pd.DataFrame,
    *,
    label: str,
) -> None:
    checks = [
        ("High < Low", frame["high"] >= frame["low"]),
        ("High < Open", frame["high"] >= frame["open"]),
        ("High < Close", frame["high"] >= frame["close"]),
        ("Low > Open", frame["low"] <= frame["open"]),
        ("Low > Close", frame["low"] <= frame["close"]),
    ]

    for message, passed in checks:
        if not passed.all():
            raise JForexImportError(
                f"{label}: invalid OHLC data ({message})"
            )

    for column in ["open", "high", "low", "close"]:
        if not (frame[column] > 0).all():
            raise JForexImportError(
                f"{label}: non-positive prices in {column}"
            )


def _repair_ohlc_extrema(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    repaired = frame.copy()

    repaired["high"] = repaired[
        ["high", "open", "close"]
    ].max(axis=1)
    repaired["low"] = repaired[
        ["low", "open", "close"]
    ].min(axis=1)

    return repaired


def _collect_jforex_files(
    input_dir: Path,
    *,
    requested_symbols: tuple[str, ...],
) -> dict[str, dict[str, Path]]:
    files: dict[str, dict[str, Path]] = {}

    for path in sorted(input_dir.glob("*.csv")):
        symbol = _detect_symbol(path.name, requested_symbols)
        side = _detect_side(path.name)

        if symbol is None or side is None:
            continue

        if not _is_m15_file(path.name):
            continue

        files.setdefault(symbol, {})

        if side in files[symbol]:
            raise JForexImportError(
                f"{symbol}: multiple {side} files found"
            )

        files[symbol][side] = path

    return files


def _detect_symbol(
    filename: str,
    symbols: tuple[str, ...],
) -> str | None:
    matches = [
        symbol
        for symbol in symbols
        if symbol in filename.upper()
    ]

    if len(matches) > 1:
        raise JForexImportError(
            f"{filename}: ambiguous symbol matches {matches}"
        )

    return matches[0] if matches else None


def _detect_side(filename: str) -> str | None:
    upper = filename.upper()

    if "ASK" in upper:
        return "ask"

    if "BID" in upper:
        return "bid"

    return None


def _is_m15_file(filename: str) -> bool:
    normalized = filename.upper().replace("_", " ")
    return "15 MIN" in normalized


def _combine_bid_ask(
    *,
    symbol: str,
    bid: pd.DataFrame,
    ask: pd.DataFrame,
) -> pd.DataFrame:
    merged = bid.merge(
        ask,
        on="time",
        how="inner",
        suffixes=("_bid", "_ask"),
    )

    if len(merged) != len(bid) or len(merged) != len(ask):
        raise JForexImportError(
            f"{symbol}: Bid/Ask timestamps do not match exactly "
            f"(bid={len(bid)}, ask={len(ask)}, common={len(merged)})"
        )

    spec = instrument_specification(symbol)
    merged = _repair_crossed_boundary_prices(
        symbol=symbol,
        merged=merged,
        point=spec.point,
    )

    output = pd.DataFrame()
    output["time"] = merged["time"]

    for column in ["open", "high", "low", "close"]:
        output[column] = (
            merged[f"{column}_bid"]
            + merged[f"{column}_ask"]
        ) / 2.0

    output["tick_volume"] = (
        (
            merged["tick_volume_bid"]
            + merged["tick_volume_ask"]
        ) / 2.0
    ).round().astype("int64")

    output["spread"] = (
        merged["close_ask"]
        - merged["close_bid"]
    ) / spec.point

    output["real_volume"] = 0

    output = _repair_ohlc_extrema(output)
    _validate_ohlc(output, label=symbol)

    return output[
        [
            "time",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
            "spread",
            "real_volume",
        ]
    ]


def _repair_crossed_boundary_prices(
    *,
    symbol: str,
    merged: pd.DataFrame,
    point: float,
) -> pd.DataFrame:
    repaired = merged.copy()

    for column in ["open", "close"]:
        bid_column = f"{column}_bid"
        ask_column = f"{column}_ask"
        diff = repaired[ask_column] - repaired[bid_column]
        crossed = diff < 0

        if not crossed.any():
            continue

        too_large = diff < -(point + 1e-12)

        if too_large.any():
            raise JForexImportError(
                f"{symbol}: Ask {column} below Bid {column}"
            )

        repaired.loc[crossed, ask_column] = repaired.loc[
            crossed,
            bid_column,
        ]

    return repaired


def _build_processed_timeframes(
    *,
    symbol: str,
    m15: pd.DataFrame,
    processed_base_path: Path,
) -> tuple[Path, Path]:
    builder = TimeframeBuilder()
    output_directory = processed_base_path / symbol
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    paths: list[Path] = []

    for timeframe in ["H1", "H4"]:
        result = builder.build(
            df=m15,
            timeframe=timeframe,
        )
        output = output_directory / f"{timeframe}.parquet"
        result.to_parquet(
            output,
            index=False,
        )
        paths.append(output)

    return paths[0], paths[1]
