from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any

import pandas as pd

from backtest.instruments import instrument_specification
from research.runner import REPORTS_DIR

SCALPING_REPORTS_DIR = REPORTS_DIR / "scalping"

SUMMARY_COLUMNS = [
    "symbol",
    "timeframe",
    "bucket",
    "key",
    "rows",
    "spread_pips_mean",
    "spread_pips_median",
    "spread_pips_p75",
    "spread_pips_p90",
    "spread_pips_p95",
]


def load_scalping_frame(
    *,
    symbol: str,
    timeframe: str,
    raw_base_path: Path = Path("data/scalping/raw"),
    processed_base_path: Path = Path("data/scalping/processed"),
) -> pd.DataFrame:
    timeframe = timeframe.upper()

    if timeframe == "M1":
        path = raw_base_path / symbol / "M1.parquet"
    elif timeframe == "M5":
        path = processed_base_path / symbol / "M5.parquet"
    else:
        raise ValueError(
            "timeframe must be M1 or M5"
        )

    if not path.exists():
        raise FileNotFoundError(path)

    frame = pd.read_parquet(path)
    validate_scalping_frame(frame)
    return frame


def validate_scalping_frame(
    frame: pd.DataFrame,
) -> None:
    required = {
        "time",
        "spread",
    }
    missing = required - set(frame.columns)

    if missing:
        raise ValueError(
            f"missing columns: {sorted(missing)}"
        )

    if frame.empty:
        raise ValueError(
            "dataset is empty"
        )

    if frame["time"].dt.tz is None or str(frame["time"].dt.tz) != "UTC":
        raise ValueError(
            "timestamps must be UTC"
        )


def spread_profile(
    frame: pd.DataFrame,
    *,
    symbol: str,
    timeframe: str,
) -> dict[str, Any]:
    validate_scalping_frame(frame)
    spec = instrument_specification(symbol)
    points_per_pip = spec.pip_size / spec.point

    source = frame.sort_values("time").copy()
    source["spread_pips"] = source["spread"].astype(float) / points_per_pip
    source["utc_hour"] = source["time"].dt.hour.astype(int)
    source["london_hour"] = (
        source["time"]
        .dt.tz_convert("Europe/London")
        .dt.hour
        .astype(int)
    )
    source["ny_hour"] = (
        source["time"]
        .dt.tz_convert("America/New_York")
        .dt.hour
        .astype(int)
    )
    source["session"] = source["time"].map(session_label)

    rows: list[dict[str, Any]] = []
    rows.append(
        metric_row(
            source["spread_pips"],
            symbol=symbol,
            timeframe=timeframe,
            bucket="all",
            key="all",
        )
    )

    for bucket in ["utc_hour", "london_hour", "ny_hour", "session"]:
        for key, group in source.groupby(bucket):
            rows.append(
                metric_row(
                    group["spread_pips"],
                    symbol=symbol,
                    timeframe=timeframe,
                    bucket=bucket,
                    key=str(key),
                )
            )

    return {
        "schema_version": "scalping-spread-profile/0.1.0",
        "symbol": symbol,
        "timeframe": timeframe,
        "rows": rows,
    }


def session_label(
    timestamp: pd.Timestamp,
) -> str:
    london_hour = timestamp.tz_convert("Europe/London").hour
    ny_hour = timestamp.tz_convert("America/New_York").hour

    if 8 <= london_hour < 13:
        return "london_morning"

    if 13 <= london_hour < 17 and 8 <= ny_hour < 12:
        return "london_ny_overlap"

    if 8 <= ny_hour < 17:
        return "new_york"

    return "off_session"


def metric_row(
    values: pd.Series,
    *,
    symbol: str,
    timeframe: str,
    bucket: str,
    key: str,
) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "bucket": bucket,
        "key": key,
        "rows": int(len(values)),
        "spread_pips_mean": round(float(values.mean()), 6),
        "spread_pips_median": round(float(values.median()), 6),
        "spread_pips_p75": round(float(values.quantile(0.75)), 6),
        "spread_pips_p90": round(float(values.quantile(0.90)), 6),
        "spread_pips_p95": round(float(values.quantile(0.95)), 6),
    }


def write_profile(
    profile: dict[str, Any],
    *,
    out_dir: Path = SCALPING_REPORTS_DIR,
) -> tuple[Path, Path]:
    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    stem = (
        f"scalping_spread_profile_"
        f"{profile['symbol']}_{profile['timeframe']}"
    )
    json_path = out_dir / f"{stem}.json"
    csv_path = out_dir / f"{stem}.csv"

    json_path.write_text(
        json.dumps(
            profile,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    csv_path.write_text(
        render_csv(profile["rows"]),
        encoding="utf-8",
    )
    return json_path, csv_path


def render_csv(
    rows: list[dict[str, Any]],
) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=SUMMARY_COLUMNS,
    )
    writer.writeheader()

    for row in rows:
        writer.writerow(row)

    return buffer.getvalue()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure scalping spread profiles by hour/session."
    )
    parser.add_argument(
        "--symbol",
        default="USDJPY",
    )
    parser.add_argument(
        "--timeframe",
        choices=("M1", "M5"),
        default="M1",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=SCALPING_REPORTS_DIR,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    frame = load_scalping_frame(
        symbol=args.symbol,
        timeframe=args.timeframe,
    )
    profile = spread_profile(
        frame,
        symbol=args.symbol,
        timeframe=args.timeframe,
    )
    json_path, csv_path = write_profile(
        profile,
        out_dir=args.out_dir,
    )

    all_row = profile["rows"][0]
    print(
        f"{args.symbol} {args.timeframe}: "
        f"median={all_row['spread_pips_median']:.2f} pips "
        f"p90={all_row['spread_pips_p90']:.2f} pips "
        f"p95={all_row['spread_pips_p95']:.2f} pips"
    )
    print(f"Spread profile JSON: {json_path}")
    print(f"Spread profile CSV : {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
