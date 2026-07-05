"""Re-sweep every stored tomo_cuda grid with the 07-04 race/slowdown-fixed dll.

Background: the pre-07-04 CUDA path serialized slot inserts on a spinlock
(~130x slowdown) and dropped pixels schedule-dependently at capacity
(spurious zero cells + run-to-run nondeterminism). The 07-04 build uses a
lock-free CAS insert + deterministic 63-pixel truncation. See
Tomo_Shell2026-dev/TODO_CUDA_issues_2026-07-04.md. Every stored CUDA grid is
therefore stale and recomputed here.

Mirror of resweep_int3_new_dll.py for the CUDA backend:
  * per cache npz `{stem}_tomo_cuda_{step}deg_{ca}deg.npz`, skipped when marked
    `dll_cudafix`, else re-swept and overwritten in place (markers
    `regenerated`, `dll_cudafix`); dll_sec = fresh single-session t_CUDA (S1);
  * for the record combo (JSON angle_step/critical_angle, 1deg/60deg) the
    contour HTML and JSON tomo_cuda_* fields are refreshed. The E3 pending
    flag (set when its best was a spurious zero) is cleared by this update.
Orphan grids whose mesh is gone are left untouched and reported.

Usage: python scripts/resweep_cuda_new_dll.py [stem ...]
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import scripts.G5Test as g5  # noqa: E402
from cpp_src.Tomo_GPU2026.tomo_cpu import compute_tomo_cuda_vss_grid, tomo_best_row  # noqa: E402

OUT_DIR = PROJECT_ROOT / "Experimental" / "G5Test"
SFTF_RESULT_DIR = OUT_DIR / "SFTF_result"
CUDA_CACHE = OUT_DIR / "tomo_cuda_cache"
MESH_DIR = PROJECT_ROOT.parent / "sftf_Mesh_Data" / "g5test"

CACHE_RE = re.compile(r"^(?P<stem>.+)_tomo_cuda_(?P<step>[0-9p.]+)deg_(?P<ca>[0-9p.]+)deg\.npz$")
MESH_EXTS = {".stl", ".obj", ".ply", ".off", ".3mf", ".glb"}


def mesh_path_for(stem: str) -> Path | None:
    matches = sorted(p for p in MESH_DIR.glob(stem + ".*") if p.suffix.lower() in MESH_EXTS)
    return matches[0] if matches else None


def main() -> None:
    only = set(sys.argv[1:])

    jobs: dict[str, list[tuple[float, float, Path]]] = {}
    for npz_path in sorted(CUDA_CACHE.glob("*_tomo_cuda_*deg_*deg.npz")):
        m = CACHE_RE.match(npz_path.name)
        if not m:
            print(f"[skip] unrecognized cache name {npz_path.name}", flush=True)
            continue
        stem = m.group("stem")
        if only and stem not in only:
            continue
        step = float(m.group("step").replace("p", "."))
        ca = float(m.group("ca").replace("p", "."))
        jobs.setdefault(stem, []).append((step, ca, npz_path))

    for stem in sorted(jobs):  # A -> E: cheap groups land first
        mesh_path = mesh_path_for(stem)
        if mesh_path is None:
            print(f"== {stem}: ORPHAN (mesh not in roster), left untouched ==", flush=True)
            continue
        print(f"== {stem} ({mesh_path.name}) ==", flush=True)

        json_path = SFTF_RESULT_DIR / f"{stem}.json"
        record = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else None
        rec_step = float(record.get("angle_step_deg") or 1.0) if record else 1.0
        rec_ca = float(record.get("critical_angle_deg") or 60.0) if record else 60.0

        for step, ca, npz_path in sorted(jobs[stem], key=lambda c: (-c[0], c[1])):
            try:
                with np.load(npz_path, allow_pickle=False) as old:
                    if "dll_cudafix" in old.files:
                        print(f"  [tomo_cuda {step:g}deg/{ca:g}deg] already re-swept; skip", flush=True)
                        continue
            except Exception:
                pass  # unreadable -> recompute

            start = time.perf_counter()
            try:
                tomo = compute_tomo_cuda_vss_grid(mesh_path, critical_angle=ca, angle_step=step)
            except Exception as exc:
                print(f"  [tomo_cuda {step:g}deg/{ca:g}deg] FAILED: {type(exc).__name__}: {exc}", flush=True)
                if record is not None and (step, ca) == (rec_step, rec_ca):
                    record["tomo_cuda_error"] = f"{type(exc).__name__}: {exc}"
                    json_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
                continue
            dll_sec = time.perf_counter() - start
            yaw = np.asarray(tomo["yaw_values"], dtype=np.float64)
            pitch = np.asarray(tomo["pitch_values"], dtype=np.float64)
            grid = np.asarray(tomo["vss_grid"], dtype=np.float64)
            np.savez_compressed(npz_path, yaw_values=yaw, pitch_values=pitch,
                                vss_grid=grid, dll_sec=np.float64(dll_sec),
                                regenerated=np.int8(1), dll_cudafix=np.int8(1))
            best = tomo_best_row(yaw, pitch, grid)
            print(f"  [tomo_cuda {step:g}deg/{ca:g}deg] {dll_sec:.1f}s "
                  f"best vss={best['vss']:.6g} yaw={best['yaw']:.1f} pitch={best['pitch']:.1f} "
                  f"zeros={(grid == 0).sum()}", flush=True)

            if record is not None and (step, ca) == (rec_step, rec_ca):
                fig = g5.build_tomo_contour_figure(stem, yaw, pitch, grid, method="TOMO_CUDA")
                fig.write_html(OUT_DIR / f"{stem}_tomo_cuda.html", include_plotlyjs="cdn")
                record.update({
                    "tomo_cuda_dll_sec": dll_sec, "tomo_cuda_cached": False,
                    "tomo_cuda_html": f"{stem}_tomo_cuda.html",
                    "tomo_cuda_best": best, "tomo_cuda_error": None,
                })
                json_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

    print("RESWEEP DONE", flush=True)


if __name__ == "__main__":
    main()
