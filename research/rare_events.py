# -*- coding: utf-8 -*-
"""
Rare-event statistics toolkit (docs/26 §24).

Reusable, tested primitives for low-sample research:

- bootstrap_ci:   percentile bootstrap 95% CI of the mean
- leave_one_year_out: mean after removing each year in turn
- without_largest_n: drop the n samples with the largest magnitude
- summarize:      exact n, mean, positive rate, median

All functions are pure; randomness is seeded for reproducibility.
Built from the H07 weekly-gap analysis (docs/26 §21/§23).
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Sequence
from typing import Any


def summarize(samples: Sequence[float]) -> dict[str, Any]:
    """Exact-n summary: mean, positive rate, median."""
    if not samples:
        return {
            "n": 0,
            "mean": None,
            "positive_rate": None,
            "median": None,
        }
    return {
        "n": len(samples),
        "mean": sum(samples) / len(samples),
        "positive_rate": sum(1 for v in samples if v > 0) / len(samples),
        "median": float(sorted(samples)[len(samples) // 2]),
    }


def bootstrap_ci(
    samples: Sequence[float],
    *,
    n_resamples: int = 10_000,
    seed: int = 42,
    ci: float = 0.95,
) -> dict[str, float] | None:
    """Percentile bootstrap CI of the mean. None if sample too small."""
    if len(samples) < 10:
        return None
    if not 0 < ci < 1:
        raise ValueError("ci must be in (0, 1)")
    if n_resamples <= 0:
        raise ValueError("n_resamples must be positive")

    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(n_resamples):
        sample = [rng.choice(samples) for _ in range(len(samples))]
        means.append(sum(sample) / len(sample))
    means.sort()

    tail = int(round((1.0 - ci) / 2.0 * n_resamples))
    return {"lo": means[tail], "hi": means[n_resamples - tail]}


def _mean_default(samples: Sequence[float]) -> float:
    return sum(samples) / len(samples)


def leave_one_year_out(
    by_year: dict[str, Sequence[float]],
    *,
    metric: Callable[[Sequence[float]], float] | None = None,
) -> dict[str, dict[str, Any]]:
    """Mean of the pooled samples after removing each year in turn."""
    fn = metric or _mean_default
    pooled_all = [v for vals in by_year.values() for v in vals]
    result: dict[str, dict[str, Any]] = {}
    for year, vals in by_year.items():
        pooled_rest = [
            v for y, vv in by_year.items() if y != year for v in vv
        ]
        result[f"without_{year}"] = {
            "n": len(pooled_rest),
            "metric": fn(pooled_rest) if pooled_rest else None,
        }
    result["all_years"] = {
        "n": len(pooled_all),
        "metric": fn(pooled_all) if pooled_all else None,
    }
    return result


def without_largest_n(
    samples: Sequence[float],
    magnitudes: Sequence[float],
    *,
    n: int = 5,
) -> list[float]:
    """Drop the n samples with the largest |magnitude| (aligned by index)."""
    if len(samples) != len(magnitudes):
        raise ValueError("samples and magnitudes must be aligned")
    if n < 0:
        raise ValueError("n must be non-negative")

    drop_indices = set(
        sorted(
            range(len(magnitudes)),
            key=lambda i: -abs(magnitudes[i]),
        )[:n]
    )
    return [v for i, v in enumerate(samples) if i not in drop_indices]
