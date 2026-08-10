import math
from dataclasses import dataclass, field
from numbers import Real

from backtest.context import BacktestContext
from backtest.models import Signal, SignalAction


@dataclass(slots=True)
class SimpleCarryStrategy:
    """
    Static carry-direction baseline.

    Rules:

    - carry_score >= entry_threshold -> ENTER_LONG
    - carry_score <= -entry_threshold -> ENTER_SHORT
    - abs(carry_score) <= exit_threshold -> EXIT
    - otherwise -> HOLD

    Positive carry_score means the baseline favors holding
    the base currency against the quote currency.

    Negative carry_score means the baseline favors holding
    the quote currency against the base currency.

    This strategy does not model accrued swap or interest.
    It only tests the directional exposure implied by a static
    carry proxy.
    """

    symbol: str
    carry_score: float = -1.0
    entry_threshold: float = 0.5
    exit_threshold: float = 0.0
    strategy_id: str = "SIMPLE-CARRY"

    _exposed: bool = field(
        default=False,
        init=False,
        repr=False,
    )

    @property
    def closed_bar_limit(self) -> int:
        return 1

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

        self._validate_number(
            "carry_score",
            self.carry_score,
        )

        self._validate_non_negative_number(
            "entry_threshold",
            self.entry_threshold,
        )

        self._validate_non_negative_number(
            "exit_threshold",
            self.exit_threshold,
        )

        if self.exit_threshold > self.entry_threshold:
            raise ValueError(
                "exit_threshold must be less than or equal "
                "to entry_threshold"
            )

    def reset(self) -> None:
        self._exposed = False

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

        if not context.closed_bars:
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Warm-up",
            )

        metadata = {
            "carry_score": self.carry_score,
            "entry_threshold": self.entry_threshold,
            "exit_threshold": self.exit_threshold,
            "exposed": self._exposed,
        }

        if (
            self._exposed
            and abs(self.carry_score) <= self.exit_threshold
        ):
            self._exposed = False

            return self._signal(
                context,
                action=SignalAction.EXIT,
                reason="Carry score returned to neutral",
                metadata={
                    **metadata,
                    "exposed": self._exposed,
                },
            )

        if self._exposed:
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Carry exposure already active",
                metadata=metadata,
            )

        if self.carry_score >= self.entry_threshold:
            self._exposed = True

            return self._signal(
                context,
                action=SignalAction.ENTER_LONG,
                reason="Positive carry score",
                metadata={
                    **metadata,
                    "exposed": self._exposed,
                },
            )

        if self.carry_score <= -self.entry_threshold:
            self._exposed = True

            return self._signal(
                context,
                action=SignalAction.ENTER_SHORT,
                reason="Negative carry score",
                metadata={
                    **metadata,
                    "exposed": self._exposed,
                },
            )

        return self._signal(
            context,
            action=SignalAction.HOLD,
            reason="Carry score inside neutral zone",
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
