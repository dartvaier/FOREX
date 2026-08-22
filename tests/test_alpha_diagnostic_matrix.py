from __future__ import annotations

from pathlib import Path

from research.alpha_diagnostic_matrix import (
    VARIANTS,
    AlphaDiagnosticVariant,
    render_csv,
    render_variant_config,
    run_alpha_diagnostic_matrix,
    write_summary_files,
    write_variant_configs,
)


def test_render_variant_config_for_single_alpha() -> None:
    config = render_variant_config(
        AlphaDiagnosticVariant(
            key="tsmom_only",
            strategy_id="TEST-TSMOM",
            models=("time-series-momentum",),
            min_active_models=1,
        ),
        symbol="USDJPY",
    )

    assert "symbol: USDJPY" in config
    assert "strategy_id: TEST-TSMOM" in config
    assert "id: time-series-momentum" in config
    assert "id: ema-trend" not in config
    assert "min_active_models: 1" in config
    assert "pip_size: auto" in config
    assert "cost_gate:" not in config
    assert "regime_gate:" not in config


def test_render_variant_config_can_include_regime_and_cost_gates() -> None:
    config = render_variant_config(
        AlphaDiagnosticVariant(
            key="full",
            strategy_id="TEST-FULL",
            models=("time-series-momentum", "ema-trend"),
            min_active_models=2,
            use_regime_gate=True,
            use_cost_gate=True,
            cost_estimate_pips=2.8,
        ),
        symbol="USDJPY",
    )

    assert "id: time-series-momentum" in config
    assert "id: ema-trend" in config
    assert "regime_gate:" in config
    assert "allowed_regimes: [trending_up, trending_down]" in config
    assert "cost_gate:" in config
    assert "cost_estimate_pips: 2.8" in config


def test_write_variant_configs_creates_one_yaml_per_variant(
    tmp_path: Path,
) -> None:
    paths = write_variant_configs(
        symbol="USDJPY",
        out_dir=tmp_path,
    )

    assert set(paths) == {
        variant.key
        for variant in VARIANTS
    }
    assert all(
        path.exists()
        for path in paths.values()
    )


def test_run_alpha_diagnostic_matrix_calls_runner_per_variant(
    tmp_path: Path,
) -> None:
    calls = []

    def fake_run_multi_symbol(**kwargs):
        calls.append(kwargs)
        variant = Path(
            kwargs["strategy_params"]["config_path"]
        ).stem
        return [
            {
                "symbol": kwargs["symbols"][0],
                "cost": "explicit",
                "trades": 10,
                "net_profit": 1.23,
                "return_pct": 0.0123,
                "max_dd_pct": 0.1,
                "win_rate": 50.0,
                "profit_factor": 1.1,
                "expectancy": 0.123,
                "round_trip_cost_pips": 2.28,
                "report_path": f"{variant}.json",
            }
        ]

    rows = run_alpha_diagnostic_matrix(
        symbol="USDJPY",
        cost="explicit",
        date_from=None,
        date_to=None,
        calibrated_spread=True,
        calibration_path=tmp_path / "costs.json",
        out_dir=tmp_path,
        run_multi_symbol_fn=fake_run_multi_symbol,
    )

    assert len(calls) == len(VARIANTS)
    assert len(rows) == len(VARIANTS)
    assert {
        row["variant"]
        for row in rows
    } == {
        variant.key
        for variant in VARIANTS
    }
    assert all(
        call["calibrated_spread"] is True
        for call in calls
    )


def test_write_summary_files_writes_json_and_csv(tmp_path: Path) -> None:
    rows = [
        {
            "variant": "tsmom_only",
            "symbol": "USDJPY",
            "cost": "explicit",
            "trades": 10,
            "net_profit": 1.23,
            "return_pct": 0.0123,
            "max_dd_pct": 0.1,
            "win_rate": 50.0,
            "profit_factor": 1.1,
            "expectancy": 0.123,
            "round_trip_cost_pips": 2.28,
            "report_path": "report.json",
        }
    ]

    json_path, csv_path = write_summary_files(
        rows,
        symbol="USDJPY",
        cost="explicit",
        out_dir=tmp_path,
    )

    assert json_path.exists()
    assert csv_path.exists()
    assert "alpha-diagnostic-matrix/0.1.0" in json_path.read_text(
        encoding="utf-8"
    )
    assert render_csv(rows).startswith("variant,symbol,cost")
