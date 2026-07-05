"""Experiment G: does non-dimensionalizing the objective terms help or hurt?

J(n) = R + P + B + 0.05 S + 0.05 sigma_1 sums terms of inconsistent physical
units (area^2, area, ...) with lambda = 1, so the largest-magnitude term
dominates the raw sum. This compares the raw objective against
dimensionally-balanced variants where each term is rescaled within the candidate
pool before an equal-weight sum:

  * raw_J        -- R + P + B + 0.05 S + 0.05 sigma_1 (current)
  * minmax_equal -- equal-weight sum of min-max [0,1] scaled terms
  * zscore_equal -- equal-weight sum of standardized terms

Lower best-of-3 ratio / higher Spearman is better. If balancing the magnitudes
makes things worse, the raw objective's accuracy rides on one dominant term
(the build-plate penalty), not on a balanced combination. The rank-tuning T is
invariant to per-feature monotonic rescaling, so non-dimensionalization only
affects the raw objective -- that is what we probe here. No GPU needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_sftf_feature_correlations import _best_of_k_ratio  # noqa: E402
from scripts.cross_validate_sftf_tuning import HAPPY_NAME, build_mesh_record  # noqa: E402
from scripts.regenerate_sftf_vs_saved_tomo_summary import GRID_SUFFIX, MESH_DIR  # noqa: E402

# raw_features columns: [J, R, P, B, H, S, s1]. Build the objective from the
# components R, P, B, S, s1 (indices 1, 2, 3, 5, 6).
IDX = {"R": 1, "P": 2, "B": 3, "S": 5, "s1": 6}


def _minmax(col: np.ndarray) -> np.ndarray:
    lo, hi = float(np.min(col)), float(np.max(col))
    return (col - lo) / (hi - lo) if hi - lo > 1e-12 else np.zeros_like(col)


def _zscore(col: np.ndarray) -> np.ndarray:
    sd = float(np.std(col))
    return (col - float(np.mean(col))) / sd if sd > 1e-12 else np.zeros_like(col)


def objective_scores(raw: np.ndarray) -> dict[str, np.ndarray]:
    # Objective is J = R + P + B (nuclear/sigma_1 dropped). Test whether
    # balancing the magnitudes of these terms helps or hurts.
    R, P, B = (raw[:, IDX[k]] for k in ("R", "P", "B"))
    raw_j = R + P + B
    minmax_equal = _minmax(R) + _minmax(P) + _minmax(B)
    zscore_equal = _zscore(R) + _zscore(P) + _zscore(B)
    return {"raw_J": raw_j, "minmax_equal": minmax_equal, "zscore_equal": zscore_equal}


def main() -> None:
    grid_paths = sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}"))
    records = [build_mesh_record(p) for p in grid_paths]
    records = [r for r in records if r["mesh"] != HAPPY_NAME]
    names = [r["mesh"].split(")")[-1].replace(".ply", "")[:10] for r in records]

    variants = ["raw_J", "minmax_equal", "zscore_equal"]
    ratios = {v: [] for v in variants}
    spearmans = {v: [] for v in variants}
    for rec in records:
        scores = objective_scores(np.asarray(rec["raw_features"], dtype=np.float64))
        for v in variants:
            ratios[v].append(
                _best_of_k_ratio(scores[v], rec["directions"], rec["signed_vss"], rec["tomo_best_vss"])
            )
            spearmans[v].append(float(spearmanr(scores[v], rec["signed_vss"])[0]))

    print("=== best-of-3 ratio by objective scaling (lower is better) ===")
    print(f"{'variant':<14}" + "".join(f"{n:>11}" for n in names) + f"{'mean':>9}")
    for v in variants:
        print(f"{v:<14}" + "".join(f"{x:>11.2f}" for x in ratios[v]) + f"{np.mean(ratios[v]):>9.2f}")

    print("\n=== Spearman(score, v_ss) by objective scaling (higher is better) ===")
    print(f"{'variant':<14}" + "".join(f"{n:>11}" for n in names) + f"{'mean':>9}")
    for v in variants:
        print(f"{v:<14}" + "".join(f"{x:>11.2f}" for x in spearmans[v]) + f"{np.mean(spearmans[v]):>9.2f}")


if __name__ == "__main__":
    main()
