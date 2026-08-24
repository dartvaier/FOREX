import math
from dataclasses import dataclass, field
from numbers import Integral, Real
from types import MappingProxyType
from typing import Any, Mapping

from alpha.models import AlphaSignal
from alpha.protocol import AlphaModel
from backtest.context import BacktestContext
from backtest.models import Timeframe

REGIME_WARM_UP = "warm_up"
REGIME_HIGH_VOLATILITY = "high_volatility"
REGIME_TRENDING_UP = "trending_up"
REGIME_TRENDING_DOWN = "trending_down"
REGIME_RANGING = "ranging"

REGIMES = (
    REGIME_WARM_UP,
    REGIME_HIGH_VOLATILITY,
    REGIME_TRENDING_UP,
    REGIME_TRENDING_DOWN,
    REGIME_RANGING,
)


@dataclass(frozen=True, slots=True)
class RegimeDecision:
    """
    Immutable causal decision produced by a regime gate.
    """

    regime: str
    allowed: bool
    reason: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.regime not in REGIMES:
            raise ValueError(
                f"regime must be one of {REGIMES}"
            )

        if not isinstance(self.allowed, bool):
            raise TypeError(
                "allowed must be a bool"
            )

        if (
            not isinstance(self.reason, str)
            or not self.reason.strip()
        ):
            raise ValueError(
                "reason must be a non-empty string"
            )

        if not isinstance(self.metadata, Mapping):
            raise TypeError(
                "metadata must be a mapping"
            )

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )


@dataclass(frozen=True, slots=True)
class TrendVolatilityRegimeGate:
    """
    Causal trend/volatility regime gate.

    The gate reads only closed bars from BacktestContext and
    decides whether alpha models should vote in the current
    regime. It does not produce operational Signals.
    """

    trend_lookback: int = 96
    volatility_lookback: int = 96
    trend_threshold: float = 0.0025
    max_volatility: float = 0.00055
    allowed_regimes: tuple[str, ...] = (
        REGIME_TRENDING_UP,
        REGIME_TRENDING_DOWN,
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
        self._validate_period(
            "trend_lookback",
            self.trend_lookback,
        )
        self._validate_period(
            "volatility_lookback",
            self.volatility_lookback,
        )
        self._validate_positive_number(
            "trend_threshold",
            self.trend_threshold,
        )
        self._validate_positive_number(
            "max_volatility",
            self.max_volatility,
        )

        if not isinstance(self.allowed_regimes, tuple):
            raise TypeError(
                "allowed_regimes must be a tuple"
            )

        if not self.allowed_regimes:
            raise ValueError(
                "allowed_regimes must not be empty"
            )

        for regime in self.allowed_regimes:
            if regime not in REGIMES:
                raise ValueError(
                    f"allowed_regimes must contain only {REGIMES}"
                )

    def evaluate(
        self,
        context: BacktestContext,
    ) -> RegimeDecision:
        if not isinstance(
            context,
            BacktestContext,
        ):
            raise TypeError(
                "context must be a BacktestContext"
            )

        if len(context.closed_bars) < self.closed_bar_limit:
            return self._decision(
                REGIME_WARM_UP,
                reason="Regime warm-up",
                metadata={
                    "required_closed_bars": self.closed_bar_limit,
                    "available_closed_bars": len(context.closed_bars),
                },
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
            "trend_threshold": self.trend_threshold,
            "realized_volatility": realized_volatility,
            "max_volatility": self.max_volatility,
        }

        if realized_volatility > self.max_volatility:
            return self._decision(
                REGIME_HIGH_VOLATILITY,
                reason="High-volatility regime",
                metadata=metadata,
            )

        if trend_return >= self.trend_threshold:
            return self._decision(
                REGIME_TRENDING_UP,
                reason="Bullish trend regime",
                metadata=metadata,
            )

        if trend_return <= -self.trend_threshold:
            return self._decision(
                REGIME_TRENDING_DOWN,
                reason="Bearish trend regime",
                metadata=metadata,
            )

        return self._decision(
            REGIME_RANGING,
            reason="Ranging regime",
            metadata=metadata,
        )

    def _decision(
        self,
        regime: str,
        *,
        reason: str,
        metadata: Mapping[str, Any],
    ) -> RegimeDecision:
        return RegimeDecision(
            regime=regime,
            allowed=regime in self.allowed_regimes,
            reason=reason,
            metadata=metadata,
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


@dataclass(frozen=True, slots=True)
class RegimeGatedAlphaModel:
    """
    AlphaModel wrapper that abstains when a regime gate blocks
    the inner model.
    """

    inner: AlphaModel
    gate: TrendVolatilityRegimeGate

    def __post_init__(self) -> None:
        if not isinstance(self.inner, AlphaModel):
            raise TypeError(
                "inner must satisfy the AlphaModel protocol"
            )

        if not isinstance(
            self.gate,
            TrendVolatilityRegimeGate,
        ):
            raise TypeError(
                "gate must be a TrendVolatilityRegimeGate"
            )

    @property
    def model_id(self) -> str:
        return self.inner.model_id

    @property
    def closed_bar_limit(self) -> int | None:
        inner_limit = getattr(
            self.inner,
            "closed_bar_limit",
            None,
        )

        if inner_limit is None:
            return self.gate.closed_bar_limit

        if (
            not isinstance(inner_limit, int)
            or isinstance(inner_limit, bool)
            or inner_limit <= 0
        ):
            raise ValueError(
                "inner closed_bar_limit must be a positive "
                "integer or None"
            )

        return max(
            inner_limit,
            self.gate.closed_bar_limit,
        )

    @property
    def higher_timeframe_bar_limits(
        self,
    ) -> dict[Timeframe, int]:
        limits = getattr(
            self.inner,
            "higher_timeframe_bar_limits",
            {},
        )

        if limits is None:
            return {}

        if not isinstance(limits, dict):
            raise TypeError(
                "inner higher_timeframe_bar_limits must be a dict"
            )

        return dict(limits)

    def predict(
        self,
        context: BacktestContext,
    ) -> AlphaSignal:
        decision = self.gate.evaluate(context)

        if not decision.allowed:
            symbol = getattr(
                self.inner,
                "symbol",
                "",
            )

            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError(
                    "inner model must expose a non-empty symbol "
                    "when regime-gated"
                )

            return AlphaSignal.abstain(
                model_id=self.model_id,
                symbol=symbol,
                timestamp=context.current_time,
                reason=f"Regime gate blocked: {decision.reason}",
                metadata={
                    "regime": decision.regime,
                    "regime_allowed": decision.allowed,
                    **decision.metadata,
                },
            )

        signal = self.inner.predict(context)

        metadata = {
            **signal.metadata,
            "regime": decision.regime,
            "regime_allowed": decision.allowed,
            **{
                f"regime_{key}": value
                for key, value in decision.metadata.items()
            },
        }

        return AlphaSignal(
            model_id=signal.model_id,
            symbol=signal.symbol,
            timestamp=signal.timestamp,
            value=signal.value,
            confidence=signal.confidence,
            abstained=signal.abstained,
            reason=signal.reason,
            metadata=metadata,
        )
