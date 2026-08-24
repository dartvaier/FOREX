from enum import StrEnum


class Timeframe(StrEnum):
    """Timeframes supported by the first backtest baseline."""

    M15 = "M15"
    H1 = "H1"
    H4 = "H4"


class SimulationPhase(StrEnum):
    """The observable phase of a historical bar."""

    BAR_OPEN = "BAR_OPEN"
    BAR_CLOSE = "BAR_CLOSE"
