# R5 — drape partition benchmark (baselines vs drape-aware)

Mirrors the SFTF-Clustering validation protocol: four methods on a difficulty
ladder, scored with composite-manufacturing metrics. Lower lock_area / dart_frac /
seam = better; higher purity = better. Methods produce k=6 patches; realised shear
is scored on a shared seed pool (apples-to-apples). `python -m drape.bench`.

Methods: **coordinate** (k-medoids on face centres), **axis_bsp** (slabs along
longest axis), **curvature** (k-medoids on |K|), **sftf_drape** (feature-fusion
k-medoids on [centres | shear, |K|]).

## Analytic ladder (k=6)

| part | tier | method | lock_area | dart | purity | seam |
|---|---|---|---|---|---|---|
| cylinder | T0 | coordinate / axis / curvature / sftf | 0.000 | 0.000 | 1.000 | — |
| cone | T0 | (all) | 0.000 | 0.000 | 1.000 | — |
| sphere_cap | T2 | coordinate | **0.042** | 0.027 | 0.973 | 12 |
| sphere_cap | T2 | sftf_drape | 0.152 | 0.113 | 0.887 | 27 |
| sphere_cap | T2 | axis_bsp / curvature | 0.26 / 0.53 | — | 0.82 / 0.91 | — |
| bump_plane | T2 | coordinate | **0.041** | 0.035 | 0.655 | 28 |
| bump_plane | T2 | sftf_drape | 0.055 | 0.049 | 0.641 | 36 |

## Real meshes (k=6)

| mesh | method | lock_area | dart | purity | seam |
|---|---|---|---|---|---|
| manikin | coordinate | 0.045 | 0.388 | 0.664 | 684 |
| manikin | axis_bsp | 0.045 | 0.388 | **0.712** | 749 |
| manikin | sftf_drape | 0.045 | 0.388 | 0.706 | 758 |
| liver | coordinate | **0.362** | 0.663 | 0.711 | 2173 |
| liver | sftf_drape | 0.389 | 0.687 | 0.734 | 2535 |
| liver | curvature | 0.696 | 0.907 | **0.907** | 4243 |

**Aggregate (manikin+liver):** coordinate lock_area 0.204 / purity 0.688;
sftf_drape 0.217 / 0.720; axis 0.289 / 0.765; curvature 0.371 / 0.790.

## Honest reading (this is the SFTF-Clustering finding, reproduced)

- **Spatial compactness is a strong baseline for raw shear.** Minimising per-patch
  single-seed shear rewards compact patches (small geodesic spread → low shear),
  which is exactly what `coordinate` k-medoids optimises. So on *raw* lock_area,
  coordinate is hard to beat and `sftf_drape` is competitive, not dominant.
- **The drape/curvature-aware methods improve regime purity**, i.e. they produce
  more role-coherent patches (developable vs shear vs dart kept apart):
  sftf_drape 0.720 vs coordinate 0.688 in aggregate; curvature highest purity but
  worst shear (it groups by |K| at the expense of drapeable patches).
- This is precisely the SFTF-Clustering result: the partitioner's value is
  **interpretable, role-coherent patches and the re-seeding/realign mechanism**
  (R2/R3), *not* beating a compactness baseline on raw cost. On uniform-curvature
  primitives (sphere) the drape features are nearly constant, so they add little;
  the discrimination needs spatially-varying geometry (bump_plane, real meshes).
- `lock_area`/`dart` are partition-insensitive on manikin (0.045/0.388 for all):
  the wrinkle-risk is set by intrinsic curvature, not by how you cut — consistent
  with R2/R3 (intrinsic darts). Purity is the discriminating metric there, as in
  the paper.

## Use

```bash
python -m drape.bench                       # analytic ladder
python -m drape.bench --folder path/to/real_meshes --k 6 --out report.md
```

The harness is the deliverable: it encodes the protocol + metrics + baselines, so
new methods (e.g. the pure-flow `drape_region`, or fishnet-fidelity shear) and new
meshes plug straight in.
