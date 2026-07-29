# TODO: research logic gap #5 — delimit warm-start usefulness

Date: 2026-07-19  
Source: cross-project Graphify research-logic audit

## Current logical boundary

The existing result is already informative: the tested strong/cheap downstream solver erases the
initializer, and D-SFTF does not provide general iteration acceleration. This must remain a
falsification result. A follow-up should test only regimes where initialization could matter, not
relabel solver-free direct planning as universal warm-start success.

## Tasks

- [ ] Preserve the current negative result and its 450-run evidence as the default conclusion for
  easy/strong-solver instances.
- [ ] Predeclare expensive regimes before testing: larger networks, discrete coupling,
  truncated/time-budgeted solution, costly simulation-in-the-loop evaluation, or incident
  recovery with limited iterations.
- [ ] Compare D-SFTF against local, equal/fixed, random, previous-solution, and a simple demand
  imbalance initializer under identical solver and stopping rules.
- [ ] Measure initializer overhead, wall-clock time to a fixed gap, iterations to the same gap,
  objective-versus-time curves, and final objective at a fixed budget. Final convergence alone is
  insufficient.
- [ ] Use paired scenarios/seeds and report confidence intervals plus per-regime failures.
- [ ] Keep solver-free direct projection and noisy-demand robustness as separate claims with exact
  DP/UE references; do not use them as evidence of solver acceleration.
- [ ] If no expensive regime shows benefit, narrow the paper permanently to direct-plan/noisy
  observation utility and remove general warm-start wording.

## Done when

- A reader can see exactly when D-SFTF saves total compute after including initialization cost.
- Positive wording is restricted to a predeclared regime with paired baseline evidence.
- The easy-instance null/negative result remains visible and reproducible.
