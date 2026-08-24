import pytest

from backtest.holding_period import (
    calculate_bars_held,
)
from backtest.models.enums import SimulationPhase


def test_exit_at_next_bar_open_counts_one_bar():
    bars_held = calculate_bars_held(
        entry_bar_index=10,
        exit_bar_index=11,
        exit_phase=SimulationPhase.BAR_OPEN,
    )

    assert bars_held == 1


def test_exit_at_next_bar_close_counts_two_bars():
    bars_held = calculate_bars_held(
        entry_bar_index=10,
        exit_bar_index=11,
        exit_phase=SimulationPhase.BAR_CLOSE,
    )

    assert bars_held == 2


def test_exit_at_same_bar_close_counts_one_bar():
    bars_held = calculate_bars_held(
        entry_bar_index=10,
        exit_bar_index=10,
        exit_phase=SimulationPhase.BAR_CLOSE,
    )

    assert bars_held == 1


def test_exit_at_same_bar_open_counts_zero_bars():
    bars_held = calculate_bars_held(
        entry_bar_index=10,
        exit_bar_index=10,
        exit_phase=SimulationPhase.BAR_OPEN,
    )

    assert bars_held == 0


def test_count_uses_observed_bar_indexes():
    # Imagine these observed bars:
    #
    # index 100 -> Friday 21:45
    # index 101 -> Sunday 22:00
    #
    # Wall-clock time contains a large weekend gap.
    # The Position was nevertheless exposed through only
    # one observed completed bar before index 101 BAR_OPEN.

    bars_held = calculate_bars_held(
        entry_bar_index=100,
        exit_bar_index=101,
        exit_phase=SimulationPhase.BAR_OPEN,
    )

    assert bars_held == 1


def test_multiple_observed_bars_are_counted():
    bars_held = calculate_bars_held(
        entry_bar_index=5,
        exit_bar_index=9,
        exit_phase=SimulationPhase.BAR_OPEN,
    )

    # Exposure:
    # bars 5, 6, 7, 8
    assert bars_held == 4


def test_exit_index_cannot_precede_entry_index():
    with pytest.raises(
        ValueError,
        match="earlier",
    ):
        calculate_bars_held(
            entry_bar_index=10,
            exit_bar_index=9,
            exit_phase=SimulationPhase.BAR_OPEN,
        )


@pytest.mark.parametrize(
    "value",
    [
        -1,
        True,
    ],
)
def test_rejects_invalid_entry_bar_index(
    value,
):
    with pytest.raises(
        ValueError,
        match="entry_bar_index",
    ):
        calculate_bars_held(
            entry_bar_index=value,
            exit_bar_index=10,
            exit_phase=SimulationPhase.BAR_OPEN,
        )


@pytest.mark.parametrize(
    "value",
    [
        -1,
        True,
    ],
)
def test_rejects_invalid_exit_bar_index(
    value,
):
    with pytest.raises(
        ValueError,
        match="exit_bar_index",
    ):
        calculate_bars_held(
            entry_bar_index=0,
            exit_bar_index=value,
            exit_phase=SimulationPhase.BAR_OPEN,
        )


def test_requires_simulation_phase():
    with pytest.raises(
        TypeError,
        match="SimulationPhase",
    ):
        calculate_bars_held(
            entry_bar_index=0,
            exit_bar_index=1,
            exit_phase="BAR_OPEN",  # type: ignore[arg-type]
        )