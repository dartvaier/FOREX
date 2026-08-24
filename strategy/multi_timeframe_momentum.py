import math
from dataclasses import dataclass, field
from numbers import Integral, Real

from backtest.context import BacktestContext
from backtest.models import Signal, SignalAction, Timeframe


@dataclass(slots=True)
class MultiTimeframeMomentumStrategy:
    """
    H4/H1/M15 momentum alignment baseline.

    Rules:

    - H4 defines the directional regime
    - H1 confirms the same direction
    - M15 triggers the entry
    - loss of M15 momentum or higher-timeframe alignment exits

    This strategy requires the BacktestEngine to provide H1 and
    H4 bars through BacktestContext.timeframe_bars. Those bars
    are only valid after their own close time, so the strategy
    remains causal even though it combines multiple timeframes.
    """

    symbol: str
    m15_lookback: int = 16
    h1_lookback: int = 24
    h4_lookback: int = 30
    m15_entry_threshold: float = 0.0005
    h1_entry_threshold: float = 0.0005
    h4_entry_threshold: float = 0.0010
    exit_threshold: float = 0.0
    strategy_id: str = "MULTI-TIMEFRAME-MOMENTUM"

    _exposure_side: str | None = field(
        default=None,
        init=False,
        repr=False,
    )

    @property
    def closed_bar_limit(self) -> int:
        return self.m15_lookback + 1

    @property
    def higher_timeframes(self) -> tuple[Timeframe, ...]:
        return (
            Timeframe.H1,
            Timeframe.H4,
        )

    @property
    def higher_timeframe_bar_limits(
        self,
    ) -> dict[Timeframe, int]:
        return {
            Timeframe.H1: self.h1_lookback + 1,
            Timeframe.H4: self.h4_lookback + 1,
        }

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

        for name, value in (
            (
                "m15_lookback",
                self.m15_lookback,
            ),
            (
                "h1_lookback",
                self.h1_lookback,
            ),
            (
                "h4_lookback",
                self.h4_lookback,
            ),
        ):
            self._validate_period(
                name,
                value,
            )

        for name, value in (
            (
                "m15_entry_threshold",
                self.m15_entry_threshold,
            ),
            (
                "h1_entry_threshold",
                self.h1_entry_threshold,
            ),
            (
                "h4_entry_threshold",
                self.h4_entry_threshold,
            ),
        ):
            self._validate_positive_number(
                name,
                value,
            )

        self._validate_non_negative_number(
            "exit_threshold",
            self.exit_threshold,
        )

    def reset(self) -> None:
        self._exposure_side = None

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

        h1_bars = context.timeframe_bars.get(
            Timeframe.H1,
            (),
        )

        h4_bars = context.timeframe_bars.get(
            Timeframe.H4,
            (),
        )

        if (
            len(context.closed_bars) < self.closed_bar_limit
            or len(h1_bars) < self.h1_lookback + 1
            or len(h4_bars) < self.h4_lookback + 1
        ):
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Warm-up",
            )

        m15_return = self._window_return(
            context.closed_bars,
            self.m15_lookback,
        )

        h1_return = self._window_return(
            h1_bars,
            self.h1_lookback,
        )

        h4_return = self._window_return(
            h4_bars,
            self.h4_lookback,
        )

        metadata = {
            "m15_lookback": self.m15_lookback,
            "h1_lookback": self.h1_lookback,
            "h4_lookback": self.h4_lookback,
            "m15_return": m15_return,
            "h1_return": h1_return,
            "h4_return": h4_return,
            "m15_entry_threshold": self.m15_entry_threshold,
            "h1_entry_threshold": self.h1_entry_threshold,
            "h4_entry_threshold": self.h4_entry_threshold,
            "exit_threshold": self.exit_threshold,
            "exposure_side": self._exposure_side,
        }

        long_aligned = (
            h4_return >= self.h4_entry_threshold
            and h1_return >= self.h1_entry_threshold
            and m15_return >= self.m15_entry_threshold
        )

        short_aligned = (
            h4_return <= -self.h4_entry_threshold
            and h1_return <= -self.h1_entry_threshold
            and m15_return <= -self.m15_entry_threshold
        )

        if self._exposure_side == "LONG":
            if (
                not long_aligned
                and m15_return <= self.exit_threshold
            ):
                self._exposure_side = None

                return self._signal(
                    context,
                    action=SignalAction.EXIT,
                    reason="Multi-timeframe long alignment lost",
                    metadata={
                        **metadata,
                        "exposure_side": self._exposure_side,
                    },
                )

            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Long alignment already active",
                metadata=metadata,
            )

        if self._exposure_side == "SHORT":
            if (
                not short_aligned
                and m15_return >= -self.exit_threshold
            ):
                self._exposure_side = None

                return self._signal(
                    context,
                    action=SignalAction.EXIT,
                    reason="Multi-timeframe short alignment lost",
                    metadata={
                        **metadata,
                        "exposure_side": self._exposure_side,
                    },
                )

            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Short alignment already active",
                metadata=metadata,
            )

        if long_aligned:
            self._exposure_side = "LONG"

            return self._signal(
                context,
                action=SignalAction.ENTER_LONG,
                reason="Bullish multi-timeframe alignment",
                metadata={
                    **metadata,
                    "exposure_side": self._exposure_side,
                },
            )

        if short_aligned:
            self._exposure_side = "SHORT"

            return self._signal(
                context,
                action=SignalAction.ENTER_SHORT,
                reason="Bearish multi-timeframe alignment",
                metadata={
                    **metadata,
                    "exposure_side": self._exposure_side,
                },
            )

        return self._signal(
            context,
            action=SignalAction.HOLD,
            reason="No multi-timeframe alignment",
            metadata=metadata,
        )

    @staticmethod
    def _window_return(
        bars,
        lookback: int,
    ) -> float:
        start_bar = bars[-lookback - 1]
        current_bar = bars[-1]

        return current_bar.close / start_bar.close - 1.0

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
