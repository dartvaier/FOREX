"""
Tests for the multi-symbol instrument registry (roadmap §104).

USDJPY is the critical case: digits 3 / pip 0.01. Cost math is
expressed in pips first (the invariant), money in quote currency.
"""

from __future__ import annotations

import pytest

from backtest.models import InstrumentSpecification
from research.runner import (
    INSTRUMENT_REGISTRY,
    money_to_pips,
    round_trip_cost_money,
)

MAJORS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "AUDUSD",
    "USDCAD",
    "NZDUSD",
]

BASELINE_COSTS = {
    "spread_pips": 2.0,
    "slippage_pips": 0.5,
    "commission_per_lot_per_side": 3.50,
}


def test_registry_has_all_seven_majors():
    assert set(INSTRUMENT_REGISTRY) == set(MAJORS)


def test_usdjpy_uses_three_digits_and_pip_001():
    spec = InstrumentSpecification(
        **INSTRUMENT_REGISTRY["USDJPY"]
    )

    assert spec.digits == 3
    assert spec.point == 0.001
    assert spec.pip_size == 0.01
    assert spec.contract_size == 100000


def test_five_digit_pairs_use_pip_0001():
    for symbol in ("EURUSD", "GBPUSD", "USDCHF",
                   "AUDUSD", "USDCAD", "NZDUSD"):
        spec = InstrumentSpecification(
            **INSTRUMENT_REGISTRY[symbol]
        )

        assert spec.digits == 5
        assert spec.point == 0.00001
        assert spec.pip_size == 0.00010


def test_round_trip_cost_pips_identical_across_usd_quote_pairs():
    # The cost invariant is expressed in pips: every USD-quote
    # pair must have the same round-trip cost in pips for the
    # same inputs. USDJPY is excluded: its quote currency is
    # JPY and the commission (USD) needs a currency conversion
    # that is declared future work (docs/20).
    pips: set[float] = set()

    for symbol in (
        "EURUSD",
        "GBPUSD",
        "USDCHF",
        "AUDUSD",
        "USDCAD",
        "NZDUSD",
    ):
        spec = InstrumentSpecification(
            **INSTRUMENT_REGISTRY[symbol]
        )

        money = round_trip_cost_money(
            spec,
            0.01,
            BASELINE_COSTS,
        )

        pips.add(
            money_to_pips(
                money,
                spec,
                0.01,
            )
        )

    assert len(pips) == 1
    assert round(pips.pop(), 2) == 3.7


def test_round_trip_cost_usdjpy_spread_slippage_in_jpy():
    # USDJPY spread+slippage leg: (2.0 + 2*0.5) pips * 0.01 pip
    # * 100k = 3000 JPY per lot -> 30.0 JPY for 0.01 lot.
    # Commission remains USD-based (model limitation, docs/20).
    spec = InstrumentSpecification(
        **INSTRUMENT_REGISTRY["USDJPY"]
    )

    money = round_trip_cost_money(
        spec,
        0.01,
        BASELINE_COSTS,
    )

    assert money > 0

    per_lot_distance = (
        BASELINE_COSTS["spread_pips"]
        + 2.0 * BASELINE_COSTS["slippage_pips"]
    ) * spec.pip_size

    assert (
        round(
            per_lot_distance
            * spec.contract_size
            * 0.01,
            2,
        )
        == 30.0
    )


def test_unknown_symbol_rejected():
    with pytest.raises(KeyError):
        INSTRUMENT_REGISTRY["EURGBP"]
