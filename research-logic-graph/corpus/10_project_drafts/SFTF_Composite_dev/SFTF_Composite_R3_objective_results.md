# R3 — seam-vs-realign objective + automatic patch count

The composite port of SFTF-Clustering's ray-free support objective. There:
`S(Pi) ~= S_whole + dS_cut - dS_reorient`. Here the same decomposition with the
drape meanings:

    drape cost(Pi) = sum_patch min_seed sum_{i in patch} A_i * shear_i(seed)   (realign)
                   + w_seam * seam_length(Pi)                                   (cut)

- **realign** = each patch is a ply free to adopt its own best drape seed → its
  shear is the minimum over seeds. More/smaller patches realign better.
- **seam** = each partition boundary is a fibre-continuity cut, penalised by length.

`auto_patch_count` sweeps K spread seeds, scores each, and picks `K*` by the
normalised objective + an `alpha*K/k_max` complexity penalty.

## Headline behaviour (matches SFTF-Clustering)

| mould | curvature | drape cost vs K | **K\*** |
|---|---|---|---|
| plane | developable | flat at 0 | **1** (don't cut) |
| cylinder | developable | flat at 0 | **1** (don't cut) |
| sphere cap | doubly curved | 5.6 → 1.3 (k=8) | **5** |
| saddle | doubly curved | 7.1 → 0.7 (k=8) | **6** |

On a developable mould realigning saves nothing, so any seam is pure loss → the
objective keeps one patch. On a doubly-curved mould seams pay for themselves and
the knee of the cost curve sets the patch count. This is exactly the
SFTF-Clustering result — *cut only when reorientation (here re-seeding) freedom
actually pays*.

## Honest finding on a real body mesh

On the manikin the auto count returns **K\*=1 even up to 30 seeds** (per-patch
drape cost drops only ~11%). This is not a failure — it is the faithful
"one ply → one drape origin" cost saying that a human-form shell is *intrinsically*
too curved for a modest number of flat plies to help: each region-grown patch
still spans enough double curvature that its single best seed shears a lot. (The
per-*face* lower bound `min_shear` drops far more, but that is not realisable as
one ply per patch.) The practical readings:

- the body genuinely needs **many small patches**, a **formable material**, or
  **darts** in the high-curvature regions (consistent with R2's intrinsic darts);
- a higher-fidelity **per-patch mesh fishnet** (R1b) conforms better than the
  `|K|·g²` proxy and would lower the realised per-patch cost, likely shifting the
  trade-off toward `K*>1` — the natural next fidelity step.

So R3 cleanly demonstrates the seam-vs-realign mechanism on controlled shapes and,
on a real body, honestly flags where the cheap proxy stops being informative.

## Use

```python
from drape import auto_patch_count
res = auto_patch_count(mesh, k_max=8)
print(res.k_star, res.curve)     # chosen patch count + the full trade-off curve
labels = res.labels              # the partition at K*
```
