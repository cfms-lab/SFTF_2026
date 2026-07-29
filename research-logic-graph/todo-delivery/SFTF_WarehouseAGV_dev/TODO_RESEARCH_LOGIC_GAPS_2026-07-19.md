# TODO: research logic gap #5 — verify conditional AGV warm-start value

Date: 2026-07-19  
Source: cross-project Graphify research-logic audit

## Current logical boundary

The draft correctly records that naive directionality can be catastrophic and narrows the positive
scope to narrow aisles with switching delay/return-flow structure. The remaining task is to show
that this directional field improves a real downstream optimizer or DES search after accounting
for initializer cost.

## Tasks

- [ ] Freeze the claim to the narrow-aisle, positive-switching-delay regime; retain the
  flow-through failure as a mandatory negative control.
- [ ] Define a downstream decision problem and solver explicitly: aisle direction schedule,
  reversal timing, or layout/control search evaluated by the same SimPy DES.
- [ ] Compare directed SFTF with equal/fixed, local demand imbalance, random, previous-schedule,
  and return-flow-aware heuristic initializers.
- [ ] Sweep switching delay, aisle width/capacity, return-flow fraction, OD skew, fleet size, and
  congestion. Predeclare which combinations constitute the claimed regime.
- [ ] Measure total wall-clock cost, DES calls, time/iterations to a common objective, completion
  time, throughput, deadlock/infeasibility, and final objective at a fixed budget.
- [ ] Use paired seeds and report confidence intervals and worst-case regressions, not only means.
- [ ] Verify reachability and conservation for every positive OD pair before sending a candidate
  to DES; invalid candidates count as failures.
- [ ] If SFTF does not beat a simple return-flow-aware heuristic after overhead, retain it only as
  an interpretable candidate generator and narrow the manuscript claim accordingly.

## Done when

- The claimed regime has a reproducible phase map showing where warm-start benefit appears and
  disappears.
- Benefit is measured against solver cost, not merely correlation with directional demand.
- The catastrophic naive-direction and no-switching controls remain in the reported evidence.
