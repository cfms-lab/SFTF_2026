"""Feature correlation + objective ablation for the Support Flow Tensor Field.

For every saved TOMO_CPU ``v_ss`` grid, this re-evaluates the SFTF candidate
pool (current code, so it honours SUPPORT_FLOW_USE_FALLBACK_RAY_HITS) and asks
two questions a reviewer will ask:

1. Correlation -- does each feature (J, R, P, B, H, S, sigma_1) actually predict
   the TOMO ``v_ss`` of the candidate it scores? Reported as Pearson and
   Spearman (rank) correlation per mesh and averaged.

2. Ablation -- if we rank candidates by different objective variants and keep the
   best-of-3 (3 deg angular NMS), which terms carry the result? If "bed_only"
   matches "J_raw", the asymmetric-tensor terms add nothing.

Outputs Experimental/sftf_feature_correlation_ablation.{csv,json} and a console
report. No GPU is needed (saved grids are reused).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    SUPPORT_FLOW_USE_FALLBACK_RAY_HITS,
    SUPPORT_SCORE_NUCLEAR_WEIGHT,
    SUPPORT_SCORE_SIGMA1_WEIGHT,
    evaluate_support_flow_candidate_pool,
    load_mesh,
)
from scripts.regenerate_sftf_vs_saved_tomo_summary import (  # noqa: E402
    GRID_SUFFIX,
    MESH_DIR,
    _resolve_mesh_path,
    _signed_orientation,
    _tomo_best,
)

# Features whose correlation with v_ss we report. Higher score should mean
# higher v_ss for the feature to be a useful (positively correlated) cost.
FEATURE_NAMES = ["J_raw", "R_rayleigh", "P_pair", "B_bed", "H_hit", "S_nuclear", "sigma1"]

# Objective variants used to rank candidates (lower = predicted better).
def _variant_scores(feat: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    # Ablation variant coefficients are literal (0.05), independent of the
    # objective weights, so the test stays meaningful after the nuclear/sigma_1
    # terms were dropped from J.
    rpb = feat["R_rayleigh"] + feat["P_pair"] + feat["B_bed"]
    return {
        "J = R+P+B": rpb,
        "old J (+0.05S+0.05s1)": rpb + 0.05 * feat["S_nuclear"] + 0.05 * feat["sigma1"],
        "T_rank_tuned": feat["T_tuned"],
        "bed_only (B)": feat["B_bed"],
        "tensor_only (0.05S+0.05s1)": 0.05 * feat["S_nuclear"] + 0.05 * feat["sigma1"],
        "pair_only (P)": feat["P_pair"],
    }


def _best_of_k_ratio(
    scores: np.ndarray,
    directions: np.ndarray,
    signed_vss: np.ndarray,
    tomo_best_vss: float,
    *,
    k: int = 3,
    min_angle_deg: float = 3.0,
) -> float:
    """Rank by ``scores`` (asc), keep k angularly separated picks, return the
    smallest signed v_ss among them divided by the TOMO optimum."""
    min_dot = float(np.cos(np.deg2rad(min_angle_deg)))
    order = np.argsort(scores, kind="stable")
    picked: list[int] = []
    for idx in order:
        d = directions[idx]
        if any(abs(float(np.dot(d, directions[p]))) >= min_dot for p in picked):
            continue
        picked.append(int(idx))
        if len(picked) >= k:
            break
    best = float(np.min(signed_vss[picked])) if picked else float("inf")
    return best / tomo_best_vss if abs(tomo_best_vss) > 1e-12 else float("inf")


def _safe_corr(corr_fn, score: np.ndarray, vss: np.ndarray) -> float:
    if np.std(score) < 1e-12 or np.std(vss) < 1e-12 or score.size < 3:
        return float("nan")
    return float(corr_fn(score, vss)[0])


def analyze_mesh(grid_path: Path) -> dict[str, object]:
    mesh_path = _resolve_mesh_path(grid_path.name[: -len(GRID_SUFFIX)])
    data = np.load(grid_path, allow_pickle=True)
    yaw_deg = np.asarray(data["yaw_values"], dtype=np.float64)
    pitch_deg = np.asarray(data["pitch_values"], dtype=np.float64)
    vss_grid = np.asarray(data["vss_grid"], dtype=np.float64)
    tomo_best = _tomo_best(yaw_deg, pitch_deg, vss_grid)

    mesh = load_mesh(str(mesh_path))
    pool = evaluate_support_flow_candidate_pool(mesh)

    directions = np.asarray([result[5] for result in pool], dtype=np.float64)
    T_tuned = np.asarray([result[0] for result in pool], dtype=np.float64)
    R = np.asarray([result[1] for result in pool], dtype=np.float64)
    P = np.asarray([result[2] for result in pool], dtype=np.float64)
    B = np.asarray([result[3] for result in pool], dtype=np.float64)
    H = np.asarray([result[4] for result in pool], dtype=np.float64)
    sv = [np.asarray(result[7], dtype=np.float64) for result in pool]
    S = np.asarray([float(np.sum(s)) for s in sv], dtype=np.float64)
    sigma1 = np.asarray([float(s[0]) if s.size else 0.0 for s in sv], dtype=np.float64)
    J_raw = R + P + B + SUPPORT_SCORE_NUCLEAR_WEIGHT * S + SUPPORT_SCORE_SIGMA1_WEIGHT * sigma1

    signed_vss = np.asarray(
        [_signed_orientation(d, yaw_deg, pitch_deg, vss_grid)[1]["vss"] for d in directions],
        dtype=np.float64,
    )

    feat = {
        "J_raw": J_raw, "R_rayleigh": R, "P_pair": P, "B_bed": B,
        "H_hit": H, "S_nuclear": S, "sigma1": sigma1, "T_tuned": T_tuned,
    }

    pearson = {name: _safe_corr(pearsonr, feat[name], signed_vss) for name in FEATURE_NAMES}
    spearman = {name: _safe_corr(spearmanr, feat[name], signed_vss) for name in FEATURE_NAMES}

    variants = _variant_scores(feat)
    ablation = {}
    for name, score in variants.items():
        ablation[name] = {
            "best3_ratio": _best_of_k_ratio(score, directions, signed_vss, tomo_best["vss"]),
            "spearman_vss": _safe_corr(spearmanr, score, signed_vss),
        }

    oracle_ratio = float(np.min(signed_vss)) / tomo_best["vss"] if abs(tomo_best["vss"]) > 1e-12 else float("inf")

    return {
        "mesh": mesh_path.name,
        "face_count": int(len(mesh.faces)),
        "pool_size": int(len(pool)),
        "tomo_best_vss": tomo_best["vss"],
        "oracle_best_in_pool_ratio": oracle_ratio,
        "pearson": pearson,
        "spearman": spearman,
        "ablation": ablation,
    }


def _fmt(value: float) -> str:
    return f"{value:6.2f}" if np.isfinite(value) else "   nan"


def main() -> None:
    grid_paths = sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}"))
    if not grid_paths:
        raise FileNotFoundError(f"no saved TOMO grids found in {MESH_DIR}")

    print(f"SUPPORT_FLOW_USE_FALLBACK_RAY_HITS = {SUPPORT_FLOW_USE_FALLBACK_RAY_HITS}\n", flush=True)
    rows = [analyze_mesh(path) for path in grid_paths]

    short = [r["mesh"].split(")")[-1].replace(".ply", "")[:10] for r in rows]

    print("=== Spearman rank correlation of each feature with TOMO v_ss (per candidate) ===")
    header = "feature        " + "".join(f"{s:>11}" for s in short) + f"{'mean':>9}"
    print(header)
    for name in FEATURE_NAMES:
        vals = [r["spearman"][name] for r in rows]
        mean = float(np.nanmean(vals))
        print(f"{name:<15}" + "".join(f"{_fmt(v):>11}" for v in vals) + f"{_fmt(mean):>9}")

    print("\n=== Ablation: best-of-3 ratio vs TOMO optimum (lower is better) ===")
    print("oracle best-in-pool:" + "".join(f"{_fmt(r['oracle_best_in_pool_ratio']):>11}" for r in rows))
    print("variant" + " " * 22 + "".join(f"{s:>11}" for s in short) + f"{'mean':>9}")
    variant_names = list(rows[0]["ablation"].keys())
    for name in variant_names:
        vals = [r["ablation"][name]["best3_ratio"] for r in rows]
        mean = float(np.nanmean(vals))
        print(f"{name:<29}" + "".join(f"{_fmt(v):>11}" for v in vals) + f"{_fmt(mean):>9}")

    print("\n=== Ablation: Spearman(score, v_ss) per ranking variant ===")
    for name in variant_names:
        vals = [r["ablation"][name]["spearman_vss"] for r in rows]
        mean = float(np.nanmean(vals))
        print(f"{name:<29}" + "".join(f"{_fmt(v):>11}" for v in vals) + f"{_fmt(mean):>9}")

    out_json = MESH_DIR / "sftf_feature_correlation_ablation.json"
    out_csv = MESH_DIR / "sftf_feature_correlation_ablation.csv"
    out_json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["mesh", "metric", "key", "value"])
        for r in rows:
            for name in FEATURE_NAMES:
                writer.writerow([r["mesh"], "pearson", name, r["pearson"][name]])
                writer.writerow([r["mesh"], "spearman", name, r["spearman"][name]])
            for name, entry in r["ablation"].items():
                writer.writerow([r["mesh"], "ablation_best3_ratio", name, entry["best3_ratio"]])
                writer.writerow([r["mesh"], "ablation_spearman", name, entry["spearman_vss"]])
    print(f"\nsaved: {out_csv.name}, {out_json.name}", flush=True)


if __name__ == "__main__":
    main()
