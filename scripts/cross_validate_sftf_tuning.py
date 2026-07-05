"""Leave-one-mesh-out cross-validation of the SFTF rank-tuning weights.

The paper's final rank-tuning weights (w_R ... w_sigma1) were calibrated on the
same TOMO_CPU grids that the result table reports -- i.e. training on the test
set. This script quantifies the resulting optimism.

For each held-out mesh it refits the 7 rank-tuning weights on the *other* meshes
(ridge regression of per-mesh rank-normalized v_ss on the per-mesh
rank-normalized features [J, R, P, B, H, S, sigma1]) and reports the held-out
best-of-3 ratio. The gap between in-sample and held-out is the overfit.

happy is excluded by default (its failure is candidate-generation limited, see
the feature-correlation analysis); pass --include-happy to keep it.

No GPU is needed (saved grids are reused).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    SUPPORT_SCORE_NUCLEAR_WEIGHT,
    SUPPORT_SCORE_RANK_BED_WEIGHT,
    SUPPORT_SCORE_RANK_CURRENT_WEIGHT,
    SUPPORT_SCORE_RANK_HIT_WEIGHT,
    SUPPORT_SCORE_RANK_NUCLEAR_WEIGHT,
    SUPPORT_SCORE_RANK_PAIR_WEIGHT,
    SUPPORT_SCORE_RANK_RAYLEIGH_WEIGHT,
    SUPPORT_SCORE_RANK_SIGMA1_WEIGHT,
    SUPPORT_SCORE_SIGMA1_WEIGHT,
    _rank_normalized_feature,
    evaluate_support_flow_candidate_pool,
    load_mesh,
)
from scripts.analyze_sftf_feature_correlations import _best_of_k_ratio  # noqa: E402
from scripts.regenerate_sftf_vs_saved_tomo_summary import (  # noqa: E402
    GRID_SUFFIX,
    MESH_DIR,
    _resolve_mesh_path,
    _signed_orientation,
    _tomo_best,
)

# Rank-tuning feature order, matching _tune_final_support_flow_scores.
FEATURE_LABELS = ["J", "R", "P", "B", "H", "S", "s1"]
HARDCODED_WEIGHTS = np.array(
    [
        SUPPORT_SCORE_RANK_CURRENT_WEIGHT,
        SUPPORT_SCORE_RANK_RAYLEIGH_WEIGHT,
        SUPPORT_SCORE_RANK_PAIR_WEIGHT,
        SUPPORT_SCORE_RANK_BED_WEIGHT,
        SUPPORT_SCORE_RANK_HIT_WEIGHT,
        SUPPORT_SCORE_RANK_NUCLEAR_WEIGHT,
        SUPPORT_SCORE_RANK_SIGMA1_WEIGHT,
    ],
    dtype=np.float64,
)
HAPPY_NAME = "(4)happy_50k_0.75x.ply"
RIDGE_ALPHA = 1.0


def build_mesh_record(grid_path: Path) -> dict[str, object]:
    stem = grid_path.name[: -len(GRID_SUFFIX)]
    mesh_path = _resolve_mesh_path(stem)
    data = np.load(grid_path, allow_pickle=True)
    yaw_deg = np.asarray(data["yaw_values"], dtype=np.float64)
    pitch_deg = np.asarray(data["pitch_values"], dtype=np.float64)
    vss_grid = np.asarray(data["vss_grid"], dtype=np.float64)
    tomo_best = _tomo_best(yaw_deg, pitch_deg, vss_grid)

    mesh = load_mesh(str(mesh_path))
    pool = evaluate_support_flow_candidate_pool(mesh)

    directions = np.asarray([r[5] for r in pool], dtype=np.float64)
    R = np.asarray([r[1] for r in pool], dtype=np.float64)
    P = np.asarray([r[2] for r in pool], dtype=np.float64)
    B = np.asarray([r[3] for r in pool], dtype=np.float64)
    H = np.asarray([r[4] for r in pool], dtype=np.float64)
    sv = [np.asarray(r[7], dtype=np.float64) for r in pool]
    S = np.asarray([float(np.sum(s)) for s in sv], dtype=np.float64)
    s1 = np.asarray([float(s[0]) if s.size else 0.0 for s in sv], dtype=np.float64)
    J = R + P + B + SUPPORT_SCORE_NUCLEAR_WEIGHT * S + SUPPORT_SCORE_SIGMA1_WEIGHT * s1

    raw = np.column_stack([J, R, P, B, H, S, s1])
    rank_features = np.column_stack([_rank_normalized_feature(raw[:, i]) for i in range(raw.shape[1])])
    signed_vss = np.asarray(
        [_signed_orientation(d, yaw_deg, pitch_deg, vss_grid)[1]["vss"] for d in directions],
        dtype=np.float64,
    )
    target = _rank_normalized_feature(signed_vss)

    return {
        "mesh": f"{stem}.ply",
        "rank_features": rank_features,
        "raw_features": raw,  # columns: [J, R, P, B, H, S, s1] in physical units
        "target": target,
        "directions": directions,
        "signed_vss": signed_vss,
        "tomo_best_vss": tomo_best["vss"],
        "oracle_ratio": float(np.min(signed_vss)) / tomo_best["vss"],
        "untuned_ratio": _best_of_k_ratio(J, directions, signed_vss, tomo_best["vss"]),
    }


def ridge_fit(records: list[dict[str, object]], alpha: float = RIDGE_ALPHA, cols: list[int] | None = None) -> np.ndarray:
    """Ridge weights for ranking; intercept is irrelevant to ranking so omitted.

    ``cols`` restricts the fit to a feature subset (other weights forced to 0).
    """
    cols = list(range(len(FEATURE_LABELS))) if cols is None else cols
    x = np.vstack([r["rank_features"][:, cols] for r in records])
    y = np.concatenate([r["target"] for r in records])
    gram = x.T @ x + alpha * np.eye(len(cols))
    sub = np.linalg.solve(gram, x.T @ y)
    weights = np.zeros(len(FEATURE_LABELS), dtype=np.float64)
    weights[cols] = sub
    return weights


def lomo_mean_ratio(records: list[dict[str, object]], alpha: float, cols: list[int] | None) -> float:
    ratios = []
    for held in records:
        train = [r for r in records if r["mesh"] != held["mesh"]]
        ratios.append(ratio_for_weights(held, ridge_fit(train, alpha, cols)))
    return float(np.mean(ratios))


def ratio_for_weights(record: dict[str, object], weights: np.ndarray) -> float:
    scores = record["rank_features"] @ weights
    return _best_of_k_ratio(scores, record["directions"], record["signed_vss"], record["tomo_best_vss"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-happy", action="store_true")
    parser.add_argument("--alpha", type=float, default=RIDGE_ALPHA)
    args = parser.parse_args()

    grid_paths = sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}"))
    records = [build_mesh_record(p) for p in grid_paths]
    if not args.include_happy:
        records = [r for r in records if r["mesh"] != HAPPY_NAME]
    names = [r["mesh"].split(")")[-1].replace(".ply", "")[:10] for r in records]
    print(f"meshes: {names}  (ridge alpha={args.alpha})\n", flush=True)

    insample_w = ridge_fit(records, args.alpha)

    print("=== best-of-3 ratio vs TOMO optimum (lower is better) ===")
    print(f"{'mesh':<12}{'oracle':>9}{'untuned J':>11}{'hardcoded':>11}{'in-sample':>11}{'LOMO':>9}")
    lomo_ratios, insample_ratios, hardcoded_ratios, untuned_ratios = [], [], [], []
    fold_weights = []
    for held in records:
        train = [r for r in records if r["mesh"] != held["mesh"]]
        fold_w = ridge_fit(train, args.alpha)
        fold_weights.append(fold_w)
        lomo = ratio_for_weights(held, fold_w)
        insample = ratio_for_weights(held, insample_w)
        hard = ratio_for_weights(held, HARDCODED_WEIGHTS)
        untuned = float(held["untuned_ratio"])
        lomo_ratios.append(lomo)
        insample_ratios.append(insample)
        hardcoded_ratios.append(hard)
        untuned_ratios.append(untuned)
        short = held["mesh"].split(")")[-1].replace(".ply", "")[:10]
        print(
            f"{short:<12}{held['oracle_ratio']:>9.2f}{untuned:>11.2f}"
            f"{hard:>11.2f}{insample:>11.2f}{lomo:>9.2f}"
        )
    print(
        f"{'MEAN':<12}{np.mean([r['oracle_ratio'] for r in records]):>9.2f}"
        f"{np.mean(untuned_ratios):>11.2f}{np.mean(hardcoded_ratios):>11.2f}"
        f"{np.mean(insample_ratios):>11.2f}{np.mean(lomo_ratios):>9.2f}"
    )

    print("\n=== fitted weight stability across LOMO folds (sign/magnitude drift = overfit) ===")
    print(f"{'fold held-out':<14}" + "".join(f"{lab:>9}" for lab in FEATURE_LABELS))
    for held, w in zip(records, fold_weights):
        short = held["mesh"].split(")")[-1].replace(".ply", "")[:12]
        print(f"{short:<14}" + "".join(f"{v:>9.2f}" for v in w))
    print(f"{'in-sample(all)':<14}" + "".join(f"{v:>9.2f}" for v in insample_w))
    print(f"{'hardcoded':<14}" + "".join(f"{v:>9.2f}" for v in HARDCODED_WEIGHTS))

    overfit_gap = float(np.mean(lomo_ratios) - np.mean(insample_ratios))
    print(f"\noverfit gap (mean LOMO - mean in-sample best-of-3 ratio): {overfit_gap:+.2f}")

    print("\n=== minimal-model LOMO: does a stable feature subset generalize? (mean ratio) ===")
    label_to_col = {lab: i for i, lab in enumerate(FEATURE_LABELS)}
    subsets = [["B"], ["R", "B"], ["R", "P", "B"], ["R", "B", "H"], FEATURE_LABELS]
    subset_means = {}
    for subset in subsets:
        cols = [label_to_col[lab] for lab in subset]
        mean_ratio = lomo_mean_ratio(records, args.alpha, cols)
        subset_means["+".join(subset)] = mean_ratio
        print(f"  LOMO [{'+'.join(subset):<14}] -> {mean_ratio:.2f}")
    print(f"  (reference: untuned J={np.mean(untuned_ratios):.2f}, "
          f"hardcoded 7-w={np.mean(hardcoded_ratios):.2f}, full-7 LOMO={np.mean(lomo_ratios):.2f})")

    out = {
        "meshes": [r["mesh"] for r in records],
        "alpha": args.alpha,
        "mean": {
            "oracle": float(np.mean([r["oracle_ratio"] for r in records])),
            "untuned_J": float(np.mean(untuned_ratios)),
            "hardcoded": float(np.mean(hardcoded_ratios)),
            "in_sample": float(np.mean(insample_ratios)),
            "lomo": float(np.mean(lomo_ratios)),
        },
        "per_mesh": [
            {
                "mesh": r["mesh"],
                "oracle": r["oracle_ratio"],
                "untuned_J": untuned_ratios[i],
                "hardcoded": hardcoded_ratios[i],
                "in_sample": insample_ratios[i],
                "lomo": lomo_ratios[i],
                "lomo_weights": dict(zip(FEATURE_LABELS, fold_weights[i].tolist())),
            }
            for i, r in enumerate(records)
        ],
        "in_sample_weights": dict(zip(FEATURE_LABELS, insample_w.tolist())),
        "overfit_gap": overfit_gap,
    }
    out_path = MESH_DIR / "sftf_rank_tuning_lomo_cv.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsaved: {out_path.name}", flush=True)


if __name__ == "__main__":
    main()
