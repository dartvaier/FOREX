from typing import Protocol, runtime_checkable

from backtest.context import BacktestContext
from backtest.models.signal import Signal


@runtime_checkable
class Strategy(Protocol):
    """
    Contract implemented by strategies evaluated by the
    BacktestEngine.

    A Strategy:

    - receives only a Strategy-safe BacktestContext
    - never receives the complete historical DataFrame
    - never controls simulation time
    - never submits Orders directly
    - produces exactly one Signal per evaluation

    The baseline BacktestEngine will evaluate strategies only
    after BAR_CLOSE events.

    When no market action is desired, the Strategy must return
    an explicit Signal with:

        SignalAction.HOLD

    rather than returning None.
    """

    @property
    def strategy_id(self) -> str:
        """
        Stable identifier used for auditability and ledgers.
        """

        ...

    def on_bar(
        self,
        context: BacktestContext,
    ) -> Signal:
        """
        Evaluate the information currently available and
        return exactly one Signal.
        """

        ...