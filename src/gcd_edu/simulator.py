"""Small, reproducible synthetic-learner simulator for the GCD-EDU starter prototype.

This is a toy environment for software and methodological testing, not a validated
model of human learning. Policy differences are conditional on the assumptions below.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

ACTIONS = ("explain", "practice", "retrieve", "transfer")
POLICIES = ("random", "fixed_practice", "rule_based", "gcd_adaptive")


@dataclass
class SyntheticLearner:
    """Latent synthetic learner; values are simulation parameters, not psychometrics."""

    mastery: float
    learning_rate: float
    forgetting_rate: float
    response_noise: float
    transfer_skill: float


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return float(np.clip(value, low, high))


def _make_learner(rng: np.random.Generator) -> SyntheticLearner:
    return SyntheticLearner(
        mastery=float(rng.uniform(0.15, 0.65)),
        learning_rate=float(rng.uniform(0.025, 0.075)),
        forgetting_rate=float(rng.uniform(0.005, 0.025)),
        response_noise=float(rng.uniform(0.03, 0.15)),
        transfer_skill=float(rng.uniform(0.45, 0.95)),
    )


def _action_gain(action: str, learner: SyntheticLearner) -> float:
    """Toy learning response with action effects defined by design assumptions."""
    remaining = 1.0 - learner.mastery
    multipliers = {
        "explain": 0.90,
        "practice": 0.75,
        "retrieve": 0.80,
        "transfer": 0.45 * learner.transfer_skill,
    }
    return learner.learning_rate * multipliers[action] * remaining


def _observe(learner: SyntheticLearner, rng: np.random.Generator) -> int:
    """Noisy response observation; observation noise is independent per trial."""
    probability = _clip(learner.mastery + rng.normal(0.0, learner.response_noise))
    return int(rng.random() < probability)


def _choose_action(
    policy: str,
    rng: np.random.Generator,
    observations: list[int],
) -> str:
    if policy == "random":
        return str(rng.choice(ACTIONS))
    if policy == "fixed_practice":
        return "practice"

    # Laplace-smoothed estimate. It is intentionally simple and inspectable.
    n = len(observations)
    estimated_mastery = (sum(observations) + 1.0) / (n + 2.0)
    uncertainty = 1.0 / np.sqrt(n + 2.0)

    if policy == "rule_based":
        if estimated_mastery < 0.40:
            return "explain"
        if estimated_mastery < 0.72:
            return "retrieve"
        return "transfer"

    if policy == "gcd_adaptive":
        # Uncertainty-aware diagnostic action at the start / when evidence is sparse.
        if n < 3 or uncertainty > 0.42:
            return "retrieve"
        if estimated_mastery < 0.40:
            return "explain"
        if estimated_mastery < 0.72:
            return "retrieve"
        return "transfer"

    raise ValueError(f"Unknown policy: {policy}")


def simulate_episode(
    policy: str,
    *,
    seed: int,
    steps: int = 30,
    delay_steps: int = 8,
) -> dict[str, float | int | str]:
    """Run one synthetic learner episode and return transparent outcome metrics."""
    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {POLICIES}")
    if steps < 1 or delay_steps < 0:
        raise ValueError("steps must be >= 1 and delay_steps must be >= 0")

    # Independent RNG streams make each episode deterministic for its seed.
    rng = np.random.default_rng(seed)
    learner = _make_learner(rng)
    observations: list[int] = []
    action_counts = {action: 0 for action in ACTIONS}

    for _ in range(steps):
        # Observe current performance, then use the evidence to choose the next action.
        observations.append(_observe(learner, rng))
        action = _choose_action(policy, rng, observations)
        action_counts[action] += 1
        learner.mastery = _clip(
            learner.mastery + _action_gain(action, learner) - learner.forgetting_rate
        )

    immediate = learner.mastery
    delayed = _clip(immediate - learner.forgetting_rate * delay_steps)
    transfer = _clip(delayed * learner.transfer_skill)

    result: dict[str, float | int | str] = {
        "policy": policy,
        "seed": seed,
        "steps": steps,
        "immediate_mastery": immediate,
        "delayed_retention": delayed,
        "transfer_score": transfer,
        "observed_accuracy": float(np.mean(observations)),
    }
    result.update({f"n_{action}": count for action, count in action_counts.items()})
    return result


def run_comparison(
    *,
    n_replicates: int = 200,
    steps: int = 30,
    delay_steps: int = 8,
    seed: int = 20261015,
) -> pd.DataFrame:
    """Run all policies over the same seed list and return one row per episode.

    Caveat: policies share the same seed values but consume random numbers differently.
    This is reproducible but is not a perfectly paired counterfactual design.
    """
    if n_replicates < 1:
        raise ValueError("n_replicates must be >= 1")

    seed_sequence = np.random.SeedSequence(seed)
    episode_seeds = [
        int(child.generate_state(1, dtype=np.uint32)[0])
        for child in seed_sequence.spawn(n_replicates)
    ]
    rows = []
    for policy in POLICIES:
        for episode_seed in episode_seeds:
            rows.append(
                simulate_episode(
                    policy,
                    seed=episode_seed,
                    steps=steps,
                    delay_steps=delay_steps,
                )
            )
    return pd.DataFrame(rows)


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    """Summarize means and standard deviations by policy."""
    metrics = ["immediate_mastery", "delayed_retention", "transfer_score", "observed_accuracy"]
    summary = results.groupby("policy")[metrics].agg(["mean", "std"])
    summary.columns = [f"{metric}_{stat}" for metric, stat in summary.columns]
    return summary.reset_index()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=200)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--delay-steps", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20261015)
    parser.add_argument("--output", type=Path, default=Path("results/comparison.csv"))
    args = parser.parse_args()

    results = run_comparison(
        n_replicates=args.replicates,
        steps=args.steps,
        delay_steps=args.delay_steps,
        seed=args.seed,
    )
    summary = summarize(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output, index=False)
    summary_path = args.output.with_name(f"{args.output.stem}_summary.csv")
    summary.to_csv(summary_path, index=False)
    print(summary.to_string(index=False))
    print(f"\nRaw results: {args.output}")
    print(f"Summary:     {summary_path}")


if __name__ == "__main__":
    main()
