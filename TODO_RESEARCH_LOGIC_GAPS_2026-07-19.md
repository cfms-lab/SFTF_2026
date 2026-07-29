# RESOLVED: research logic gap #1 - independent validation boundary

Date: 2026-07-19  
Source: cross-project Graphify research-logic audit

## Why this belongs here

Base SFTF/TDP is the common source of the directional proxy and therefore must define the
validation vocabulary inherited by the application papers. Agreement with TOMO or another
SFTF-derived quantity is an internal consistency check, not independent physical validation.

The current machine has the same PrusaSlicer 2.9.6 CLI used on the remote PC:

`D:\__PFTF_Projects(2026)\_tools_prusa\extracted\PrusaSlicer-2.9.6\prusa-slicer-console.exe`

`PRUSASLICER_CONSOLE` is configured, and the executable/ZIP hashes match the frozen provenance.

## Resolution (2026-07-19)

The project now has a machine-checkable validation ladder and claim-to-evidence
matrix. The exact evaluated Prusa profile is archived in the project with the
recorded SHA256; the audit also verifies the Cura/Prusa executable hashes, the
same 30-mesh panel, the predeclared 64-direction plus anchor/offset menu, the
73-74 successful common directions per mesh, and the complete retry/failure
accounting. The physical boundary was resolved by narrowing the manuscript:
no printed-part experiment was performed, so no physical-accuracy or
manufacturing-superiority claim is made.

Primary evidence:

- `draft/TDP_v2/VALIDATION_CLAIM_EVIDENCE.md`
- `draft/TDP_v2/generated/tdp_v2_validation_audit.json`
- `draft/TDP_v2/profiles/prusa_support_tdp_v2.ini`
- `draft/TDP_v2/experiments/tdp_v2/results/cross_slicer_results.json`
- `draft/TDP_v2/experiments/tdp_v2/results/cross_slicer_raw.jsonl`

## Completed tasks

- [x] Add a one-page validation ladder to the manuscript/reproducibility material:
  `SFTF proxy -> TOMO internal check -> Cura/Prusa held-out slicer check -> physical check`.
- [x] Label every reported result as one of: correctness, proxy correlation, cross-slicer
  transfer, solver acceleration, or physical accuracy. Do not let one category imply another.
- [x] Confirm that Cura and Prusa evaluations use frozen profiles, recorded hashes, the same
  held-out meshes, and a predeclared orientation menu.
- [x] Report per-mesh results and failures, not only aggregate correlation. Include zero-range,
  unsliceable, and first-layer-failure cases in the accounting.
- [x] Decide the physical-validation boundary explicitly. Claims are narrowed to corrected-TOMO
  and slicer-estimated support demand because no printed-part measurement was performed.
- [x] Establish the source terminology and claim boundary inherited by SFTFCluster, SFTFSoft,
  and application manuscripts. Downstream manuscript edits remain tracked in their project-local
  TODO files.

## Done evidence

- The manuscript contains a table mapping every main claim to a reference and source artifact.
- Two separately implemented slicer engines are reproduced from frozen profiles and hashes.
- Any claim without physical measurements is explicitly written as slicer-level or solver-level,
  not physical accuracy.
- `scripts/generate_tdp_v2_validation_audit.py` passes all checks and the TDP_v2 test suite passes.

## Non-goal

This task does not turn SFTF into a final solver claim. SFTF remains a candidate generator,
initializer, or proxy unless independent downstream evidence supports a narrower statement.
