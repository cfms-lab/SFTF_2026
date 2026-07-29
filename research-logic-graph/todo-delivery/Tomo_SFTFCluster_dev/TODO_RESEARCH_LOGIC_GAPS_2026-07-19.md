# TODO: research logic gaps #1 and #2 — independent slicer and validation ladder

Date: 2026-07-19  
Source: cross-project Graphify research-logic audit

## Current logical boundary

The draft correctly states that the ray-free score is a screening proxy and that final part
orientation is chosen by a 48-direction CuraEngine search. Slicer-derived purity is also more
independent than reusing the geometric labels. The remaining gap is that the main ground truth is
still one slicer/configuration family, and the path from proxy to final claim is not yet expressed
as a reusable acceptance/escalation protocol.

## Tasks

- [ ] Re-run a predeclared held-out subset with PrusaSlicer 2.9.6 using the frozen console at
  `D:\__PFTF_Projects(2026)\_tools_prusa\extracted\PrusaSlicer-2.9.6\prusa-slicer-console.exe`.
- [ ] Freeze and record Cura and Prusa profiles, executable hashes, mesh hashes, orientation menu,
  support mode, material density, and G-code parsing rules.
- [ ] Compare methods under both slicers using per-shape support mass, method ranking, selected
  orientation regret, and failure/zero-range counts. Do not tune the partitioner to Prusa.
- [ ] Separate three claims in text and tables:
  1. the ray-free objective is a cheap screening score;
  2. slicer-in-the-loop search chooses final orientation/part count;
  3. slicer-derived purity checks contact-label robustness.
- [ ] Predeclare the escalation rule: if the proxy and either slicer disagree materially on a
  candidate, send it to full slicer search and exclude it from any proxy-only final decision.
- [ ] Add a limitation stating that two-slicer agreement is not physical-print validation. Either
  add a small printed-support/contact check or keep the claim at slicer level.

## Done when

- Every proxy-reported conclusion has a traceable Cura/Prusa result or is explicitly marked as
  screening-only.
- Cross-slicer disagreement and failed slices are visible per mesh; no post-hoc case removal.
- Final orientation and part-count conclusions are never derived from the ray-free score alone.
