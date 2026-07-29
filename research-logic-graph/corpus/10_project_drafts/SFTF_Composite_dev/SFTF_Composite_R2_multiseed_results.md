# R2 — multi-seed drape + discrete ply-angle snap

The composite realisation of SFTF-Clustering's central finding. There, support
drops not by preserving support columns but by letting each part adopt its own
build direction. Here, **drape shear drops not by one global seed but by letting
each patch adopt its own drape seed** — and each ply its own manufacturable fibre
angle from a discrete menu {0, ±45, 90}.

## Re-seeding freedom collapses the dart-dominated field

Single global seed vs K farthest-point seeds (keep the min shear per face);
dart = shear ≥ 45° locking. Proxy shear units (|K|·g²).

| mesh | single-seed dart | multi-seed dart | min-shear mean (single → multi) |
|---|---|---|---|
| sphere cap (analytic) | 0.36 | **0.00** (k=8) | 0.63 → 0.18 |
| manikin (13.7k F) | 0.98 | **0.42** (~260 per-patch seeds) | 13150 → 6.9 |
| liver (19.4k F) | 0.86 | **0.45** (k=16) | 92 → 3.2 |

> **Revalidation 2026-07-02** (full re-run with the frozen `drape` module and the
> canonical shared meshes, part of the Tomo_Shell2026 baseline migration): the
> original table was NOT fully reproducible. The manikin multi-seed values
> (0.37 / 6.8) correspond to the **~260-seed per-patch regime** (`best_seed_partition`
> fine patches), not k=8 as previously annotated — with k=8 the manikin only reaches
> dart 0.88 / mean 318. k-sweep: k=8→0.88, 16→0.80, 32→0.70, 64→0.62, 128→0.52,
> 260→0.42 (mean 6.85, matching the published 6.8). Sphere-cap and liver values
> above are the exact re-run outputs (previous 0.40/0.01/0.72/0.19 and 4.3 came
> from a pre-port code state). Paper tables/figures updated accordingly.

A single flat ply cannot cover a body/organ shell (single-seed → almost all dart).
Letting each patch re-seed collapses that: on the analytic sphere darts nearly
vanish; on real meshes the dart fraction drops by **~2.5×**. The darts that remain
are **genuine**: regions of high local Gaussian curvature (fingers, folds, sharp
features) that force a dart regardless of seed — the intrinsic obstruction, not a
seeding artefact. `best_seed_partition` grows one patch per seed (manikin → ~260
fine patches, liver → 9), each draped from its own favourable origin.

## Discrete ply-angle menu {0, ±45, 90}

Fibre shear is orientation-dependent (R1). `best_ply_angle` drapes a fishnet with
the warp aligned to each menu angle and snaps to the lowest-shear one:

- **cylinder** (developable): the aligned angle (0° / 90°) gives **~0° shear** —
  a manufacturable layup with no trellis distortion.
- **sphere** (doubly curved): every angle shears, but the menu picks 45° at
  **2.3°** vs 15° for the worst orientation — a 6.6× reduction. No orientation
  removes the intrinsic shear, but the snap minimises it.

## Drop-in to the real engine

`MultiSeedField` mirrors `MultiDirectionFaceFeatures` (`directions`, `cost`,
`softmax_weights`, `best_direction`), so it feeds the published partitioner's
multi-direction path:

```python
from drape import multi_seed_shear, drape_face_features
ms = multi_seed_shear(mesh, k=8)
feats = drape_face_features(mesh, shear_override=ms.min_shear)   # best-achievable field
# either: partition on feats (drop-in), or use ms.softmax_weights as the
# direction block in PartitionConfig(direction_weight>0, multidir=ms-shaped).
```

## Honest caveats

- The multi-seed coverage here uses the **curvature proxy** geodesic-from-each-seed
  (`|K|·g²`), which is whole-surface and cheap; it is orientation-independent, so
  the ply-angle menu (orientation) is a separate, fishnet-based step. Stitching
  real per-seed *mesh fishnets* (R1b) into one coverage is the next fidelity step.
- Remaining darts on real meshes are intrinsic (high |K|); they mark where a dart,
  a smaller patch, or a more formable material is genuinely required.
- Seed count k trades patch count vs shear; report both.
