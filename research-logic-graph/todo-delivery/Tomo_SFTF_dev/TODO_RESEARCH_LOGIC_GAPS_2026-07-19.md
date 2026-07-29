# TODO: research logic gap #1 — independent validation boundary

Date: 2026-07-19  
Source: cross-project Graphify research-logic audit

## Why this belongs here

Base SFTF/TDP is the common source of the directional proxy and therefore must define the
validation vocabulary inherited by the application papers. Agreement with TOMO or another
SFTF-derived quantity is an internal consistency check, not independent physical validation.

The current machine now has the same PrusaSlicer 2.9.6 CLI used on the remote PC:

`D:\__PFTF_Projects(2026)\_tools_prusa\extracted\PrusaSlicer-2.9.6\prusa-slicer-console.exe`

`PRUSASLICER_CONSOLE` is configured, and the executable/ZIP hashes match the frozen provenance.

## Tasks

- [ ] Add a one-page validation ladder to the manuscript/reproducibility material:
  `SFTF proxy -> TOMO internal check -> Cura/Prusa held-out slicer check -> physical check`.
- [ ] Label every reported result as one of: correctness, proxy correlation, cross-slicer
  transfer, solver acceleration, or physical accuracy. Do not let one category imply another.
- [ ] Confirm that Cura and Prusa evaluations use frozen profiles, recorded hashes, the same
  held-out meshes, and a predeclared orientation menu.
- [ ] Report per-mesh results and failures, not only aggregate correlation. Include zero-range,
  unsliceable, and first-layer-failure cases in the accounting.
- [ ] Decide the physical-validation boundary explicitly. Either add a small measured coupon
  experiment or narrow the claim to slicer-level support demand.
- [ ] Propagate the same terminology and claim boundary to SFTFCluster, SFTFSoft, and application
  manuscripts.

## Done when

- The manuscript contains a table mapping every main claim to an independent reference and a
  source artifact.
- At least two independent slicers are reproduced from frozen profiles and hashes.
- Any claim without physical measurements is explicitly written as slicer-level or solver-level,
  not physical accuracy.

## Non-goal

This task must not turn SFTF into a final solver claim. SFTF remains a candidate generator,
initializer, or proxy unless independent downstream evidence supports a narrower statement.
