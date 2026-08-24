from __future__ import annotations

import pandas as pd
import pytest

from research.cross_sectional_carry import (
    CURRENCY_BY_SYMBOL,
    rate_observation_month,
    run_cross_sectional_carry,
)


SYMBOLS = list(CURRENCY_BY_SYMBOL)
CURRENCIES = ["AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"]


def constant_closes() -> pd.DataFrame:
    dates = pd.to_datetime(
        ["2019-01-31", "2019-02-28", "2019-03-31"],
        utc=True,
    )
    return pd.DataFrame(
        {
            "AUDUSD": [1.0, 1.0, 1.0],
            "EURUSD": [1.1, 1.1, 1.1],
            "GBPUSD": [1.2, 1.2, 1.2],
            "NZDUSD": [0.7, 0.7, 0.7],
            "USDCAD": [1.3, 1.3, 1.3],
            "USDCHF": [1.0, 1.0, 1.0],
            "USDJPY": [110.0, 110.0, 110.0],
        },
        index=dates,
    )


def rate_frame() -> pd.DataFrame:
    dates = pd.to_datetime(
        ["2018-12-01", "2019-01-01", "2019-02-01"],
        utc=True,
    )
    return pd.DataFrame(
        {
            "AUD": [8.0, -8.0, -8.0],
            "CAD": [0.0, 0.0, 0.0],
            "CHF": [-2.0, 2.0, 2.0],
            "EUR": [6.0, -6.0, -6.0],
            "GBP": [4.0, -4.0, -4.0],
            "JPY": [-4.0, 4.0, 4.0],
            "NZD": [2.0, -2.0, -2.0],
            "USD": [0.0, 0.0, 0.0],
        },
        index=dates,
    )[CURRENCIES]


def test_rate_observation_month_is_t_minus_two_for_holding_month():
    formation = pd.Timestamp("2019-01-31", tz="UTC")

    assert rate_observation_month(formation) == pd.Timestamp(
        "2018-12-01", tz="UTC"
    )


def test_carry_accrual_uses_lagged_differentials_and_correct_sign():
    results = run_cross_sectional_carry(
        constant_closes(),
        rate_frame(),
        round_trip_cost_pips=0.0,
        n_select=2,
    )
    first = results.iloc[0]

    assert first["rate_observation_date"] == pd.Timestamp(
        "2018-12-01", tz="UTC"
    )
    assert first["weights"]["AUDUSD"] == pytest.approx(0.25)
    assert first["weights"]["EURUSD"] == pytest.approx(0.25)
    assert first["weights"]["USDJPY"] == pytest.approx(-0.25)
    assert first["weights"]["USDCHF"] == pytest.approx(-0.25)
    assert first["spot_return"] == pytest.approx(0.0)
    assert first["carry_accrual_return"] == pytest.approx(5.0 / 100.0 / 12.0)
    assert first["gross_return"] == pytest.approx(first["carry_accrual_return"])


def test_future_rate_and_price_mutation_does_not_change_earlier_result():
    closes = constant_closes()
    rates = rate_frame()
    baseline = run_cross_sectional_carry(
        closes,
        rates,
        round_trip_cost_pips=0.0,
    )

    mutated_closes = closes.copy()
    mutated_closes.iloc[-1] = [9.0, 0.2, 8.0, 0.3, 4.0, 0.4, 20.0]
    mutated_rates = rates.copy()
    mutated_rates.loc[mutated_rates.index >= pd.Timestamp("2019-01-01", tz="UTC")] *= -100.0
    replay = run_cross_sectional_carry(
        mutated_closes,
        mutated_rates,
        round_trip_cost_pips=0.0,
    )

    assert baseline.iloc[0]["weights"] == replay.iloc[0]["weights"]
    assert baseline.iloc[0]["net_return"] == pytest.approx(
        replay.iloc[0]["net_return"]
    )


def test_missing_required_rate_is_rejected_without_forward_fill():
    rates = rate_frame()
    rates.loc[pd.Timestamp("2018-12-01", tz="UTC"), "JPY"] = float("nan")

    with pytest.raises(ValueError, match="missing rates for 2018-12"):
        run_cross_sectional_carry(constant_closes(), rates)
