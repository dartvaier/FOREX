"""Collect broker Bid/Ask ticks and current swap terms without trading."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path

from broker.history_export import collect_broker_snapshot


DEFAULT_SYMBOLS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "AUDUSD",
    "USDCAD",
    "NZDUSD",
]

FP_MARKETS_RAW_H17_SYMBOLS = [
    "AUDUSD.r",
    "USDBRL.r",
    "USDCAD.r",
    "USDCHF.r",
    "USDCZK.r",
    "USDDKK.r",
    "EURUSD.r",
    "GBPUSD.r",
    "USDHUF.r",
    "USDJPY.r",
    "USDKRW.r",
    "USDMXN.r",
    "USDNOK.r",
    "NZDUSD.r",
    "USDPLN.r",
    "USDSEK.r",
    "USDSGD.r",
    "USDTRY.r",
    "USDZAR.r",
]

BROKER_PROFILES = {
    "fpmarkets_raw_h17": FP_MARKETS_RAW_H17_SYMBOLS,
}


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="+", default=None)
    parser.add_argument("--profile", choices=sorted(BROKER_PROFILES))
    parser.add_argument(
        "--date-from",
        help="início UTC inclusivo; omita junto com --date-to para snapshot de swap",
    )
    parser.add_argument("--date-to", help="fim UTC exclusivo")
    parser.add_argument("--chunk-hours", type=int, default=24)
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path("data/external/broker/mt5"),
    )
    return parser


def main() -> int:
    import MetaTrader5 as mt5

    from broker.mt5_client import MT5Client

    args = build_parser().parse_args()
    if bool(args.date_from) != bool(args.date_to):
        raise SystemExit("--date-from e --date-to devem ser informados juntos")
    if args.symbols and args.profile:
        raise SystemExit("use --symbols ou --profile, não ambos")

    symbols = (
        args.symbols
        or (BROKER_PROFILES[args.profile] if args.profile else DEFAULT_SYMBOLS)
    )

    observed_at = datetime.now(timezone.utc)
    snapshot = args.out_root / observed_at.strftime("%Y%m%dT%H%M%S%fZ")
    with MT5Client() as client:
        manifest = collect_broker_snapshot(
            client,
            symbols=symbols,
            date_from=parse_utc(args.date_from) if args.date_from else None,
            date_to=parse_utc(args.date_to) if args.date_to else None,
            output_dir=snapshot,
            chunk_hours=args.chunk_hours,
            tick_flags=mt5.COPY_TICKS_INFO,
            observed_at=observed_at,
        )
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
