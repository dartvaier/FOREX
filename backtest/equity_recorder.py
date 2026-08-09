from backtest.clock import ClockEvent
from backtest.equity_ledger import (
    EquityLedger,
    EquityPoint,
)
from backtest.portfolio import Portfolio


class EquityRecorder:
    """
    Records immutable Portfolio snapshots into an EquityLedger.

    The recorder does not mark positions to market itself.

    At BAR_CLOSE, the caller must first mark the Portfolio using
    the newly available closing price and only then record the
    snapshot.

    At BAR_OPEN, the Portfolio state is recorded as it exists
    after any executions processed at that open.
    """

    def __init__(
        self,
        ledger: EquityLedger,
    ) -> None:
        if not isinstance(
            ledger,
            EquityLedger,
        ):
            raise TypeError(
                "ledger must be an EquityLedger"
            )

        self._ledger = ledger

    @property
    def ledger(self) -> EquityLedger:
        return self._ledger

    def record(
        self,
        event: ClockEvent,
        portfolio: Portfolio,
    ) -> EquityPoint:
        if not isinstance(
            event,
            ClockEvent,
        ):
            raise TypeError(
                "event must be a ClockEvent"
            )

        if not isinstance(
            portfolio,
            Portfolio,
        ):
            raise TypeError(
                "portfolio must be a Portfolio"
            )

        point = EquityPoint(
            timestamp=event.timestamp,
            bar_index=event.bar_index,
            phase=event.phase,
            cash=portfolio.cash,
            equity=portfolio.equity,
            realized_pnl=portfolio.realized_pnl,
            unrealized_pnl=portfolio.unrealized_pnl,
        )

        self._ledger.append(point)

        return point