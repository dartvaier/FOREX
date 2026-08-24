from __future__ import annotations

import pandas as pd
import pytest

from research.cross_sectional_momentum import (
    formation_weights,
    foreign_currency_value,
    run_cross_sectional_momentum,
    turnover_cost_fraction,
)


def test_foreign_currency_value_normalizes_ticker_orientation():
    assert foreign_currency_value("EURUSD", 1.20) == pytest.approx(1.20)
    assert foreign_currency_value("USDJPY", 120.0) == pytest.approx(
        1.0 / 120.0
    )


def test_formation_weights_are_dollar_neutral_and_deterministic():
    scores = pd.Series(
        {
            "AUDUSD": 0.03,
            "EURUSD": 0.03,
            "GBPUSD": 0.01,
            "USDCHF": -0.01,
            "USDJPY": -0.02,
        }
    )

    weights = formation_weights(scores, n_select=2)

    assert weights == {
        "AUDUSD": 0.25,
        "EURUSD": 0.25,
        "GBPUSD": 0.0,
        "USDCHF": -0.25,
        "USDJPY": -0.25,
    }
    assert sum(weights.values()) == pytest.approx(0.0)
    assert sum(abs(value) for value in weights.values()) == pytest.approx(1.0)


def test_turnover_cost_uses_half_round_trip_and_correct_pip_size():
    cost = turnover_cost_fraction(
        previous_weights={"EURUSD": 0.0, "USDJPY": 0.0},
        target_weights={"EURUSD": 0.25, "USDJPY": -0.25},
        pair_prices=pd.Series({"EURUSD": 1.20, "USDJPY": 120.0}),
        round_trip_cost_pips=3.7,
    )

    expected = 0.25 * 0.5 * 3.7 * 0.0001 / 1.20
    expected += 0.25 * 0.5 * 3.7 * 0.01 / 120.0
    assert cost == pytest.approx(expected)


def test_future_mutation_does_not_change_earlier_formation_weights():
    dates = pd.to_datetime(
        [
            "2019-01-31",
            "2019-02-28",
            "2019-03-31",
            "2019-04-30",
            "2019-05-31",
        ],
        utc=True,
    )
    closes = pd.DataFrame(
        {
            "AUDUSD": [1.00, 1.10, 1.21, 1.33, 1.46],
            "EURUSD": [1.00, 1.05, 1.10, 1.15, 1.20],
            "GBPUSD": [1.00, 1.00, 1.00, 1.00, 1.00],
            "USDCHF": [1.00, 1.05, 1.10, 1.15, 1.20],
            "USDJPY": [100.0, 110.0, 121.0, 133.1, 146.41],
        },
        index=dates,
    )

    baseline = run_cross_sectional_momentum(
        closes,
        lookback_months=1,
        round_trip_cost_pips=0.0,
    )
    mutated = closes.copy()
    mutated.iloc[-1] = [9.0, 0.1, 8.0, 0.2, 20.0]
    replay = run_cross_sectional_momentum(
        mutated,
        lookback_months=1,
        round_trip_cost_pips=0.0,
    )

    earlier = baseline.index[:-1]
    assert baseline.loc[earlier, "weights"].tolist() == replay.loc[
        earlier, "weights"
    ].tolist()
    assert baseline.loc[earlier, "net_return"].tolist() == pytest.approx(
        replay.loc[earlier, "net_return"].tolist()
    )
