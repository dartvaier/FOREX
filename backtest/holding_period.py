from backtest.models.enums import SimulationPhase


def calculate_bars_held(
    *,
    entry_bar_index: int,
    exit_bar_index: int,
    exit_phase: SimulationPhase,
) -> int:
    """
    Count observed historical bars during which a Position
    had market exposure.

    The calculation uses simulation bar indexes rather than
    elapsed wall-clock time. Missing historical bars therefore
    do not artificially increase bars_held.

    Baseline assumption:
        Positions are opened at BAR_OPEN.

    Exit at BAR_OPEN:
        The exit bar itself is not counted because the Position
        is closed before exposure to that bar.

    Exit at BAR_CLOSE:
        The exit bar is counted because the Position was exposed
        during that bar.
    """

    _validate_bar_index(
        "entry_bar_index",
        entry_bar_index,
    )

    _validate_bar_index(
        "exit_bar_index",
        exit_bar_index,
    )

    if not isinstance(
        exit_phase,
        SimulationPhase,
    ):
        raise TypeError(
            "exit_phase must be a SimulationPhase"
        )

    if exit_bar_index < entry_bar_index:
        raise ValueError(
            "exit_bar_index cannot be earlier "
            "than entry_bar_index"
        )

    observed_distance = (
        exit_bar_index
        - entry_bar_index
    )

    if exit_phase == SimulationPhase.BAR_OPEN:
        return observed_distance

    if exit_phase == SimulationPhase.BAR_CLOSE:
        return observed_distance + 1

    raise ValueError(
        f"unsupported SimulationPhase: {exit_phase}"
    )


def _validate_bar_index(
    name: str,
    value: int,
) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise ValueError(
            f"{name} must be a non-negative integer"
        )