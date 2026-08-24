import math
from dataclasses import dataclass, field
from datetime import date
from numbers import Integral, Real

from backtest.context import BacktestContext
from backtest.models import Signal, SignalAction


@dataclass(slots=True)
class AsianRangeBreakoutStrategy:
    """
    UTC-session Asian range breakout baseline.

    Rules:

    - build the range during [range_start_hour_utc,
      range_end_hour_utc)
    - after the range closes, one breakout per UTC day is
      allowed
    - close above range high -> ENTER_LONG
    - close below range low -> ENTER_SHORT
    - at trade_end_hour_utc -> EXIT

    The strategy reads only closed bars from BacktestContext.
    It does not create orders, size positions, calculate costs
    or access broker/dataframe objects.
    """

    symbol: str
    range_start_hour_utc: int = 0
    range_end_hour_utc: int = 6
    trade_end_hour_utc: int = 20
    min_range_pips: float = 5.0
    pip_size: float = 0.00010
    strategy_id: str = "ASIAN-RANGE-BREAKOUT"

    _session_date: date | None = field(
        default=None,
        init=False,
        repr=False,
    )

    _range_high: float | None = field(
        default=None,
        init=False,
        repr=False,
    )

    _range_low: float | None = field(
        default=None,
        init=False,
        repr=False,
    )

    _range_complete: bool = field(
        default=False,
        init=False,
        repr=False,
    )

    _trade_taken: bool = field(
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

        for name, value in (
            (
                "range_start_hour_utc",
                self.range_start_hour_utc,
            ),
            (
                "range_end_hour_utc",
                self.range_end_hour_utc,
            ),
            (
                "trade_end_hour_utc",
                self.trade_end_hour_utc,
            ),
        ):
            self._validate_hour(name, value)

        if not (
            self.range_start_hour_utc
            < self.range_end_hour_utc
            < self.trade_end_hour_utc
        ):
            raise ValueError(
                "range_start_hour_utc < range_end_hour_utc "
                "< trade_end_hour_utc is required"
            )

        self._validate_non_negative_number(
            "min_range_pips",
            self.min_range_pips,
        )

        self._validate_positive_number(
            "pip_size",
            self.pip_size,
        )

    def reset(self) -> None:
        self._session_date = None
        self._range_high = None
        self._range_low = None
        self._range_complete = False
        self._trade_taken = False

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

        current_bar = context.closed_bars[-1]
        bar_date = current_bar.time.date()

        if bar_date != self._session_date:
            self._start_new_session(bar_date)

        bar_hour = current_bar.time.hour

        if self._in_range_window(bar_hour):
            self._update_range(
                high=current_bar.high,
                low=current_bar.low,
            )

            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Building Asian range",
                metadata=self._metadata(),
            )

        if bar_hour >= self.trade_end_hour_utc:
            if self._trade_taken:
                return self._signal(
                    context,
                    action=SignalAction.EXIT,
                    reason="Asian breakout time exit",
                    metadata=self._metadata(),
                )

            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Asian breakout window closed",
                metadata=self._metadata(),
            )

        if not self._range_complete:
            self._range_complete = (
                self._range_high is not None
                and self._range_low is not None
            )

        if not self._range_complete:
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="No Asian range",
                metadata=self._metadata(),
            )

        range_pips = self._range_pips()

        if range_pips < self.min_range_pips:
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Asian range too small",
                metadata=self._metadata(),
            )

        if self._trade_taken:
            return self._signal(
                context,
                action=SignalAction.HOLD,
                reason="Asian breakout already taken",
                metadata=self._metadata(),
            )

        if (
            self._range_high is not None
            and current_bar.close > self._range_high
        ):
            self._trade_taken = True

            return self._signal(
                context,
                action=SignalAction.ENTER_LONG,
                reason="Close broke above Asian range",
                metadata=self._metadata(),
            )

        if (
            self._range_low is not None
            and current_bar.close < self._range_low
        ):
            self._trade_taken = True

            return self._signal(
                context,
                action=SignalAction.ENTER_SHORT,
                reason="Close broke below Asian range",
                metadata=self._metadata(),
            )

        return self._signal(
            context,
            action=SignalAction.HOLD,
            reason="No Asian range breakout",
            metadata=self._metadata(),
        )

    def _start_new_session(
        self,
        session_date: date,
    ) -> None:
        self._session_date = session_date
        self._range_high = None
        self._range_low = None
        self._range_complete = False
        self._trade_taken = False

    def _in_range_window(
        self,
        hour: int,
    ) -> bool:
        return (
            self.range_start_hour_utc
            <= hour
            < self.range_end_hour_utc
        )

    def _update_range(
        self,
        *,
        high: float,
        low: float,
    ) -> None:
        if self._range_high is None:
            self._range_high = high
        else:
            self._range_high = max(
                self._range_high,
                high,
            )

        if self._range_low is None:
            self._range_low = low
        else:
            self._range_low = min(
                self._range_low,
                low,
            )

    def _range_pips(self) -> float:
        if (
            self._range_high is None
            or self._range_low is None
        ):
            return 0.0

        return (
            self._range_high
            - self._range_low
        ) / self.pip_size

    def _metadata(self) -> dict:
        return {
            "session_date": (
                None
                if self._session_date is None
                else self._session_date.isoformat()
            ),
            "range_high": self._range_high,
            "range_low": self._range_low,
            "range_pips": self._range_pips(),
            "range_complete": self._range_complete,
            "trade_taken": self._trade_taken,
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
    def _validate_hour(
        name: str,
        value: int,
    ) -> None:
        if (
            not isinstance(value, Integral)
            or isinstance(value, bool)
            or value < 0
            or value > 23
        ):
            raise ValueError(
                f"{name} must be an integer from 0 to 23"
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
