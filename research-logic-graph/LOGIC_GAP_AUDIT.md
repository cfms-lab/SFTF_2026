# SFTF cross-project research-logic audit

This audit is derived from the directed Graphify graph built from 30 development notes and
79 top-level draft sources. Edges marked `INFERRED` are hypotheses to inspect, not established
facts. The interactive graph and raw evidence remain the source of truth.

## Highest-priority logical gaps

1. **Independent validation is still the main shared bottleneck.** The graph joins the
   "Independent slicer and physical validation gap" to the "Circular TOMO validation risk".
   A result validated only against a related TOMO/SFTF computation cannot establish physical
   support accuracy. Core claims need at least one held-out slicer, exact oracle, trusted solver,
   or physical measurement that is not constructed from the same proxy.

2. **The proxy-to-trusted-solver ladder is uneven across projects.** PDN, sewer, thermal-chip,
   and injection-mould drafts name explicit downstream checks (IR solve, SWMM, exact thermal
   solve, exact mouldability oracle). Composite evidence also records a forming-shear negative
   result and a failed free-hang reference. Every application should use the same explicit
   structure: `cheap directional proxy -> trusted solver/oracle -> claim boundary`, including
   a predeclared failure or escalation rule.

3. **SFTFSoft's soft-to-hard consistency is conditional on the receiver model.** The graph
   connects the generic hard-receiver assumption to the soft-to-hard proposition, while the
   centroid-attention counterexample connects to a sharp-limit limitation. A temperature limit
   alone is therefore insufficient: the receiver construction must also converge to the same
   visibility-consistent first-hit rule as hard SFTF, or the theorem and implementation can
   converge to different objectives.

4. **Historical ranking claims need a correctness-boundary audit.** The graph contains a
   high-confidence chain from int16 overflow and exclusion of nonpositive best candidates to
   claim revision. Any table, learned weight, or ablation generated before both fixes should be
   tagged as invalidated or rerun; otherwise corrected code and legacy evidence remain mixed.

5. **Warm-start usefulness is not implied by directional structure.** UrbanTraffic records that
   a warm start may be unnecessary on easy instances, while WarehouseAGV narrows the positive
   scope to switching-delay/narrow-aisle regimes. Application papers should establish both
   problem hardness and measurable solver benefit (time, iterations, or objective at a fixed
   budget), not only proxy correlation.

## Cross-project checks to add

- Give every proxy equation an explicit node for assumptions, trusted reference, acceptance
  threshold, and out-of-domain failure condition.
- Separate correctness validation, ranking correlation, solver acceleration, and physical
  accuracy; success in one does not imply the others.
- Extend the notation crosswalk across base SFTF, SFTFCluster, SFTFSoft, and domain transfers so
  reused symbols such as support score, receiver, ground node, and direction have one declared
  meaning per manuscript.
- Treat the graph's semantic-similarity edges as investigation prompts. They expose recurring
  patterns, but they do not prove mathematical equivalence between thermal, flow, drape, and
  manufacturing proxies.

## Reproducibility boundary

The corpus intentionally excludes PDFs, DOCX files, images, bibliographies, and nested generated
assets to avoid duplicate prose and figure noise. LaTeX sources are copied verbatim into `.tex.md`
sidecars because the installed Graphify detector does not ingest `.tex` directly. Original paths
are recorded in `corpus/CORPUS_MANIFEST.md`.
