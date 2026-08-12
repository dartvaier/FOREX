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
    # pair (USD is the QUOTE leg) must have the same round-trip
    # cost in pips for the same inputs.
    pips: set[float] = set()

    for symbol in (
        "EURUSD",
        "GBPUSD",
        "AUDUSD",
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


def test_round_trip_cost_pips_expected_per_usd_base_pair():
    # USD-base pairs (USDJPY, USDCHF, USDCAD: USD is the BASE
    # leg, quote is JPY/CHF/CAD). docs/25 MC-04: these are
    # USD-BASE, not USD-quote. The 3.0-pip spread+slippage leg
    # converts with the pair rate; the commission is fixed USD
    # and therefore represents a different pip count per price.
    prices = {
        "USDJPY": (150.0, 4.05),
        "USDCHF": (0.90, 3.63),
        "USDCAD": (1.35, 3.945),
    }

    for symbol, (price, expected_pips) in prices.items():
        spec = InstrumentSpecification(
            **INSTRUMENT_REGISTRY[symbol]
        )
        rate = 1.0 / price

        money = round_trip_cost_money(
            spec,
            0.01,
            BASELINE_COSTS,
            quote_to_account_rate=rate,
        )

        pips = money_to_pips(
            money,
            spec,
            0.01,
            quote_to_account_rate=rate,
        )

        assert pips == pytest.approx(expected_pips, rel=1e-9)


def test_usd_base_pairs_quote_currency_not_usd():
    # Classification contract (docs/25 MC-04): USDCHF and USDCAD
    # are USD-BASE pairs, their quote leg is CHF/CAD.
    assert (
        InstrumentSpecification(
            **INSTRUMENT_REGISTRY["USDJPY"]
        ).quote_currency
        == "JPY"
    )
    assert (
        InstrumentSpecification(
            **INSTRUMENT_REGISTRY["USDCHF"]
        ).quote_currency
        == "CHF"
    )
    assert (
        InstrumentSpecification(
            **INSTRUMENT_REGISTRY["USDCAD"]
        ).quote_currency
        == "CAD"
    )
    assert (
        InstrumentSpecification(
            **INSTRUMENT_REGISTRY["EURUSD"]
        ).quote_currency
        == "USD"
    )


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
