"""Phase A onboarding for the swapped-in E-group meshes (CPU only).

For each of Group_E2_790253 / Group_E3_931902 / Group_E4_439142 /
Group_E9_82675:
  1. Python SFTF: candidate pool -> landscape HTML, candidates CSV, per-mesh
     JSON (sibling `tomo_int3_*` key convention)
  2. SFTF C++ (sftf_cpp.dll): optimal/worst + compute_ms
  3. TOMO_CPU (TomoSh_INT3) 1deg/60deg sweep  -> tomo_int3_cache npz + contour
     HTML + record best/timing (Supplementary S1 t_CPU, Table-5 audit grid)
  4. TOMO_CPU 3deg/60deg sweep -> npz (3deg audit variant / per-angle tables)

CUDA sweeps are Phase B (GPU currently busy). Incremental: stages already
stored in the JSON / npz marked `regenerated` are skipped, so the script can
be re-run safely.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import scripts.G5Test as g5  # noqa: E402
from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    SUPPORT_FLOW_COARSE_DIRECTION_COUNT,
    evaluate_support_flow_candidate_pool,
    load_mesh,
    support_flow_directions_from_candidate_pool,
)
from cpp_src.Tomo_GPU2026.tomo_cpu import compute_tomo_cpu_vss_grid, tomo_best_row  # noqa: E402
from cpp_src.Tomo_GPU2026.tomo_sftf import compute_sftf_directions_cpp  # noqa: E402
from scripts._mesh_paths import G5_RAW_MESH  # noqa: E402

OUT_DIR = PROJECT_ROOT / "Experimental" / "G5Test"
SFTF_RESULT_DIR = OUT_DIR / "SFTF_result"
INT3_CACHE = OUT_DIR / "tomo_int3_cache"
MESH_DIR = G5_RAW_MESH

STEMS = ["Group_E2_790253", "Group_E3_931902", "Group_E4_439142", "Group_E9_82675"]


def blank_record_int3(mesh_path: Path) -> dict:
    """Sibling-convention blank record (`tomo_int3_*` keys, not `tomo_cpu_*`)."""
    group, gid = g5.parse_group_id(mesh_path.stem)
    return {
        "group": group, "group_id": gid, "mesh": mesh_path.name,
        "angle_step_deg": 1.0, "critical_angle_deg": 60.0,
        "face_count": None, "coarse_direction_count": None, "candidate_pool_size": None,
        "score_min": None, "score_median": None, "score_max": None,
        "top_directions": [], "html": None, "candidates_csv": None,
        "elapsed_sec": None,
        "tomo_int3_dll_sec": None, "tomo_int3_cached": None,
        "tomo_int3_html": None, "tomo_int3_best": None, "tomo_int3_error": None,
        "tomo_cuda_dll_sec": None, "tomo_cuda_cached": None,
        "tomo_cuda_html": None, "tomo_cuda_best": None, "tomo_cuda_error": None,
        "sftf_cpp_ms": None, "sftf_cpp_optimal": None,
        "sftf_cpp_worst": None, "sftf_cpp_error": None,
    }


def save_record(stem: str, record: dict) -> None:
    (SFTF_RESULT_DIR / f"{stem}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    for stem in STEMS:
        matches = sorted(p for p in MESH_DIR.glob(stem + ".*")
                         if p.suffix.lower() in {".stl", ".obj", ".ply"})
        if not matches:
            print(f"== {stem}: MESH NOT FOUND, skipping ==", flush=True)
            continue
        mesh_path = matches[0]
        json_path = SFTF_RESULT_DIR / f"{stem}.json"
        record = (json.loads(json_path.read_text(encoding="utf-8"))
                  if json_path.exists() else blank_record_int3(mesh_path))
        print(f"== {stem} ({mesh_path.name}) ==", flush=True)

        # --- 1. Python SFTF ---
        if not record.get("top_directions"):
            start = time.perf_counter()
            mesh = load_mesh(str(mesh_path))
            pool = evaluate_support_flow_candidate_pool(mesh)
            directions = support_flow_directions_from_candidate_pool(pool)
            elapsed = time.perf_counter() - start
            scores = np.asarray([r[0] for r in pool], dtype=np.float64) if pool else np.zeros(0)
            fig = g5.build_landscape_figure(stem, pool, directions)
            fig.write_html(SFTF_RESULT_DIR / f"{stem}.html", include_plotlyjs="cdn")
            g5.save_candidate_pool_csv(SFTF_RESULT_DIR / f"{stem}_candidates.csv", pool)
            record.update({
                "face_count": int(len(mesh.faces)),
                "coarse_direction_count": int(SUPPORT_FLOW_COARSE_DIRECTION_COUNT),
                "candidate_pool_size": int(len(pool)),
                "score_min": float(np.min(scores)) if scores.size else None,
                "score_median": float(np.median(scores)) if scores.size else None,
                "score_max": float(np.max(scores)) if scores.size else None,
                "top_directions": [g5.direction_record(i) for i in directions],
                "html": f"SFTF_result/{stem}.html",
                "candidates_csv": f"SFTF_result/{stem}_candidates.csv",
                "elapsed_sec": elapsed,
            })
            save_record(stem, record)
            top = record["top_directions"][0]
            print(f"  [SFTF py] {elapsed:.2f}s top1 hit={top['hit_count']} "
                  f"R={top['rayleigh_score']:.4g} P={top['pair_score']:.4g} "
                  f"B={top['bed_score']:.4g}", flush=True)
        else:
            print("  [SFTF py] already stored; skip", flush=True)

        # --- 2. SFTF C++ ---
        if record.get("sftf_cpp_ms") is None:
            record["sftf_cpp_error"] = None
            try:
                sftf = compute_sftf_directions_cpp(str(mesh_path))
                record["sftf_cpp_ms"] = float(sftf["compute_ms"])
                record["sftf_cpp_optimal"] = sftf["optimal"]
                record["sftf_cpp_worst"] = sftf["worst"]
                print(f"  [SFTF C++] {record['sftf_cpp_ms']:.1f}ms "
                      f"top1 hit={sftf['optimal'][0].get('hit_count')}", flush=True)
            except Exception as exc:
                record["sftf_cpp_error"] = f"{type(exc).__name__}: {exc}"
                print(f"  [SFTF C++] FAILED: {record['sftf_cpp_error']}", flush=True)
            save_record(stem, record)
        else:
            print("  [SFTF C++] already stored; skip", flush=True)

        # --- 3./4. TOMO_CPU sweeps ---
        for step in (1.0, 3.0):
            npz_path = INT3_CACHE / f"{stem}_tomo_int3_{step:g}deg_60deg.npz"
            if npz_path.exists():
                print(f"  [tomo_int3 {step:g}deg/60deg] cache present; skip", flush=True)
                continue
            start = time.perf_counter()
            try:
                tomo = compute_tomo_cpu_vss_grid(mesh_path, critical_angle=60.0, angle_step=step)
            except Exception as exc:
                print(f"  [tomo_int3 {step:g}deg/60deg] FAILED: {type(exc).__name__}: {exc}", flush=True)
                if step == 1.0:
                    record["tomo_int3_error"] = f"{type(exc).__name__}: {exc}"
                    save_record(stem, record)
                continue
            dll_sec = time.perf_counter() - start
            yaw = np.asarray(tomo["yaw_values"], dtype=np.float64)
            pitch = np.asarray(tomo["pitch_values"], dtype=np.float64)
            grid = np.asarray(tomo["vss_grid"], dtype=np.float64)
            np.savez_compressed(npz_path, yaw_values=yaw, pitch_values=pitch,
                                vss_grid=grid, dll_sec=np.float64(dll_sec),
                                regenerated=np.int8(1))
            best = tomo_best_row(yaw, pitch, grid)
            print(f"  [tomo_int3 {step:g}deg/60deg] {dll_sec:.1f}s "
                  f"best vss={best['vss']:.6g} yaw={best['yaw']:.1f} pitch={best['pitch']:.1f}",
                  flush=True)
            if step == 1.0:
                fig = g5.build_tomo_contour_figure(stem, yaw, pitch, grid, method="TOMO_CPU")
                fig.write_html(OUT_DIR / f"{stem}_tomo_int3.html", include_plotlyjs="cdn")
                record.update({
                    "tomo_int3_dll_sec": dll_sec, "tomo_int3_cached": False,
                    "tomo_int3_html": f"{stem}_tomo_int3.html",
                    "tomo_int3_best": best, "tomo_int3_error": None,
                })
                save_record(stem, record)

    print("PHASE A DONE", flush=True)


if __name__ == "__main__":
    main()
