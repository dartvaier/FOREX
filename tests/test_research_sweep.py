"""
Unit tests for the F8 sensitivity harness helpers.

Only pure functions are tested here; actual backtests reuse the
already-tested research/runner.py run_single().
"""

import pytest

from research.runner import STRATEGY_REGISTRY, discover_strategy_class
from research.sweep import (
    STANDARD_SUBPERIODS,
    parse_range,
    parse_sweep_spec,
    parse_values,
    validate_sweep_key,
)


def test_parse_range_inclusive_end():
    assert parse_range("96:192:32") == [
        "96",
        "128",
        "160",
        "192",
    ]


def test_parse_range_float_values():
    assert parse_range("1.0:2.0:0.5") == [
        "1",
        "1.5",
        "2",
    ]


def test_parse_range_single_value():
    assert parse_range("37:37:1") == ["37"]


def test_parse_range_rejects_bad_format():
    with pytest.raises(
        ValueError,
        match="start:end:step",
    ):
        parse_range("96:192")


def test_parse_range_rejects_inverted_bounds():
    with pytest.raises(
        ValueError,
        match="start",
    ):
        parse_range("192:96:32")


def test_parse_range_rejects_non_positive_step():
    with pytest.raises(
        ValueError,
        match="step",
    ):
        parse_range("96:192:0")


def test_parse_values_explicit_list():
    assert parse_values("32,48,64") == [
        "32",
        "48",
        "64",
    ]


def test_parse_values_strips_whitespace():
    assert parse_values(" 32 , 48 ") == ["32", "48"]


def test_parse_values_rejects_empty():
    with pytest.raises(
        ValueError,
        match="v1,v2,v3",
    ):
        parse_values("")


def test_parse_sweep_spec_range_mode():
    key, values = parse_sweep_spec(
        "lookback=96:192:32",
        mode="range",
    )

    assert key == "lookback"
    assert values == ["96", "128", "160", "192"]


def test_parse_sweep_spec_values_mode():
    key, values = parse_sweep_spec(
        "lookback=32,48,64",
        mode="values",
    )

    assert key == "lookback"
    assert values == ["32", "48", "64"]


def test_parse_sweep_spec_rejects_missing_equals():
    with pytest.raises(
        ValueError,
        match="key=",
    ):
        parse_sweep_spec(
            "lookback",
            mode="range",
        )


def test_parse_sweep_spec_rejects_empty_key():
    with pytest.raises(
        ValueError,
        match="key",
    ):
        parse_sweep_spec(
            "=96:192:32",
            mode="range",
        )


def test_validate_sweep_key_accepts_strategy_param():
    strategy_class = discover_strategy_class(
        STRATEGY_REGISTRY["time_series_momentum"]
    )

    validate_sweep_key(
        strategy_class,
        "lookback",
    )


def test_validate_sweep_key_rejects_unknown_param():
    strategy_class = discover_strategy_class(
        STRATEGY_REGISTRY["time_series_momentum"]
    )

    with pytest.raises(
        ValueError,
        match="unknown parameter",
    ):
        validate_sweep_key(
            strategy_class,
            "magic_number",
        )


def test_standard_subperiods_are_four_contiguous_windows():
    assert len(STANDARD_SUBPERIODS) == 4

    for label, date_from, date_to in STANDARD_SUBPERIODS:
        assert label
        assert date_from < date_to

    # contiguity: end of one window == start of the next
    for previous, current in zip(
        STANDARD_SUBPERIODS,
        STANDARD_SUBPERIODS[1:],
    ):
        assert previous[2] == current[1]
