"""Re-measure 1deg/60deg TOMO_CPU + TOMO_CUDA wall time with the 07-05
performance-optimized dll, for the final timing tables (S1, Table 10).

Grid VALUES are unchanged by a performance optimization (INT3 is deterministic
and identical; CUDA differs only by benign float-atomic ordering, <=0.3%), so
this only refreshes the timing: it recomputes the record combo, writes the new
dll_sec into the cache npz (grid re-stored) and updates the JSON
tomo_int3_dll_sec / tomo_cuda_dll_sec. Marker `dll_v0705` lets it be re-run
safely. Run on an idle machine (single-session timing).

Usage: python scripts/retime_1deg_optimized_dll.py [stem ...]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from cpp_src.Tomo_GPU2026.tomo_cpu import (  # noqa: E402
    compute_tomo_cpu_vss_grid,
    compute_tomo_cuda_vss_grid,
    tomo_best_row,
)

OUT_DIR = PROJECT_ROOT / "Experimental" / "G5Test"
SFTF_RESULT_DIR = OUT_DIR / "SFTF_result"
MESH_DIR = PROJECT_ROOT.parent / "sftf_Mesh_Data" / "g5test"

BACKENDS = [
    ("tomo_int3", OUT_DIR / "tomo_int3_cache", compute_tomo_cpu_vss_grid),
    ("tomo_cuda", OUT_DIR / "tomo_cuda_cache", compute_tomo_cuda_vss_grid),
]


def mesh_for(stem: str) -> Path | None:
    m = sorted(p for p in MESH_DIR.glob(stem + ".*")
               if p.suffix.lower() in {".stl", ".obj", ".ply"})
    return m[0] if m else None


def main() -> None:
    only = set(sys.argv[1:])
    jsons = sorted(SFTF_RESULT_DIR.glob("Group_*.json"))
    for jp in jsons:
        stem = jp.stem
        if only and stem not in only:
            continue
        mesh = mesh_for(stem)
        if mesh is None:
            continue
        record = json.loads(jp.read_text(encoding="utf-8"))
        print(f"== {stem} ==", flush=True)
        for tag, cache, fn in BACKENDS:
            npz = cache / f"{stem}_{tag}_1deg_60deg.npz"
            if not npz.exists():
                print(f"  [{tag}] no 1deg grid; skip", flush=True)
                continue
            try:
                with np.load(npz, allow_pickle=False) as z:
                    if "dll_v0705" in z.files:
                        print(f"  [{tag}] already re-timed (v0705); skip", flush=True)
                        continue
            except Exception:
                pass
            start = time.perf_counter()
            try:
                tomo = fn(mesh, critical_angle=60.0, angle_step=1.0)
            except Exception as exc:
                print(f"  [{tag}] FAILED: {type(exc).__name__}: {exc}", flush=True)
                continue
            dll_sec = time.perf_counter() - start
            yaw = np.asarray(tomo["yaw_values"], dtype=np.float64)
            pitch = np.asarray(tomo["pitch_values"], dtype=np.float64)
            grid = np.asarray(tomo["vss_grid"], dtype=np.float64)
            np.savez_compressed(npz, yaw_values=yaw, pitch_values=pitch, vss_grid=grid,
                                dll_sec=np.float64(dll_sec), regenerated=np.int8(1),
                                dll_v0705=np.int8(1))
            record[f"{tag}_dll_sec"] = dll_sec
            best = tomo_best_row(yaw, pitch, grid)
            record[f"{tag}_best"] = best
            print(f"  [{tag}] {dll_sec:.1f}s  best vss={best['vss']:.4g} "
                  f"neg={(grid < 0).sum()} zeros={(grid == 0).sum()}", flush=True)
        jp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print("RETIME DONE", flush=True)


if __name__ == "__main__":
    main()
