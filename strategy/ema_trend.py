from dataclasses import dataclass, field
from numbers import Integral
from typing import ClassVar

from backtest.context import BacktestContext
from backtest.models import Signal, SignalAction


@dataclass(slots=True)
class SimpleEmaTrendStrategy:
    """
    Long-only EMA crossover baseline for Strategy Research.

    Rules:

    - fast EMA crosses above slow EMA -> ENTER_LONG
    - fast EMA crosses below slow EMA -> EXIT
    - otherwise -> HOLD

    The strategy only reads closed bars from BacktestContext.
    It does not size positions, create orders, calculate costs
    or access broker/dataframe objects.
    """

    symbol: str
    fast_period: int = 20
    slow_period: int = 50
    strategy_id: str = "SIMPLE-EMA-TREND"

    closed_bar_limit: ClassVar[int] = 1

    _fast_ema: float | None = field(
        default=None,
        init=False,
        repr=False,
    )

    _slow_ema: float | None = field(
        default=None,
        init=False,
        repr=False,
    )

    _previous_fast_ema: float | None = field(
        default=None,
        init=False,
        repr=False,
    )

    _previous_slow_ema: float | None = field(
        default=None,
        init=False,
        repr=False,
    )

    _observations: int = field(
        default=0,
        init=False,
        repr=False,
    )

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
            "fast_period",
            self.fast_period,
        )

        self._validate_period(
            "slow_period",
            self.slow_period,
        )

        if self.fast_period >= self.slow_period:
            raise ValueError(
                "fast_period must be smaller than slow_period"
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

        closes = tuple(
            bar.close
            for bar in context.closed_bars
        )

        if len(closes) == 1:
            return self._on_incremental_bar(
                context,
                close=closes[-1],
            )

        if len(closes) < self.slow_period + 1:
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Warm-up",
            )

        fast_ema = self._ema_series(
            closes,
            period=self.fast_period,
        )

        slow_ema = self._ema_series(
            closes,
            period=self.slow_period,
        )

        previous_fast = fast_ema[-2]
        previous_slow = slow_ema[-2]
        current_fast = fast_ema[-1]
        current_slow = slow_ema[-1]

        crossed_above = (
            previous_fast <= previous_slow
            and current_fast > current_slow
        )

        crossed_below = (
            previous_fast >= previous_slow
            and current_fast < current_slow
        )

        if crossed_above:
            return self._signal(
                context,
                action=SignalAction.ENTER_LONG,
                reason="Fast EMA crossed above slow EMA",
                metadata={
                    "fast_ema": current_fast,
                    "slow_ema": current_slow,
                },
            )

        if crossed_below:
            return self._signal(
                context,
                action=SignalAction.EXIT,
                reason="Fast EMA crossed below slow EMA",
                metadata={
                    "fast_ema": current_fast,
                    "slow_ema": current_slow,
                },
            )

        return self._signal(
            context,
            action=SignalAction.HOLD,
            reason="No EMA crossover",
            metadata={
                "fast_ema": current_fast,
                "slow_ema": current_slow,
            },
        )

    def reset(self) -> None:
        self._fast_ema = None
        self._slow_ema = None
        self._previous_fast_ema = None
        self._previous_slow_ema = None
        self._observations = 0

    def _on_incremental_bar(
        self,
        context: BacktestContext,
        *,
        close: float,
    ) -> Signal:
        self._previous_fast_ema = self._fast_ema
        self._previous_slow_ema = self._slow_ema

        self._fast_ema = self._next_ema(
            previous=self._fast_ema,
            value=close,
            period=self.fast_period,
        )

        self._slow_ema = self._next_ema(
            previous=self._slow_ema,
            value=close,
            period=self.slow_period,
        )

        self._observations += 1

        if self._observations < self.slow_period + 1:
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Warm-up",
            )

        if (
            self._previous_fast_ema is None
            or self._previous_slow_ema is None
            or self._fast_ema is None
            or self._slow_ema is None
        ):
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Warm-up",
            )

        crossed_above = (
            self._previous_fast_ema
            <= self._previous_slow_ema
            and self._fast_ema > self._slow_ema
        )

        crossed_below = (
            self._previous_fast_ema
            >= self._previous_slow_ema
            and self._fast_ema < self._slow_ema
        )

        if crossed_above:
            return self._signal(
                context,
                action=SignalAction.ENTER_LONG,
                reason="Fast EMA crossed above slow EMA",
                metadata={
                    "fast_ema": self._fast_ema,
                    "slow_ema": self._slow_ema,
                },
            )

        if crossed_below:
            return self._signal(
                context,
                action=SignalAction.EXIT,
                reason="Fast EMA crossed below slow EMA",
                metadata={
                    "fast_ema": self._fast_ema,
                    "slow_ema": self._slow_ema,
                },
            )

        return self._signal(
            context,
            action=SignalAction.HOLD,
            reason="No EMA crossover",
            metadata={
                "fast_ema": self._fast_ema,
                "slow_ema": self._slow_ema,
            },
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
    def _ema_series(
        values: tuple[float, ...],
        *,
        period: int,
    ) -> tuple[float, ...]:
        if not values:
            raise ValueError(
                "values cannot be empty"
            )

        multiplier = 2.0 / (period + 1.0)
        ema_values = [float(values[0])]

        for value in values[1:]:
            ema_values.append(
                (
                    float(value)
                    - ema_values[-1]
                )
                * multiplier
                + ema_values[-1]
            )

        return tuple(ema_values)

    @staticmethod
    def _next_ema(
        *,
        previous: float | None,
        value: float,
        period: int,
    ) -> float:
        if previous is None:
            return float(value)

        multiplier = 2.0 / (period + 1.0)

        return (
            (
                float(value)
                - previous
            )
            * multiplier
            + previous
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
