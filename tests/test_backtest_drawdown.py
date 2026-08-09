from datetime import datetime, timedelta, timezone
import pytest

from backtest.drawdown import (
    DrawdownResult,
    calculate_max_drawdown,
)
from backtest.equity_ledger import (
    EquityLedger,
    EquityPoint,
)
from backtest.models.enums import SimulationPhase


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


def append_equity(
    ledger: EquityLedger,
    *,
    equity: float,
    index: int,
) -> None:
    ledger.append(
        EquityPoint(
            timestamp=(
                utc_time(10)
                + timedelta(minutes=index * 15)
            ),
            bar_index=index,
            phase=SimulationPhase.BAR_CLOSE,
            cash=equity,
            equity=equity,
            realized_pnl=(
                equity - 10000.0
            ),
            unrealized_pnl=0.0,
        )
    )


def test_empty_ledger_has_zero_drawdown():
    result = calculate_max_drawdown(
        EquityLedger()
    )

    assert result == DrawdownResult(
        max_drawdown=0.0,
        max_drawdown_pct=0.0,
        peak_index=None,
        trough_index=None,
    )


def test_rising_equity_has_zero_drawdown():
    ledger = EquityLedger()

    append_equity(
        ledger,
        equity=10000.0,
        index=0,
    )

    append_equity(
        ledger,
        equity=10100.0,
        index=1,
    )

    append_equity(
        ledger,
        equity=10200.0,
        index=2,
    )

    result = calculate_max_drawdown(
        ledger
    )

    assert result.max_drawdown == 0.0
    assert result.max_drawdown_pct == 0.0

    assert result.peak_index is None
    assert result.trough_index is None


def test_simple_drawdown():
    ledger = EquityLedger()

    append_equity(
        ledger,
        equity=10000.0,
        index=0,
    )

    append_equity(
        ledger,
        equity=10100.0,
        index=1,
    )

    append_equity(
        ledger,
        equity=9900.0,
        index=2,
    )

    result = calculate_max_drawdown(
        ledger
    )

    assert result.max_drawdown == pytest.approx(
        200.0
    )

    assert result.max_drawdown_pct == pytest.approx(
        200.0 / 10100.0 * 100.0
    )

    assert result.peak_index == 1
    assert result.trough_index == 2


def test_maximum_drawdown_uses_largest_peak_to_trough_loss():
    ledger = EquityLedger()

    equities = [
        10000.0,
        10200.0,
        10100.0,
        10300.0,
        9900.0,
        10100.0,
    ]

    for index, equity in enumerate(
        equities
    ):
        append_equity(
            ledger,
            equity=equity,
            index=index,
        )

    result = calculate_max_drawdown(
        ledger
    )

    # Peak = 10300
    # Trough = 9900
    assert result.max_drawdown == pytest.approx(
        400.0
    )

    assert result.max_drawdown_pct == pytest.approx(
        400.0 / 10300.0 * 100.0
    )

    assert result.peak_index == 3
    assert result.trough_index == 4


def test_new_equity_high_resets_drawdown_peak():
    ledger = EquityLedger()

    equities = [
        10000.0,
        9800.0,
        10500.0,
        10000.0,
    ]

    for index, equity in enumerate(
        equities
    ):
        append_equity(
            ledger,
            equity=equity,
            index=index,
        )

    result = calculate_max_drawdown(
        ledger
    )

    # First drawdown:
    # 10000 -> 9800 = 200
    #
    # New high:
    # 10500
    #
    # Second drawdown:
    # 10500 -> 10000 = 500
    assert result.max_drawdown == pytest.approx(
        500.0
    )

    assert result.peak_index == 2
    assert result.trough_index == 3


def test_recovery_without_new_high_keeps_original_peak():
    ledger = EquityLedger()

    equities = [
        10000.0,
        9500.0,
        9800.0,
        9600.0,
    ]

    for index, equity in enumerate(
        equities
    ):
        append_equity(
            ledger,
            equity=equity,
            index=index,
        )

    result = calculate_max_drawdown(
        ledger
    )

    # Maximum remains:
    # 10000 -> 9500
    assert result.max_drawdown == pytest.approx(
        500.0
    )

    assert result.peak_index == 0
    assert result.trough_index == 1


def test_drawdown_uses_equity_not_realized_pnl():
    ledger = EquityLedger()

    ledger.append(
        EquityPoint(
            timestamp=utc_time(10, 0),
            bar_index=0,
            phase=SimulationPhase.BAR_CLOSE,
            cash=10000.0,
            equity=10000.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
        )
    )

    ledger.append(
        EquityPoint(
            timestamp=utc_time(10, 15),
            bar_index=1,
            phase=SimulationPhase.BAR_CLOSE,
            cash=10000.0,
            equity=9700.0,
            realized_pnl=0.0,
            unrealized_pnl=-300.0,
        )
    )

    result = calculate_max_drawdown(
        ledger
    )

    # Even though nothing was realized,
    # equity suffered a 300 drawdown.
    assert result.max_drawdown == pytest.approx(
        300.0
    )


def test_requires_equity_ledger():
    with pytest.raises(
        TypeError,
        match="EquityLedger",
    ):
        calculate_max_drawdown(
            object()  # type: ignore[arg-type]
        )