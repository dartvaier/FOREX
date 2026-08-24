from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from research.scalping_breakout_study import (
    build_breakout_events,
    render_csv,
    validate_inputs,
    write_study,
)
from research.scalping_pullback_study import summarize_events


def m5_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2020-01-02 13:00:00+00:00",
                    "2020-01-02 13:05:00+00:00",
                    "2020-01-02 13:10:00+00:00",
                    "2020-01-02 13:15:00+00:00",
                    "2020-01-02 13:20:00+00:00",
                    "2020-01-02 13:25:00+00:00",
                    "2020-01-02 13:30:00+00:00",
                    "2020-01-02 13:35:00+00:00",
                    "2020-01-02 13:40:00+00:00",
                ],
                utc=True,
            ),
            "open": [
                150.00,
                150.01,
                150.02,
                150.03,
                150.04,
                150.05,
                150.06,
                150.08,
                150.10,
            ],
            "high": [
                150.02,
                150.03,
                150.04,
                150.05,
                150.06,
                150.07,
                150.09,
                150.12,
                150.14,
            ],
            "low": [
                149.99,
                150.00,
                150.01,
                150.02,
                150.03,
                150.04,
                150.05,
                150.07,
                150.09,
            ],
            "close": [
                150.01,
                150.02,
                150.03,
                150.04,
                150.05,
                150.06,
                150.08,
                150.11,
                150.13,
            ],
            "spread": [4.0] * 9,
        }
    )


def states_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "state_time": pd.to_datetime(
                ["2020-01-02 13:05:00+00:00"],
                utc=True,
            ),
            "direction": [1],
            "blended_value": [0.65],
        }
    )


def test_build_breakout_events_finds_long_continuation() -> None:
    events = build_breakout_events(
        m5_frame(),
        states_frame(),
        symbol="USDJPY",
        breakout_lookback=3,
        min_breakout_pips=0.5,
        min_body_pips=0.5,
        cost_overhead_pips=1.7,
        horizons=(1, 2),
    )

    assert set(events["horizon_bars"]) == {1, 2}
    assert (events["direction"] == 1).all()
    assert (events["breakout_pips"] >= 0.5).all()
    assert (events["body_pips"] >= 0.5).all()
    assert events["entry_spread_pips"].iloc[0] == pytest.approx(0.4)
    assert events["regime_strength"].iloc[0] == pytest.approx(0.65)
    assert "spread_slot_percentile" in events.columns


def test_summarize_events_includes_session_and_all_rows() -> None:
    events = build_breakout_events(
        m5_frame(),
        states_frame(),
        symbol="USDJPY",
        breakout_lookback=3,
        min_breakout_pips=0.5,
        min_body_pips=0.5,
        horizons=(1,),
    )
    rows = summarize_events(
        events,
        symbol="USDJPY",
    )

    assert {
        row["session"]
        for row in rows
    } >= {"london_ny_overlap", "all"}
    assert all(
        row["events"] > 0
        for row in rows
    )


def test_write_study_outputs_json_and_csv(tmp_path: Path) -> None:
    study = {
        "schema_version": "scalping-breakout-study/0.1.0",
        "symbol": "USDJPY",
        "summary": [
            {
                "symbol": "USDJPY",
                "session": "all",
                "direction": "all",
                "horizon_bars": 1,
                "events": 1,
                "mean_gross_pips": 0.1,
                "median_gross_pips": 0.1,
                "hit_rate": 1.0,
                "mean_net_pips": -2.0,
                "median_entry_spread_pips": 0.4,
                "mean_entry_spread_pips": 0.4,
            }
        ],
    }

    json_path, csv_path = write_study(
        study,
        out_dir=tmp_path,
    )

    assert json_path.exists()
    assert csv_path.exists()
    assert render_csv(study["summary"]).startswith(
        "symbol,session,direction"
    )


def test_validate_inputs_rejects_empty_frames() -> None:
    with pytest.raises(ValueError, match="m5 cannot be empty"):
        validate_inputs(
            pd.DataFrame(),
            states_frame(),
            breakout_lookback=3,
            min_breakout_pips=0.5,
            min_body_pips=0.5,
            horizons=(1,),
        )


def test_validate_inputs_rejects_missing_high_low() -> None:
    with pytest.raises(ValueError, match="m5 missing column: high"):
        validate_inputs(
            m5_frame().drop(columns=["high"]),
            states_frame(),
            breakout_lookback=3,
            min_breakout_pips=0.5,
            min_body_pips=0.5,
            horizons=(1,),
        )
