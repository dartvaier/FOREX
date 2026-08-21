import math
from dataclasses import dataclass
from numbers import Integral, Real

from alpha.cost import expected_move_pips_from_return
from alpha.models import AlphaSignal
from backtest.context import BacktestContext


@dataclass(frozen=True, slots=True)
class TimeSeriesMomentumAlphaModel:
    """
    Causal time-series momentum AlphaModel.

    The model reads only closed bars from BacktestContext and
    expresses lookback return as a normalized alpha view. It does
    not create operational Signals, Orders, positions or sizing.
    """

    symbol: str
    lookback: int = 96
    score_scale: float = 0.01
    pip_size: float = 0.00010
    model_id: str = "TIME-SERIES-MOMENTUM-ALPHA"

    @property
    def closed_bar_limit(self) -> int:
        return self.lookback + 1

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

        if (
            not isinstance(self.lookback, Integral)
            or isinstance(self.lookback, bool)
            or self.lookback <= 0
        ):
            raise ValueError(
                "lookback must be a positive integer"
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

        if (
            not isinstance(self.pip_size, Real)
            or isinstance(self.pip_size, bool)
            or not math.isfinite(self.pip_size)
            or self.pip_size <= 0
        ):
            raise ValueError(
                "pip_size must be a finite positive number"
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
                    "lookback": self.lookback,
                    "required_closed_bars": self.closed_bar_limit,
                    "available_closed_bars": len(context.closed_bars),
                },
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

        value = max(
            -1.0,
            min(
                1.0,
                momentum_return / self.score_scale,
            ),
        )
        expected_move_pips = expected_move_pips_from_return(
            reference_price=current_bar.close,
            expected_return=momentum_return,
            pip_size=self.pip_size,
        )

        reason = "Neutral time-series momentum"

        if value > 0.0:
            reason = "Positive time-series momentum"

        elif value < 0.0:
            reason = "Negative time-series momentum"

        return AlphaSignal(
            model_id=self.model_id,
            symbol=self.symbol,
            timestamp=context.current_time,
            value=value,
            confidence=None,
            abstained=False,
            reason=reason,
            metadata={
                "lookback": self.lookback,
                "momentum_return": momentum_return,
                "score_scale": self.score_scale,
                "pip_size": self.pip_size,
                "expected_move_pips": expected_move_pips,
            },
        )
