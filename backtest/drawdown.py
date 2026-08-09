from dataclasses import dataclass

from backtest.equity_ledger import EquityLedger


@dataclass(frozen=True, slots=True)
class DrawdownResult:
    max_drawdown: float
    max_drawdown_pct: float

    peak_index: int | None
    trough_index: int | None


def calculate_max_drawdown(
    ledger: EquityLedger,
) -> DrawdownResult:
    """
    Calculate maximum peak-to-trough drawdown from the
    observed EquityLedger sequence.

    Drawdown is calculated from equity, not cash.

    Equal timestamps are not a problem because ledger insertion
    order is authoritative.

    Empty ledger:
        returns zero drawdown.

    Percentage drawdown:

        (peak_equity - trough_equity)
        / peak_equity

    expressed as a percentage.
    """

    if not isinstance(
        ledger,
        EquityLedger,
    ):
        raise TypeError(
            "ledger must be an EquityLedger"
        )

    points = ledger.points

    if not points:
        return DrawdownResult(
            max_drawdown=0.0,
            max_drawdown_pct=0.0,
            peak_index=None,
            trough_index=None,
        )

    peak_equity = points[0].equity
    peak_index = 0

    max_drawdown = 0.0
    max_drawdown_pct = 0.0

    max_peak_index: int | None = None
    max_trough_index: int | None = None

    for index, point in enumerate(points):
        equity = point.equity

        if equity > peak_equity:
            peak_equity = equity
            peak_index = index
            continue

        drawdown = (
            peak_equity
            - equity
        )

        if peak_equity > 0:
            drawdown_pct = (
                drawdown
                / peak_equity
                * 100.0
            )
        else:
            drawdown_pct = 0.0

        if drawdown > max_drawdown:
            max_drawdown = drawdown
            max_drawdown_pct = drawdown_pct
            max_peak_index = peak_index
            max_trough_index = index

    return DrawdownResult(
        max_drawdown=max_drawdown,
        max_drawdown_pct=max_drawdown_pct,
        peak_index=max_peak_index,
        trough_index=max_trough_index,
    )