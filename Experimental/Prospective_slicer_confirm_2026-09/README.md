# Pre-registered prospective slicer confirmation (2026-09-16/17)

Companion data for the revision of manuscript 3DP-2026-0119 (*3D Printing and
Additive Manufacturing*), Sections 2.8 and 3.5, Table 5, Figure 8, and ESM
Tables S14–S15. Two pre-registered tests, both described in
`GATE_2026-09-16_prospective_slicer_confirmation.md` at the repository root.

| Part | Question | Sample | Verdict |
|---|---|---|---|
| 1 | Does SFTF alone beat budget-matched uniform search at B = 10 under CuraEngine 5.13 and PrusaSlicer 2.9.6? | 70 complex meshes (≥50k faces), never sliced before | **not confirmed** |
| 2 | Does a hybrid allocation (5 uniform + 5 SFTF cells) beat uniform-10? | 30 sealed holdout meshes of the original slicer panel (never combined before) | **confirmed** (Holm p < 0.001, both engines) |

## Files

| File | Content |
|---|---|
| `prereg_lock.json`, `prereg_lock_part2.json` | SHA256 hashes of protocol, manifest, scripts and inputs, written before any outcome of the respective part was computed |
| `select_prospective70.py`, `prospective_manifest.csv`, `prospective_selection_audit.json` | geometry-only selection (33 complex meshes of the earlier N001–N080 draw + 37 new meshes in the same salted-hash order) |
| `run_prospective.py` | part-1 driver: `score` → `slice` → `tomo` → `analyze` (resumable; `status` prints counts only) |
| `scores/*.npz` | SFTF v2 scores (K = 4,096 and 8,192) on 2,048 Fibonacci directions per mesh |
| `policy_cells.json` | uniform 5/10/20 cells and SFTF top-20 cells (1° yaw–pitch lattice indices), gate diagnostics, generation times |
| `slicer_raw.jsonl` | every slice (7,700 rows): engine, cell, support volume (mm³), wall time, ok/error |
| `tomo_grids/P*.npz` | dense 1°/60° TOMO grids for the 37 new meshes (the 33 N-meshes reuse `Experimental/R_term_recalib/confirm80_grids/`) |
| `prospective_results.json/.csv`, `RESULTS.md` | part-1 pre-specified analysis (per-mesh rows + summary) |
| `hybrid_policy_analysis.py`, `hybrid_policy_70_exploratory.json`, `figure8_prospective.png` | exploratory hybrid analysis on the 70 meshes (hypothesis formed after part 1) and Figure 8 |
| `part2_mixed_policy_holdout30.json` | part-2 pre-registered confirmation on the 30 holdout meshes (per-mesh rows, primary/secondary statistics, Holm) |
| `inputs_part2/` | inputs of part 2 copied from the development snapshot: the original small-budget slicer rows (`budget_slicer_raw.jsonl`) and the SFTF candidate caches of the 30 cross-slicer meshes; the holdout manifest is in `experiments/tdp_v2/manifests/` |

## Reproducing the statistics without re-slicing

All reported numbers can be recomputed from the per-mesh rows in
`prospective_results.json`, `hybrid_policy_70_exploratory.json` and
`part2_mixed_policy_holdout30.json` (bootstrap 10,000 replicates, sign-flip
permutation 100,000 replicates, seeds recorded in the files and in the GATE).

## Re-running the slicing

`run_prospective.py` was written against the development-repository layout
(`draft/src/legacy/TDP_v2/scripts` for the shared helpers, `_Cura_CLI` for the
CuraEngine wrapper, the archived PrusaSlicer profile). The helper functions it
imports (`fibonacci_directions`, `nms_basins`, `expand_around_basins`,
`uniform_cells`, `evaluate_v2_arrays`) are the ones in this repository's
`scripts/` and `python_src/`; adjust the four path constants at the top of the
script to run it here. Thingi10K meshes are not redistributed; the manifest
gives Thing IDs and SHA256 hashes.

Timings in this folder were measured while other experiments shared the
workstation and are descriptive only; the manuscript's Table 4 uses the
original holdout timing records.
