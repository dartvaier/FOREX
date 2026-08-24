"""Causal, deterministic EMA crossover signals for the H1 EURUSD baseline."""

from dataclasses import dataclass, field
from numbers import Integral

from backtest.context import BacktestContext
from backtest.models.enums import SimulationPhase
from backtest.models.bar import MarketBar
from backtest.strategy import Strategy
from domain.signal import Signal, SignalAction


@dataclass(slots=True)
class EmaCrossoverStrategy(Strategy):
    """Emit directional Signals from closed-bar EMA crossovers only.

    The strategy has no dependency on Risk, Portfolio, costs, execution or MT5.
    It is configured for the initial EURUSD/H1 experiment; timeframe selection
    is enforced by the experiment runner because Context intentionally exposes
    market observations, not its backing feed configuration.
    """

    symbol: str = "EURUSD"
    fast_period: int = 20
    slow_period: int = 50
    strategy_id: str = "ema-crossover"
    _processed_count: int = field(init=False, default=0, repr=False, compare=False)
    _fast_seed: list[float] = field(init=False, default_factory=list, repr=False, compare=False)
    _slow_seed: list[float] = field(init=False, default_factory=list, repr=False, compare=False)
    _fast_ema: float | None = field(init=False, default=None, repr=False, compare=False)
    _slow_ema: float | None = field(init=False, default=None, repr=False, compare=False)
    _previous_fast: float | None = field(init=False, default=None, repr=False, compare=False)
    _previous_slow: float | None = field(init=False, default=None, repr=False, compare=False)
    _last_bar: MarketBar | None = field(init=False, default=None, repr=False, compare=False)
    _last_decision: tuple[SignalAction, str] = field(init=False, default=(SignalAction.HOLD, "waiting for a closed H1 bar"), repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol must be a non-empty string")
        if not isinstance(self.strategy_id, str) or not self.strategy_id.strip():
            raise ValueError("strategy_id must be a non-empty string")
        for name in ("fast_period", "slow_period"):
            value = getattr(self, name)
            if not isinstance(value, Integral) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be smaller than slow_period")

    def on_bar(self, context: BacktestContext) -> Signal:
        if not isinstance(context, BacktestContext):
            raise TypeError("context must be a BacktestContext")
        closes = tuple(bar.close for bar in context.closed_bars)
        if context.phase is not SimulationPhase.BAR_CLOSE:
            action, reason = SignalAction.HOLD, "waiting for a closed H1 bar"
        elif context.current_bar_index == self._processed_count:
            self._advance(closes[-1])
            action, reason = self._current_decision()
            self._last_bar, self._last_decision = context.current_bar, (action, reason)
        elif len(closes) == self._processed_count and context.current_bar == self._last_bar:
            action, reason = self._last_decision
        else:
            action, reason = self._decision_from_history(closes)
        return Signal(
            signal_id=f"{self.strategy_id}-{context.current_bar_index}",
            strategy_id=self.strategy_id,
            symbol=self.symbol,
            timestamp=context.current_time,
            action=action,
            reason=reason,
        )

    def _advance(self, close: float) -> None:
        self._previous_fast, self._fast_ema = self._next_ema(close, self.fast_period, self._fast_seed, self._fast_ema)
        self._previous_slow, self._slow_ema = self._next_ema(close, self.slow_period, self._slow_seed, self._slow_ema)
        self._processed_count += 1

    @staticmethod
    def _next_ema(close: float, period: int, seed: list[float], current: float | None) -> tuple[float | None, float | None]:
        if current is None:
            seed.append(close)
            return None, (sum(seed) / period if len(seed) == period else None)
        return current, 2.0 / (period + 1) * close + (1 - 2.0 / (period + 1)) * current

    def _current_decision(self) -> tuple[SignalAction, str]:
        if self._processed_count < self.slow_period + 1:
            return SignalAction.HOLD, f"warm-up requires {self.slow_period + 1} closed bars"
        if self._previous_fast <= self._previous_slow and self._fast_ema > self._slow_ema:
            return SignalAction.ENTER_LONG, "fast EMA crossed above slow EMA"
        if self._previous_fast >= self._previous_slow and self._fast_ema < self._slow_ema:
            return SignalAction.ENTER_SHORT, "fast EMA crossed below slow EMA"
        return SignalAction.HOLD, "no EMA crossover"

    def _decision_from_history(self, closes: tuple[float, ...]) -> tuple[SignalAction, str]:
        if len(closes) < self.slow_period + 1:
            return SignalAction.HOLD, f"warm-up requires {self.slow_period + 1} closed bars"
        previous_fast, current_fast = self._ema_last_two(closes, self.fast_period)
        previous_slow, current_slow = self._ema_last_two(closes, self.slow_period)
        if previous_fast <= previous_slow and current_fast > current_slow:
            return SignalAction.ENTER_LONG, "fast EMA crossed above slow EMA"
        if previous_fast >= previous_slow and current_fast < current_slow:
            return SignalAction.ENTER_SHORT, "fast EMA crossed below slow EMA"
        return SignalAction.HOLD, "no EMA crossover"

    @staticmethod
    def _ema_last_two(values: tuple[float, ...], period: int) -> tuple[float, float]:
        ema = sum(values[:period]) / period
        previous = ema
        alpha = 2.0 / (period + 1)
        for value in values[period:]:
            previous, ema = ema, alpha * value + (1 - alpha) * ema
        return previous, ema
