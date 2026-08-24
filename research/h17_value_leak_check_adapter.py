"""Adapter for numerical causality checks of the H17 public value panel."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.value_data import VALUE_UNIVERSE, lag_monthly_panel, load_value_snapshot


def discover_cases(config: dict) -> list[dict]:
    return [
        {"case_id": f"h17_reer_{currency.lower()}", "currency": currency}
        for currency in VALUE_UNIVERSE
    ]


def load_input(case: dict, config: dict) -> pd.DataFrame:
    panel = load_value_snapshot(Path(config["manifest"]))["bis_reer_monthly"]
    date_from = pd.Timestamp(config["date_from"], tz="UTC")
    date_to = pd.Timestamp(config["date_to"], tz="UTC")
    currency = case["currency"]
    return panel.loc[(panel.index >= date_from) & (panel.index < date_to), [currency]]


def run_target(input_obj: pd.DataFrame, case: dict, config: dict) -> pd.DataFrame:
    return lag_monthly_panel(input_obj, lag_months=int(config["lag_months"]))


def input_length(input_obj: pd.DataFrame, case: dict, config: dict) -> int:
    return len(input_obj)


def choose_checkpoints(
    input_obj: pd.DataFrame, case: dict, config: dict
) -> list[int]:
    rows = len(input_obj)
    requested = {
        2,
        3,
        11,
        12,
        13,
        23,
        24,
        25,
        59,
        60,
        61,
        119,
        120,
        121,
        int(rows * 0.50),
        int(rows * 0.82),
        int(rows * 0.93),
        rows - 3,
        rows - 2,
    }
    return sorted(cut for cut in requested if 2 <= cut < rows - 1)


def make_prefix(
    input_obj: pd.DataFrame, cut: int, case: dict, config: dict
) -> pd.DataFrame:
    return input_obj.iloc[: cut + 1].copy()


def mutate_future(
    input_obj: pd.DataFrame, cut: int, case: dict, config: dict
) -> pd.DataFrame:
    result = input_obj.copy()
    future_rows = np.arange(len(result)) > cut
    if future_rows.any():
        scales = np.where(np.arange(len(result))[future_rows] % 2 == 0, 7.0, 0.15)
        result.iloc[future_rows] = result.iloc[future_rows].mul(scales, axis=0)
    return result


def compare_outputs(
    full_output: pd.DataFrame,
    test_output: pd.DataFrame,
    cut: int,
    case: dict,
    config: dict,
) -> dict:
    lag_months = int(config["lag_months"])
    source_cut = full_output.index[cut] - pd.DateOffset(months=lag_months)
    available_cut = source_cut + pd.DateOffset(months=lag_months)
    common = full_output.index.intersection(test_output.index)
    common = common[common <= available_cut]

    difference = (full_output.loc[common] - test_output.loc[common]).abs()
    values = difference.to_numpy(dtype=float).ravel()
    atol = float(config.get("atol", 1e-12))
    bad_locations = np.argwhere(difference.to_numpy(dtype=float) > atol)
    first_bad = ""
    if len(bad_locations):
        row, column = bad_locations[0]
        first_bad = f"{difference.index[row]}|{difference.columns[column]}"
    return {
        "max_abs_diff": float(np.nanmax(values)) if len(values) else 0.0,
        "bad_points": int((values > atol).sum()),
        "first_bad_idx": first_bad,
        "compared_points": int(len(values)),
        "notes": "compared only observations available by the simulated decision time",
    }
