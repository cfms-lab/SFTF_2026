# R7 — validating the kinematic shear field against the Baraff cloth solver

R7 closes the loop the validation design (B) set up: score the kinematic shear
field against a **high-fidelity Baraff–Witkin implicit cloth solve** (`cfmsDrape`),
the way the SFTF→TOMO and TOMO→slicer tables grade a fast proxy with an expensive
reference. The headline is an **honest negative**: under gravity drape, the cloth
engine does not produce a clean *forming* shear field, so neither the cheap
`|K|·g²` proxy nor the real pin-jointed-net (fishnet) field validates against it —
and the fishnet does **not** beat the proxy. The value delivered is the integration
itself plus a precise diagnosis of *why* free-hang is the wrong reference.

## What was unblocked

The engine lives in a separate, actively rebuilt repo. It is now **vendored
on-device**: `scripts/sync_cfmsdrape.py` copies the ctypes binding + `cfmsDrape.dll`
into `python/src/` (re-run after any rebuild), and the binding loads against the
local 3.12 venv. `scripts/compare_kinematic_vs_baraff.py` runs the full comparison
against the real `SDECore` implicit solver, with `--mould {dome,bowl}`,
`--field {proxy,fishnet}`, a conforming-region filter, and a `--sweep` table.

## Experiment

A flat fabric sheet drapes under gravity onto a spherical-cap mould (CGS, Y-up,
g = 980). Per-element warp/weft shear is recovered from the deformed state via the
in-plane deformation gradient (`shear_metrics`, analytically verified: stretch→0,
20° affine→20°, cylinder→0, sphere→grows). The kinematic field is computed on the
same mould from the apex seed and correlated over the conforming region.

## Result — gravity drape is not a forming-shear reference

Per-mould, across cap half-angle, fixed material (E=5×10⁴, SE=2×10⁴):

| mould | Baraff shear (mean) | proxy Spearman | fishnet Spearman |
|---|---|---|---|
| dome (convex, free-hang) | ~5° | −0.03 … 0.05 | −0.03 … 0.03 |
| bowl (concave, gather)   | ~40° | −0.02 … 0.33 | 0.02 … 0.26 |

> **Revalidation 2026-07-02** (re-vendored cfmsDrape 0.2, caps 35/55/75/90°, fixed
> default material): ranges updated to the current engine's outputs; the qualitative
> conclusion (dome ≈ 0, bowl weak and inconsistent, strongest only at the 90° crumple)
> is unchanged. NOTE: the forming-pressure experiment below (`form_pressure_demo.py`,
> Spearman 0.1–0.2, ~19° shear, Fig6 4-fold bins) could NOT be re-verified — the
> current upstream cfmsDrape build no longer exports the external-force API
> (`set_node_forces` / `SDE_SetExternalForces`). Restore it in cfmsDrape2026_dev and
> re-run before submission.
>
> **Update 2026-07-05** (re-vendored cfmsDrape 0.2, `1563cf22…`): the external-force
> API is back (`cfms_set_node_forces` confirmed present in the DLL), so the forming
> experiment was **re-run** via the new `scripts/form_trellis_analysis.py` (same
> mesh/material/pressure as `form_pressure_demo.py`). Current numbers: residual
> ~0.9 cm, shear mean ~19° / p90 ~34°, **Spearman ≈ 0** (proxy/fishnet −0.03…0.01,
> OpenMP jitter ±0.03), Fig6 4-fold bins **16.1 / 17.8 / 20.0 / 20.2°**. The earlier
> 0.1–0.2 / 6.8→9.6° values (an older build) are superseded; the honest-negative
> conclusion is unchanged and slightly stronger. Paper (`main.tex`/`main_en.tex`
> forming text + Fig6) and `make_paper_figures.py::fig_trellis` updated accordingly.

