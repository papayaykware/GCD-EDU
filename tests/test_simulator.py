import pandas as pd
import pytest

from gcd_edu.simulator import POLICIES, run_comparison, simulate_episode, summarize


def test_episode_is_reproducible():
    a = simulate_episode("gcd_adaptive", seed=123, steps=10)
    b = simulate_episode("gcd_adaptive", seed=123, steps=10)
    assert a == b


def test_episode_metrics_are_bounded():
    result = simulate_episode("rule_based", seed=123, steps=12)
    for key in ("immediate_mastery", "delayed_retention", "transfer_score", "observed_accuracy"):
        assert 0.0 <= result[key] <= 1.0


def test_comparison_contains_all_policies():
    results = run_comparison(n_replicates=3, steps=5, seed=7)
    assert set(results["policy"]) == set(POLICIES)
    assert len(results) == 3 * len(POLICIES)


def test_summary_has_one_row_per_policy():
    results = run_comparison(n_replicates=3, steps=5, seed=7)
    summary = summarize(results)
    assert len(summary) == len(POLICIES)
    assert "delayed_retention_mean" in summary.columns


def test_invalid_policy_raises():
    with pytest.raises(ValueError):
        simulate_episode("not-a-policy", seed=1)
