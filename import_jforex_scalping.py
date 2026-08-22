from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from data.jforex_importer import (
    JForexImportError,
    import_jforex_scalping_directory,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Import JForex/Dukascopy M1 Bid/Ask CSV exports into a "
            "separate scalping dataset and build M5."
        )
    )
    parser.add_argument(
        "--input-dir",
        default="data/import/JForex",
        help="directory containing JForex M1 Bid/Ask CSV exports",
    )
    parser.add_argument(
        "--symbol",
        default="USDJPY",
        help="symbol to import (default: USDJPY)",
    )
    parser.add_argument(
        "--raw-base-path",
        default="data/scalping/raw",
        help="output base directory for raw M1 parquet files",
    )
    parser.add_argument(
        "--processed-base-path",
        default="data/scalping/processed",
        help="output base directory for M5 parquet files",
    )
    parser.add_argument(
        "--source-timezone",
        default="Europe/Helsinki",
        help=(
            "timezone used by JForex timestamps "
            "(default: Europe/Helsinki for EET/EEST exports)"
        ),
    )
    parser.add_argument(
        "--strict-ohlc",
        action="store_true",
        help=(
            "fail on rounded JForex extrema instead of repairing "
            "high/low to contain open/close"
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        result = import_jforex_scalping_directory(
            Path(args.input_dir),
            symbol=args.symbol,
            raw_base_path=Path(args.raw_base_path),
            processed_base_path=Path(args.processed_base_path),
            source_timezone=args.source_timezone,
            repair_ohlc=not args.strict_ohlc,
        )
    except JForexImportError as exc:
        print(f"JForex scalping import failed: {exc}")
        return 1

    print(
        f"{result.symbol}: {result.m1_rows} M1 candles "
        f"{result.first_time} -> {result.last_time}"
    )
    print(f"  raw M1: {result.m1_path}")
    print(f"  M5:     {result.m5_path} ({result.m5_rows} candles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
