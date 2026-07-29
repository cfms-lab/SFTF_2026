# Validation (B): kinematic drape shear vs Baraff cloth-drape shear

Connects the composite drape work to the `cfmsDrape2026` physics engine. The
cheap **kinematic shear field** (our `drape_field`) is validated against a
**high-fidelity Baraff–Witkin implicit cloth solver** — the composite-drape analog
of the SFTF→TOMO and TOMO→slicer validations, where an expensive reference scores
a fast proxy.

## Why these two "drapes" can be compared

Garment cloth drape (cfmsDrape) and composite layup drape share one governing
quantity: the **warp/weft trellis shear** of a woven sheet, with a locking angle
beyond which it wrinkles. Baraff's continuum **shear condition `Cs`** measures
exactly this; our kinematic γ approximates it from surface curvature and geodesic
distance. So the two engines are scored on the *same* per-element quantity.

## Extracting shear from the engine (it doesn't export `Cs`)

`cfmsdrape.Drape` exposes the flat 2D rest pattern (`set_mesh_2d`) and the
deformed 3D positions (`positions()`), not `Cs`. We recover the shear from the
in-plane deformation gradient `F` (3×2) between rest and deformed states:

    warp = F·(1,0),  weft = F·(0,1),   sin(γ) = (warp·weft)/(|warp||weft|)

This metric (`element_shear_from_deformation`) is **verified analytically**
(`test_shear_metrics.py`): pure stretch → 0 shear; a 20° affine shear → 20°
exactly; an isometric cylinder wrap (developable) → 0; a sphere wrap → shear that
grows from the pole outward. So the comparison rests on a trusted metric.

## The experiment (`scripts/compare_kinematic_vs_baraff.py`, device)

1. Drape a **flat fabric sheet** onto a doubly-curved **dome mould** with the
   implicit cloth solver (body collision + self-collision, CGS units, Y-up,
   gravity 980).
2. Recover per-element Baraff shear from (rest 2D pattern, deformed positions).
3. Run the **kinematic field** on the same mould (seed = +y).
4. Map cloth elements to nearest mould faces, keep the conforming region, and
   **correlate** the two shear fields (Spearman + Pearson), exactly as the
   SFTF/TOMO tables report.

```bash
uv run python scripts/compare_kinematic_vs_baraff.py --R 6 --grid 41 --steps 250
```

## How to read the result

- **High Spearman (≈0.8+)** would validate the cheap kinematic γ as a stand-in for
  physics-based shear — i.e. it is sound to drive partitioning with the fast field
  and reserve Baraff for spot-checks. This is the green light for using the
  kinematic field in the SFTF-Clustering composite pipeline.
- **Low / structured residual** would tell us *where* curvature+geodesic misses the
  real fabric behaviour (bending-dominated folds, contact, anisotropy) — pointing
  to BUILDSPEC R1 (a real pin-jointed-net field) or to using Baraff itself as the
  field generator (option A).

## Honest caveats

- **Garment free-hang ≠ composite forming.** The sheet drapes under gravity onto
  the mould; true layup adds forming pressure / membrane tension. The conforming
  region (where the sheet sits on the mould) is the valid comparison zone — the
  harness drops folded/hanging elements at a distance quantile.
- The kinematic γ is a curvature+geodesic *proxy*; it cannot see bending or
  contact. That is the point of the validation — to quantify the gap.
- Locking angle and material (`E`, `SE`, `BE`) are parameters; report results
  with them stated. Mesh resolution affects both fields.
- Baraff is far more expensive (implicit dynamic solve + collisions) than the
  kinematic field, so it is a *reference*, not the partitioning workhorse.

## Where this sits

This is validation step (B). If the proxy validates, the composite pipeline keeps
the fast kinematic field for partitioning (drop-in to `partition_mesh`), with
Baraff as the high-fidelity check — and option (A), using Baraff forming as a
higher-fidelity drape field, becomes a justified next step.
