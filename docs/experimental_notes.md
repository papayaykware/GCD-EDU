# Experimental notes — starter prototype

## Scope

This simulator tests software reproducibility and illustrates how policy choices
behave under a deliberately simplified synthetic environment. It does **not**
validate a model of human learning and does not establish that GCD-EDU outperforms
the baselines in real education.

## Current policies

- `random`: random action from the action catalogue.
- `fixed_practice`: always selects practice.
- `rule_based`: chooses explanation, retrieval, or transfer from a smoothed observed-accuracy estimate.
- `gcd_adaptive`: uses the same simple estimate plus an uncertainty-triggered retrieval phase.

## Important methodological limitation

The current simulation has only one latent mastery variable, and action effects are
stipulated in code. The policy therefore operates in an environment whose dynamics
are designed by the same project. Any policy ranking is conditional on those assumptions.

The simulator uses deterministic seeds, but each policy consumes random numbers
differently. The current run is reproducible but is not a paired potential-outcomes
experiment. A future version should generate learner profiles and random streams
independently from policy execution, then evaluate all policies against shared profiles.

## Not a human-subject study

No real student data are included. Do not infer educational effectiveness, diagnostic
meaning, or individual suitability from these synthetic results.
