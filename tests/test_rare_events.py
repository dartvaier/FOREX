# -*- coding: utf-8 -*-
"""Tests for the rare-event statistics toolkit (docs/26 §24)."""

import pytest

from research.rare_events import (
    bootstrap_ci,
    leave_one_year_out,
    summarize,
    without_largest_n,
)


def test_summarize_exact_small_sample():
    s = summarize([1.0, 2.0, 3.0])
    assert s["n"] == 3
    assert s["mean"] == pytest.approx(2.0)
    assert s["positive_rate"] == pytest.approx(1.0)
    assert s["median"] == pytest.approx(2.0)


def test_summarize_empty():
    s = summarize([])
    assert s["n"] == 0
    assert s["mean"] is None
    assert s["positive_rate"] is None


def test_summarize_positive_rate_mixed():
    s = summarize([1.0, -2.0, 3.0, -4.0])
    assert s["positive_rate"] == pytest.approx(0.5)


def test_bootstrap_ci_reproducible_seed():
    a = bootstrap_ci([0.01] * 300 + [-0.01] * 100)
    b = bootstrap_ci([0.01] * 300 + [-0.01] * 100)
    assert a == b  # same seed -> identical resamples


def test_bootstrap_ci_small_sample_returns_none():
    assert bootstrap_ci([1.0, 2.0, 3.0, 4.0]) is None


def test_bootstrap_ci_validates_args():
    with pytest.raises(ValueError):
        bootstrap_ci([1.0] * 10, ci=1.5)
    with pytest.raises(ValueError):
        bootstrap_ci([1.0] * 10, n_resamples=0)


def test_bootstrap_ci_contains_true_mean():
    samples = [0.001] * 500 + [-0.0005] * 500
    ci = bootstrap_ci(samples, n_resamples=2000)
    assert ci["lo"] <= 0.00025 <= ci["hi"]


def test_leave_one_year_out_pooled_mean():
    by_year = {
        "2015": [1.0, 2.0],
        "2016": [4.0],
        "2017": [5.0, 6.0, 7.0],
    }
    result = leave_one_year_out(by_year)
    # all years pooled: (1+2+4+5+6+7)/6 = 25/6
    assert result["all_years"]["n"] == 6
    assert result["all_years"]["metric"] == pytest.approx(25 / 6)
    # without 2016: (1+2+5+6+7)/5 = 21/5
    assert result["without_2016"]["n"] == 5
    assert result["without_2016"]["metric"] == pytest.approx(21 / 5)


def test_leave_one_year_out_custom_metric():
    result = leave_one_year_out(
        {"2015": [1.0, 3.0], "2016": [5.0]},
        metric=max,
    )
    assert result["without_2015"]["metric"] == 5.0


def test_without_largest_n_drops_top_by_magnitude():
    samples = [0.1, 0.2, 0.3, 0.4]
    magnitudes = [-9.0, 1.0, 1.0, 1.0]  # index 0 has the largest |mag|
    rest = without_largest_n(samples, magnitudes, n=1)
    assert rest == [0.2, 0.3, 0.4]


def test_without_largest_n_n_smaller_than_sample():
    rest = without_largest_n([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], n=2)
    assert rest == [1.0]


def test_without_largest_n_validates_alignment():
    with pytest.raises(ValueError):
        without_largest_n([1.0, 2.0], [1.0], n=1)
    with pytest.raises(ValueError):
        without_largest_n([1.0], [1.0], n=-1)
