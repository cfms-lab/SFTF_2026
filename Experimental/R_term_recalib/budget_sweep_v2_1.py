"""Tight-budget confirmatory evaluation of frozen SFTF v2.1 (FREEZE.md part 2).

Budgets {5, 10, 20} on the 60-mesh external holdout, cached grids only.
Primary endpoint: paired (v2.1 - V0) policy NRR at budget 10.
Score arrays are recomputed once per mesh and saved for audit.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "python_src"))
sys.path.insert(0, str(HERE))

from extract_and_calibrate import fibonacci_directions, nms_basins  # noqa: E402
from v2_1_holdout_confirm import (  # noqa: E402
    BUDGET, CACHE_DIR, EXTERNAL_CSV, GRID_DIR, MANIFEST, MESH_ROOT, V21,
    canonical_grid_cells, expand_around_basins, extract_features,
)

OUT = HERE / "holdout_scores"
OUT.mkdir(exist_ok=True)
BUDGETS = [5, 10, 20]
DIRECTION_COUNT = 2048


def nearest_grid_flat(direction, yaw_deg, pitch_deg):
    unit = np.asarray(direction, dtype=np.float64)
    unit /= max(float(np.linalg.norm(unit)), 1.0e-15)
    pitch_target = (-math.degrees(math.asin(float(np.clip(unit[0], -1.0, 1.0))))) % 360.0
    yaw_target = math.degrees(math.atan2(float(unit[1]), float(unit[2]))) % 360.0

    def nearest(values, target):
        delta = np.abs((np.asarray(values) - target + 180.0) % 360.0 - 180.0)
        return int(np.argmin(delta))

    return nearest(pitch_deg, pitch_target) * len(yaw_deg) + nearest(yaw_deg, yaw_target)


def uniform_cells(yaw_deg, pitch_deg, budget):
    selected, seen = [], set()
    for count in (int(budget), int(budget) * 4, int(budget) * 8):
        for direction in fibonacci_directions(count):
            flat = nearest_grid_flat(direction, yaw_deg, pitch_deg)
            if flat in seen:
                continue
            seen.add(flat)
            selected.append(flat)
            if len(selected) >= int(budget):
                return np.asarray(selected, dtype=np.int64)
    raise RuntimeError("uniform mapping failed")


def scores_for(hid, mrow, directions):
    path = OUT / f"{hid}_scores.npz"
    if path.exists():
        d = np.load(path, allow_pickle=False)
        return d["s_v0"], d["s_v21"]
    mesh_path = MESH_ROOT / mrow["relative_path"]
    assert hashlib.sha256(mesh_path.read_bytes()).hexdigest().lower() == mrow["sha256"].lower()
    mesh = trimesh.load_mesh(str(mesh_path), force="mesh", process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)
    F = extract_features(mesh, directions)
    s_v0 = F["R"] + F["F_bm"] + F["F_bv"]
    s_v21 = (V21["a_R"] * F["R"] + V21["a_hv"] * F["F_hv"] + V21["a_hm"] * F["F_hm"]
             + V21["a_bm"] * F["F_bm"] + F["F_bv"])
    cache = np.load(CACHE_DIR / f"{hid}.npz", allow_pickle=False)
    assert float(np.max(np.abs(np.asarray(cache["scores_8192"]) - s_v0))) < 1e-12
    np.savez_compressed(path, s_v0=s_v0, s_v21=s_v21, **{k: F[k] for k in F})
    return s_v0, s_v21


def main() -> None:
    with MANIFEST.open(newline="", encoding="utf-8") as fh:
        manifest = list(csv.DictReader(fh))
    directions = fibonacci_directions(DIRECTION_COUNT)
    rows = []
    for seq, mrow in enumerate(manifest, start=1):
        hid = mrow["holdout_id"]
        started = time.perf_counter()
        s_v0, s_v21 = scores_for(hid, mrow, directions)
        with np.load(GRID_DIR / f"{hid}.npz", allow_pickle=False) as data:
            yaw = np.asarray(data["yaw_values"], dtype=np.float64)
            pitch = np.asarray(data["pitch_values"], dtype=np.float64)
            grid = np.asarray(data["vss_grid"], dtype=np.float64)
        grid_flat = grid.reshape(-1)
        gmin, gmax = float(grid_flat.min()), float(grid_flat.max())
        canonical_flat, canonical_directions = canonical_grid_cells(yaw, pitch)

        def nrr_of(cells):
            return (float(np.min(grid_flat[np.asarray(cells, dtype=np.int64)])) - gmin) \
                / max(gmax - gmin, 1e-12)

        row = {"holdout_id": hid, "stratum": mrow["stratum"],
               "face_count": int(mrow["face_count"])}
        for label, s in (("v0", s_v0), ("v21", s_v21)):
            basins = directions[nms_basins(directions, s)]
            full = expand_around_basins(basins, canonical_flat, canonical_directions, BUDGET)
            for b in BUDGETS:
                row[f"{label}_nrr_b{b}"] = nrr_of(full[:b] if len(full) >= b else full)
        for b in BUDGETS:
            row[f"uniform_nrr_b{b}"] = nrr_of(uniform_cells(yaw, pitch, b))
        rows.append(row)
        print(f"[{seq}/60] {hid} b10: v0 {row['v0_nrr_b10']:.4f} "
              f"v2.1 {row['v21_nrr_b10']:.4f} uni {row['uniform_nrr_b10']:.4f} "
              f"({time.perf_counter()-started:.1f}s)", flush=True)

    (HERE / "budget_sweep_v2_1_rows.json").write_text(json.dumps(rows, indent=1),
                                                      encoding="utf-8")
    rng = np.random.default_rng(20260729)

    def paired(diffs):
        d = np.asarray(diffs, dtype=np.float64)
        idx = rng.integers(0, len(d), size=(10000, len(d)))
        boot = np.mean(d[idx], axis=1)
        return (float(np.mean(d)), float(np.percentile(boot, 2.5)),
                float(np.percentile(boot, 97.5)))

    print()
    for b in BUDGETS:
        d = [r[f"v21_nrr_b{b}"] - r[f"v0_nrr_b{b}"] for r in rows]
        m, lo, hi = paired(d)
        wins = sum(x < -1e-9 for x in d); ties = sum(abs(x) <= 1e-9 for x in d)
        tag = "PRIMARY" if b == 10 else "secondary"
        print(f"[{tag}] budget {b:3d}: (v2.1-V0) mean {m:+.4f}  CI [{lo:+.4f}, {hi:+.4f}]  "
              f"w/t/l {wins}/{ties}/{len(d)-wins-ties}")
        if b == 10:
            verdict = "개선 확인" if hi < 0 else ("악화" if lo > 0 else "미확정")
            print(f"          pre-registered verdict: {verdict}")
        du = [r[f"v21_nrr_b{b}"] - r[f"uniform_nrr_b{b}"] for r in rows]
        m, lo, hi = paired(du)
        d0u = [r[f"v0_nrr_b{b}"] - r[f"uniform_nrr_b{b}"] for r in rows]
        m0, lo0, hi0 = paired(d0u)
        print(f"           (v2.1-uniform) mean {m:+.4f}  CI [{lo:+.4f}, {hi:+.4f}]   "
              f"| (V0-uniform) mean {m0:+.4f}  CI [{lo0:+.4f}, {hi0:+.4f}]")
    complex_rows = [r for r in rows if r["face_count"] >= 50000]
    d = [r["v21_nrr_b10"] - r["v0_nrr_b10"] for r in complex_rows]
    m, lo, hi = paired(d)
    print(f"[secondary] complex >=50k (n={len(complex_rows)}) budget 10: "
          f"(v2.1-V0) mean {m:+.4f}  CI [{lo:+.4f}, {hi:+.4f}]")
    du = [r["v21_nrr_b10"] - r["uniform_nrr_b10"] for r in complex_rows]
    m, lo, hi = paired(du)
    d0u = [r["v0_nrr_b10"] - r["uniform_nrr_b10"] for r in complex_rows]
    m0, lo0, hi0 = paired(d0u)
    print(f"           (v2.1-uniform) {m:+.4f} [{lo:+.4f}, {hi:+.4f}] "
          f"| (V0-uniform) {m0:+.4f} [{lo0:+.4f}, {hi0:+.4f}]")


if __name__ == "__main__":
    main()
