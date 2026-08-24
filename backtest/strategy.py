from abc import ABC, abstractmethod

from backtest.context import BacktestContext
from domain.signal import Signal


class Strategy(ABC):
    @abstractmethod
    def on_bar(self, context: BacktestContext) -> Signal:
        """Return one signal after the supplied bar has closed."""
