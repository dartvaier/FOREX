"""Tests for data-mining bias significance tests (WRC / MCP)."""
import numpy as np
import pytest

from research.data_mining_tests import (
    monte_carlo_permutation,
    white_reality_check,
)


def test_wrc_single_noisy_rule_not_significant():
    # one rule, pure noise, mean ~0 -> p-value large (H0 not rejected)
    rng = np.random.default_rng(7)
    returns = {"r1": rng.normal(0, 1, 400)}
    out = white_reality_check(returns, n_bootstrap=500, seed=1)
    assert out["p_value"] > 0.05


def test_wrc_best_of_many_noise_rules_not_significant():
    # best of 40 noise rules must NOT look significant (data-mining bias)
    rng = np.random.default_rng(11)
    returns = {f"r{i}": rng.normal(0, 1, 300) for i in range(40)}
    out = white_reality_check(returns, n_bootstrap=800, seed=3)
    assert out["p_value"] > 0.05
    assert out["best_mean"] > 0  # best of 40 is positively biased


def test_wrc_strong_single_rule_significant():
    # one rule with a real edge (mean 0.5, sd 1, n=500) -> p small
    rng = np.random.default_rng(5)
    returns = {"edge": rng.normal(0.5, 1, 500), "noise": rng.normal(0, 1, 500)}
    out = white_reality_check(returns, n_bootstrap=500, seed=2)
    assert out["p_value"] < 0.05
    assert out["best_rule"] == "edge"


def test_wrc_max_dist_mean_grows_with_n_rules():
    # the null distribution of max-of-N must be higher for N=100 vs N=5
    rng = np.random.default_rng(13)
    small = {f"r{i}": rng.normal(0, 1, 400) for i in range(5)}
    big = {f"r{i}": rng.normal(0, 1, 400) for i in range(100)}
    out_small = white_reality_check(small, n_bootstrap=400, seed=9)
    out_big = white_reality_check(big, n_bootstrap=400, seed=9)
    assert out_big["max_dist_mean"] > out_small["max_dist_mean"]


def test_wrc_best_of_many_with_hidden_edge_still_found():
    # one good rule among 50 noise rules, edge large enough -> significant
    rng = np.random.default_rng(17)
    returns = {"edge": rng.normal(0.6, 1, 600)}
    for i in range(49):
        returns[f"n{i}"] = rng.normal(0, 1, 600)
    out = white_reality_check(returns, n_bootstrap=800, seed=4)
    assert out["best_rule"] == "edge"
    assert out["p_value"] < 0.05


def test_wrc_rejects_non_array_and_empty():
    with pytest.raises(ValueError):
        white_reality_check({"bad": np.zeros((2, 2))})
    with pytest.raises(ValueError):
        white_reality_check({"bad": np.array([])})


def test_mcp_noise_outputs_not_significant():
    # outputs randomly paired with market -> H0 holds
    rng = np.random.default_rng(23)
    mr = rng.normal(0, 1, 500)
    outputs = {f"r{i}": rng.choice([-1, 1], size=500) for i in range(30)}
    out = monte_carlo_permutation(outputs, mr, n_perm=600, seed=5)
    assert out["p_value"] > 0.05


def test_mcp_true_predictive_output_significant():
    # outputs that actually track the market -> significant even among noise
    rng = np.random.default_rng(29)
    signal = rng.normal(0, 1, 500)
    mr = signal + rng.normal(0, 0.5, 500)
    outputs = {"good": np.sign(signal)}
    for i in range(19):
        outputs[f"n{i}"] = rng.choice([-1, 1], size=500)
    out = monte_carlo_permutation(outputs, mr, n_perm=600, seed=6)
    assert out["p_value"] < 0.05
    assert out["best_rule"] == "good"


def test_mcp_length_mismatch_raises():
    with pytest.raises(ValueError):
        monte_carlo_permutation({"r1": np.array([1.0, -1.0])}, np.zeros(3))
