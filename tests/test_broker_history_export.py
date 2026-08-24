from __future__ import annotations

from datetime import datetime, timezone
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from broker.history_export import (
    build_swap_terms,
    collect_broker_snapshot,
    normalize_ticks,
    verify_broker_snapshot,
)


UTC = timezone.utc


def _ticks(*rows: tuple[int, float, float]) -> np.ndarray:
    values = np.zeros(
        len(rows),
        dtype=[
            ("time", "i8"),
            ("bid", "f8"),
            ("ask", "f8"),
            ("last", "f8"),
            ("volume", "u8"),
            ("time_msc", "i8"),
            ("flags", "u4"),
            ("volume_real", "f8"),
        ],
    )
    for index, (time_msc, bid, ask) in enumerate(rows):
        values[index] = (
            time_msc // 1000,
            bid,
            ask,
            0.0,
            0,
            time_msc,
            6,
            0.0,
        )
    return values


def test_normalize_ticks_uses_utc_half_open_window_and_preserves_bad_quotes():
    start = datetime(2026, 8, 21, 10, tzinfo=UTC)
    end = datetime(2026, 8, 21, 11, tzinfo=UTC)
    raw = _ticks(
        (int(start.timestamp() * 1000), 1.1000, 1.1002),
        (int(start.timestamp() * 1000) + 1, 1.1001, 1.1000),
        (int(end.timestamp() * 1000), 1.1002, 1.1004),
    )

    frame = normalize_ticks(raw, symbol="EURUSD", date_from=start, date_to=end)

    assert len(frame) == 2
    assert str(frame["time_utc"].dt.tz) == "UTC"
    assert frame["valid_quote"].tolist() == [True, False]
    assert frame.loc[0, "spread_price"] == pytest.approx(0.0002)
    assert frame["time_utc"].max() < pd.Timestamp(end)


def test_build_swap_terms_records_units_and_daily_multipliers():
    info = SimpleNamespace(
        name="EURUSD",
        description="Euro vs US Dollar",
        path="Forex\\Majors\\EURUSD",
        currency_base="EUR",
        currency_profit="USD",
        currency_margin="EUR",
        digits=5,
        point=0.00001,
        trade_contract_size=100000.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        swap_mode=1,
        swap_long=-0.7,
        swap_short=-1.0,
        swap_rollover3days=3,
        swap_sunday=0.0,
        swap_monday=1.0,
        swap_tuesday=1.0,
        swap_wednesday=3.0,
        swap_thursday=1.0,
        swap_friday=0.0,
        swap_saturday=0.0,
    )
    observed_at = datetime(2026, 8, 22, 12, tzinfo=UTC)

    terms = build_swap_terms(info, observed_at=observed_at)

    assert terms["observed_at_utc"] == "2026-08-22T12:00:00+00:00"
    assert terms["swap_mode"] == 1
    assert terms["swap_long"] == -0.7
    assert terms["swap_wednesday"] == 3.0
    assert terms["trade_contract_size"] == 100000.0


class FakeClient:
    def account_info(self):
        return SimpleNamespace(
            company="Broker Example",
            server="Broker-Demo",
            trade_mode=0,
            currency="USD",
        )

    def symbol_info(self, symbol):
        return SimpleNamespace(
            name=symbol,
            description=symbol,
            path=f"Forex\\{symbol}",
            currency_base=symbol[:3],
            currency_profit=symbol[3:],
            currency_margin=symbol[:3],
            digits=5,
            point=0.00001,
            trade_contract_size=100000.0,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            swap_mode=1,
            swap_long=-0.7,
            swap_short=-1.0,
            swap_rollover3days=3,
            swap_sunday=0.0,
            swap_monday=1.0,
            swap_tuesday=1.0,
            swap_wednesday=3.0,
            swap_thursday=1.0,
            swap_friday=0.0,
            swap_saturday=0.0,
        )

    def ticks_range(self, symbol, date_from, date_to, flags):
        midpoint = date_from + (date_to - date_from) / 2
        return _ticks((int(midpoint.timestamp() * 1000), 1.1000, 1.1002))


def test_collect_broker_snapshot_writes_hashed_read_only_artifacts(tmp_path):
    observed_at = datetime(2026, 8, 22, 12, tzinfo=UTC)
    manifest_path = collect_broker_snapshot(
        FakeClient(),
        symbols=["EURUSD"],
        date_from=datetime(2026, 8, 20, tzinfo=UTC),
        date_to=datetime(2026, 8, 22, tzinfo=UTC),
        output_dir=tmp_path / "snapshot",
        chunk_hours=24,
        tick_flags=1,
        observed_at=observed_at,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tick_files = manifest["tick_files"]

    assert manifest["read_only"]
    assert manifest["broker"]["server"] == "Broker-Demo"
    assert len(tick_files) == 2
    assert all(item["sha256"] for item in tick_files)
    assert all(item["rows"] == 1 for item in tick_files)
    assert (manifest_path.parent / manifest["swap_terms_file"]["file"]).exists()
    assert verify_broker_snapshot(manifest_path)["read_only"]

    swap_path = manifest_path.parent / manifest["swap_terms_file"]["file"]
    swap_path.write_bytes(swap_path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="SHA256"):
        verify_broker_snapshot(manifest_path)
