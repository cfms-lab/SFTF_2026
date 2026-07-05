"""Verify the 'virtual ground node' reframing of the build-plate penalty B.

Claim: B(n) is not an ad-hoc external scalar. It equals the Rayleigh contribution
of the Support Flow Tensor augmented with a virtual ground receiver whose normal
is the build direction n and whose flow coefficient is c_i = A_i (1 + alpha h_iP).

We test two things per candidate direction:
  1. IDENTITY:  R_aug := max(0, -n^T tilde F_s n)  ==  R + B   (to float tol)
     where tilde F = face-face flow + sum_bed c_i (m_i n^T).
  2. RECOVERY:  Spearman(R_aug = R+B, v_ss) vs Spearman(R, v_ss), Spearman(B, v_ss).

No GPU needed: saved TOMO grids are reused for v_ss.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import python_src.SupportFlowTensorField.support_flow_tensor_field as sftf  # noqa: E402
from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    _adaptive_k_ray,
    _first_valid_ray_hits,
    _safe_unit,
    _sample_ray_face_ids,
    _triangle_surface_data,
    evaluate_support_flow_candidate_pool,
    load_mesh,
)
from scripts.regenerate_sftf_vs_saved_tomo_summary import (  # noqa: E402
    GRID_SUFFIX,
    MESH_DIR,
    _signed_orientation,
    _tomo_best,
)


def augmented_rayleigh_and_official(mesh, direction, surface_data):
    """Recompute face-face flow + plate (ground-node) flow for one direction and
    return (R_aug, R_official, B_official) where R_aug uses the augmented tensor."""
    n = _safe_unit(direction)
    data = surface_data
    normals, areas, centers, vertices = data.normals, data.areas, data.centers, data.vertices
    k_ray = _adaptive_k_ray(len(areas))
    overhang = np.maximum(0.0, -(normals @ n))
    source_face_ids = _sample_ray_face_ids(areas, overhang, k_ray)
    if source_face_ids.size == 0:
        return 0.0, 0.0, 0.0

    origins = centers[source_face_ids] - data.ray_epsilon * n
    ray_directions = np.tile(-n, (len(source_face_ids), 1))
    hit_map = _first_valid_ray_hits(
        mesh, origins, ray_directions, source_face_ids,
        normals, centers, n, data.height_epsilon,
    )

    # --- face-face flow (identical to the official implementation) ---
    flow = np.zeros((3, 3), dtype=np.float64)
    if hit_map:
        hit_ray_ids = np.fromiter(hit_map.keys(), dtype=np.int64, count=len(hit_map))
        target_face_ids = np.fromiter(hit_map.values(), dtype=np.int64, count=len(hit_map))
        hit_source_face_ids = source_face_ids[hit_ray_ids]
        h_ij = (centers[hit_source_face_ids] - centers[target_face_ids]) @ n
        valid_pair = h_ij > data.height_epsilon
        if np.any(valid_pair):
            source_ids = hit_source_face_ids[valid_pair]
            target_ids = target_face_ids[valid_pair]
            heights = h_ij[valid_pair]
            pair_base = overhang[source_ids] * areas[source_ids] * areas[target_ids]
            pair_weights = pair_base / (1.0 + data.alpha * heights)
            flow = np.einsum("i,ij,ik->jk", pair_weights, normals[source_ids], normals[target_ids])
    else:
        hit_ray_ids = np.empty(0, dtype=np.int64)

    # --- official build-plate scalar B (identical to the implementation) ---
    support_floor = float(np.min(vertices @ n))
    bed_source_mask = np.ones(len(source_face_ids), dtype=bool)
    bed_source_mask[hit_ray_ids] = False
    bed_source_ids = source_face_ids[bed_source_mask]
    bed_score = 0.0
    plate_flow = np.zeros((3, 3), dtype=np.float64)
    if bed_source_ids.size:
        bed_heights = centers[bed_source_ids] @ n - support_floor
        valid_bed = bed_heights > data.height_epsilon
        if np.any(valid_bed):
            sids = bed_source_ids[valid_bed]
            h = bed_heights[valid_bed]
            bed_score = float(np.sum(overhang[sids] * areas[sids] * (1.0 + data.alpha * h)))
            # --- virtual ground node: c_i * (m_i  outer  n), c_i = A_i (1 + alpha h_iP) ---
            c = areas[sids] * (1.0 + data.alpha * h)
            plate_flow = np.einsum("i,ij,k->jk", c, normals[sids], n)

    # official R from face-face only
    Fs = 0.5 * (flow + flow.T)
    R_official = max(0.0, -float(n @ Fs @ n))

    # augmented R from face-face + plate
    aug = flow + plate_flow
    aug_s = 0.5 * (aug + aug.T)
    R_aug = max(0.0, -float(n @ aug_s @ n))
    return R_aug, R_official, bed_score


def main() -> None:
    grid_paths = sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}"))
    meshes = sys.argv[1:] if len(sys.argv) > 1 else None

    print("=== Ground-node reframing verification ===\n")
    head = f"{'mesh':<14}{'max|Raug-(R+B)|':>18}{'sp(R)':>9}{'sp(B)':>9}{'sp(R+B)=Raug':>14}{'sp(J)':>9}"
    print(head)
    results = []
    for grid_path in grid_paths:
        stem = grid_path.name[: -len(GRID_SUFFIX)]
        if meshes and not any(m in stem for m in meshes):
            continue
        mesh_path = grid_path.with_name(stem + ".ply")
        data = np.load(grid_path, allow_pickle=True)
        yaw = np.asarray(data["yaw_values"], dtype=np.float64)
        pitch = np.asarray(data["pitch_values"], dtype=np.float64)
        vss_grid = np.asarray(data["vss_grid"], dtype=np.float64)

        mesh = load_mesh(str(mesh_path))
        surface_data = _triangle_surface_data(mesh)
        pool = evaluate_support_flow_candidate_pool(mesh)

        dirs = np.asarray([r[5] for r in pool], dtype=np.float64)
        R = np.asarray([r[1] for r in pool], dtype=np.float64)
        P = np.asarray([r[2] for r in pool], dtype=np.float64)
        B = np.asarray([r[3] for r in pool], dtype=np.float64)

        # identity check on a subset of candidates (recompute augmented tensor)
        rng_idx = np.linspace(0, len(pool) - 1, min(60, len(pool))).astype(int)
        max_abs_err = 0.0
        for i in rng_idx:
            R_aug, R_off, B_off = augmented_rayleigh_and_official(mesh, dirs[i], surface_data)
            # compare augmented Rayleigh against official R + B
            err = abs(R_aug - (R_off + B_off))
            max_abs_err = max(max_abs_err, err)

        signed_vss = np.asarray(
            [_signed_orientation(d, yaw, pitch, vss_grid)[1]["vss"] for d in dirs],
            dtype=np.float64,
        )

        def sp(x):
            if np.std(x) < 1e-12 or np.std(signed_vss) < 1e-12:
                return float("nan")
            return float(spearmanr(x, signed_vss)[0])

        tomo_best = _tomo_best(yaw, pitch, vss_grid)["vss"]

        def best3(scores, k=3, min_angle_deg=3.0):
            min_dot = float(np.cos(np.deg2rad(min_angle_deg)))
            picked = []
            for idx in np.argsort(scores, kind="stable"):
                d = dirs[idx]
                if any(abs(float(np.dot(d, dirs[p]))) >= min_dot for p in picked):
                    continue
                picked.append(int(idx))
                if len(picked) >= k:
                    break
            best = float(np.min(signed_vss[picked])) if picked else float("inf")
            return best / tomo_best if abs(tomo_best) > 1e-12 else float("inf")

        R_plus_B = R + B
        J = R + P + B
        short = stem.split(")")[-1][:12]
        results.append((short, max_abs_err, sp(R), sp(B), sp(R_plus_B), sp(J),
                        best3(J), best3(R_plus_B), best3(B)))
        print(f"{short:<14}{max_abs_err:>18.3e}{sp(R):>9.2f}{sp(B):>9.2f}{sp(R_plus_B):>14.2f}{sp(J):>9.2f}")

    print("\n=== best-of-3 ratio (lower=better): rank by J vs R_aug(=R+B) vs B ===")
    print(f"{'mesh':<14}{'J=R+P+B':>10}{'R_aug=R+B':>12}{'B only':>9}")
    for r in results:
        print(f"{r[0]:<14}{r[6]:>10.2f}{r[7]:>12.2f}{r[8]:>9.2f}")
    arr = np.array([[r[6], r[7], r[8]] for r in results])
    print(f"{'mean':<14}{arr[:,0].mean():>10.2f}{arr[:,1].mean():>12.2f}{arr[:,2].mean():>9.2f}")


if __name__ == "__main__":
    main()
