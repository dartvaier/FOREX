from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from research.scalping_breakout_filter_sweep import (
    quality_filter_row,
    quality_filter_sweep,
    render_csv,
    validate_events,
    write_filter_sweep,
)


def events_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "session": [
                "london_morning",
                "london_ny_overlap",
                "london_ny_overlap",
                "new_york",
            ],
            "direction": [1, 1, -1, 1],
            "horizon_bars": [6, 6, 6, 3],
            "spread_slot_percentile": [0.40, 0.55, 0.45, 0.30],
            "regime_strength": [0.70, 0.55, 0.80, 0.90],
            "breakout_pips": [2.5, 1.5, 3.0, 2.0],
            "body_pips": [1.2, 0.6, 1.5, 0.7],
            "gross_pips": [4.0, 2.0, -1.0, 1.0],
            "net_pips": [1.9, -0.1, -3.1, -1.2],
            "entry_spread_pips": [0.4, 0.4, 0.4, 0.5],
        }
    )


def test_quality_filter_sweep_applies_all_filters() -> None:
    rows = quality_filter_sweep(
        events_frame(),
        symbol="USDJPY",
        session_groups={
            "liquid": ("london_morning", "london_ny_overlap"),
        },
        direction_groups={"long": 1},
        horizons=(6,),
        max_spread_slot_percentiles=(0.50,),
        min_regime_strengths=(0.60,),
        min_breakout_pips=(2.0,),
        min_body_pips=(1.0,),
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["events"] == 1
    assert row["mean_gross_pips"] == pytest.approx(4.0)
    assert row["mean_net_pips"] == pytest.approx(1.9)


def test_quality_filter_row_handles_empty_group() -> None:
    row = quality_filter_row(
        events_frame().iloc[0:0],
        symbol="USDJPY",
        session_group="liquid",
        direction_group="long",
        horizon_bars=6,
        max_spread_slot_percentile=0.5,
        min_regime_strength=0.6,
        min_breakout_pips=2.0,
        min_body_pips=1.0,
    )

    assert row["events"] == 0
    assert row["mean_net_pips"] is None


def test_validate_events_rejects_empty_frame() -> None:
    with pytest.raises(ValueError, match="events cannot be empty"):
        validate_events(pd.DataFrame())


def test_validate_events_rejects_missing_column() -> None:
    with pytest.raises(ValueError, match="events missing columns"):
        validate_events(events_frame().drop(columns=["breakout_pips"]))


def test_write_filter_sweep_outputs_json_and_csv(tmp_path: Path) -> None:
    study = {
        "schema_version": "scalping-breakout-filter-sweep/0.1.0",
        "symbol": "USDJPY",
        "summary": [
            quality_filter_row(
                events_frame(),
                symbol="USDJPY",
                session_group="all",
                direction_group="all",
                horizon_bars=6,
                max_spread_slot_percentile=0.6,
                min_regime_strength=0.5,
                min_breakout_pips=1.0,
                min_body_pips=0.5,
            )
        ],
    }

    json_path, csv_path = write_filter_sweep(
        study,
        out_dir=tmp_path,
    )

    assert json_path.exists()
    assert csv_path.exists()
    assert render_csv(study["summary"]).startswith(
        "symbol,session_group,direction_group"
    )
