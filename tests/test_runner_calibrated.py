# -*- coding: utf-8 -*-
"""Tests for runner --calibrated-spread (docs/26 §25)."""
import json
from pathlib import Path

import pytest

import research.runner as runner


def _calibration_fixture(tmp_path: Path, spreads: dict[str, float]) -> Path:
    path = tmp_path / "cost_measurement_all.json"
    path.write_text(
        json.dumps(
            {"symbols": {s: {"spread_pips_median": v} for s, v in spreads.items()}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_load_calibrated_spread_returns_median(tmp_path):
    path = _calibration_fixture(tmp_path, {"EURUSD": 0.2, "NZDUSD": 0.9})
    assert runner.load_calibrated_spread("EURUSD", path) == pytest.approx(0.2)
    assert runner.load_calibrated_spread("NZDUSD", path) == pytest.approx(0.9)


def test_load_calibrated_spread_missing_file(tmp_path):
    with pytest.raises(ValueError, match="calibrated-spread requires"):
        runner.load_calibrated_spread("EURUSD", tmp_path / "missing.json")


def test_load_calibrated_spread_unknown_symbol(tmp_path):
    path = _calibration_fixture(tmp_path, {"EURUSD": 0.2})
    with pytest.raises(ValueError, match="not found"):
        runner.load_calibrated_spread("GBPUSD", path)


def test_resolve_spread_calibrated(tmp_path):
    path = _calibration_fixture(tmp_path, {"EURUSD": 0.2})
    spread = runner.resolve_spread_pips(
        symbol="EURUSD",
        spread_pips=None,
        calibrated=True,
        cost_mode="explicit",
        calibration_path=path,
    )
    assert spread == pytest.approx(0.2)


def test_resolve_spread_explicit_override_wins():
    spread = runner.resolve_spread_pips(
        symbol="EURUSD",
        spread_pips=1.5,
        calibrated=False,
        cost_mode="explicit",
    )
    assert spread == pytest.approx(1.5)


def test_resolve_spread_default_baseline():
    spread = runner.resolve_spread_pips(
        symbol="EURUSD",
        spread_pips=None,
        calibrated=False,
        cost_mode="explicit",
    )
    assert spread == pytest.approx(runner.DEFAULT_EXPLICIT_COSTS["spread_pips"])


def test_resolve_spread_calibrated_ignored_under_zero_costs(tmp_path):
    path = _calibration_fixture(tmp_path, {"EURUSD": 0.2})
    spread = runner.resolve_spread_pips(
        symbol="EURUSD",
        spread_pips=None,
        calibrated=True,
        cost_mode="zero",
        calibration_path=path,
    )
    assert spread == pytest.approx(runner.DEFAULT_EXPLICIT_COSTS["spread_pips"])


def test_resolve_spread_rejects_calibrated_and_override(tmp_path):
    path = _calibration_fixture(tmp_path, {"EURUSD": 0.2})
    with pytest.raises(ValueError, match="not both"):
        runner.resolve_spread_pips(
            symbol="EURUSD",
            spread_pips=0.5,
            calibrated=True,
            cost_mode="explicit",
            calibration_path=path,
        )


def test_build_parser_has_calibrated_flag():
    parser = runner.build_parser()
    args = parser.parse_args(["--strategy", "ema_trend", "--calibrated-spread"])
    assert args.calibrated_spread is True
    assert args.spread_pips is None
