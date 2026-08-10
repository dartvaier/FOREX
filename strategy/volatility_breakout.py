import math
from dataclasses import dataclass
from numbers import Integral, Real

from backtest.context import BacktestContext
from backtest.models import Signal, SignalAction


@dataclass(frozen=True, slots=True)
class VolatilityBreakoutStrategy:
    """
    Long-only channel breakout baseline.

    Rules:

    - current close breaks above the previous channel high
      and the previous channel range is large enough
      -> ENTER_LONG
    - current close breaks below the previous exit channel low
      -> EXIT
    - otherwise -> HOLD

    The strategy uses closed bars only and does not create
    orders, size positions, calculate costs or access broker
    objects.
    """

    symbol: str
    entry_lookback: int = 20
    exit_lookback: int = 10
    min_range_pips: float = 10.0
    pip_size: float = 0.00010
    strategy_id: str = "VOLATILITY-BREAKOUT"

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
            "entry_lookback",
            self.entry_lookback,
        )

        self._validate_period(
            "exit_lookback",
            self.exit_lookback,
        )

        self._validate_non_negative_number(
            "min_range_pips",
            self.min_range_pips,
        )

        self._validate_positive_number(
            "pip_size",
            self.pip_size,
        )

    @property
    def closed_bar_limit(self) -> int:
        return (
            max(
                self.entry_lookback,
                self.exit_lookback,
            )
            + 1
        )

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

        required_bars = self.closed_bar_limit

        if len(context.closed_bars) < required_bars:
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Warm-up",
            )

        current_bar = context.closed_bars[-1]
        previous_bars = context.closed_bars[:-1]

        entry_window = previous_bars[
            -self.entry_lookback:
        ]

        exit_window = previous_bars[
            -self.exit_lookback:
        ]

        channel_high = max(
            bar.high
            for bar in entry_window
        )

        channel_low = min(
            bar.low
            for bar in entry_window
        )

        exit_channel_low = min(
            bar.low
            for bar in exit_window
        )

        range_pips = (
            channel_high
            - channel_low
        ) / self.pip_size

        metadata = {
            "channel_high": channel_high,
            "channel_low": channel_low,
            "exit_channel_low": exit_channel_low,
            "range_pips": range_pips,
        }

        if (
            current_bar.close > channel_high
            and range_pips >= self.min_range_pips
        ):
            return self._signal(
                context,
                action=SignalAction.ENTER_LONG,
                reason="Close broke above volatility channel",
                metadata=metadata,
            )

        if current_bar.close < exit_channel_low:
            return self._signal(
                context,
                action=SignalAction.EXIT,
                reason="Close broke below exit channel",
                metadata=metadata,
            )

        return self._signal(
            context,
            action=SignalAction.HOLD,
            reason="No volatility breakout",
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
    def _validate_positive_number(
        name: str,
        value: float,
    ) -> None:
        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(
                f"{name} must be a finite positive number"
            )

    @staticmethod
    def _validate_non_negative_number(
        name: str,
        value: float,
    ) -> None:
        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(
                f"{name} must be a finite non-negative number"
            )
