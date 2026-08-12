"""
Data-mining bias significance tests (Aronson 2007, ch. 6).

white_reality_check(rule_returns, n_bootstrap):
    Bootstrap sampling distribution of the MAX mean return among N rules
    under H0: all rules have zero expected return. Each rule's returns are
    centered (demeaned) before resampling; dates are resampled with
    replacement per rule's own length; the max of the N resampled means is
    recorded each iteration. p-value = P(max_dist >= observed max mean).

monte_carlo_permutation(rule_outputs, market_returns, n_perm):
    H0: rule outputs are randomly paired with future market changes.
    A single permutation of market returns is applied to ALL rules (same
    pairing), preserving cross-rule correlation. p-value = P(permuted max
    mean >= observed max mean).

Both answer: given we tested N rules and picked the best, is its
performance significant? This is the correction missing from plain
per-rule bootstrap CIs (AGENTS.md §12 audit).
"""

from __future__ import annotations

import numpy as np

DEFAULT_N = 1000


def _as_arrays(rule_returns: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    out = {}
    for k, v in rule_returns.items():
        arr = np.asarray(v, dtype=float)
        if arr.ndim != 1 or arr.size == 0:
            raise ValueError(f"rule {k}: expected 1-D non-empty array")
        out[k] = arr
    return out


def white_reality_check(
    rule_returns: dict[str, np.ndarray],
    *,
    n_bootstrap: int = DEFAULT_N,
    seed: int | None = None,
) -> dict:
    """WRC bootstrap. Returns p-value of the best rule vs max-of-N null."""
    rules = _as_arrays(rule_returns)
    rng = np.random.default_rng(seed)

    observed_means = {k: float(v.mean()) for k, v in rules.items()}
    best_id = max(observed_means, key=observed_means.get)
    best_mean = observed_means[best_id]

    maxes = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        resampled_means = []
        for k, v in rules.items():
            idx = rng.integers(0, v.size, size=v.size)
            resampled_means.append(float(v[idx].mean()) - observed_means[k])
        maxes[i] = max(resampled_means)

    p_value = float((maxes >= best_mean).mean())
    return {
        "best_rule": best_id,
        "best_mean": best_mean,
        "n_rules": len(rules),
        "p_value": p_value,
        "max_dist_mean": float(maxes.mean()),
        "max_dist_p95": float(np.quantile(maxes, 0.95)),
        "max_dist_p99": float(np.quantile(maxes, 0.99)),
        "significant_05": p_value < 0.05,
    }


def monte_carlo_permutation(
    rule_outputs: dict[str, np.ndarray],
    market_returns: np.ndarray,
    *,
    n_perm: int = DEFAULT_N,
    seed: int | None = None,
) -> dict:
    """MCP (Masters). Same random pairing for all rules.

    rule_outputs[k]: +1/-1 series aligned with market_returns.
    market_returns: same length; the "future market change" each day.
    """
    rules = _as_arrays(rule_outputs)
    mr = np.asarray(market_returns, dtype=float)
    rng = np.random.default_rng(seed)

    for k, v in rules.items():
        if v.size != mr.size:
            raise ValueError(f"rule {k}: length {v.size} != market {mr.size}")

    observed_means = {k: float((v * mr).mean()) for k, v in rules.items()}
    best_id = max(observed_means, key=observed_means.get)
    best_mean = observed_means[best_id]

    maxes = np.empty(n_perm)
    for i in range(n_perm):
        perm = rng.permutation(mr)  # same permutation for ALL rules
        resampled_means = [float((v * perm).mean()) for v in rules.values()]
        maxes[i] = max(resampled_means)

    p_value = float((maxes >= best_mean).mean())
    return {
        "best_rule": best_id,
        "best_mean": best_mean,
        "n_rules": len(rules),
        "p_value": p_value,
        "max_dist_mean": float(maxes.mean()),
        "max_dist_p95": float(np.quantile(maxes, 0.95)),
        "max_dist_p99": float(np.quantile(maxes, 0.99)),
        "significant_05": p_value < 0.05,
    }
