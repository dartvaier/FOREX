"""
Tests for quote-to-account currency conversion (docs/20-21 fix).

The realized PnL of a trade is expressed in quote currency; it is
converted to account currency (USD) with the pair's own rate at the
exit price (causal). USD-quote pairs keep rate 1.0 (regression).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backtest.models import (
    BacktestConfig,
    InstrumentSpecification,
    MarketBar,
    Timeframe,
)
from backtest.models.enums import (
    OrderType,
    OrderSide,
    OrderStatus,
    PositionSide,
    SimulationPhase,
)
from backtest.models.fill import Fill
from backtest.models.order import Order
from backtest.execution import ExecutionResult

from research.runner import (
    INSTRUMENT_REGISTRY,
    money_to_pips,
    round_trip_cost_money,
)


def make_instrument(
    symbol: str = "EURUSD",
) -> InstrumentSpecification:
    return InstrumentSpecification(
        **INSTRUMENT_REGISTRY[symbol]
    )


# ---------------------------------------------------------------------------
# quote_to_account_rate
# ---------------------------------------------------------------------------


def test_usd_quote_pairs_rate_is_one():
    for symbol in ("EURUSD", "GBPUSD", "AUDUSD",
                   "NZDUSD"):
        spec = make_instrument(symbol)

        assert spec.quote_to_account_rate(1.10) == 1.0


def test_usd_base_pairs_rate_is_inverse_of_price():
    spec = make_instrument("USDJPY")

    assert spec.quote_to_account_rate(150.0) == pytest.approx(
        1.0 / 150.0
    )

    chf = make_instrument("USDCHF")

    assert chf.quote_to_account_rate(0.90) == pytest.approx(
        1.0 / 0.90
    )


def test_cross_currency_rejected():
    spec = InstrumentSpecification(
        symbol="EURGBP",
        digits=5,
        point=0.00001,
        pip_size=0.00010,
        contract_size=100000,
        volume_min=0.01,
        volume_max=500.0,
        volume_step=0.01,
        tick_size=0.00001,
        tick_value=1.0,
        base_currency="EUR",
        quote_currency="GBP",
    )

    with pytest.raises(ValueError):
        spec.quote_to_account_rate(0.85)


def test_currency_codes_validated():
    with pytest.raises(ValueError):
        InstrumentSpecification(
            symbol="EURUSD",
            digits=5,
            point=0.00001,
            pip_size=0.00010,
            contract_size=100000,
            volume_min=0.01,
            volume_max=500.0,
            volume_step=0.01,
            tick_size=0.00001,
            base_currency="eur",
            quote_currency="USD",
        )


# ---------------------------------------------------------------------------
# Portfolio PnL conversion (10 pips on 1 lot)
# ---------------------------------------------------------------------------


def _fill(
    price: float,
    quantity: float,
    *,
    order_id: str = "ORD-1",
    fill_id: str = "FILL-1",
) -> Fill:
    return Fill(
        fill_id=fill_id,
        order_id=order_id,
        fill_time=datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc),
        reference_price=price,
        execution_price=price,
        quantity=quantity,
        spread_impact=0.0,
        slippage=0.0,
        commission=0.0,
    )


def _order(
    side: OrderSide,
    price: float,
    quantity: float,
    symbol: str = "EURUSD",
) -> Order:
    now = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)

    return Order(
        order_id="ORD-1",
        signal_id="SIG-1",
        symbol=symbol,
        side=side,
        quantity=quantity,
        order_type=OrderType.MARKET,
        created_at=now,
        scheduled_for=now,
        status=OrderStatus.FILLED,
    )


def _portfolio(
    instrument: InstrumentSpecification,
) -> Portfolio:
    from backtest.portfolio import Portfolio

    config = BacktestConfig(
        symbol=instrument.symbol,
        timeframe=Timeframe.M15,
        date_from=datetime(2026, 8, 8, 10, 0, tzinfo=timezone.utc),
        date_to=datetime(2026, 8, 8, 14, 0, tzinfo=timezone.utc),
        initial_capital=10000.0,
    )

    return Portfolio(
        config=config,
        instrument=instrument,
    )


def _execution(
    order: Order,
    fill: Fill,
) -> ExecutionResult:
    filled = replace(
        order,
        status=OrderStatus.FILLED,
    )

    return ExecutionResult(
        filled_order=filled,
        fill=fill,
    )


from dataclasses import replace


def test_usdjpy_pnl_converted_to_usd():
    # LONG 1 lot from 150.00 to 150.10 = 10 pips = 10000 JPY
    # (0.10 price diff x 100k contract). At the exit rate 150.10
    # -> 10000 / 150.10 ~= 66.62 USD.
    instrument = make_instrument("USDJPY")
    portfolio = _portfolio(instrument)

    portfolio.apply_execution(
        _execution(
            _order(OrderSide.BUY, 150.00, 1.0, "USDJPY"),
            _fill(150.00, 1.0),
        )
    )

    close = portfolio.apply_execution(
        _execution(
            _order(OrderSide.SELL, 150.10, 1.0, "USDJPY"),
            _fill(150.10, 1.0),
        )
    )

    assert close is not None
    assert close.gross_pnl == pytest.approx(
        10000.0 / 150.10,
        rel=1e-9,
    )


def test_eurusd_pnl_unchanged():
    # Regression: 10 pips on 1 lot EURUSD = 100.0 USD exactly
    # (10 USD per pip per lot).
    instrument = make_instrument("EURUSD")
    portfolio = _portfolio(instrument)

    portfolio.apply_execution(
        _execution(
            _order(OrderSide.BUY, 1.1000, 1.0, "EURUSD"),
            _fill(1.1000, 1.0),
        )
    )

    close = portfolio.apply_execution(
        _execution(
            _order(OrderSide.SELL, 1.1010, 1.0, "EURUSD"),
            _fill(1.1010, 1.0),
        )
    )

    assert close is not None
    assert close.gross_pnl == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Round-trip cost helpers with rate
# ---------------------------------------------------------------------------

BASELINE_COSTS = {
    "spread_pips": 2.0,
    "slippage_pips": 0.5,
    "commission_per_lot_per_side": 3.50,
}


def test_round_trip_pips_invariant_usd_quote():
    # USD-quote pairs only (USD is the quote leg): EURUSD, GBPUSD,
    # AUDUSD, NZDUSD. docs/25 MC-04: USDCHF/USDCAD are USD-BASE.
    pips: set[float] = set()

    for symbol in ("EURUSD", "GBPUSD", "AUDUSD",
                   "NZDUSD"):
        spec = make_instrument(symbol)

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


def test_round_trip_pips_expected_per_usd_base_pair():
    # USD-base pairs (USDJPY, USDCHF, USDCAD): the spread+slippage
    # leg converts with the pair rate; the fixed-USD commission
    # yields a different pip count per pair price (docs/25 MC-04).
    prices = {
        "USDJPY": (150.0, 4.05),
        "USDCHF": (0.90, 3.63),
        "USDCAD": (1.35, 3.945),
    }

    for symbol, (price, expected_pips) in prices.items():
        spec = make_instrument(symbol)
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


def test_usdchf_usdcad_classified_as_usd_base():
    # docs/25 MC-04: USDCHF/USDCAD are USD-BASE (quote CHF/CAD).
    assert make_instrument("USDCHF").quote_currency == "CHF"
    assert make_instrument("USDCAD").quote_currency == "CAD"
    assert make_instrument("USDCHF").quote_to_account_rate(0.90) == (
        pytest.approx(1.0 / 0.90)
    )
    assert make_instrument("USDCAD").quote_to_account_rate(1.35) == (
        pytest.approx(1.0 / 1.35)
    )


def test_round_trip_usdjpy_with_rate():
    # USDJPY @ 150: quote leg = 3000 JPY -> 20.0 USD;
    # commission 7.0 USD -> total 27.0 USD per lot.
    spec = make_instrument("USDJPY")

    money = round_trip_cost_money(
        spec,
        1.0,
        BASELINE_COSTS,
        quote_to_account_rate=1.0 / 150.0,
    )

    assert money == pytest.approx(27.0)

    # In pips: 27.0 USD / (10 USD-per-pip-per-lot @ 150)
    # = 4.05 pips (commission costs more pips on JPY pairs).
    pips = money_to_pips(
        money,
        spec,
        1.0,
        quote_to_account_rate=1.0 / 150.0,
    )

    assert pips == pytest.approx(4.05, rel=1e-9)


# ---------------------------------------------------------------------------
# Hardening RA-04: zero-cost report shows zero effective costs
# ---------------------------------------------------------------------------


def test_effective_round_trip_zero_cost_is_zero():
    from research.runner import effective_round_trip

    money, pips = effective_round_trip(
        cost_mode="zero",
        instrument=make_instrument("EURUSD"),
        fixed_quantity=0.01,
        cost_params=dict(BASELINE_COSTS),
    )

    assert money == 0.0
    assert pips == 0.0


def test_effective_round_trip_explicit_cost_uses_params():
    from research.runner import effective_round_trip

    money, pips = effective_round_trip(
        cost_mode="explicit",
        instrument=make_instrument("EURUSD"),
        fixed_quantity=0.01,
        cost_params=dict(BASELINE_COSTS),
    )

    assert money > 0.0
    assert pips == pytest.approx(3.7, rel=1e-9)