> **Revalidation 2026-07-06 (engine audit — `e294f00`).** The engine used for all
> numbers above predated commit `c2ee047`, which fixed an **identically-zero Provot
> shear term** (`_dCv_dxm` used `dwvx - dwvx`), a misplaced bending-Jacobian block,
> and a half-initialized first-frame velocity buffer; separately, local `main` and
> `origin/main` had diverged (typo fix on one side, the `set_node_forces` restoration
> on the other), which also explains the untraceable `1563cf22` hash cited above.
> Both lines were merged (`e294f00`), the DLL rebuilt and re-vendored, and both
> experiments re-run:
>
> - **Free-hang sweep** (`_r7_sweep_table_engine_e294f00.md`, same config as
>   `_r7_sweep_table.md`): quantitatively different — dome mean shear roughly halves
>   (3.7→1.8° base material; the corrected shear force resists spurious shear),
>   stiff-bowl p90 drops 68→45° — but qualitatively unchanged: dome Spearman
>   0.007–0.10, bowl 0.11–0.19. Proxy-field material sweep:
>   `_r7_sweep_table_proxy_e294f00.md` (dome −0.03…0.06, bowl 0.25…0.39).
> - **Cap-angle sweep** (paper Table tab:r7 design: caps 35/55/75/90°, fixed base
>   material, both fields; `_r7_capsweep_e294f00.md`): dome mean 1.8–2.6° (was ~5°),
>   proxy −0.03…0.03, fishnet −0.01…0.04; bowl mean 35–44°, proxy −0.03…0.41,
>   fishnet 0.00…0.27 (rising with cap, the 90° crumple as before). Paper table and
>   free-hang narrative updated to these values.
> - **Forming** (`form_trellis_analysis.py`): residual 0.835 cm, shear mean 18.6° /
>   p90 35.8°, proxy Spearman **0.031**, fishnet **0.046** — still ≈ 0. Fig6 4-fold
>   bins now **16.6 / 18.4 / 17.8 / 20** (endpoint contrast warp/weft→±45° holds at
>   ~3°, but the middle bins are no longer monotonic).
>
> **Conclusion: the honest negative survives the engine fix** — it is physics
> (wrinkle-dominated forming shear + angular structure the radial proxy cannot see),
> not an engine artifact. HOWEVER the paper's concrete numbers (free-hang table,
> forming stats, Fig6 bins and the monotonic-bins wording) came from the buggy build
> and must be updated to the `e294f00` values before submission.

- **Convex dome → the sheet avoids shear.** A flat sheet on a convex dome drapes
  developably (cone/cylinder skirt) and slides; Baraff shear stays ~5° and
  structureless, so there is nothing for any curvature-driven field to track →
  Spearman ≈ 0. This is the pre-registered caveat made concrete: **free-hang ≠
  forming**.
- **Concave bowl → the sheet piles, it does not conform.** Dropped into a bowl the
  sheet bunches at the lowest point (~40° mean shear *regardless of cap size*, even
  at a gentle 35° cap) — a crumple, not a forming gather. Correlation is weak and
  inconsistent (mostly ≈0, rising to ~0.29 only at the largest caps where a gross
  radial trend coincides).
- **The fishnet does not beat the proxy.** The real R1b pin-jointed-net field tracks
  Baraff no better than `|K|·g²` (both near zero); on the full-90° bowl the net even
  saturates near the locking angle in its outer rings. An earlier single-config
  "Spearman ≈ 0.4" was this 90° crumple — not a robust signal, and it does not
  survive the cap-angle sweep.
- **Self-collision is unstable.** Enabling cloth self-collision faults the engine
  (`access violation`) on every cap mesh tried — so the pile-up/fold cannot be
  cleaned up from the cloth side. Reported upstream to the cfmsDrape project.

A pinned-boundary "wrap" variant (corners pinned, membrane tension over a convex
dome) was also tried: it is dominated by corner-to-corner stretch (~55° mean) and
likewise gives weak, sign-unstable correlation (proxy −0.23…0.18, fishnet
0.06…0.11). No gravity configuration available in this engine produces clean
forced conformance.

## Reading it honestly

The kinematic field is **not** validated by free-hang cloth drape — but the right
conclusion is about the *reference*, not the field. γ = |K|·g² (and the fishnet)
predict the shear of a sheet **forced to conform** to the surface (the forming /
vacuum condition). Gravity drape lets the sheet escape that condition — sliding,
piling, or stretching between pins — so the two quantities are simply not the same
boundary-value problem, and the correlation is near zero by construction.

The fishnet field therefore keeps its standing on the grounds it already had: it is
inextensible to faceting precision and matches analytic GT (developable→0, sphere→
grows) in its own acceptance tests — not because gravity cloth agrees with it.

Consequences (both already on the roadmap):

1. **A forming boundary condition is required for a meaningful validation.** The
   comparison needs forced conformance (membrane pressure / vacuum / a forming
   tool), not free hang. This is exactly the motivation for option (A): use a
   Baraff **forming** solve — not free-hang drape — as the higher-fidelity field.
