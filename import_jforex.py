from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from backtest.instruments import MAJOR_SYMBOLS
from data.jforex_importer import import_jforex_directory


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Import JForex/Dukascopy M15 Bid/Ask CSV exports "
            "into data/raw and build H1/H4 processed datasets."
        )
    )

    parser.add_argument(
        "--input-dir",
        default="data/import/JForex",
        help="directory containing JForex CSV exports",
    )
    parser.add_argument(
        "--raw-base-path",
        default="data/raw",
        help="output base directory for raw M15 parquet files",
    )
    parser.add_argument(
        "--processed-base-path",
        default="data/processed",
        help="output base directory for H1/H4 parquet files",
    )
    parser.add_argument(
        "--symbols",
        default=",".join(MAJOR_SYMBOLS),
        help="comma-separated symbols to import",
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
        "--no-build-timeframes",
        action="store_true",
        help="only write data/raw/<SYMBOL>/M15.parquet",
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

    symbols = tuple(
        symbol.strip().upper()
        for symbol in args.symbols.split(",")
        if symbol.strip()
    )

    results = import_jforex_directory(
        Path(args.input_dir),
        raw_base_path=Path(args.raw_base_path),
        processed_base_path=Path(args.processed_base_path),
        symbols=symbols,
        source_timezone=args.source_timezone,
        build_timeframes=not args.no_build_timeframes,
        repair_ohlc=not args.strict_ohlc,
    )

    for result in results:
        print(
            f"{result.symbol}: {result.rows} M15 candles "
            f"{result.first_time} -> {result.last_time}"
        )
        print(f"  raw: {result.m15_path}")
        if result.h1_path is not None:
            print(f"  H1:  {result.h1_path}")
        if result.h4_path is not None:
            print(f"  H4:  {result.h4_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
