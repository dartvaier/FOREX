from dataclasses import dataclass
from datetime import datetime

from backtest.models.bar import MarketBar
from backtest.models.config import BacktestConfig
from backtest.models.enums import (
    AmbiguousBarPolicy,
    ExitReason,
    PositionSide,
)
from backtest.models.position import Position


@dataclass(frozen=True, slots=True)
class ProtectiveExitDecision:
    """
    Result of evaluating Stop Loss / Take Profit against
    one historical bar.

    reference_price:
        Frictionless reference price that will later be passed
        through the CostModel.

    triggered_at_open:
        True when the exit condition already existed at the
        opening price.

    ambiguous:
        True when both Stop Loss and Take Profit were touched
        inside the same bar and the configured ambiguity policy
        had to resolve the outcome.
    """

    position_id: str
    bar_time: datetime

    exit_reason: ExitReason
    reference_price: float

    triggered_at_open: bool
    ambiguous: bool


class ProtectiveExitEvaluator:
    """
    Evaluates protective exits for an existing Position.

    Baseline rules:

    LONG:
        stop hit   -> low <= stop_loss
        target hit -> high >= take_profit

    SHORT:
        stop hit   -> high >= stop_loss
        target hit -> low <= take_profit

    Gap through Stop Loss:

        LONG:
            open <= stop_loss
            -> exit reference = open

        SHORT:
            open >= stop_loss
            -> exit reference = open

    This preserves adverse gap behavior instead of pretending
    the position was filled at the original stop level.

    Gap through Take Profit is treated conservatively at the
    configured target level rather than granting a better
    opening price.

    If Stop Loss and Take Profit are both touched in the same
    bar and the path is unknown, WORST_CASE selects Stop Loss.
    """

    def __init__(
        self,
        config: BacktestConfig,
    ) -> None:
        if not isinstance(
            config,
            BacktestConfig,
        ):
            raise TypeError(
                "config must be a BacktestConfig"
            )

        if (
            config.ambiguous_bar_policy
            != AmbiguousBarPolicy.WORST_CASE
        ):
            raise ValueError(
                "unsupported ambiguous bar policy"
            )

        self._config = config

    @property
    def config(self) -> BacktestConfig:
        return self._config

    def evaluate(
        self,
        position: Position,
        bar: MarketBar,
    ) -> ProtectiveExitDecision | None:
        if not isinstance(
            position,
            Position,
        ):
            raise TypeError(
                "position must be a Position"
            )

        if not isinstance(
            bar,
            MarketBar,
        ):
            raise TypeError(
                "bar must be a MarketBar"
            )

        if position.symbol != self._config.symbol:
            raise ValueError(
                "position symbol does not match BacktestConfig"
            )

        # No protection configured.
        if (
            position.stop_loss is None
            and position.take_profit is None
        ):
            return None

        if position.side == PositionSide.LONG:
            return self._evaluate_long(
                position,
                bar,
            )

        if position.side == PositionSide.SHORT:
            return self._evaluate_short(
                position,
                bar,
            )

        raise ValueError(
            f"unsupported PositionSide: {position.side}"
        )

    def _evaluate_long(
        self,
        position: Position,
        bar: MarketBar,
    ) -> ProtectiveExitDecision | None:
        stop_loss = position.stop_loss
        take_profit = position.take_profit

        # Adverse gap through stop.
        if (
            stop_loss is not None
            and bar.open <= stop_loss
        ):
            return self._decision(
                position=position,
                bar=bar,
                exit_reason=ExitReason.STOP_LOSS,
                reference_price=bar.open,
                triggered_at_open=True,
                ambiguous=False,
            )

        # Favorable gap through target.
        #
        # Conservative baseline:
        # do not grant price improvement beyond the target.
        if (
            take_profit is not None
            and bar.open >= take_profit
        ):
            return self._decision(
                position=position,
                bar=bar,
                exit_reason=ExitReason.TAKE_PROFIT,
                reference_price=take_profit,
                triggered_at_open=True,
                ambiguous=False,
            )

        stop_hit = (
            stop_loss is not None
            and bar.low <= stop_loss
        )

        target_hit = (
            take_profit is not None
            and bar.high >= take_profit
        )

        if stop_hit and target_hit:
            return self._decision(
                position=position,
                bar=bar,
                exit_reason=ExitReason.STOP_LOSS,
                reference_price=stop_loss,
                triggered_at_open=False,
                ambiguous=True,
            )

        if stop_hit:
            return self._decision(
                position=position,
                bar=bar,
                exit_reason=ExitReason.STOP_LOSS,
                reference_price=stop_loss,
                triggered_at_open=False,
                ambiguous=False,
            )

        if target_hit:
            return self._decision(
                position=position,
                bar=bar,
                exit_reason=ExitReason.TAKE_PROFIT,
                reference_price=take_profit,
                triggered_at_open=False,
                ambiguous=False,
            )

        return None

    def _evaluate_short(
        self,
        position: Position,
        bar: MarketBar,
    ) -> ProtectiveExitDecision | None:
        stop_loss = position.stop_loss
        take_profit = position.take_profit

        # Adverse gap through stop.
        if (
            stop_loss is not None
            and bar.open >= stop_loss
        ):
            return self._decision(
                position=position,
                bar=bar,
                exit_reason=ExitReason.STOP_LOSS,
                reference_price=bar.open,
                triggered_at_open=True,
                ambiguous=False,
            )

        # Favorable gap through target.
        if (
            take_profit is not None
            and bar.open <= take_profit
        ):
            return self._decision(
                position=position,
                bar=bar,
                exit_reason=ExitReason.TAKE_PROFIT,
                reference_price=take_profit,
                triggered_at_open=True,
                ambiguous=False,
            )

        stop_hit = (
            stop_loss is not None
            and bar.high >= stop_loss
        )

        target_hit = (
            take_profit is not None
            and bar.low <= take_profit
        )

        if stop_hit and target_hit:
            return self._decision(
                position=position,
                bar=bar,
                exit_reason=ExitReason.STOP_LOSS,
                reference_price=stop_loss,
                triggered_at_open=False,
                ambiguous=True,
            )

        if stop_hit:
            return self._decision(
                position=position,
                bar=bar,
                exit_reason=ExitReason.STOP_LOSS,
                reference_price=stop_loss,
                triggered_at_open=False,
                ambiguous=False,
            )

        if target_hit:
            return self._decision(
                position=position,
                bar=bar,
                exit_reason=ExitReason.TAKE_PROFIT,
                reference_price=take_profit,
                triggered_at_open=False,
                ambiguous=False,
            )

        return None

    @staticmethod
    def _decision(
        *,
        position: Position,
        bar: MarketBar,
        exit_reason: ExitReason,
        reference_price: float,
        triggered_at_open: bool,
        ambiguous: bool,
    ) -> ProtectiveExitDecision:
        return ProtectiveExitDecision(
            position_id=position.position_id,
            bar_time=bar.time,
            exit_reason=exit_reason,
            reference_price=reference_price,
            triggered_at_open=triggered_at_open,
            ambiguous=ambiguous,
        )