2. **For the partitioning pipeline, prefer the fishnet field on geometric grounds.**
   R7 gives no reason to switch back to the proxy; it gives a reason to source a
   forming reference before making any quantitative fidelity claim.

## Option (A): a forming pressure was added to the engine

The cfmsDrape engine had **no pressure/forming force** — only gravity and rigid
colliders. So a distributed per-node external force was added to the SDECore
implicit solver and exposed end-to-end (a true CGS force added to the RHS each step
exactly like gravity, off by default so existing behaviour is byte-identical):

    SDEPCGSolver::pExternalForce + AssembleForce   (Sdll/.../SDESparseMatrix.cpp)
    SDE_SetExternalForces                          (Sdll/.../SDEVC.cpp/.h)
    cfms_set_node_forces                           (src/cfms_api.cpp/.h)
    Drape.set_node_forces(forces)                  (cfmsdrape/__init__.py)

The DLL was rebuilt and re-vendored (`scripts/sync_cfmsdrape.py`); the new API loads
and **demonstrably drives the cloth** (`scripts/form_pressure_demo.py` applies a
vacuum/diaphragm load — each node pushed along the local mould normal).

### Forming-process tuning (option A, step 2)

The pressure load was then tuned into a **working forming process** and used to test
the validation properly:

- **Clean conformance achieved.** The fix was a **radial vacuum** (push each
  still-outside node toward the sphere centre — pure radial, no tangential scramble —
  so collision seats it on the dome) with the sheet sized to the cap footprint, an
  apex pin, a quasi-static pressure ramp, and a woven material (stiff stretch /
  compliant shear). Residual dropped from ~12 cm (naive normal-pressure) to **~0.9 cm**
  with physical trellis shear (mean ~19°, p90 ~34°). `scripts/form_trellis_analysis.py`
  (was `form_pressure_demo.py`; the analysis script adds the Fig6 binning).
- **There is essentially no element-wise correlation.** Even with clean conformance the
  Baraff forming shear shows **≈0** Spearman with the kinematic γ proxy or the
  single-net fishnet (−0.03…0.01, run-to-run jitter ±0.03 from OpenMP reduction order).
  Two physical reasons, both confirmed by decomposition:
  1. **4-fold trellis angular pattern.** Sphere trellis shear is lower along the warp/weft
     axes and higher on the ±45° diagonals (Baraff mean rises 16→20° with |sin 2φ|; the
     whole conformed cap is floored ~16° by wrinkling, so the 4-fold contrast is mild),
     while γ = |K|·g² is radially symmetric — it cannot see the angular structure.
  2. **Wrinkling/buckling dominates.** Almost the whole conformed cap is at high shear
     (mean ~19°, many elements driven to ~90° locking) with very little clean
     sub-locking core, so the field is process/wrinkle-noisy rather than the smooth
     monotonic profile the proxy predicts.

**Conclusion.** Forming does **not** rescue a strong quantitative validation: the
cheap kinematic field is a weak element-wise predictor of physics-based forming shear,
and the fishnet does not beat the proxy. This is consistent with R5's honest finding —
the field's value is **regime-coherence + the re-seeding mechanism for partitioning**,
not element-wise shear prediction. The delivered pressure API + working forming rig
remain useful infrastructure (e.g. for generating forming ground truth, or a future
angular/trellis-aware field); chasing a higher correlation by further tuning the
forming process would risk overfitting the experiment rather than revealing signal.

## Use

```bash
uv run python scripts/sync_cfmsdrape.py --verify           # vendor the engine
uv run python scripts/compare_kinematic_vs_baraff.py --mould bowl --field fishnet
uv run python scripts/compare_kinematic_vs_baraff.py --sweep --out draft/_r7_sweep_table.md
```

## Caveats

- **Gravity ≠ layup pressure.** The conforming region is the valid zone; even so,
  gravity gather/pile is not forming membrane tension — that is the whole finding.
- **Recovered shear, not engine `Cs`.** cfmsDrape does not export its shear
  condition; warp/weft shear is reconstructed from (rest 2D, deformed 3D) with an
  analytically verified metric.
- **Self-collision off** (it crashes the engine), so concave gathers self-
  interpenetrate — a second reason the bowl reference is unclean.
- The negative result is specific to *free-hang gravity drape*; it does not refute
  the kinematic field, it refutes this choice of reference experiment.
