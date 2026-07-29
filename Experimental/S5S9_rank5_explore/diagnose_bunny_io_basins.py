"""Why does SFTF miss TOMO basins Io2/Io4 on Bunny 69k?

For each of the five TOMO optimal basins (Io1-Io5) this prints, side by side:

  * TOMO v_ss and NRR at the basin cell (ground truth: all five are good).
  * The PAPER (v2, dimensionless, K=8192) score evaluated exactly at the basin
    direction, decomposed into R (face-to-face Rayleigh) and B (plate), plus
    its percentile within today's cached 2,048-direction sweep and the angle
    to the nearest of the 24 NMS basins the paper pipeline would keep.
  * The LEGACY (G5 rank-tuned) candidate nearest to the basin direction with
    its rayleigh/pair/bed components as pool percentiles (the S5-S9 figures
    use this score).

Reference rows for the v2 top-5 NMS candidates are printed as well.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROJECT_ROOT / "python_src"))

from explore_rank5_contours import (  # noqa: E402
    ETC, NPZ_SUFFIX, SFTF_RESULT,
    direction_from_yaw_pitch, grid_basin_rows, yaw_pitch_from_direction,
)
from SupportFlowTensorField.sftf_v2 import (  # noqa: E402
    SFTFV2Config, deterministic_surface_samples, evaluate_sftf_v2,
)

MESH = Path(r"D:\__SFTF_Projects(2026)\sftf_Mesh_Data\g5test\Group_C1_Bunny_69k.ply")
CACHE = PROJECT_ROOT / "Experimental" / "GroupC_runtime_tdp_submit3" / "candidates" / "Group_C1_Bunny_69k.npz"

# ---- TOMO ground truth ----
data = np.load(ETC / f"(1)Bunny_69k{NPZ_SUFFIX}", allow_pickle=False)
yaw_v = np.asarray(data["yaw_values"], dtype=np.float64)
pitch_v = np.asarray(data["pitch_values"], dtype=np.float64)
grid = np.asarray(data["vss_grid"], dtype=np.float64)
gmin, gmax = float(grid.min()), float(grid.max())
io = grid_basin_rows(grid, yaw_v, pitch_v, count=5, reverse=False)

# ---- paper v2 sweep (cached) + NMS basins ----
cache = np.load(CACHE, allow_pickle=False)
fib_dirs = np.asarray(cache["directions"], dtype=np.float64)
scores_8192 = np.asarray(cache["scores_8192"], dtype=np.float64)

def nms_basins(directions, scores, count=24, separation_deg=12.0):
    order = np.lexsort((np.arange(len(scores)), scores))
    cosine = np.cos(np.deg2rad(separation_deg))
    sel: list[int] = []
    for idx in order:
        d = directions[int(idx)]
        if sel and np.max(directions[sel] @ d) > cosine:
            continue
        sel.append(int(idx))
        if len(sel) >= count:
            break
    return np.asarray(sel)

basin_ids = nms_basins(fib_dirs, scores_8192)
basin_dirs = fib_dirs[basin_ids]

# ---- v2 evaluation at arbitrary directions ----
mesh = trimesh.load_mesh(str(MESH), force="mesh", process=False)
if isinstance(mesh, trimesh.Scene):
    mesh = mesh.dump(concatenate=True)
config = SFTFV2Config(sample_count=8192, critical_angle_deg=60.0)
samples = deterministic_surface_samples(mesh, 8192)

def v2_at(direction):
    return evaluate_sftf_v2(mesh, np.asarray(direction, dtype=np.float64),
                            config=config, samples=samples)

# ---- legacy pool ----
legacy = []
with (SFTF_RESULT / "Group_C1_Bunny_69k_candidates.csv").open(newline="", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        d = np.array([float(r["dir_x"]), float(r["dir_y"]), float(r["dir_z"])])
        d /= max(float(np.linalg.norm(d)), 1e-12)
        legacy.append({
            "direction": d,
            "tuned": float(r["tuned_score"]),
            "rayleigh": float(r["rayleigh"]),
            "pair": float(r["pair"]),
            "bed": float(r["bed"]),
        })
leg_dirs = np.stack([r["direction"] for r in legacy])
leg_tuned = np.array([r["tuned"] for r in legacy])

def pct(values, v):
    return 100.0 * float(np.mean(np.asarray(values) <= v))

def angle_deg(a, b):
    return float(np.degrees(np.arccos(np.clip(float(np.dot(a, b)), -1.0, 1.0))))

def describe(tag, direction, yaw=None, pitch=None):
    if yaw is None:
        yaw, pitch = yaw_pitch_from_direction(direction)
    yi = int(np.argmin(np.abs((yaw_v - yaw + 180.0) % 360.0 - 180.0)))
    pi = int(np.argmin(np.abs((pitch_v - pitch + 180.0) % 360.0 - 180.0)))
    vss = float(grid[pi, yi])
    nrr = (vss - gmin) / (gmax - gmin)

    ev = v2_at(direction)
    v2_pct = pct(scores_8192, ev.score)
    nms_angle = min(angle_deg(direction, b) for b in basin_dirs)

    ang = np.degrees(np.arccos(np.clip(leg_dirs @ direction, -1.0, 1.0)))
    j = int(np.argmin(ang))
    lg = legacy[j]
    print(f"{tag:6s} yaw {yaw:6.1f} pitch {pitch:6.1f} | vss {vss:8.0f} NRR {nrr:.3f} | "
          f"v2 S {ev.score:7.4f} (R {ev.rayleigh_score:6.4f} B {ev.bed_score:7.4f}) "
          f"pct {v2_pct:5.1f}% nmsAng {nms_angle:5.1f} | "
          f"legacy@{ang[j]:4.1f}deg tuned {lg['tuned']:7.3f} pct {pct(leg_tuned, lg['tuned']):5.1f}% "
          f"ray {lg['rayleigh']:7.2f} pair {lg['pair']:7.2f} bed {lg['bed']:7.2f}")

print("=== TOMO optimal basins Io1-Io5 ===")
for k, row in enumerate(io, start=1):
    describe(f"Io{k}", row["direction"], row["yaw"], row["pitch"])

print()
print("=== paper-v2 top-5 NMS candidates (reference) ===")
for k in range(5):
    describe(f"v2#{k+1}", basin_dirs[k])

print()
print("=== legacy top-3 (S5-S9 markers, reference) ===")
order = np.argsort(leg_tuned)
seen: list[np.ndarray] = []
count = 0
for idx in order:
    d = leg_dirs[int(idx)]
    if seen and max(float(np.dot(d, s)) for s in seen) > np.cos(np.deg2rad(12.0)):
        continue
    seen.append(d)
    count += 1
    describe(f"Lg#{count}", d)
    if count >= 3:
        break
