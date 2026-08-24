from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from alpha.models import AlphaSignal

if TYPE_CHECKING:
    from backtest.context import BacktestContext


@runtime_checkable
class AlphaModel(Protocol):
    """
    Contract implemented by alpha models evaluated before a
    Strategy turns views into operational Signals.

    An AlphaModel never sizes positions, creates Orders, touches
    execution, changes simulation time or bypasses BacktestContext.
    """

    @property
    def model_id(self) -> str:
        """
        Stable identifier used by alpha ledgers and blenders.
        """

        ...

    def predict(
        self,
        context: BacktestContext,
    ) -> AlphaSignal:
        """
        Evaluate currently available information and return one
        explicit AlphaSignal, including abstention when applicable.
        """

        ...
