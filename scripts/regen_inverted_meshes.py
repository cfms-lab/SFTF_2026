"""Regenerate SFTF / TOMO artifacts for the five inside-out group meshes.

The five meshes (A2 sphere, B4 pipe_elbow, D10 37416, E8 64445, E9 64446) have
fully inverted winding+normals in their source files. The loaders now repair
orientation at load time, so every artifact recomputed here reflects correct
outward normals. This script surgically redoes only the affected meshes,
preserving the repo's stored-grid naming (`tomo_int3_cache` / `_tomo_int3_`)
and the per-mesh JSON key names (`tomo_int3_*`) used by the sibling records.

Per mesh:
  1. Python SFTF: candidate pool -> landscape HTML, candidates CSV, JSON fields
  2. SFTF C++ (sftf_cpp.dll): optimal/worst directions + compute_ms
  3. Every existing TOMO grid cache combo (backend x step x critical angle) is
     re-swept and the .npz overwritten in place
  4. Contour HTMLs ({stem}_tomo_int3.html / {stem}_tomo_cuda.html) rebuilt from
     the grid matching the record's angle_step/critical_angle (1deg/60deg)
  5. JSON tomo_int3_* / tomo_cuda_* best/timing fields updated

Incremental: JSON is saved after each stage; grids already re-swept in a
previous run of this script (marker key `regenerated`) are skipped.
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

import scripts.G5Test as g5  # noqa: E402  (helpers; main() not invoked)
from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    SUPPORT_FLOW_COARSE_DIRECTION_COUNT,
    evaluate_support_flow_candidate_pool,
    load_mesh,
    support_flow_directions_from_candidate_pool,
)
from cpp_src.Tomo_GPU2026.tomo_cpu import (  # noqa: E402
    compute_tomo_cpu_vss_grid,
    compute_tomo_cuda_vss_grid,
    tomo_best_row,
)
from cpp_src.Tomo_GPU2026.tomo_sftf import compute_sftf_directions_cpp  # noqa: E402

OUT_DIR = PROJECT_ROOT / "Experimental" / "G5Test"
SFTF_RESULT_DIR = OUT_DIR / "SFTF_result"
MESH_DIR = PROJECT_ROOT.parent / "sftf_Mesh_Data" / "g5test"

STEMS = [
    "Group_A2_sphere",
    "Group_B4_pipe_elbow",
    "Group_D10_37416",
    "Group_E8_64445",
    "Group_E9_64446",
]

# stored-grid dirs use the pre-rename naming kept for the figure scripts
BACKENDS = {
    "tomo_int3": (OUT_DIR / "tomo_int3_cache", compute_tomo_cpu_vss_grid, "TOMO_CPU"),
    "tomo_cuda": (OUT_DIR / "tomo_cuda_cache", compute_tomo_cuda_vss_grid, "TOMO_CUDA"),
}
CACHE_RE = re.compile(r"_(tomo_int3|tomo_cuda)_([0-9p.]+)deg_([0-9p.]+)deg\.npz$")


def mesh_path_for(stem: str) -> Path:
    matches = sorted(MESH_DIR.glob(stem + ".*"))
    matches = [p for p in matches if p.suffix.lower() in {".stl", ".obj", ".ply", ".off", ".3mf", ".glb"}]
    if not matches:
        raise FileNotFoundError(stem)
    return matches[0]


def save_record(stem: str, record: dict) -> None:
    path = SFTF_RESULT_DIR / f"{stem}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def regen_sftf_python(stem: str, mesh_path: Path, record: dict) -> None:
    start = time.perf_counter()
    mesh = load_mesh(str(mesh_path))
    pool = evaluate_support_flow_candidate_pool(mesh)
    directions = support_flow_directions_from_candidate_pool(pool)
    elapsed = time.perf_counter() - start

    scores = np.asarray([row[0] for row in pool], dtype=np.float64) if pool else np.zeros(0)
    figure = g5.build_landscape_figure(stem, pool, directions)
    html_path = SFTF_RESULT_DIR / f"{stem}.html"
    figure.write_html(html_path, include_plotlyjs="cdn")
    csv_path = SFTF_RESULT_DIR / f"{stem}_candidates.csv"
    g5.save_candidate_pool_csv(csv_path, pool)

    record.update({
        "face_count": int(len(mesh.faces)),
        "coarse_direction_count": int(SUPPORT_FLOW_COARSE_DIRECTION_COUNT),
        "candidate_pool_size": int(len(pool)),
        "score_min": float(np.min(scores)) if scores.size else None,
        "score_median": float(np.median(scores)) if scores.size else None,
        "score_max": float(np.max(scores)) if scores.size else None,
        "top_directions": [g5.direction_record(item) for item in directions],
        "html": f"SFTF_result/{html_path.name}",
        "candidates_csv": f"SFTF_result/{csv_path.name}",
        "elapsed_sec": elapsed,
    })
    top = record["top_directions"][0] if record["top_directions"] else {}
    print(f"  [SFTF py] {elapsed:.2f}s top1 hit={top.get('hit_count')} "
          f"R={top.get('rayleigh_score'):.4g} P={top.get('pair_score'):.4g} "
          f"B={top.get('bed_score'):.4g}", flush=True)


def regen_sftf_cpp(stem: str, mesh_path: Path, record: dict) -> None:
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


def regen_tomo_grids(stem: str, mesh_path: Path, record: dict) -> None:
    rec_step = float(record.get("angle_step_deg") or 1.0)
    rec_ca = float(record.get("critical_angle_deg") or 60.0)

    for tag, (cache_dir, compute_fn, method) in BACKENDS.items():
        for npz_path in sorted(cache_dir.glob(f"{stem}_{tag}_*deg_*deg.npz")):
            m = CACHE_RE.search(npz_path.name)
            if not m:
                print(f"  [skip] unrecognized cache name {npz_path.name}", flush=True)
                continue
            step = float(m.group(2).replace("p", "."))
            ca = float(m.group(3).replace("p", "."))
            try:
                with np.load(npz_path, allow_pickle=False) as old:
                    if "regenerated" in old.files:
                        print(f"  [{tag} {step:g}deg/{ca:g}deg] already regenerated; skip", flush=True)
                        # still refresh record/contour if this is the record combo
                        grid = {k: np.asarray(old[k], dtype=np.float64)
                                for k in ("yaw_values", "pitch_values", "vss_grid")}
                        dll_sec = float(old["dll_sec"]) if "dll_sec" in old.files else None
                        if step == rec_step and ca == rec_ca:
                            _apply_record_combo(stem, tag, method, grid, dll_sec, record)
                        continue
            except Exception:
                pass  # unreadable -> recompute below

            start = time.perf_counter()
            try:
                tomo = compute_fn(mesh_path, critical_angle=ca, angle_step=step)
            except Exception as exc:
                print(f"  [{tag} {step:g}deg/{ca:g}deg] FAILED: {type(exc).__name__}: {exc}", flush=True)
                if step == rec_step and ca == rec_ca:
                    record[f"{tag}_error"] = f"{type(exc).__name__}: {exc}"
                continue
            dll_sec = time.perf_counter() - start
            grid = {
                "yaw_values": np.asarray(tomo["yaw_values"], dtype=np.float64),
                "pitch_values": np.asarray(tomo["pitch_values"], dtype=np.float64),
                "vss_grid": np.asarray(tomo["vss_grid"], dtype=np.float64),
            }
            np.savez_compressed(
                npz_path,
                yaw_values=grid["yaw_values"],
                pitch_values=grid["pitch_values"],
                vss_grid=grid["vss_grid"],
                dll_sec=np.float64(dll_sec),
                regenerated=np.int8(1),
            )
            best = tomo_best_row(grid["yaw_values"], grid["pitch_values"], grid["vss_grid"])
            print(f"  [{tag} {step:g}deg/{ca:g}deg] {dll_sec:.1f}s best vss={best['vss']:.6g} "
                  f"yaw={best['yaw']:.1f} pitch={best['pitch']:.1f}", flush=True)
            if step == rec_step and ca == rec_ca:
                _apply_record_combo(stem, tag, method, grid, dll_sec, record)
                save_record(stem, record)


def _apply_record_combo(stem: str, tag: str, method: str, grid: dict, dll_sec, record: dict) -> None:
    """Update the per-mesh JSON fields + contour HTML for the record's combo."""
    fig = g5.build_tomo_contour_figure(
        stem, grid["yaw_values"], grid["pitch_values"], grid["vss_grid"], method=method
    )
    contour_path = OUT_DIR / f"{stem}_{tag}.html"
    fig.write_html(contour_path, include_plotlyjs="cdn")
    record[f"{tag}_dll_sec"] = dll_sec
    record[f"{tag}_cached"] = False
    record[f"{tag}_html"] = contour_path.name
    record[f"{tag}_best"] = tomo_best_row(grid["yaw_values"], grid["pitch_values"], grid["vss_grid"])
    record[f"{tag}_error"] = None


def main() -> None:
    only = set(sys.argv[1:])
    for stem in STEMS:
        if only and stem not in only:
            continue
        mesh_path = mesh_path_for(stem)
        json_path = SFTF_RESULT_DIR / f"{stem}.json"
        record = json.loads(json_path.read_text(encoding="utf-8"))
        print(f"== {stem} ({mesh_path.name}) ==", flush=True)

        regen_sftf_python(stem, mesh_path, record)
        save_record(stem, record)

        regen_sftf_cpp(stem, mesh_path, record)
        save_record(stem, record)

        regen_tomo_grids(stem, mesh_path, record)
        save_record(stem, record)

    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
