from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from research.scalping_pullback_study import (
    build_pullback_events,
    render_csv,
    summarize_events,
    summary_row,
    validate_inputs,
    write_study,
)


def m5_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": pd.to_datetime(
                [
                    "2020-01-02 13:40:00+00:00",
                    "2020-01-02 13:45:00+00:00",
                    "2020-01-02 13:50:00+00:00",
                    "2020-01-02 13:55:00+00:00",
                    "2020-01-02 14:00:00+00:00",
                    "2020-01-02 14:05:00+00:00",
                    "2020-01-02 14:10:00+00:00",
                    "2020-01-02 14:15:00+00:00",
                    "2020-01-02 14:20:00+00:00",
                    "2020-01-02 14:25:00+00:00",
                ],
                utc=True,
            ),
            "open": [
                150.00,
                149.98,
                149.96,
                149.95,
                149.94,
                149.91,
                149.92,
                149.95,
                149.98,
                150.00,
            ],
            "close": [
                149.99,
                149.97,
                149.95,
                149.94,
                149.91,
                149.92,
                149.95,
                149.98,
                150.00,
                150.02,
            ],
            "spread": [4.0] * 10,
        }
    )


def states_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "state_time": pd.to_datetime(
                ["2020-01-02 13:45:00+00:00"],
                utc=True,
            ),
            "direction": [1],
            "blended_value": [0.5],
        }
    )


def test_build_pullback_events_finds_long_pullback_reversal() -> None:
    events = build_pullback_events(
        m5_frame(),
        states_frame(),
        symbol="USDJPY",
        pullback_lookback=3,
        pullback_min_pips=2.0,
        cost_overhead_pips=1.7,
        horizons=(1, 2),
    )

    assert set(events["horizon_bars"]) == {1, 2}
    assert (events["direction"] == 1).all()
    assert (events["pullback_pips"] <= -2.0).all()
    assert (events["body_pips"] > 0).all()
    assert events["entry_spread_pips"].iloc[0] == pytest.approx(0.4)


def test_summarize_events_includes_session_and_all_rows() -> None:
    events = build_pullback_events(
        m5_frame(),
        states_frame(),
        symbol="USDJPY",
        pullback_lookback=3,
        pullback_min_pips=2.0,
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


def test_summary_row_calculates_net_and_hit_rate() -> None:
    group = pd.DataFrame(
        {
            "gross_pips": [1.0, -0.5, 2.0],
            "net_pips": [-1.1, -2.6, -0.1],
            "entry_spread_pips": [0.4, 0.5, 0.6],
        }
    )

    row = summary_row(
        group,
        symbol="USDJPY",
        session="all",
        direction="all",
        horizon_bars=1,
    )

    assert row["events"] == 3
    assert row["hit_rate"] == pytest.approx(2 / 3)
    assert row["mean_gross_pips"] == pytest.approx(0.833333)
    assert row["mean_net_pips"] == pytest.approx(-1.266667)


def test_write_study_outputs_json_and_csv(tmp_path: Path) -> None:
    study = {
        "schema_version": "scalping-pullback-study/0.1.0",
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
            pullback_lookback=3,
            pullback_min_pips=2.0,
            horizons=(1,),
        )
