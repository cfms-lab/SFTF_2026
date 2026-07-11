"""Re-sweep the recovered legacy G5 meshes at the manuscript's 1deg/60deg setting.

The three meshes were absent when ``resweep_int3_new_dll.py`` applied the
int32-accumulator fix, so their tracked grids retained pre-fix values.  This
script intentionally updates only the 1-degree/60-degree grids used by the TDP
pipeline and writes an auditable old/new hash report.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cpp_src.Tomo_GPU2026.tomo_cpu import compute_tomo_cpu_vss_grid, tomo_best_row
from python_src.SupportFlowTensorField.support_flow_tensor_field import load_mesh
from scripts._mesh_paths import G5_RAW_MESH


CACHE = ROOT / "Experimental" / "G5Test" / "tomo_int3_cache"
REPORT = ROOT / "Experimental" / "etc" / "sftf_recovered_mesh_resweep.json"
STEMS = ("Group_E2_45809", "Group_E3_45811", "Group_E4_46012")
SUFFIX = "_tomo_int3_1deg_60deg.npz"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    rows: list[dict[str, object]] = []
    for stem in STEMS:
        meshes = sorted(G5_RAW_MESH.glob(f"{stem}.*"))
        if len(meshes) != 1:
            raise RuntimeError(f"expected exactly one mesh for {stem}, got {meshes}")
        mesh_path = meshes[0]
        grid_path = CACHE / f"{stem}{SUFFIX}"
        if not grid_path.is_file():
            raise FileNotFoundError(grid_path)

        old_sha = _sha256(grid_path)
        with np.load(grid_path, allow_pickle=False) as old:
            old_grid = np.asarray(old["vss_grid"], dtype=np.float64)
            old_min = float(np.nanmin(old_grid))
            old_max = float(np.nanmax(old_grid))
            old_had_int32fix = "dll_int32fix" in old.files
        mesh = load_mesh(str(mesh_path))
        mesh_sha = _sha256(mesh_path)

        print(f"[{stem}] faces={len(mesh.faces)} old_min={old_min:.6g}", flush=True)
        started = time.perf_counter()
        tomo = compute_tomo_cpu_vss_grid(mesh_path, critical_angle=60.0, angle_step=1.0)
        elapsed = time.perf_counter() - started
        yaw = np.asarray(tomo["yaw_values"], dtype=np.float64)
        pitch = np.asarray(tomo["pitch_values"], dtype=np.float64)
        grid = np.asarray(tomo["vss_grid"], dtype=np.float64)
        if grid.shape != (361, 361) or not np.all(np.isfinite(grid)):
            raise RuntimeError(f"unexpected regenerated grid for {stem}: {grid.shape}")

        temporary = grid_path.with_suffix(".tmp.npz")
        np.savez_compressed(
            temporary,
            yaw_values=yaw,
            pitch_values=pitch,
            vss_grid=grid,
            dll_sec=np.float64(elapsed),
            regenerated=np.int8(1),
            dll_int32fix=np.int8(1),
            recovered_mesh_20260711=np.int8(1),
            mesh_sha256=np.asarray(mesh_sha),
        )
        temporary.replace(grid_path)
        best = tomo_best_row(yaw, pitch, grid)
        row = {
            "mesh": stem,
            "mesh_path": str(mesh_path.resolve()),
            "mesh_sha256": mesh_sha,
            "mesh_size_bytes": mesh_path.stat().st_size,
            "face_count": int(len(mesh.faces)),
            "grid_path": str(grid_path.resolve()),
            "old_grid_sha256": old_sha,
            "old_grid_had_int32fix_marker": old_had_int32fix,
            "old_grid_min": old_min,
            "old_grid_max": old_max,
            "new_grid_sha256": _sha256(grid_path),
            "new_grid_min": float(np.min(grid)),
            "new_grid_max": float(np.max(grid)),
            "new_grid_negative_count": int(np.sum(grid < 0)),
            "new_grid_zero_count": int(np.sum(grid == 0)),
            "new_grid_best": best,
            "dll_wall_s": elapsed,
            "critical_angle_deg": 60.0,
            "angle_step_deg": 1.0,
        }
        rows.append(row)
        print(
            f"  {elapsed:.2f}s new_min={row['new_grid_min']:.6g} "
            f"best=({best['yaw']:.1f},{best['pitch']:.1f})",
            flush=True,
        )

        partial = {
            "status": "partial",
            "backend": "current TOMO_CPU DLL with int32 accumulator fix",
            "records": rows,
        }
        REPORT.write_text(json.dumps(partial, indent=2, ensure_ascii=False), encoding="utf-8")

    payload = {
        "status": "complete",
        "backend": "current TOMO_CPU DLL with int32 accumulator fix",
        "record_count": len(rows),
        "records": rows,
    }
    REPORT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved: {REPORT.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
