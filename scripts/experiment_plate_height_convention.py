"""Which build-plate (ground-node) height convention best predicts TOMO v_ss?

Face-face flow uses height ATTENUATION 1/(1+a*h). The current build-plate term B
uses height AMPLIFICATION (1+a*h). This script tests, per candidate direction,
several plate-cost conventions and asks which one (alone, and combined with the
face-face Rayleigh R) best tracks the saved TOMO v_ss.

Plate-cost variants (summed over bed faces = overhang sources with no face hit):
  B_amp  = sum O_i A_i (1 + a h)         # current, amplification, linear in O
  B_flat = sum O_i A_i                   # no height dependence
  B_att  = sum O_i A_i / (1 + a h)       # attenuation, mirrors face-face height law
  B_uni  = sum O_i^2 A_i / (1 + a h)     # fully unified face-face weight law, A_P=1

For each we report Spearman(B_variant, v_ss) and the best-of-3 ratio of the
combined tensor cost R + B_variant. No GPU needed (saved grids reused).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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

VARIANTS = ["B_amp", "B_flat", "B_att", "B_uni"]


def plate_variants_and_rayleigh(mesh, direction, data):
    """Recompute face-face Rayleigh R and the four plate-cost variants for one
    direction, mirroring the official implementation."""
    n = _safe_unit(direction)
    normals, areas, centers, vertices = data.normals, data.areas, data.centers, data.vertices
    k_ray = _adaptive_k_ray(len(areas))
    overhang = np.maximum(0.0, -(normals @ n))
    source_face_ids = _sample_ray_face_ids(areas, overhang, k_ray)
    zero = {v: 0.0 for v in VARIANTS}
    if source_face_ids.size == 0:
        return 0.0, zero

    origins = centers[source_face_ids] - data.ray_epsilon * n
    ray_directions = np.tile(-n, (len(source_face_ids), 1))
    hit_map = _first_valid_ray_hits(
        mesh, origins, ray_directions, source_face_ids,
        normals, centers, n, data.height_epsilon,
    )

    flow = np.zeros((3, 3), dtype=np.float64)
    if hit_map:
        hit_ray_ids = np.fromiter(hit_map.keys(), dtype=np.int64, count=len(hit_map))
        target_face_ids = np.fromiter(hit_map.values(), dtype=np.int64, count=len(hit_map))
        hit_source_face_ids = source_face_ids[hit_ray_ids]
        h_ij = (centers[hit_source_face_ids] - centers[target_face_ids]) @ n
        valid_pair = h_ij > data.height_epsilon
        if np.any(valid_pair):
            s, t, h = hit_source_face_ids[valid_pair], target_face_ids[valid_pair], h_ij[valid_pair]
            pair_w = overhang[s] * areas[s] * areas[t] / (1.0 + data.alpha * h)
            flow = np.einsum("i,ij,ik->jk", pair_w, normals[s], normals[t])
    else:
        hit_ray_ids = np.empty(0, dtype=np.int64)

    Fs = 0.5 * (flow + flow.T)
    R = max(0.0, -float(n @ Fs @ n))

    support_floor = float(np.min(vertices @ n))
    bed_mask = np.ones(len(source_face_ids), dtype=bool)
    bed_mask[hit_ray_ids] = False
    bed_ids = source_face_ids[bed_mask]
    out = dict(zero)
    if bed_ids.size:
        bh = centers[bed_ids] @ n - support_floor
        valid = bh > data.height_epsilon
        if np.any(valid):
            sid, h = bed_ids[valid], bh[valid]
            O, A = overhang[sid], areas[sid]
            att = 1.0 / (1.0 + data.alpha * h)
            out["B_amp"] = float(np.sum(O * A * (1.0 + data.alpha * h)))
            out["B_flat"] = float(np.sum(O * A))
            out["B_att"] = float(np.sum(O * A * att))
            out["B_uni"] = float(np.sum(O * O * A * att))
    return R, out


def main() -> None:
    grid_paths = sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}"))
    meshes = sys.argv[1:] if len(sys.argv) > 1 else None

    sp_rows, b3_rows = [], []
    for grid_path in grid_paths:
        stem = grid_path.name[: -len(GRID_SUFFIX)]
        if meshes and not any(m in stem for m in meshes):
            continue
        mesh_path = grid_path.with_name(stem + ".ply")
        data = np.load(grid_path, allow_pickle=True)
        yaw = np.asarray(data["yaw_values"], dtype=np.float64)
        pitch = np.asarray(data["pitch_values"], dtype=np.float64)
        vss_grid = np.asarray(data["vss_grid"], dtype=np.float64)
        tomo_best = _tomo_best(yaw, pitch, vss_grid)["vss"]

        mesh = load_mesh(str(mesh_path))
        surf = _triangle_surface_data(mesh)
        pool = evaluate_support_flow_candidate_pool(mesh)
        dirs = np.asarray([r[5] for r in pool], dtype=np.float64)

        R = np.empty(len(pool))
        Bv = {v: np.empty(len(pool)) for v in VARIANTS}
        for i, d in enumerate(dirs):
            r, bv = plate_variants_and_rayleigh(mesh, d, surf)
            R[i] = r
            for v in VARIANTS:
                Bv[v][i] = bv[v]

        signed_vss = np.asarray(
            [_signed_orientation(d, yaw, pitch, vss_grid)[1]["vss"] for d in dirs],
            dtype=np.float64,
        )

        def sp(x):
            if np.std(x) < 1e-12 or np.std(signed_vss) < 1e-12:
                return float("nan")
            return float(spearmanr(x, signed_vss)[0])

        def best3(scores, k=3, min_angle_deg=3.0):
            min_dot = float(np.cos(np.deg2rad(min_angle_deg)))
            picked = []
            for idx in np.argsort(scores, kind="stable"):
                if any(abs(float(np.dot(dirs[idx], dirs[p]))) >= min_dot for p in picked):
                    continue
                picked.append(int(idx))
                if len(picked) >= k:
                    break
            best = float(np.min(signed_vss[picked])) if picked else float("inf")
            return best / tomo_best if abs(tomo_best) > 1e-12 else float("inf")

        short = stem.split(")")[-1][:12]
        sp_rows.append((short, {v: sp(Bv[v]) for v in VARIANTS}))
        b3_rows.append((short, {v: best3(R + Bv[v]) for v in VARIANTS}))
        print(f"done {short}", flush=True)

    print("\n=== Spearman(plate-cost variant, v_ss)  (higher=better) ===")
    print(f"{'mesh':<14}" + "".join(f"{v:>9}" for v in VARIANTS))
    for short, d in sp_rows:
        print(f"{short:<14}" + "".join(f"{d[v]:>9.2f}" for v in VARIANTS))
    print(f"{'mean':<14}" + "".join(f"{np.nanmean([d[v] for _, d in sp_rows]):>9.2f}" for v in VARIANTS))

    print("\n=== best-of-3 ratio of R + plate-variant  (lower=better) ===")
    print(f"{'mesh':<14}" + "".join(f"{v:>9}" for v in VARIANTS))
    for short, d in b3_rows:
        print(f"{short:<14}" + "".join(f"{d[v]:>9.2f}" for v in VARIANTS))
    print(f"{'mean':<14}" + "".join(f"{np.nanmean([d[v] for _, d in b3_rows]):>9.2f}" for v in VARIANTS))
    nonhappy = [d for short, d in b3_rows if "happy" not in short]
    if nonhappy:
        print(f"{'mean(no happy)':<14}" + "".join(f"{np.nanmean([d[v] for d in nonhappy]):>9.2f}" for v in VARIANTS))


if __name__ == "__main__":
    main()
