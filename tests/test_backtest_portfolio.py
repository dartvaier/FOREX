from datetime import datetime, timezone

import pytest

from backtest.execution import ExecutionResult
from backtest.models import (
    BacktestConfig,
    Fill,
    InstrumentSpecification,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    Timeframe,
)
from backtest.models.enums import ExitReason
from backtest.portfolio import (
    Portfolio,
    PositionCloseResult,
)


def utc_time(
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026,
        8,
        8,
        hour,
        minute,
        tzinfo=timezone.utc,
    )


def make_config() -> BacktestConfig:
    return BacktestConfig(
        symbol="EURUSD",
        timeframe=Timeframe.M15,
        date_from=utc_time(10, 0),
        date_to=utc_time(12, 0),
        initial_capital=10000.0,
    )


def make_instrument() -> InstrumentSpecification:
    return InstrumentSpecification(
        symbol="EURUSD",
        digits=5,
        point=0.00001,
        pip_size=0.00010,
        contract_size=100000,
        volume_min=0.01,
        volume_max=500.0,
        volume_step=0.01,
        tick_size=0.00001,
    )


def make_execution(
    *,
    side: OrderSide,
    price: float,
    quantity: float = 0.01,
    commission: float = 0.0,
    suffix: str = "001",
) -> ExecutionResult:
    order = Order(
        order_id=f"ORD-{suffix}",
        signal_id=f"SIG-{suffix}",
        symbol="EURUSD",
        side=side,
        quantity=quantity,
        order_type=OrderType.MARKET,
        created_at=utc_time(10, 15),
        scheduled_for=utc_time(10, 15),
        status=OrderStatus.FILLED,
        metadata={
            "strategy_id": "TEST",
        },
    )

    fill = Fill(
        fill_id=f"FILL-{suffix}",
        order_id=order.order_id,
        fill_time=(
            utc_time(10, 15)
            if suffix == "ENTRY"
            else utc_time(10, 30)
        ),
        reference_price=price,
        execution_price=price,
        quantity=quantity,
        commission=commission,
    )

    return ExecutionResult(
        filled_order=order,
        fill=fill,
    )


def make_portfolio() -> Portfolio:
    return Portfolio(
        config=make_config(),
        instrument=make_instrument(),
    )


def test_portfolio_starts_flat():
    portfolio = make_portfolio()

    assert portfolio.is_flat is True
    assert portfolio.current_position is None

    assert portfolio.cash == 10000.0
    assert portfolio.equity == 10000.0

    assert portfolio.realized_pnl == 0.0
    assert portfolio.unrealized_pnl == 0.0


def test_buy_fill_opens_long_position():
    portfolio = make_portfolio()

    result = portfolio.apply_execution(
        make_execution(
            side=OrderSide.BUY,
            price=1.1600,
            suffix="ENTRY",
        )
    )

    assert result is None

    position = portfolio.current_position

    assert position is not None
    assert position.side == PositionSide.LONG
    assert position.entry_price == 1.1600
    assert position.quantity == 0.01


def test_sell_fill_opens_short_position():
    portfolio = make_portfolio()

    portfolio.apply_execution(
        make_execution(
            side=OrderSide.SELL,
            price=1.1700,
            suffix="ENTRY",
        )
    )

    position = portfolio.current_position

    assert position is not None
    assert position.side == PositionSide.SHORT
    assert position.entry_price == 1.1700


def test_long_mark_to_market_profit():
    portfolio = make_portfolio()

    portfolio.apply_execution(
        make_execution(
            side=OrderSide.BUY,
            price=1.1600,
            suffix="ENTRY",
        )
    )

    pnl = portfolio.mark_to_market(
        1.1700
    )

    assert pnl == pytest.approx(10.0)

    assert portfolio.unrealized_pnl == (
        pytest.approx(10.0)
    )

    assert portfolio.equity == (
        pytest.approx(10010.0)
    )


def test_long_mark_to_market_loss():
    portfolio = make_portfolio()

    portfolio.apply_execution(
        make_execution(
            side=OrderSide.BUY,
            price=1.1600,
            suffix="ENTRY",
        )
    )

    portfolio.mark_to_market(
        1.1500
    )

    assert portfolio.unrealized_pnl == (
        pytest.approx(-10.0)
    )

    assert portfolio.equity == (
        pytest.approx(9990.0)
    )


def test_short_mark_to_market_profit():
    portfolio = make_portfolio()

    portfolio.apply_execution(
        make_execution(
            side=OrderSide.SELL,
            price=1.1700,
            suffix="ENTRY",
        )
    )

    portfolio.mark_to_market(
        1.1600
    )

    assert portfolio.unrealized_pnl == (
        pytest.approx(10.0)
    )

    assert portfolio.equity == (
        pytest.approx(10010.0)
    )


def test_short_mark_to_market_loss():
    portfolio = make_portfolio()

    portfolio.apply_execution(
        make_execution(
            side=OrderSide.SELL,
            price=1.1700,
            suffix="ENTRY",
        )
    )

    portfolio.mark_to_market(
        1.1800
    )

    assert portfolio.unrealized_pnl == (
        pytest.approx(-10.0)
    )


def test_sell_fill_closes_long_position():
    portfolio = make_portfolio()

    portfolio.apply_execution(
        make_execution(
            side=OrderSide.BUY,
            price=1.1600,
            suffix="ENTRY",
        )
    )

    close_result = portfolio.apply_execution(
        make_execution(
            side=OrderSide.SELL,
            price=1.1700,
            suffix="EXIT",
        )
    )

    assert isinstance(
        close_result,
        PositionCloseResult,
    )

    assert close_result.gross_pnl == (
        pytest.approx(10.0)
    )

    assert close_result.net_pnl == (
        pytest.approx(10.0)
    )

    assert portfolio.is_flat is True
    assert portfolio.cash == pytest.approx(
        10010.0
    )

    assert portfolio.realized_pnl == (
        pytest.approx(10.0)
    )

    assert portfolio.equity == pytest.approx(
        10010.0
    )


