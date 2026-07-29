# R3+R1b — auto patch count scored with the real mesh fishnet

R3's automatic patch count originally used the cheap `|K|·g²` shear proxy and
returned **K\*=1 on the manikin** (the proxy's per-patch cost barely dropped, so
cutting never paid off). R3's results doc predicted that a higher-fidelity
**per-patch mesh fishnet** (R1b) would conform better, lower the realised per-patch
cost, and shift the trade-off to K\*>1. This combines them and confirms it.

## What changed

`multi_seed_shear_fishnet` builds the per-seed cost matrix by draping the **real
mesh fishnet** (R1b) from each seed and reading its trellis shear, falling back to
the `|K|·g²` proxy only on faces a seed's net does not reach. `auto_patch_count`
now accepts this cost (`ms=`) and runs the same seam-vs-realign objective on it.

## Headline result

| mesh | proxy K\* | **fishnet K\*** | fishnet drape-cost (K=1 → K=8) |
|---|---|---|---|
| manikin (13.7k F) | 1 | **5** (338 patches) | 22676 → 11381 (~50% ↓) |
| sphere cap | 6 | 4 | 3.5 → 0.69 |

Under the real fishnet the manikin's per-patch cost halves as it subdivides, so
seams now pay for themselves and the auto count chooses **5 patches** — exactly the
prediction. The proxy could not see this because it had no notion of a patch
draping (conforming) from its own origin; the fishnet does.

## Honest caveats

- **Orientation dependence.** The fishnet cost uses a *fixed* world warp direction
  per seed, so a developable surface can still show shear when that direction is
  unaligned to its rulings (e.g. a cylinder nets ~14° from a (1,0,0) warp). This is
  real R1 behaviour, not an artefact — but it means "developable → K\*=1" needs the
  per-seed **{0,±45,90} ply-angle optimisation (R2)** wired into the cost. That
  coupling (each seed drapes at its lowest-shear angle) is the natural next step.
- **Coverage.** A single seed's net covers a patch; uncovered faces fall back to
  the proxy. The cost therefore blends conformance (where the net reaches) and the
  proxy (elsewhere). More seeds / larger nets trade cost for runtime.
- Runtime: each seed runs a mesh fishnet (O(net_nodes × faces)); manikin k=8 builds
  in ~5 s.

## Use

```python
from drape import multi_seed_shear_fishnet, auto_patch_count
ms = multi_seed_shear_fishnet(mesh, k=8, net_n=8)   # real fishnet cost (R1b)
res = auto_patch_count(mesh, ms=ms)                  # seam-vs-realign on it (R3)
res.k_star, res.labels
```

This closes the loop flagged in the R3 results: with drape fidelity, the body mesh
*does* partition.
