import math
from dataclasses import dataclass, field
from numbers import Real

from alpha.blender import WeightedAlphaBlender
from alpha.ledger import AlphaLedger
from alpha.models import AlphaSignal, BlendedAlphaView
from alpha.protocol import AlphaModel
from backtest.context import BacktestContext
from backtest.models import Signal, SignalAction, Timeframe

POSITION_FLAT = "flat"
POSITION_LONG = "long"
POSITION_SHORT = "short"
POSITIONS = (
    POSITION_FLAT,
    POSITION_LONG,
    POSITION_SHORT,
)


@dataclass(frozen=True, slots=True)
class EnsembleStrategy:
    """
    Strategy adapter that turns blended alpha views into normal
    operational Signals.

    The strategy is intentionally small: AlphaModels create views,
    the blender combines them, and this class applies fixed
    thresholds. Risk, sizing and execution remain downstream.
    """

    symbol: str
    models: tuple[AlphaModel, ...]
    blender: WeightedAlphaBlender
    strategy_id: str = "ENSEMBLE"
    min_conviction: float = 0.0
    enter_long: float = 0.30
    enter_short: float = -0.30
    exit_long_below: float = 0.0
    exit_short_above: float = 0.0
    alpha_ledger: AlphaLedger | None = None

    _position_state: str = field(
        default=POSITION_FLAT,
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

        if not isinstance(self.models, tuple):
            raise TypeError(
                "models must be a tuple"
            )

        if not self.models:
            raise ValueError(
                "models must not be empty"
            )

        if not all(
            isinstance(model, AlphaModel)
            for model in self.models
        ):
            raise TypeError(
                "models must contain only AlphaModel objects"
            )

        model_ids = tuple(
            model.model_id
            for model in self.models
        )

        if len(set(model_ids)) != len(model_ids):
            raise ValueError(
                "models must have unique model_id values"
            )

        if not isinstance(
            self.blender,
            WeightedAlphaBlender,
        ):
            raise TypeError(
                "blender must be a WeightedAlphaBlender"
            )

        if (
            self.alpha_ledger is not None
            and not isinstance(self.alpha_ledger, AlphaLedger)
        ):
            raise TypeError(
                "alpha_ledger must be an AlphaLedger or None"
            )

        for model_id in model_ids:
            if model_id not in self.blender.weights:
                raise ValueError(
                    f"missing blender weight for model_id: {model_id}"
                )

        self._validate_threshold(
            "min_conviction",
            self.min_conviction,
            lower=0.0,
            upper=1.0,
        )
        self._validate_threshold(
            "enter_long",
            self.enter_long,
            lower=-1.0,
            upper=1.0,
        )
        self._validate_threshold(
            "enter_short",
            self.enter_short,
            lower=-1.0,
            upper=1.0,
        )
        self._validate_threshold(
            "exit_long_below",
            self.exit_long_below,
            lower=-1.0,
            upper=1.0,
        )
        self._validate_threshold(
            "exit_short_above",
            self.exit_short_above,
            lower=-1.0,
            upper=1.0,
        )

        if self.enter_long <= self.min_conviction:
            raise ValueError(
                "enter_long must be greater than min_conviction"
            )

        if self.enter_short >= -self.min_conviction:
            raise ValueError(
                "enter_short must be smaller than -min_conviction"
            )

        if self.exit_long_below >= self.enter_long:
            raise ValueError(
                "exit_long_below must be smaller than enter_long"
            )

        if self.exit_short_above <= self.enter_short:
            raise ValueError(
                "exit_short_above must be greater than enter_short"
            )

    @property
    def closed_bar_limit(self) -> int | None:
        limits = tuple(
            getattr(model, "closed_bar_limit")
            for model in self.models
            if getattr(model, "closed_bar_limit", None) is not None
        )

        if not limits:
            return None

        for limit in limits:
            if (
                not isinstance(limit, int)
                or isinstance(limit, bool)
                or limit <= 0
            ):
                raise ValueError(
                    "model closed_bar_limit must be a positive "
                    "integer or None"
                )

        return max(limits)

    @property
    def higher_timeframe_bar_limits(
        self,
    ) -> dict[Timeframe, int]:
        result: dict[Timeframe, int] = {}

        for model in self.models:
            limits = getattr(
                model,
                "higher_timeframe_bar_limits",
                {},
            )

            if limits is None:
                continue

            if not isinstance(limits, dict):
                raise TypeError(
                    "model higher_timeframe_bar_limits must be a "
                    "dict"
                )

            for timeframe, limit in limits.items():
                if not isinstance(timeframe, Timeframe):
                    raise TypeError(
                        "model higher_timeframe_bar_limits keys "
                        "must be Timeframe values"
                    )

                if (
                    not isinstance(limit, int)
                    or isinstance(limit, bool)
                    or limit <= 0
                ):
                    raise ValueError(
                        "model higher_timeframe_bar_limits values "
                        "must be positive integers"
                    )

                result[timeframe] = max(
                    limit,
                    result.get(timeframe, 0),
                )

        return result

    def reset(self) -> None:
        object.__setattr__(
            self,
            "_position_state",
            POSITION_FLAT,
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

        alpha_signals = tuple(
            model.predict(context)
            for model in self.models
        )

        self._validate_alpha_signals(
            alpha_signals,
            context,
        )

        view = self.blender.blend(
            alpha_signals
        )

        action, reason = self._decide(view)

        self._record_alpha(
            alpha_signals,
            view=view,
            action=action,
        )

        if action == SignalAction.ENTER_LONG:
            object.__setattr__(
                self,
                "_position_state",
                POSITION_LONG,
            )

        elif action == SignalAction.ENTER_SHORT:
            object.__setattr__(
                self,
                "_position_state",
                POSITION_SHORT,
            )

        elif action == SignalAction.EXIT:
            object.__setattr__(
                self,
                "_position_state",
                POSITION_FLAT,
            )

        return self._signal(
            context,
            action=action,
            reason=reason,
            view=view,
        )

    def _decide(
        self,
        view: BlendedAlphaView,
    ) -> tuple[SignalAction, str]:
        if view.abstained:
            return (
                SignalAction.HOLD,
                "All alpha models abstained",
            )

        if self._position_state == POSITION_LONG:
            if view.value <= self.exit_long_below:
                return (
                    SignalAction.EXIT,
                    "Blended alpha fell below long exit threshold",
                )

            return (
                SignalAction.HOLD,
                "Long held by blended alpha",
            )

        if self._position_state == POSITION_SHORT:
            if view.value >= self.exit_short_above:
                return (
                    SignalAction.EXIT,
                    "Blended alpha rose above short exit threshold",
                )

            return (
                SignalAction.HOLD,
                "Short held by blended alpha",
            )

        if abs(view.value) < self.min_conviction:
            return (
                SignalAction.HOLD,
                "Blended alpha below minimum conviction",
            )

        if view.value >= self.enter_long:
            return (
                SignalAction.ENTER_LONG,
                "Blended alpha crossed long entry threshold",
            )

        if view.value <= self.enter_short:
            return (
                SignalAction.ENTER_SHORT,
                "Blended alpha crossed short entry threshold",
            )

        return (
            SignalAction.HOLD,
            "Blended alpha between entry thresholds",
        )

    def _signal(
        self,
        context: BacktestContext,
        *,
        action: SignalAction,
        reason: str,
        view: BlendedAlphaView,
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
            metadata={
                "blended_value": view.value,
                "blended_abstained": view.abstained,
                "contributors": tuple(
                    {
                        "model_id": contribution.model_id,
                        "value": contribution.value,
                        "weight": contribution.weight,
                        "confidence": contribution.confidence,
                    }
                    for contribution in view.contributors
                ),
                "abstained_models": view.abstained_models,
                "position_state": self._position_state,
                "min_conviction": self.min_conviction,
                "enter_long": self.enter_long,
                "enter_short": self.enter_short,
                "exit_long_below": self.exit_long_below,
                "exit_short_above": self.exit_short_above,
            },
        )

    def _record_alpha(
        self,
        signals: tuple[AlphaSignal, ...],
        *,
        view: BlendedAlphaView,
        action: SignalAction,
    ) -> None:
        if self.alpha_ledger is None:
            return

        for signal in signals:
            self.alpha_ledger.append_signal(
                signal,
                blended_value=view.value,
                strategy_decision=action.value,
            )

    def _validate_alpha_signals(
        self,
        signals: tuple[AlphaSignal, ...],
        context: BacktestContext,
    ) -> None:
        if len(signals) != len(self.models):
            raise RuntimeError(
                "each AlphaModel must produce exactly one AlphaSignal"
            )

        expected_model_ids = {
            model.model_id
            for model in self.models
        }

        for signal in signals:
            if signal.model_id not in expected_model_ids:
                raise ValueError(
                    "alpha signal model_id does not match models"
                )

            if signal.symbol != self.symbol:
                raise ValueError(
                    "alpha signal symbol does not match strategy"
                )

            if signal.timestamp != context.current_time:
                raise ValueError(
                    "alpha signal timestamp must equal context "
                    "current_time"
                )

    @staticmethod
    def _validate_threshold(
        name: str,
        value: float,
        *,
        lower: float,
        upper: float,
    ) -> None:
        if (
            not isinstance(value, Real)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < lower
            or value > upper
        ):
            raise ValueError(
                f"{name} must be a finite number in "
                f"[{lower}, {upper}]"
            )
