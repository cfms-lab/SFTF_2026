# TODO: research logic gaps #1 and #3 — independent evidence and soft-first-hit consistency

Date: 2026-07-19  
Source: cross-project Graphify research-logic audit

## Current logical boundary

The Prusa transfer artifacts are useful independent slicer evidence, but they do not prove that
the centroid receiver relaxation converges to the hard visibility/first-hit receiver. The existing
counterexample shows that a laterally close non-intersected face can win as temperature sharpens.
Therefore temperature-to-zero convergence alone is insufficient for the current soft-to-hard
statement.

## Tasks for gap #3

- [ ] Amend the soft-to-hard proposition so its receiver assumptions are explicit. Do not claim
  unconditional convergence for centroid attention.
- [ ] Promote the centroid-vs-ray counterexample from an auxiliary limitation into the proof
  boundary referenced directly by the proposition.
- [ ] Implement or specify a visibility-consistent soft first-hit receiver using ordered ray
  intersections and transmittance/occlusion recursion.
- [ ] Prove or numerically verify that the receiver distribution converges to the same hard
  first-hit face under nondegenerate intersections. State tie, coplanar, grazing, and no-hit cases.
- [ ] Add regression tests for: a closer non-intersected centroid, two intersected faces at
  different depths, near ties, grazing intersections, and no receiver.
- [ ] Sweep temperature and check both forward-value convergence and usable/non-exploding
  gradients. Compare centroid attention, visibility-consistent attention, and hard SFTF.

## Tasks for gap #1

- [ ] Keep Cura/Prusa results as external objective evidence, not as proof of mathematical
  soft-to-hard consistency.
- [ ] Reproduce the Prusa validation from the frozen profile/executable hash and list all failed
  or unsliceable cases.
- [ ] Preserve the negative shape-optimization cases where surrogate improvement increases real
  Prusa support; use them to delimit the objective claim.
- [ ] If no physical print/force/contact measurement is added, use the phrase "slicer-measured
  support demand" rather than physical support accuracy.

## Done when

- The theorem, implementation, and regression tests use the same receiver definition.
- The published proof does not rely on a generic receiver assumption that the implementation
  violates.
- Slicer evidence, consistency evidence, and optimization evidence are reported as separate
  validation gates.
