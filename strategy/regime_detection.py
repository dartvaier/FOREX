import math
from dataclasses import dataclass, field
from numbers import Integral, Real

from backtest.context import BacktestContext
from backtest.models import Signal, SignalAction


@dataclass(slots=True)
class SimpleRegimeDetectionStrategy:
    """
    Trend plus volatility regime baseline.

    Rules:

    - realized volatility above max_volatility -> EXIT
    - trend return above entry threshold in low volatility
      -> ENTER_LONG
    - trend return below negative entry threshold in low
      volatility -> ENTER_SHORT
    - absolute trend return at or below exit threshold -> EXIT
    - otherwise -> HOLD

    This is a simple regime-filter strategy, not a full
    forecasting model. It reads only closed bars and keeps a
    small internal exposure state so it does not emit duplicate
    entry signals while the same regime remains active.
    """

    symbol: str
    trend_lookback: int = 96
    volatility_lookback: int = 96
    entry_threshold: float = 0.0025
    exit_threshold: float = 0.0005
    max_volatility: float = 0.00055
    strategy_id: str = "SIMPLE-REGIME-DETECTION"

    _exposure_side: str | None = field(
        default=None,
        init=False,
        repr=False,
    )

    @property
    def closed_bar_limit(self) -> int:
        return (
            max(
                self.trend_lookback,
                self.volatility_lookback,
            )
            + 1
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
            "trend_lookback",
            self.trend_lookback,
        )

        self._validate_period(
            "volatility_lookback",
            self.volatility_lookback,
        )

        self._validate_positive_number(
            "entry_threshold",
            self.entry_threshold,
        )

        self._validate_non_negative_number(
            "exit_threshold",
            self.exit_threshold,
        )

        self._validate_positive_number(
            "max_volatility",
            self.max_volatility,
        )

        if self.exit_threshold > self.entry_threshold:
            raise ValueError(
                "exit_threshold must be less than or equal "
                "to entry_threshold"
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

        if len(context.closed_bars) < self.closed_bar_limit:
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Warm-up",
            )

        current_bar = context.closed_bars[-1]
        trend_start_bar = context.closed_bars[
            -self.trend_lookback - 1
        ]

        trend_return = (
            current_bar.close
            / trend_start_bar.close
            - 1.0
        )

        realized_volatility = self._realized_volatility(
            context.closed_bars[
                -self.volatility_lookback - 1:
            ]
        )

        metadata = {
            "trend_lookback": self.trend_lookback,
            "volatility_lookback": self.volatility_lookback,
            "trend_return": trend_return,
            "entry_threshold": self.entry_threshold,
            "exit_threshold": self.exit_threshold,
            "realized_volatility": realized_volatility,
            "max_volatility": self.max_volatility,
            "exposure_side": self._exposure_side,
        }

        if realized_volatility > self.max_volatility:
            if self._exposure_side is not None:
                self._exposure_side = None

                return self._signal(
                    context,
                    action=SignalAction.EXIT,
                    reason="Regime volatility exceeded threshold",
                    metadata={
                        **metadata,
                        "exposure_side": self._exposure_side,
                    },
                )

            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="High-volatility regime",
                metadata=metadata,
            )

        if trend_return >= self.entry_threshold:
            return self._handle_directional_regime(
                context,
                target_side="LONG",
                entry_action=SignalAction.ENTER_LONG,
                entry_reason="Bullish low-volatility regime",
                metadata=metadata,
            )

        if trend_return <= -self.entry_threshold:
            return self._handle_directional_regime(
                context,
                target_side="SHORT",
                entry_action=SignalAction.ENTER_SHORT,
                entry_reason="Bearish low-volatility regime",
                metadata=metadata,
            )

        if abs(trend_return) <= self.exit_threshold:
            if self._exposure_side is not None:
                self._exposure_side = None

                return self._signal(
                    context,
                    action=SignalAction.EXIT,
                    reason="Regime returned to neutral",
                    metadata={
                        **metadata,
                        "exposure_side": self._exposure_side,
                    },
                )

            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Neutral regime",
                metadata=metadata,
            )

        return self._signal(
            context,
            action=SignalAction.HOLD,
            reason="No regime transition",
            metadata=metadata,
        )

    def _handle_directional_regime(
        self,
        context: BacktestContext,
        *,
        target_side: str,
        entry_action: SignalAction,
        entry_reason: str,
        metadata: dict,
    ) -> Signal:
        if self._exposure_side == target_side:
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason=(
                    f"{target_side.title()} regime already active"
                ),
                metadata=metadata,
            )

        if self._exposure_side is not None:
            self._exposure_side = None

            return self._signal(
                context,
                action=SignalAction.EXIT,
                reason="Regime changed direction",
                metadata={
                    **metadata,
                    "exposure_side": self._exposure_side,
                },
            )

        self._exposure_side = target_side

        return self._signal(
            context,
            action=entry_action,
            reason=entry_reason,
            metadata={
                **metadata,
                "exposure_side": self._exposure_side,
            },
        )

    @staticmethod
    def _realized_volatility(
        bars,
    ) -> float:
        returns = []

        for previous_bar, current_bar in zip(
            bars,
            bars[1:],
        ):
            returns.append(
                current_bar.close
                / previous_bar.close
                - 1.0
            )

        if not returns:
            return 0.0

        mean_return = sum(returns) / len(returns)
        variance = sum(
            (
                value
                - mean_return
            )
            ** 2
            for value in returns
        ) / len(returns)

        return math.sqrt(variance)

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
