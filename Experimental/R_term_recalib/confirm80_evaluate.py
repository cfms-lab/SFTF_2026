"""Pre-registered confirmatory evaluation on the NEW 80-mesh set (FREEZE.md part 3).

Primary endpoint: paired (v2.1 - V0) policy NRR at budget 5 over N001-N080.
Runs after confirm80_grids/ is complete.  Scores saved for audit.
"""

from __future__ import annotations

import csv
import hashlib
import json
import time
from pathlib import Path
import sys

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "python_src"))
sys.path.insert(0, str(HERE))

from extract_and_calibrate import fibonacci_directions, nms_basins, spearman  # noqa: E402
from v2_1_holdout_confirm import (  # noqa: E402
    MESH_ROOT, V21, canonical_grid_cells, expand_around_basins, extract_features,
)
from budget_sweep_v2_1 import uniform_cells  # noqa: E402

MANIFEST = HERE / "confirm80_manifest.csv"
GRID_DIR = HERE / "confirm80_grids"
SCORE_DIR = HERE / "confirm80_scores"
SCORE_DIR.mkdir(exist_ok=True)
BUDGETS = [5, 10, 20]
NMS_BUDGET_FULL = 2400
DIRECTION_COUNT = 2048


def main() -> None:
    with MANIFEST.open(newline="", encoding="utf-8") as fh:
        manifest = list(csv.DictReader(fh))
    directions = fibonacci_directions(DIRECTION_COUNT)
    rows = []
    for seq, mrow in enumerate(manifest, start=1):
        hid = mrow["holdout_id"]
        started = time.perf_counter()
        spath = SCORE_DIR / f"{hid}_scores.npz"
        if spath.exists():
            d = np.load(spath, allow_pickle=False)
            s_v0, s_v21 = d["s_v0"], d["s_v21"]
        else:
            mesh_path = MESH_ROOT / mrow["relative_path"]
            assert hashlib.sha256(mesh_path.read_bytes()).hexdigest().lower() == mrow["sha256"].lower()
            mesh = trimesh.load_mesh(str(mesh_path), force="mesh", process=False)
            if isinstance(mesh, trimesh.Scene):
                mesh = mesh.dump(concatenate=True)
            F = extract_features(mesh, directions)
            s_v0 = F["R"] + F["F_bm"] + F["F_bv"]
            s_v21 = (V21["a_R"] * F["R"] + V21["a_hv"] * F["F_hv"]
                     + V21["a_hm"] * F["F_hm"] + V21["a_bm"] * F["F_bm"] + F["F_bv"])
            np.savez_compressed(spath, s_v0=s_v0, s_v21=s_v21, **{k: F[k] for k in F})

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

        pitch_t = (-np.degrees(np.arcsin(np.clip(directions[:, 0], -1, 1)))) % 360.0
        yaw_t = np.degrees(np.arctan2(directions[:, 1], directions[:, 2])) % 360.0
        yi = np.argmin(np.abs((yaw[None, :] - yaw_t[:, None] + 180.0) % 360.0 - 180.0), axis=1)
        pi = np.argmin(np.abs((pitch[None, :] - pitch_t[:, None] + 180.0) % 360.0 - 180.0), axis=1)
        vss = grid[pi, yi]
        nrr_dir = (vss - gmin) / max(gmax - gmin, 1e-12)

        row = {"holdout_id": hid, "stratum": mrow["stratum"],
               "face_count": int(mrow["face_count"])}
        for label, s in (("v0", s_v0), ("v21", s_v21)):
            basins = directions[nms_basins(directions, s)]
            full = expand_around_basins(basins, canonical_flat, canonical_directions,
                                        NMS_BUDGET_FULL)
            for b in BUDGETS:
                row[f"{label}_nrr_b{b}"] = nrr_of(full[:b])
            order = np.lexsort((np.arange(len(s)), s))
            row[f"{label}_rho"] = spearman(s, vss)
            row[f"{label}_top1"] = float(nrr_dir[order[0]])
            row[f"{label}_basin24"] = float(np.min(nrr_dir[nms_basins(directions, s)]))
        for b in BUDGETS:
            row[f"uniform_nrr_b{b}"] = nrr_of(uniform_cells(yaw, pitch, b))
        rows.append(row)
        print(f"[{seq}/80] {hid} b5: v0 {row['v0_nrr_b5']:.4f} v2.1 {row['v21_nrr_b5']:.4f} "
              f"uni {row['uniform_nrr_b5']:.4f} ({time.perf_counter()-started:.1f}s)", flush=True)

    (HERE / "confirm80_rows.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    rng = np.random.default_rng(20260730)

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
        tag = "PRIMARY" if b == 5 else "secondary"
        print(f"[{tag}] budget {b:3d}: (v2.1-V0) mean {m:+.4f}  CI [{lo:+.4f}, {hi:+.4f}]  "
              f"w/t/l {wins}/{ties}/{len(d)-wins-ties}")
        if b == 5:
            verdict = "개선 확인" if hi < 0 else ("악화" if lo > 0 else "미확정")
            print(f"          pre-registered verdict: {verdict}")
        du = [r[f"v21_nrr_b{b}"] - r[f"uniform_nrr_b{b}"] for r in rows]
        m, lo, hi = paired(du)
        d0u = [r[f"v0_nrr_b{b}"] - r[f"uniform_nrr_b{b}"] for r in rows]
        m0, lo0, hi0 = paired(d0u)
        print(f"           (v2.1-uniform) {m:+.4f} [{lo:+.4f}, {hi:+.4f}] "
              f"| (V0-uniform) {m0:+.4f} [{lo0:+.4f}, {hi0:+.4f}]")
    comp = [r for r in rows if r["face_count"] >= 50000]
    d = [r["v21_nrr_b5"] - r["v0_nrr_b5"] for r in comp]
    m, lo, hi = paired(d)
    print(f"[secondary] complex >=50k (n={len(comp)}) b5: (v2.1-V0) {m:+.4f} [{lo:+.4f}, {hi:+.4f}]")
    for key in ("rho", "top1", "basin24"):
        a = np.mean([r[f"v0_{key}"] for r in rows])
        b_ = np.mean([r[f"v21_{key}"] for r in rows])
        print(f"  {key:8s} V0 {a:+.4f} -> v2.1 {b_:+.4f}")


if __name__ == "__main__":
    main()