def test_buy_fill_closes_short_position():
    portfolio = make_portfolio()

    portfolio.apply_execution(
        make_execution(
            side=OrderSide.SELL,
            price=1.1700,
            suffix="ENTRY",
        )
    )

    close_result = portfolio.apply_execution(
        make_execution(
            side=OrderSide.BUY,
            price=1.1600,
            suffix="EXIT",
        )
    )

    assert close_result is not None

    assert close_result.gross_pnl == (
        pytest.approx(10.0)
    )

    assert portfolio.realized_pnl == (
        pytest.approx(10.0)
    )


def test_long_loss_is_realized():
    portfolio = make_portfolio()

    portfolio.apply_execution(
        make_execution(
            side=OrderSide.BUY,
            price=1.1600,
            suffix="ENTRY",
        )
    )

    close_result = portfolio.apply_execution(
        make_execution(
            side=OrderSide.SELL,
            price=1.1500,
            suffix="EXIT",
        )
    )

    assert close_result is not None

    assert close_result.gross_pnl == (
        pytest.approx(-10.0)
    )

    assert portfolio.cash == pytest.approx(
        9990.0
    )


def test_entry_and_exit_commission_are_applied_once():
    portfolio = make_portfolio()

    portfolio.apply_execution(
        make_execution(
            side=OrderSide.BUY,
            price=1.1600,
            commission=1.0,
            suffix="ENTRY",
        )
    )

    assert portfolio.cash == pytest.approx(
        9999.0
    )

    close_result = portfolio.apply_execution(
        make_execution(
            side=OrderSide.SELL,
            price=1.1700,
            commission=1.0,
            suffix="EXIT",
        )
    )

    assert close_result is not None

    assert close_result.gross_pnl == (
        pytest.approx(10.0)
    )

    assert close_result.commission == (
        pytest.approx(2.0)
    )

    assert close_result.net_pnl == (
        pytest.approx(8.0)
    )

    assert portfolio.cash == pytest.approx(
        10008.0
    )

    assert portfolio.realized_pnl == (
        pytest.approx(8.0)
    )


def test_same_side_execution_cannot_pyramid_long():
    portfolio = make_portfolio()

    portfolio.apply_execution(
        make_execution(
            side=OrderSide.BUY,
            price=1.1600,
            suffix="ENTRY",
        )
    )

    with pytest.raises(
        ValueError,
        match="pyramid",
    ):
        portfolio.apply_execution(
            make_execution(
                side=OrderSide.BUY,
                price=1.1610,
                suffix="SECOND",
            )
        )


def test_same_side_execution_cannot_pyramid_short():
    portfolio = make_portfolio()

    portfolio.apply_execution(
        make_execution(
            side=OrderSide.SELL,
            price=1.1700,
            suffix="ENTRY",
        )
    )

    with pytest.raises(
        ValueError,
        match="pyramid",
    ):
        portfolio.apply_execution(
            make_execution(
                side=OrderSide.SELL,
                price=1.1690,
                suffix="SECOND",
            )
        )


def test_baseline_rejects_partial_exit():
    portfolio = make_portfolio()

    portfolio.apply_execution(
        make_execution(
            side=OrderSide.BUY,
            price=1.1600,
            quantity=0.05,
            suffix="ENTRY",
        )
    )

    with pytest.raises(
        ValueError,
        match="full-position",
    ):
        portfolio.apply_execution(
            make_execution(
                side=OrderSide.SELL,
                price=1.1700,
                quantity=0.01,
                suffix="EXIT",
            )
        )


def test_mark_to_market_when_flat_returns_zero():
    portfolio = make_portfolio()

    pnl = portfolio.mark_to_market(
        1.1600
    )

    assert pnl == 0.0
    assert portfolio.equity == 10000.0


@pytest.mark.parametrize(
    "price",
    [
        0,
        -1,
        float("inf"),
        float("-inf"),
        float("nan"),
        True,
    ],
)
def test_mark_to_market_requires_valid_price(
    price,
):
    portfolio = make_portfolio()

    with pytest.raises(
        ValueError,
        match="mark_price",
    ):
        portfolio.mark_to_market(price)


def test_portfolio_requires_execution_result():
    portfolio = make_portfolio()

    with pytest.raises(
        TypeError,
        match="ExecutionResult",
    ):
        portfolio.apply_execution(
            object()  # type: ignore[arg-type]
        )


def test_portfolio_requires_matching_instrument():
    instrument = InstrumentSpecification(
        symbol="GBPUSD",
        digits=5,
        point=0.00001,
        pip_size=0.00010,
        contract_size=100000,
        volume_min=0.01,
        volume_max=500.0,
        volume_step=0.01,
        tick_size=0.00001,
    )

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        Portfolio(
            config=make_config(),
            instrument=instrument,
        )


def test_exit_reason_is_preserved():
    portfolio = make_portfolio()

    portfolio.apply_execution(
        make_execution(
            side=OrderSide.BUY,
            price=1.1600,
            suffix="ENTRY",
        )
    )

    close_result = portfolio.apply_execution(
        make_execution(
            side=OrderSide.SELL,
            price=1.1700,
            suffix="EXIT",
        ),
        exit_reason=ExitReason.MANUAL_TEST,
    )

    assert close_result is not None

    assert (
        close_result.exit_reason
        == ExitReason.MANUAL_TEST
    )