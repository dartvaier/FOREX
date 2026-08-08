from backtest.context import BacktestContext
from backtest.models.config import BacktestConfig
from backtest.models.enums import SimulationPhase
from backtest.models.signal import Signal
from backtest.strategy import Strategy


class SignalProcessor:
    """
    Evaluates a Strategy and validates the Signal produced
    for the current simulation context.

    Responsibilities:

    - allow Strategy evaluation only at BAR_CLOSE
    - require a valid Strategy contract
    - require exactly one Signal result
    - validate strategy identity
    - validate symbol identity
    - validate signal timestamp
    - preserve the Signal without silently modifying it

    The processor does not:

    - create Orders
    - apply position sizing
    - apply risk rules
    - execute trades
    - alter Signal contents
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

        self._config = config

    @property
    def config(self) -> BacktestConfig:
        return self._config

    def process(
        self,
        strategy: Strategy,
        context: BacktestContext,
    ) -> Signal:
        """
        Evaluate the Strategy against the supplied context
        and return a validated Signal.

        Strategy exceptions are intentionally not swallowed.
        A broken Strategy must fail the experiment explicitly.
        """

        if not isinstance(
            context,
            BacktestContext,
        ):
            raise TypeError(
                "context must be a BacktestContext"
            )

        if not isinstance(
            strategy,
            Strategy,
        ):
            raise TypeError(
                "strategy must satisfy the Strategy protocol"
            )

        if context.phase != SimulationPhase.BAR_CLOSE:
            raise ValueError(
                "Strategy can only be evaluated at BAR_CLOSE"
            )

        if context.current_bar is None:
            raise ValueError(
                "BAR_CLOSE context must expose current_bar"
            )

        strategy_id = strategy.strategy_id

        if (
            not isinstance(strategy_id, str)
            or not strategy_id.strip()
        ):
            raise ValueError(
                "strategy_id must be a non-empty string"
            )

        signal = strategy.on_bar(context)

        if not isinstance(signal, Signal):
            raise TypeError(
                "Strategy.on_bar must return a Signal"
            )

        if signal.strategy_id != strategy_id:
            raise ValueError(
                "signal strategy_id does not match Strategy"
            )

        if signal.symbol != self._config.symbol:
            raise ValueError(
                "signal symbol does not match BacktestConfig"
            )

        if signal.timestamp != context.current_time:
            raise ValueError(
                "signal timestamp must equal context current_time"
            )

        return signal