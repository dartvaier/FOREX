import math
from dataclasses import dataclass, field
from numbers import Integral, Real

from alpha.blender import WeightedAlphaBlender
from alpha.cost import CostAwareAlphaModel, MinimumExpectedMoveGate
from alpha.ledger import AlphaLedger
from alpha.quant import EmaTrendAlphaModel, TimeSeriesMomentumAlphaModel
from backtest.context import BacktestContext
from backtest.models import Signal, Timeframe
from strategy.ensemble import EnsembleStrategy


@dataclass(frozen=True, slots=True)
class TsmomEmaCostAwareEnsembleStrategy:
    """
    TSMOM + EMA ensemble with explicit cost-aware alpha gating.

    Each alpha model abstains when its own expected movement,
    estimated causally from closed bars, does not clear the
    configured cost hurdle.
    """

    symbol: str
    strategy_id: str = "ENSEMBLE-TSMOM-EMA-COST-AWARE"

    tsmom_lookback: int = 96
    tsmom_score_scale: float = 0.01
    tsmom_weight: float = 1.0

    ema_fast_period: int = 20
    ema_slow_period: int = 50
    ema_score_scale: float = 0.0010
    ema_weight: float = 1.0

    pip_size: float = 0.00010
    cost_estimate_pips: float = 3.7
    cost_safety_factor: float = 1.0

    min_conviction: float = 0.0
    enter_long: float = 0.30
    enter_short: float = -0.30
    exit_long_below: float = 0.0
    exit_short_above: float = 0.0

    alpha_ledger: AlphaLedger | None = None

    _ensemble: EnsembleStrategy = field(
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

        for name, value in (
            ("tsmom_lookback", self.tsmom_lookback),
            ("ema_fast_period", self.ema_fast_period),
            ("ema_slow_period", self.ema_slow_period),
        ):
            self._validate_period(name, value)

        if self.ema_fast_period >= self.ema_slow_period:
            raise ValueError(
                "ema_fast_period must be smaller than ema_slow_period"
            )

        for name, value in (
            ("tsmom_score_scale", self.tsmom_score_scale),
            ("tsmom_weight", self.tsmom_weight),
            ("ema_score_scale", self.ema_score_scale),
            ("ema_weight", self.ema_weight),
            ("pip_size", self.pip_size),
            ("cost_safety_factor", self.cost_safety_factor),
        ):
            self._validate_positive_number(name, value)

        self._validate_non_negative_number(
            "cost_estimate_pips",
            self.cost_estimate_pips,
        )

        gate = MinimumExpectedMoveGate(
            cost_estimate_pips=self.cost_estimate_pips,
            safety_factor=self.cost_safety_factor,
        )

        tsmom = CostAwareAlphaModel(
            inner=TimeSeriesMomentumAlphaModel(
                symbol=self.symbol,
                lookback=self.tsmom_lookback,
                score_scale=self.tsmom_score_scale,
                pip_size=self.pip_size,
            ),
            gate=gate,
        )
        ema = CostAwareAlphaModel(
            inner=EmaTrendAlphaModel(
                symbol=self.symbol,
                fast_period=self.ema_fast_period,
                slow_period=self.ema_slow_period,
                score_scale=self.ema_score_scale,
                pip_size=self.pip_size,
            ),
            gate=gate,
        )

        object.__setattr__(
            self,
            "_ensemble",
            EnsembleStrategy(
                symbol=self.symbol,
                strategy_id=self.strategy_id,
                models=(tsmom, ema),
                blender=WeightedAlphaBlender(
                    {
                        tsmom.model_id: self.tsmom_weight,
                        ema.model_id: self.ema_weight,
                    }
                ),
                min_conviction=self.min_conviction,
                enter_long=self.enter_long,
                enter_short=self.enter_short,
                exit_long_below=self.exit_long_below,
                exit_short_above=self.exit_short_above,
                alpha_ledger=self.alpha_ledger,
            ),
        )

    @property
    def closed_bar_limit(self) -> int | None:
        return self._ensemble.closed_bar_limit

    @property
    def higher_timeframe_bar_limits(
        self,
    ) -> dict[Timeframe, int]:
        return self._ensemble.higher_timeframe_bar_limits

    def reset(self) -> None:
        self._ensemble.reset()

    def on_bar(
        self,
        context: BacktestContext,
    ) -> Signal:
        return self._ensemble.on_bar(context)

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
