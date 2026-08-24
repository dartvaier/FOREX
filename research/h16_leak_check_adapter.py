"""Adapter for numerical causality checks of the H16 carry pipeline."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.carry_data import load_rate_snapshot
from research.cross_sectional_carry import (
    CURRENCY_BY_SYMBOL,
    _period_closes,
    rate_observation_month,
    run_cross_sectional_carry,
)
from research.cross_sectional_momentum import load_monthly_pair_closes


def discover_cases(config: dict) -> list[dict]:
    return [
        {"case_id": f"h16_top_bottom_{n_select}", "n_select": n_select}
        for n_select in (1, 2, 3)
    ]


def load_input(case: dict, config: dict) -> dict:
    date_from = pd.Timestamp(config["date_from"], tz="UTC")
    date_to = pd.Timestamp(config["date_to"], tz="UTC")
    closes = _period_closes(
        load_monthly_pair_closes(symbols=CURRENCY_BY_SYMBOL),
        date_from=date_from,
        date_to=date_to,
    )
    rates = load_rate_snapshot(Path(config["manifest"]))
    return {"closes": closes, "rates": rates}


def run_target(input_obj: dict, case: dict, config: dict) -> pd.DataFrame:
    return run_cross_sectional_carry(
        input_obj["closes"],
        input_obj["rates"],
        n_select=int(case["n_select"]),
    )


def input_length(input_obj: dict, case: dict, config: dict) -> int:
    return len(input_obj["closes"])


def choose_checkpoints(input_obj: dict, case: dict, config: dict) -> list[int]:
    rows = len(input_obj["closes"])
    requested = {
        2,
        3,
        4,
        5,
        6,
        10,
        11,
        12,
        13,
        20,
        24,
        25,
        30,
        36,
        40,
        48,
        50,
        int(rows * 0.82),
        59,
        60,
        int(rows * 0.93),
        rows - 4,
        rows - 3,
        rows - 2,
    }
    return sorted(cut for cut in requested if 2 <= cut < rows - 1)


def _last_rate_needed(closes: pd.DataFrame, cut: int) -> pd.Timestamp:
    return rate_observation_month(closes.index[cut - 1])


def make_prefix(input_obj: dict, cut: int, case: dict, config: dict) -> dict:
    closes = input_obj["closes"].iloc[: cut + 1].copy()
    last_rate = _last_rate_needed(input_obj["closes"], cut)
    rates = input_obj["rates"].loc[:last_rate].copy()
    return {"closes": closes, "rates": rates}


def mutate_future(input_obj: dict, cut: int, case: dict, config: dict) -> dict:
    result = deepcopy(input_obj)
    closes = result["closes"]
    future_rows = np.arange(len(closes)) > cut
    if future_rows.any():
        scales = np.where(np.arange(len(closes))[future_rows] % 2 == 0, 7.0, 0.15)
        closes.iloc[future_rows] = closes.iloc[future_rows].mul(scales, axis=0)

    last_rate = _last_rate_needed(closes, cut)
    future_rates = result["rates"].index > last_rate
    if future_rates.any():
        result["rates"].loc[future_rates] = (
            -100.0 * result["rates"].loc[future_rates] + 37.0
        )
    return result


def compare_outputs(
    full_output: pd.DataFrame,
    test_output: pd.DataFrame,
    cut: int,
    case: dict,
    config: dict,
) -> dict:
    prefix = len(test_output) < len(full_output)
    common = full_output.index.intersection(test_output.index)
    if not prefix:
        common = common[:cut]
    full = full_output.loc[common]
    test = test_output.loc[common]
    numeric_columns = [
        "spot_return",
        "carry_accrual_return",
        "gross_return",
        "cost_return",
        "net_return",
        "turnover",
    ]

    differences: list[tuple[str, float]] = []
    for column in numeric_columns:
        rows = common[:-1] if prefix and column in {"cost_return", "net_return"} else common
        for index, value in (full.loc[rows, column] - test.loc[rows, column]).abs().items():
            differences.append((f"{index}|{column}", float(value)))

    for column in ("formation_date", "rate_observation_date", "weights", "rate_differentials"):
        for index in common:
            equal = full.at[index, column] == test.at[index, column]
            differences.append((f"{index}|{column}", 0.0 if equal else 1.0))

    atol = float(config.get("atol", 1e-12))
    bad = [(label, value) for label, value in differences if value > atol]
    return {
        "max_abs_diff": max((value for _, value in differences), default=0.0),
        "bad_points": len(bad),
        "first_bad_idx": bad[0][0] if bad else "",
        "compared_points": len(differences),
        "notes": (
            "prefix final cost/net excluded because the prefix liquidates at its "
            "artificial boundary"
            if prefix
            else "future prices and rates strongly mutated"
        ),
    }
