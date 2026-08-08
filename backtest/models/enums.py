from enum import StrEnum


class SignalAction(StrEnum):
    """
    Actions that may be requested by a Strategy.

    A Signal expresses strategy intent only.
    It is not an Order and does not guarantee execution.
    """

    ENTER_LONG = "ENTER_LONG"
    ENTER_SHORT = "ENTER_SHORT"
    EXIT = "EXIT"
    HOLD = "HOLD"


class OrderSide(StrEnum):
    """
    Execution side of an Order.
    """

    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    """
    Supported order types.

    The v0.2 baseline supports MARKET orders only.
    """

    MARKET = "MARKET"


class OrderStatus(StrEnum):
    """
    Lifecycle status of an Order.
    """

    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    UNFILLED = "UNFILLED"


class PositionSide(StrEnum):
    """
    Direction of an open Position.

    FLAT is intentionally not represented here:
    absence of a Position represents the flat state.
    """

    LONG = "LONG"
    SHORT = "SHORT"


class ExitReason(StrEnum):
    """
    Reason why a Position was closed.
    """

    STRATEGY_EXIT = "STRATEGY_EXIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    END_OF_BACKTEST = "END_OF_BACKTEST"
    RISK_EXIT = "RISK_EXIT"
    KILL_SWITCH = "KILL_SWITCH"
    MANUAL_TEST = "MANUAL_TEST"


class AmbiguousBarPolicy(StrEnum):
    """
    Policy used when OHLC data cannot determine whether
    Stop Loss or Take Profit was reached first.

    The baseline deliberately uses WORST_CASE.
    """

    WORST_CASE = "WORST_CASE"

class Timeframe(StrEnum):
    """
    Timeframes officially supported by the baseline
    BacktestEngine.
    """

    M15 = "M15"
    H1 = "H1"
    H4 = "H4"


class EndOfBacktestPolicy(StrEnum):
    """
    Defines how an open Position is handled when the
    evaluation period reaches its end.
    """

    FORCE_CLOSE_AT_FINAL_AVAILABLE_CLOSE = (
        "FORCE_CLOSE_AT_FINAL_AVAILABLE_CLOSE"
    )

    LEAVE_OPEN = "LEAVE_OPEN"

class SimulationPhase(StrEnum):
    """
    Phase of the bar currently being processed by
    the historical simulation clock.
    """

    BAR_OPEN = "BAR_OPEN"
    BAR_CLOSE = "BAR_CLOSE"