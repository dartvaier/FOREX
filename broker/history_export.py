"""Read-only export of broker tick quotes and current swap terms.

This module never submits orders.  Tick files are immutable snapshots and every
artifact is hashed in a manifest so broker-specific inputs remain auditable.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Iterator

import pandas as pd


UTC = timezone.utc
_SAFE_COMPONENT = re.compile(r"[^0-9A-Za-z_.-]+")
_SWAP_FIELDS = (
    "swap_mode",
    "swap_long",
    "swap_short",
    "swap_rollover3days",
    "swap_sunday",
    "swap_monday",
    "swap_tuesday",
    "swap_wednesday",
    "swap_thursday",
    "swap_friday",
    "swap_saturday",
)
_CONTRACT_FIELDS = (
    "name",
    "description",
    "path",
    "currency_base",
    "currency_profit",
    "currency_margin",
    "digits",
    "point",
    "trade_contract_size",
    "volume_min",
    "volume_max",
    "volume_step",
)


def _require_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} precisa possuir timezone.")
    return value.astimezone(UTC)


def _safe_component(value: str) -> str:
    result = _SAFE_COMPONENT.sub("_", value).strip("._")
    if not result:
        raise ValueError("componente de caminho vazio ou inválido")
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def iter_utc_chunks(
    date_from: datetime,
    date_to: datetime,
    *,
    chunk_hours: int,
) -> Iterator[tuple[datetime, datetime]]:
    start = _require_utc(date_from, "date_from")
    end = _require_utc(date_to, "date_to")
    if start >= end:
        raise ValueError("date_from precisa ser anterior a date_to.")
    if chunk_hours <= 0:
        raise ValueError("chunk_hours precisa ser positivo.")
    step = timedelta(hours=chunk_hours)
    cursor = start
    while cursor < end:
        next_cursor = min(cursor + step, end)
        yield cursor, next_cursor
        cursor = next_cursor


def normalize_ticks(
    raw_ticks,
    *,
    symbol: str,
    date_from: datetime,
    date_to: datetime,
) -> pd.DataFrame:
    """Normalize MT5 ticks while preserving invalid quotes for audit."""

    start = pd.Timestamp(_require_utc(date_from, "date_from"))
    end = pd.Timestamp(_require_utc(date_to, "date_to"))
    frame = pd.DataFrame(raw_ticks)
    required = {"time_msc", "bid", "ask"}
    missing = required.difference(frame.columns)
    if missing and not frame.empty:
        raise ValueError(f"ticks sem campos obrigatórios: {sorted(missing)}")
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "symbol",
                "time_utc",
                "time_msc",
                "bid",
                "ask",
                "spread_price",
                "valid_quote",
            ]
        )

    frame["time_utc"] = pd.to_datetime(frame["time_msc"], unit="ms", utc=True)
    frame = frame.loc[(frame["time_utc"] >= start) & (frame["time_utc"] < end)].copy()
    frame.insert(0, "symbol", symbol)
    frame["spread_price"] = frame["ask"] - frame["bid"]
    frame["valid_quote"] = (frame["bid"] > 0) & (frame["ask"] >= frame["bid"])
    return frame.sort_values(["time_msc"], kind="stable").reset_index(drop=True)


def build_swap_terms(info, *, observed_at: datetime) -> dict:
    """Capture the current broker contract; this is not historical reconstruction."""

    observed = _require_utc(observed_at, "observed_at")
    result = {"observed_at_utc": observed.isoformat()}
    for field in (*_CONTRACT_FIELDS, *_SWAP_FIELDS):
        result[field] = getattr(info, field, None)
    return result


def _stamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def collect_broker_snapshot(
    client,
    *,
    symbols: list[str],
    output_dir: Path,
    observed_at: datetime,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    chunk_hours: int = 24,
    tick_flags: int = 1,
) -> Path:
    """Export current swap terms and optional historical Bid/Ask ticks."""

    observed = _require_utc(observed_at, "observed_at")
    if not symbols:
        raise ValueError("ao menos um símbolo é obrigatório")
    if (date_from is None) != (date_to is None):
        raise ValueError("date_from e date_to devem ser informados juntos")
    requested_symbols = list(dict.fromkeys(symbols))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)

    account = client.account_info()
    broker = {
        "company": getattr(account, "company", None),
        "server": getattr(account, "server", None),
        "trade_mode": getattr(account, "trade_mode", None),
        "account_currency": getattr(account, "currency", None),
    }
    swap_rows = [
        build_swap_terms(client.symbol_info(symbol), observed_at=observed)
        for symbol in requested_symbols
    ]
    swap_path = output_dir / "swap_terms.json"
    _write_json(swap_path, swap_rows)

    tick_files: list[dict] = []
    if date_from is not None and date_to is not None:
        start = _require_utc(date_from, "date_from")
        end = _require_utc(date_to, "date_to")
        for symbol in requested_symbols:
            safe_symbol = _safe_component(symbol)
            for chunk_from, chunk_to in iter_utc_chunks(
                start, end, chunk_hours=chunk_hours
            ):
                raw = client.ticks_range(
                    symbol,
                    chunk_from,
                    chunk_to,
                    tick_flags,
                )
                frame = normalize_ticks(
                    raw,
                    symbol=symbol,
                    date_from=chunk_from,
                    date_to=chunk_to,
                )
                relative = (
                    Path("ticks")
                    / safe_symbol
                    / f"{_stamp(chunk_from)}__{_stamp(chunk_to)}.parquet"
                )
                target = output_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                frame.to_parquet(target, index=False)
                valid = frame["valid_quote"] if "valid_quote" in frame else pd.Series(dtype=bool)
                tick_files.append(
                    {
                        "file": relative.as_posix(),
                        "symbol": symbol,
                        "date_from": chunk_from.isoformat(),
                        "date_to_exclusive": chunk_to.isoformat(),
                        "rows": int(len(frame)),
                        "valid_quotes": int(valid.sum()),
                        "invalid_quotes": int((~valid).sum()),
                        "first_tick_utc": (
                            frame["time_utc"].iloc[0].isoformat() if len(frame) else None
                        ),
                        "last_tick_utc": (
                            frame["time_utc"].iloc[-1].isoformat() if len(frame) else None
                        ),
                        "sha256": _sha256(target),
                        "bytes": target.stat().st_size,
                    }
                )

    manifest = {
        "schema_version": 1,
        "source": "MetaTrader5 terminal / broker server",
        "read_only": True,
        "observed_at_utc": observed.isoformat(),
        "broker": broker,
        "symbols": requested_symbols,
        "tick_request": (
            None
            if date_from is None
            else {
                "date_from": _require_utc(date_from, "date_from").isoformat(),
                "date_to_exclusive": _require_utc(date_to, "date_to").isoformat(),
                "chunk_hours": chunk_hours,
                "flags": tick_flags,
            }
        ),
        "swap_terms_are_current_snapshot": True,
        "swap_terms_file": {
            "file": swap_path.relative_to(output_dir).as_posix(),
            "sha256": _sha256(swap_path),
            "bytes": swap_path.stat().st_size,
            "rows": len(swap_rows),
        },
        "tick_files": tick_files,
        "limitations": [
            "symbol_info swap fields are current terms, not historical terms",
            "tick depth is limited by the connected broker server",
            "quote ticks do not prove executable depth for a requested lot size",
        ],
    }
    manifest_path = output_dir / "manifest.json"
    _write_json(manifest_path, manifest)
    return manifest_path


def verify_broker_snapshot(manifest_path: Path) -> dict:
    """Verify hashes, row counts, and path containment for a broker snapshot."""

    manifest_path = Path(manifest_path).resolve()
    root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = [manifest["swap_terms_file"], *manifest["tick_files"]]
    for entry in entries:
        target = (root / entry["file"]).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"arquivo fora do snapshot: {entry['file']}") from exc
        if not target.is_file():
            raise FileNotFoundError(target)
        if _sha256(target) != entry["sha256"]:
            raise ValueError(f"SHA256 inválido: {entry['file']}")
        if target.suffix == ".parquet":
            rows = len(pd.read_parquet(target, columns=["time_msc"]))
        else:
            rows = len(json.loads(target.read_text(encoding="utf-8")))
        if rows != entry["rows"]:
            raise ValueError(f"contagem de linhas inválida: {entry['file']}")
    return manifest


__all__ = [
    "build_swap_terms",
    "collect_broker_snapshot",
    "iter_utc_chunks",
    "normalize_ticks",
    "verify_broker_snapshot",
]
