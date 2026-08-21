import math
from dataclasses import dataclass
from numbers import Integral, Real

from alpha.models import AlphaSignal
from backtest.context import BacktestContext


@dataclass(frozen=True, slots=True)
class EmaTrendAlphaModel:
    """
    Causal EMA trend AlphaModel.

    The model reads only closed bars from BacktestContext and
    converts the EMA spread into a continuous normalized alpha
    view. It does not emit operational Signals or perform sizing.
    """

    symbol: str
    fast_period: int = 20
    slow_period: int = 50
    score_scale: float = 0.0010
    model_id: str = "EMA-TREND-ALPHA"

    @property
    def closed_bar_limit(self) -> int:
        return self.slow_period + 1

    def __post_init__(self) -> None:
        if (
            not isinstance(self.symbol, str)
            or not self.symbol.strip()
        ):
            raise ValueError(
                "symbol must be a non-empty string"
            )

        if (
            not isinstance(self.model_id, str)
            or not self.model_id.strip()
        ):
            raise ValueError(
                "model_id must be a non-empty string"
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

        if (
            not isinstance(self.score_scale, Real)
            or isinstance(self.score_scale, bool)
            or not math.isfinite(self.score_scale)
            or self.score_scale <= 0
        ):
            raise ValueError(
                "score_scale must be a finite positive number"
            )

    def predict(
        self,
        context: BacktestContext,
    ) -> AlphaSignal:
        if not isinstance(
            context,
            BacktestContext,
        ):
            raise TypeError(
                "context must be a BacktestContext"
            )

        if len(context.closed_bars) < self.closed_bar_limit:
            return AlphaSignal.abstain(
                model_id=self.model_id,
                symbol=self.symbol,
                timestamp=context.current_time,
                reason="Warm-up",
                metadata={
                    "fast_period": self.fast_period,
                    "slow_period": self.slow_period,
                    "required_closed_bars": self.closed_bar_limit,
                    "available_closed_bars": len(context.closed_bars),
                },
            )

        closes = tuple(
            bar.close
            for bar in context.closed_bars
        )

        fast_ema = self._ema_series(
            closes,
            period=self.fast_period,
        )[-1]
        slow_ema = self._ema_series(
            closes,
            period=self.slow_period,
        )[-1]

        ema_spread = fast_ema - slow_ema
        value = math.tanh(
            ema_spread / self.score_scale
        )

        reason = "Neutral EMA trend"

        if value > 0.0:
            reason = "Positive EMA trend"

        elif value < 0.0:
            reason = "Negative EMA trend"

        return AlphaSignal(
            model_id=self.model_id,
            symbol=self.symbol,
            timestamp=context.current_time,
            value=value,
            confidence=None,
            abstained=False,
            reason=reason,
            metadata={
                "fast_period": self.fast_period,
                "slow_period": self.slow_period,
                "fast_ema": fast_ema,
                "slow_ema": slow_ema,
                "ema_spread": ema_spread,
                "score_scale": self.score_scale,
            },
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
