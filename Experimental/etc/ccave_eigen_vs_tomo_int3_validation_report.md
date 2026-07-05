# CcaveEigen vs TOMO_INT3 validation

- TOMO_INT3: 1 degree yaw/pitch grid, critical angle 60 deg
- CcaveEigen score 1: current eigenvalue-descending optimal candidate
- Signed score 1: same eigen axis, allowing the opposite sign because eigenvectors are axes
- Best of 3: lowest TOMO v_ss among CcaveEigen score 1..3 candidates

| Mesh | TOMO best yaw,pitch | TOMO v_ss | Ccave score1 yaw,pitch | score1 v_ss / ratio | score1 +/- v_ss / ratio | best of 3 score | best of 3 v_ss / ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| (1)Bunny_69k.ply | (265.0, 49.0) | 3201.39 | (0.0, 0.0) | 12181.8 / 3.81x | 12181.8 / 3.81x | 3 | 9892.17 / 3.09x |
| (2)manikin.ply | (193.0, 7.0) | 4657.72 | (0.0, 0.0) | 13463 / 2.89x | 11450.2 / 2.46x | 1 | 13463 / 2.89x |
| (3)dragon_100k_1.5x.ply | (162.0, 258.0) | 24447 | (0.0, 0.0) | 62165.8 / 2.54x | 62165.8 / 2.54x | 1 | 62165.8 / 2.54x |
| (4)happy_50k_0.75x.ply | (91.0, 111.0) | 2112.47 | (93.0, 356.0) | 35878.4 / 17x | 35878.4 / 17x | 2 | 24225.1 / 11.5x |
| (5)lucy_50k.ply | (182.0, 359.0) | 5036.14 | (0.0, 0.0) | 23513.4 / 4.67x | 14899 / 2.96x | 1 | 23513.4 / 4.67x |

## Conclusion

The current CcaveEigen eigenvector heuristic does not match TOMO_INT3 optimum support volume on these five meshes. Even when allowing eigenvector sign flips or selecting the best of the three eigen candidates, TOMO v_ss at the CcaveEigen orientations remains about 2.22x to 16.98x larger than the TOMO optimum.

This suggests that the current concavity eigenvalue direction is not yet a reliable standalone predictor of minimum support volume. It may still be useful as a coarse feature or candidate generator, but it needs additional terms such as overhang-normal weighting, build-plate projection, and sign-aware support asymmetry.
