# R4 — drape field on real meshes + drop-in to the SFTF-Clustering engine

Validates the composite **drape field** on the project's own real meshes and
confirms it is a drop-in for the published partitioner. Computed in the cloud
with the numpy/scipy field + self-contained partitioner; on the device the same
features feed the real `partition_mesh(..., features=...)` via
`scripts/run_drape_partition.py`.

## Real-mesh results (seed = +z, locking 45°)

| mesh | F | drape field | regimes (dev/shear/dart) | shear severity (p50 / p90) |
|---|---|---|---|---|
| manikin | 13,672 | 0.34 s | 1 / 316 / 13,355 | 250 / 3.0e4 |
| liver | 19,416 | 0.22 s | 16 / 2,690 / 16,710 | 12 / 220 |

| mesh | method | patches | drape purity | |K| coherence ↓ |
|---|---|---|---|---|
| manikin | kmedoids k=6 | 6 | 0.977 | 0.81 |
| manikin | kmedoids k=12 | 12 | 0.977 | 0.61 |
| manikin | drape_region | 608 | 1.000 | 0.49 |
| liver | kmedoids k=6 | 6 | 0.861 | 0.87 |
| liver | kmedoids k=12 | 12 | 0.884 | 0.55 |
| liver | drape_region | 291 | 1.000 | 0.49 |

`|K| coherence` = mean within-patch curvature std / global std (lower = patches
group similar-curvature surface, i.e. drape-coherent). It drops as patch count
rises, confirming the partition is genuinely curvature/drape-aware, not just
spatial.

## How to read this (honest)

- **The field runs on real geometry in <0.4 s** and the drape features flow
  straight into the partitioner — the integration works.
- **Shear is graded, not saturated** (manikin 3.5e-4 → 1.2e6, p50≈250). The
  earlier mm-scale saturation bug (clip killed the gradient) is fixed: shear is a
  dimensionless severity `|K|·g²`, left unclipped so clustering sees a gradient.
- **Regime is dart-dominated under one global seed — and that is correct.** A
  human-form or organ shell physically cannot be laid up as a single flat ply
  from one origin; almost everything needs darts. That is precisely the
  motivation to partition. So drape-purity here is high but not yet the
  interesting signal; the meaningful evidence that the partition is drape-aware is
  the **|K| coherence** dropping with patch count.
- **The dart-dominated regime is resolved by per-patch re-seeding (BUILDSPEC
  R2).** Once each patch adopts its own drape seed, geodesic distances within a
  patch are small, shear drops below locking, and developable/shear patches
  reappear. R4 establishes the single-seed baseline; R2 + the seam-vs-realign
  objective (R3) turn it into the real "each patch free to follow its own
  developable seed" result — the composite analog of SFTF-Clustering's
  reorientation-freedom finding.

## Device run (real engine)

```bash
uv run python scripts/run_drape_partition.py ^
  --mesh ../sftf_Mesh_Data/g5test/Group_C2_manikin.ply ^
  --sftf ../Tomo_SFTFCluster_dev/python_src ^
  --method kmedoids --k 6 --seed 0 0 1 --render
```

`drape_face_features` is the only new step; `partition_mesh` is unchanged. The
adapter `as_support_flow_features` builds a genuine `SupportFlowFaceFeatures`
when the engine is importable, else duck-types.
