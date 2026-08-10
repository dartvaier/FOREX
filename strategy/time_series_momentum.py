import math
from dataclasses import dataclass
from numbers import Integral, Real

from backtest.context import BacktestContext
from backtest.models import Signal, SignalAction


@dataclass(frozen=True, slots=True)
class TimeSeriesMomentumStrategy:
    """
    Long-only time-series momentum baseline.

    Rules:

    - cumulative return over lookback bars is above threshold
      -> ENTER_LONG
    - cumulative return is below exit threshold
      -> EXIT
    - otherwise -> HOLD

    The strategy reads only closed bars from BacktestContext.
    It does not create orders, size positions, calculate costs
    or access broker/dataframe objects.
    """

    symbol: str
    lookback: int = 96
    entry_threshold: float = 0.0010
    exit_threshold: float = 0.0
    strategy_id: str = "TIME-SERIES-MOMENTUM"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.symbol, str)
            or not self.symbol.strip()
        ):
            raise ValueError(
                "symbol must be a non-empty string"
            )

        if (
            not isinstance(self.strategy_id, str)
            or not self.strategy_id.strip()
        ):
            raise ValueError(
                "strategy_id must be a non-empty string"
            )

        self._validate_period(
            "lookback",
            self.lookback,
        )

        self._validate_number(
            "entry_threshold",
            self.entry_threshold,
        )

        self._validate_number(
            "exit_threshold",
            self.exit_threshold,
        )

        if self.entry_threshold <= self.exit_threshold:
            raise ValueError(
                "entry_threshold must be greater than "
                "exit_threshold"
            )

    @property
    def closed_bar_limit(self) -> int:
        return self.lookback + 1

    def on_bar(
        self,
        context: BacktestContext,
    ) -> Signal:
        if not isinstance(
            context,
            BacktestContext,
        ):
            raise TypeError(
                "context must be a BacktestContext"
            )

        if len(context.closed_bars) < self.closed_bar_limit:
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Warm-up",
            )

        start_bar = context.closed_bars[
            -self.lookback - 1
        ]

        current_bar = context.closed_bars[-1]

        momentum_return = (
            current_bar.close
            / start_bar.close
            - 1.0
        )

        metadata = {
            "lookback": self.lookback,
            "momentum_return": momentum_return,
            "entry_threshold": self.entry_threshold,
            "exit_threshold": self.exit_threshold,
        }

        if momentum_return > self.entry_threshold:
            return self._signal(
                context,
                action=SignalAction.ENTER_LONG,
                reason="Positive time-series momentum",
                metadata=metadata,
            )

        if momentum_return < self.exit_threshold:
            return self._signal(
                context,
                action=SignalAction.EXIT,
                reason="Momentum fell below exit threshold",
                metadata=metadata,
            )

        return self._signal(
            context,
            action=SignalAction.HOLD,
            reason="No time-series momentum signal",
            metadata=metadata,
        )

    def _signal(
        self,
        context: BacktestContext,
        *,
        action: SignalAction,
        reason: str,
        metadata: dict | None = None,
    ) -> Signal:
        return Signal(
            signal_id=(
                f"{self.strategy_id}-{context.current_bar_index}"
            ),
            strategy_id=self.strategy_id,
            symbol=self.symbol,
            timestamp=context.current_time,
            action=action,
            reason=reason,
            metadata=(
                {}
                if metadata is None
                else metadata
            ),
        )

    @staticmethod
    def _validate_period(
        name: str,
        value: int,
    ) -> None:
        if (
            not isinstance(value, Integral)
            or isinstance(value, bool)
            or value <= 0
        ):
            raise ValueError(
                f"{name} must be a positive integer"
            )

    @staticmethod
    def _validate_number(
        name: str,
        value: float,
    ) -> None:
        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            raise ValueError(
                f"{name} must be a finite number"
            )
