# TDP v2 prospective experiment

This directory is the clean experimental boundary for a new submission to
*3D Printing and Additive Manufacturing*. It does not reinterpret the original
PiAM-era 41-mesh audit as external validation.

## Current state

- `protocol.json` fixes the scientific question, data roles, verification
  stack, endpoints, and reporting constraints.
- `manifests/holdout_manifest.json` contains 60 geometry-only, hash-ranked
  Thingi10K holdout meshes. Its SHA256 is recorded in
  `manifests/holdout_manifest.sha256`.
- Thirty of the 60 meshes were independently hash-selected for the Cura/Prusa
  panel. The `cross_slicer` column records that designation.
- No TOMO, Cura, or Prusa outcome has been computed for these meshes.
- `policy_lock.template.json` must be completed, renamed to `policy_lock.json`,
  and hashed before any external outcome is computed.

## Allowed next actions

1. Use only the existing 41 development meshes to assess SFTF v2 sample
   convergence, remeshing sensitivity, uncertainty features, and fixed
   verification budgets.
2. Calibrate Cura and Prusa support-angle conventions on synthetic coupons,
   then hash the exact slicer configuration files.
3. Fill every pending field in `policy_lock.template.json`; record the code
   commit and binary/configuration hashes.
4. Freeze `policy_lock.json` and create `policy_lock.sha256`.
5. Only then run corrected int32 TOMO on the 60 holdout meshes and the identical
   Cura/Prusa direction panel on the preselected 30 meshes.

## Prohibited actions

- Do not tune a threshold, weight, sample count, candidate count, budget,
  noninferiority margin, or tie-break after viewing any external result.
- Do not replace a failed holdout mesh based on its numerical outcome.
- Do not use legacy int16 TOMO grids in a v2 endpoint.
- Do not label Tomo_Shell or TOMO as exact Cura.
- Do not omit zero-support reference cases from the primary endpoint.
