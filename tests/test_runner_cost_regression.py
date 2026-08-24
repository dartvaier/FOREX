# -*- coding: utf-8 -*-
"""Regression test: build_report receives effective_cost_params (RA-04 bug).

The RA-04 change (7cf7c87) added `effective_cost_params` to the
report dict but never threaded the argument through build_report —
the runner crashed with NameError on every real backtest. This test
exercises the full run_single path with explicit costs and asserts
the report is produced with both cost_params and
effective_cost_params populated.
"""
import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.runner import (  # noqa: E402
    STRATEGY_REGISTRY,
    discover_strategy_class,
    run_single,
)

DATA_DIR = Path("data/raw/EURUSD/M15.parquet")


def _tsm_class():
    return discover_strategy_class(STRATEGY_REGISTRY["time_series_momentum"])


def _make_params():
    return {
        "symbol": "EURUSD",
        "timeframe": "M15",
        "strategy_params": {"lookback": 96, "entry_threshold": 0.001},
        "date_from": "2015-01-01",
        "date_to": "2016-01-01",
        "cost_mode": "explicit",
        "cost_params": {
            "spread_pips": 2.0,
            "slippage_pips": 0.5,
            "commission_per_lot_per_side": 3.50,
        },
        "cost_multiplier": 1.0,
        "initial_capital": 10_000.0,
        "fixed_quantity": 0.01,
        "write_equity": False,
    }


@pytest.mark.skipif(
    not DATA_DIR.exists(),
    reason="EURUSD M15 dataset not available",
)
def test_run_single_explicit_report_has_effective_cost_params(tmp_path):
    params = _make_params()
    params["out_dir"] = tmp_path
    params["tag"] = "regression-test"
    params["strategy_class"] = _tsm_class()
    params["strategy_module"] = STRATEGY_REGISTRY["time_series_momentum"]

    report_path = run_single(**params)
    assert report_path is not None
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))

    assert report["cost_analysis"]["baseline_cost_params"] == {
        "spread_pips": 2.0,
        "slippage_pips": 0.5,
        "commission_per_lot_per_side": 3.50,
    }
    assert report["cost_analysis"]["effective_cost_params"] == {
        "spread_pips": 2.0,
        "slippage_pips": 0.5,
        "commission_per_lot_per_side": 3.50,
    }


@pytest.mark.skipif(
    not DATA_DIR.exists(),
    reason="EURUSD M15 dataset not available",
)
def test_run_single_explicit_override_spread_is_effective(tmp_path):
    """--spread-pips override must flow into effective cost params."""
    params = _make_params()
    params["out_dir"] = tmp_path
    params["tag"] = "regression-test-override"
    params["strategy_class"] = _tsm_class()
    params["strategy_module"] = STRATEGY_REGISTRY["time_series_momentum"]
    params["cost_params"]["spread_pips"] = 0.2

    report_path = run_single(**params)
    assert report_path is not None
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))

    eff = report["cost_analysis"]["effective_cost_params"]
    assert eff["spread_pips"] == pytest.approx(0.2)
