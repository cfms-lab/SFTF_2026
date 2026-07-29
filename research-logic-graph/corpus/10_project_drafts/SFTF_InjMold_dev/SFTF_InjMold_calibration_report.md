# SFTF score calibration (BUILDSPEC R8)

Best-of-3 verifier cost = side actions of the best axis among the SFTF top-3 (lower is better; oracle = 0 where a moldable axis exists). Axis pool = Fibonacci hemisphere + X/Y/Z seeds. Means are over *moldable* parts; the die-locked part is a separate recall.

> Best-of-K here is the **raw axis pool** (no local windows), so it is a conservative view of the ranking: the deployed warm-start refines within ±windows around these basins (+ AVE) and recovers narrow basins this raw view misses. Calibration quality also depends on the pool density (`--axes`).

## Tuned weights (fit on all moldable parts)

| P | R | draft | band | B |
|---|---|---|---|---|
| 2 | 1 | 0.5 | 0.3 | -0.5 |

## Optimism (in-sample vs leave-one-mesh-out)

| estimator | mean best-of-K |
|---|---|
| DEFAULT_WEIGHTS | 1.000 |
| calibrated, in-sample | 0.250 |
| calibrated, **LOMO held-out** | 0.250 |

die-lock recall (die-locked parts SFTF also flags): 1.00

## Held-out SFTF vs baselines (mean best-of-K, moldable parts)

| method | mean cost |
|---|---|
| bbox6 | 0.500 |
| pca | 0.000 |
| support_tensor | 0.000 |
| **sftf (LOMO held-out)** | 0.250 |

## Per-part held-out best-of-K

| part | held-out cost | oracle cost |
|---|---|---|
| drafted_box | 0.000 | 0.000 |
| drafted_cone | 0.000 | 0.000 |
| rect_tube | 1.000 | 0.000 |
| rect_tube_rotated | 0.000 | 0.000 |
| sealed_shell | 1000.000 | 1000.000 |