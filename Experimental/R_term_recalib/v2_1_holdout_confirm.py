"""Confirmatory evaluation of the frozen SFTF v2.1 candidate (see FREEZE.md).

Runs on the 60-mesh external holdout using the cached dense TOMO grids only.
The v2.1 coefficients were frozen before this script was first executed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "python_src"))
sys.path.insert(0, str(HERE))

from SupportFlowTensorField.sftf_v2 import (  # noqa: E402
    SFTFV2Config,
    _first_receiver_hits,
    _unit,
    deterministic_surface_samples,
)
from extract_and_calibrate import fibonacci_directions, spearman, nms_basins  # noqa: E402

SNAPSHOT = PROJECT_ROOT / "draft" / "TDP_v2"
MANIFEST = SNAPSHOT / "experiments" / "tdp_v2" / "manifests" / "holdout_manifest.csv"
GRID_DIR = SNAPSHOT / "experiments" / "tdp_v2" / "results" / "tomo_grids"
CACHE_DIR = SNAPSHOT / "experiments" / "tdp_v2" / "results" / "sftf_candidate_cache"
EXTERNAL_CSV = SNAPSHOT / "experiments" / "tdp_v2" / "results" / "external_tomo_results.csv"
MESH_ROOT = Path(r"D:\__SFTF_Projects(2026)\sftf_Mesh_Data")
OUT = HERE / "holdout_v2_1"
OUT.mkdir(exist_ok=True)

SAMPLE_COUNT = 8192
DIRECTION_COUNT = 2048
BUDGET = 2400
V21 = dict(a_hv=0.25, a_hm=0.25, a_bm=0.5, a_R=1.0)   # FROZEN (FREEZE.md)


def grid_direction_vectors(yaw_deg, pitch_deg):
    yaw = np.deg2rad(np.rint(np.asarray(yaw_deg, dtype=np.float64)))[None, :]
    pitch = np.deg2rad(np.rint(np.asarray(pitch_deg, dtype=np.float64)))[:, None]
    sin_p, cos_p = np.sin(pitch), np.cos(pitch)
    sin_y, cos_y = np.sin(yaw), np.cos(yaw)
    x = np.broadcast_to(-sin_p, (len(pitch_deg), len(yaw_deg)))
    return np.stack((x, cos_p * sin_y, cos_p * cos_y), axis=-1).reshape(-1, 3)


def canonical_grid_cells(yaw_deg, pitch_deg):
    directions = grid_direction_vectors(yaw_deg, pitch_deg)
    _u, first = np.unique(np.round(directions, 8), axis=0, return_index=True)
    flat = np.sort(first.astype(np.int64))
    return flat, directions[flat]


def expand_around_basins(basin_directions, canonical_flat, canonical_directions, budget):
    proximity = np.max(canonical_directions @ basin_directions.T, axis=1)
    order = np.lexsort((canonical_flat, -proximity))
    return canonical_flat[order[: int(budget)]]


def extract_features(mesh, directions):
    settings = SFTFV2Config(sample_count=SAMPLE_COUNT, critical_angle_deg=60.0)
    surface = deterministic_surface_samples(mesh, SAMPLE_COUNT)
    total = len(surface.points)
    threshold = float(np.cos(np.deg2rad(settings.critical_angle_deg)))
    face_normals = np.asarray(mesh.face_normals, dtype=np.float64)
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    cols = {k: np.zeros(len(directions)) for k in ("F_hm", "F_hv", "F_bm", "F_bv", "R")}
    for di, direction in enumerate(directions):
        n = _unit(direction)
        overhang_all = np.maximum(0.0, -(surface.normals @ n))
        active = (overhang_all > 0.0) & (overhang_all >= threshold)
        ids = np.flatnonzero(active)
        if ids.size == 0:
            continue
        receiver_ids, pair_heights = _first_receiver_hits(
            mesh, surface.points[ids], surface.face_ids[ids], n,
            diameter=surface.diameter,
            receiver_normal_min=settings.receiver_normal_min,
            ray_epsilon_scale=settings.ray_epsilon_scale,
        )
        hit = receiver_ids >= 0
        O = overhang_all[ids]
        h = np.zeros(ids.size)
        if np.any(hit):
            h[hit] = pair_heights[hit] / surface.diameter
        bed = ~hit
        if np.any(bed):
            floor = float(np.min(vertices @ n))
            h[bed] = np.maximum(0.0, (surface.points[ids][bed] @ n - floor) / surface.diameter)
        cols["F_hm"][di] = float(np.sum(O[hit]) / total)
        cols["F_hv"][di] = float(np.sum(O[hit] * h[hit]) / total)
        cols["F_bm"][di] = float(np.sum(O[bed]) / total)
        cols["F_bv"][di] = float(np.sum(O[bed] * h[bed]) / total)
        if np.any(hit):
            w = O[hit] / (1.0 + h[hit])
            tensor = np.einsum("i,ij,ik->jk", w / total,
                               surface.normals[ids][hit], face_normals[receiver_ids[hit]])
            sym = 0.5 * (tensor + tensor.T)
            cols["R"][di] = max(0.0, -float(n @ sym @ n))
    return cols


def policy_nrr(scores, directions, grid_flat, canonical_flat, canonical_directions,
               gmin, gmax):
    basin_ids = nms_basins(directions, scores)
    cells = expand_around_basins(directions[basin_ids], canonical_flat,
                                 canonical_directions, BUDGET)
    value = float(np.min(grid_flat[cells]))
    return (value - gmin) / max(gmax - gmin, 1e-12)


def main() -> None:
    with MANIFEST.open(newline="", encoding="utf-8") as fh:
        manifest = list(csv.DictReader(fh))
    with EXTERNAL_CSV.open(newline="", encoding="utf-8") as fh:
        external = {r["holdout_id"]: r for r in csv.DictReader(fh)}
    directions = fibonacci_directions(DIRECTION_COUNT)
    rows = []
    for seq, mrow in enumerate(manifest, start=1):
        hid = mrow["holdout_id"]
        out_path = OUT / f"{hid}.json"
        if out_path.exists():
            rows.append(json.loads(out_path.read_text(encoding="utf-8")))
            continue
        started = time.perf_counter()
        mesh_path = MESH_ROOT / mrow["relative_path"]
        digest = hashlib.sha256(mesh_path.read_bytes()).hexdigest()
        assert digest.lower() == mrow["sha256"].lower(), f"{hid}: mesh hash mismatch"
        mesh = trimesh.load_mesh(str(mesh_path), force="mesh", process=False)
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)
        F = extract_features(mesh, directions)
        s_v0 = F["R"] + F["F_bm"] + F["F_bv"]
        s_v21 = (V21["a_R"] * F["R"] + V21["a_hv"] * F["F_hv"] + V21["a_hm"] * F["F_hm"]
                 + V21["a_bm"] * F["F_bm"] + F["F_bv"])

        # sanity: recomputed V0 must match the paper's cached scores
        cache = np.load(CACHE_DIR / f"{hid}.npz", allow_pickle=False)
        cache_diff = float(np.max(np.abs(np.asarray(cache["scores_8192"]) - s_v0)))

        with np.load(GRID_DIR / f"{hid}.npz", allow_pickle=False) as data:
            yaw = np.asarray(data["yaw_values"], dtype=np.float64)
            pitch = np.asarray(data["pitch_values"], dtype=np.float64)
            grid = np.asarray(data["vss_grid"], dtype=np.float64)
        grid_flat = grid.reshape(-1)
        gmin, gmax = float(grid_flat.min()), float(grid_flat.max())
        canonical_flat, canonical_directions = canonical_grid_cells(yaw, pitch)

        # per-direction ground truth for sweep metrics
        pitch_t = (-np.degrees(np.arcsin(np.clip(directions[:, 0], -1, 1)))) % 360.0
        yaw_t = np.degrees(np.arctan2(directions[:, 1], directions[:, 2])) % 360.0
        yi = np.argmin(np.abs((yaw[None, :] - yaw_t[:, None] + 180.0) % 360.0 - 180.0), axis=1)
        pi = np.argmin(np.abs((pitch[None, :] - pitch_t[:, None] + 180.0) % 360.0 - 180.0), axis=1)
        vss = grid[pi, yi]
        nrr_dir = (vss - gmin) / max(gmax - gmin, 1e-12)

        def sweep_metrics(s):
            order = np.lexsort((np.arange(len(s)), s))
            basins = nms_basins(directions, s)
            return (spearman(s, vss), float(nrr_dir[order[0]]),
                    float(np.min(nrr_dir[basins])))

        rho0, top10, basin0 = sweep_metrics(s_v0)
        rho1, top11, basin1 = sweep_metrics(s_v21)
        row = {
            "holdout_id": hid,
            "stratum": mrow["stratum"],
            "v0_policy_nrr": policy_nrr(s_v0, directions, grid_flat,
                                        canonical_flat, canonical_directions, gmin, gmax),
            "v21_policy_nrr": policy_nrr(s_v21, directions, grid_flat,
                                         canonical_flat, canonical_directions, gmin, gmax),
            "uniform_nrr": float(external[hid]["uniform_nrr"]),
            "paper_sftf_v2_nrr": float(external[hid]["sftf_v2_nrr"]),
            "v0_cache_max_abs_diff": cache_diff,
            "rho_v0": rho0, "rho_v21": rho1,
            "top1_v0": top10, "top1_v21": top11,
            "basin24_v0": basin0, "basin24_v21": basin1,
            "elapsed_s": time.perf_counter() - started,
        }
        out_path.write_text(json.dumps(row, indent=1), encoding="utf-8")
        rows.append(row)
        print(f"[{seq}/60] {hid} v0 {row['v0_policy_nrr']:.4f} (paper "
              f"{row['paper_sftf_v2_nrr']:.4f}, cacheD {cache_diff:.2e}) "
              f"v2.1 {row['v21_policy_nrr']:.4f}  ({row['elapsed_s']:.1f}s)", flush=True)

    # ---- pre-registered analysis ----
    d_policy = np.array([r["v21_policy_nrr"] - r["v0_policy_nrr"] for r in rows])
    d_uniform = np.array([r["v21_policy_nrr"] - r["uniform_nrr"] for r in rows])
    rng = np.random.default_rng(20260729)
    idx = rng.integers(0, len(d_policy), size=(10000, len(d_policy)))

    def ci(d):
        boot = np.mean(d[idx], axis=1)
        return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))

    lo, hi = ci(d_policy)
    lo_u, hi_u = ci(d_uniform)
    wins = int(np.sum(d_policy < -1e-9)); ties = int(np.sum(np.abs(d_policy) <= 1e-9))
    print()
    print("== PRIMARY: paired (v2.1 - V0) policy NRR over 60 holdout meshes ==")
    print(f"  mean {np.mean(d_policy):+.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]  "
          f"median {np.median(d_policy):+.4f}  win/tie/loss {wins}/{ties}/{len(d_policy)-wins-ties}")
    verdict = "개선 확인" if hi < 0 else ("악화" if lo > 0 else "미확정")
    print(f"  pre-registered verdict: {verdict}")
    print("== SECONDARY ==")
    print(f"  (v2.1 - uniform) mean {np.mean(d_uniform):+.4f}  CI [{lo_u:+.4f}, {hi_u:+.4f}]")
    for key in ("rho", "top1", "basin24"):
        a = np.array([r[f"{key}_v0"] for r in rows])
        b = np.array([r[f"{key}_v21"] for r in rows])
        print(f"  {key:8s} V0 {np.mean(a):+.4f} -> v2.1 {np.mean(b):+.4f}")
    print(f"  max V0-vs-paper-cache score diff: "
          f"{max(r['v0_cache_max_abs_diff'] for r in rows):.2e}")
    by = {}
    for r in rows:
        by.setdefault(r["stratum"], []).append(r["v21_policy_nrr"] - r["v0_policy_nrr"])
    print("  per stratum (v2.1-V0):")
    for k in sorted(by):
        print(f"    {k:12s} mean {np.mean(by[k]):+.4f} (n={len(by[k])})")
    (HERE / "holdout_v2_1_summary.json").write_text(
        json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
