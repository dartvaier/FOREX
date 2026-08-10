import math
from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np

from backtest.context import BacktestContext
from backtest.models import Signal, SignalAction, Timeframe

REGIME_FILTER_NONE = "none"
REGIME_FILTER_H4_VOL_HIGH = "h4_vol_high"
REGIME_FILTERS = (
    REGIME_FILTER_NONE,
    REGIME_FILTER_H4_VOL_HIGH,
)


@dataclass(frozen=True, slots=True)
class TimeSeriesMomentumStrategy:
    """
    Long-only time-series momentum baseline (with optional regime
    filter, hypothesis RF-01).

    Rules:

    - cumulative return over lookback bars is above threshold
      -> ENTER_LONG
    - cumulative return is below exit threshold
      -> EXIT
    - otherwise -> HOLD

    Optional regime filter (regime_filter="h4_vol_high", RF-01):

    - entries are only allowed while recent H4 volatility is ABOVE
      the median of the historical H4 |return| distribution
      (vol_recente > mediana_vol)
    - the filter blocks ENTRIES only; EXIT/HOLD logic is untouched
    - H4 bars come from BacktestContext.timeframe_bars and are only
      valid after their own close (the engine guarantees causality)

    The default regime_filter="none" preserves the baseline behavior
    exactly (regression contract).

    The strategy reads only closed bars from BacktestContext.
    It does not create orders, size positions, calculate costs
    or access broker/dataframe objects.
    """

    symbol: str
    lookback: int = 96
    entry_threshold: float = 0.0010
    exit_threshold: float = 0.0
    strategy_id: str = "TIME-SERIES-MOMENTUM"
    regime_filter: str = REGIME_FILTER_NONE
    regime_lookback: int = 48
    regime_context_lookback: int = 250

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

        if self.regime_filter not in REGIME_FILTERS:
            raise ValueError(
                f"regime_filter must be one of {REGIME_FILTERS}, "
                f"got {self.regime_filter!r}"
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

        if self.regime_filter != REGIME_FILTER_NONE:
            self._validate_period(
                "regime_lookback",
                self.regime_lookback,
            )

            self._validate_period(
                "regime_context_lookback",
                self.regime_context_lookback,
            )

            if (
                self.regime_lookback
                >= self.regime_context_lookback
            ):
                raise ValueError(
                    "regime_lookback must be smaller than "
                    "regime_context_lookback"
                )

    @property
    def closed_bar_limit(self) -> int:
        return self.lookback + 1

    @property
    def higher_timeframes(self) -> tuple[Timeframe, ...]:
        if self.regime_filter == REGIME_FILTER_NONE:
            return ()

        return (Timeframe.H4,)

    @property
    def higher_timeframe_bar_limits(
        self,
    ) -> dict[Timeframe, int]:
        if self.regime_filter == REGIME_FILTER_NONE:
            return {}

        return {
            Timeframe.H4: self.regime_context_lookback + 1,
        }

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
            "regime_filter": self.regime_filter,
        }

        if momentum_return < self.exit_threshold:
            # EXIT is never blocked by the regime filter (RF-01:
            # the filter only selects entries).
            return self._signal(
                context,
                action=SignalAction.EXIT,
                reason="Momentum fell below exit threshold",
                metadata=metadata,
            )

        if momentum_return <= self.entry_threshold:
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="No time-series momentum signal",
                metadata=metadata,
            )

        if self.regime_filter == REGIME_FILTER_NONE:
            return self._signal(
                context,
                action=SignalAction.ENTER_LONG,
                reason="Positive time-series momentum",
                metadata=metadata,
            )

        regime_ok, regime_stats = self._regime_allows_entry(
            context,
        )

        metadata = {
            **metadata,
            **regime_stats,
        }

        if not regime_ok:
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Regime filter blocked entry",
                metadata=metadata,
            )

        return self._signal(
            context,
            action=SignalAction.ENTER_LONG,
            reason="Positive momentum in favorable regime",
            metadata=metadata,
        )

    def _regime_allows_entry(
        self,
        context: BacktestContext,
    ) -> tuple[bool, dict]:
        """
        RF-01 regime check on closed H4 bars.

        vol_recente = std of log returns over the last
        `regime_lookback` closed H4 bars.
        mediana_vol = median of |log return| over the last
        `regime_context_lookback` closed H4 bars.
        Favorable: vol_recente > mediana_vol.
        """
        h4_bars = context.timeframe_bars.get(
            Timeframe.H4,
            (),
        )

        if (
            len(h4_bars)
            < self.regime_context_lookback + 1
        ):
            return False, {
                "regime_ok": False,
                "regime_reason": (
                    "H4 warm-up"
                ),
            }

        closes = np.asarray(
            [bar.close for bar in h4_bars],
            dtype=np.float64,
        )

        log_returns = np.diff(np.log(closes))

        recent = log_returns[
            -self.regime_lookback:
        ]
        context_returns = log_returns[
            -(self.regime_context_lookback):
        ]

        vol_recente = float(
            np.std(recent, ddof=1)
        )
        mediana_vol = float(
            np.median(np.abs(context_returns))
        )

        regime_ok = vol_recente > mediana_vol

        return regime_ok, {
            "regime_ok": regime_ok,
            "regime_vol_recente": round(
                vol_recente,
                8,
            ),
            "regime_vol_mediana": round(
                mediana_vol,
                8,
            ),
            "regime_lookback": self.regime_lookback,
            "regime_context_lookback": (
                self.regime_context_lookback
            ),
        }

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
