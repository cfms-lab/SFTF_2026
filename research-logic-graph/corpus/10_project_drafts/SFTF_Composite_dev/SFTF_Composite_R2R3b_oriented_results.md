# R2+R3b — per-seed ply-angle optimisation inside the fishnet cost

R3+R1b left one honest gap: the mesh-fishnet cost used a *fixed* warp direction per
seed, so a developable mould could still shear from an unaligned warp (a cylinder
netted ~14°, giving a spurious K\*=2). This wires R2's discrete **{0, ±45, 90}
ply-angle menu** into the fishnet cost: each seed drapes at its lowest-shear
*manufacturable* angle (measured in the seed's tangent plane relative to a part
reference axis). It removes the orientation dependence and snaps every patch to a
real layup angle.

## Result

| mould | fixed-warp fishnet | **angle-optimised (R2+R3b)** |
|---|---|---|
| cylinder | min_shear 0°, **K\*=2** (spurious) | min_shear **0°, K\*=1** — angles {0,90} |
| sphere cap | min_shear 5.9°, K\*=4 | min_shear **2.8°**, K\*=4 |
| manikin | K\*=5 | **K\*=2**, angles mix {0,45,90} |

- **Developable behaviour restored.** Each cylinder seed picks an aligned angle
  (0° = axial or 90° = circumferential, both geodesic) → ~0 shear → the auto count
  correctly does **not cut** (K\*=1). The fixed-warp spurious K\*=2 is gone.
- **Orientation snap halves the sphere shear** (5.9° → 2.8°) while still
  partitioning where curvature genuinely demands it.
- **Better orientation → fewer patches.** The manikin now needs **2** patches (vs 5
  at fixed warp): letting each patch choose its best manufacturable angle lowers its
  shear, so less subdivision is required. Chosen angles are a realistic {0/45/90}
  mix, attached as `field.best_angles` — directly the layup schedule.

## The full fidelity ladder, closed

    |K|·g² proxy      whole surface, orientation-blind, cheapest
    fishnet (R1)      real trellis shear on parametric moulds
    mesh fishnet (R1b) real shear on arbitrary meshes
    + multi-seed (R2)  each patch its own seed -> darts collapse
    + ply-angle (R2)   each ply its own {0,±45,90} angle
    + fishnet cost (R3b) auto patch count at real fidelity
    = R2+R3b           orientation-optimal, manufacturable, self-partitioning

## Use

```python
from drape import multi_seed_shear_fishnet, auto_patch_count
ms = multi_seed_shear_fishnet(mesh, k=8, net_n=8, optimize_angle=True,
                              ref_axis=(0, 0, 1))     # part reference axis
res = auto_patch_count(mesh, ms=ms)
res.k_star, res.labels, ms.best_angles                # patches + per-seed ply angle
```

## Caveats

- The {0,±45,90} menu is taken relative to ``ref_axis``; choosing the part's
  principal axis as the reference makes the menu meaningful (a developable aligns).
- Coverage still blends fishnet (on the net) with proxy (off it); more seeds/larger
  nets trade cost for runtime (manikin k=8 × 4 angles ≈ 22 s).
- A finer angle set would lower shear further but breaks the manufacturable-menu
  constraint — {0,±45,90} is the realistic layup choice.
