"""Measure paper-protocol per-mesh workloads on the five Group C development meshes.

Replicates the TDP v2 external-audit protocol on Group C (Bunny, Manikin,
Dragon, Happy, Lucy) so the four workloads of main-text Figure 6 can be shown
per mesh instead of as external-set means:

- SFTF candidate generation: 2,048 Fibonacci directions, K=8,192 samples,
  timed exactly like ``analyze_tdp_v2_tomo_external.evaluate_v2_arrays``.
- Dense TOMO sweep: reuses the retimed 2026-07-05 exclusive-interval
  measurements (``tomo_int3_dll_sec`` in Experimental/G5Test/SFTF_result).
- Cura/Prusa panel: identical union of 64 fixed Fibonacci directions, the
  uniform/SFTF/selective anchors at the 2,400-cell budget, and +/-5 degree
  yaw/pitch offsets, sliced sequentially (one direction at a time) by
  CuraEngine 5.13 and PrusaSlicer 2.9.6 with the TDP v2 profiles.

Phases:  --sftf-only  -> candidate generation + anchors only (fast)
         (default)    -> everything, resumable via the raw JSONL
         --summarize  -> aggregate existing rows into groupc_summary.json
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
CURA_CLI_SRC = Path(r"D:\__SFTF_Projects(2026)\_Cura_CLI\python\src")
MESH_DIR = Path(r"D:\__SFTF_Projects(2026)\sftf_Mesh_Data\g5test")
GRID_DIR = PROJECT_ROOT / "Experimental" / "etc"
G5_RESULT_DIR = PROJECT_ROOT / "Experimental" / "G5Test" / "SFTF_result"
SNAPSHOT_ROOT = PROJECT_ROOT / "draft" / "TDP_v2"
PRUSA_EXE = Path(
    r"D:\__PFTF_Projects(2026)\_tools_prusa\extracted\PrusaSlicer-2.9.6"
    r"\prusa-slicer-console.exe"
)
PRUSA_PROFILE = SNAPSHOT_ROOT / "profiles" / "prusa_support_tdp_v2.ini"
CANDIDATE_DIR = HERE / "candidates"
RAW_JSONL = HERE / "groupc_raw.jsonl"
SUMMARY_JSON = HERE / "groupc_summary.json"

BUDGET = 2400
CANDIDATE_COUNT = 2048
FIXED_DIRECTIONS = 64
OFFSET_DEG = 5.0
TARGET_DIAGONAL_MM = 140.0
CURA_ANGLE = 60.0
PRUSA_THRESHOLD = 30.0

MESHES = [
    ("Group_C1_Bunny_69k", "(1)Bunny_69k", "Bunny"),
    ("Group_C2_manikin", "(2)manikin", "Manikin"),
    ("Group_C3_dragon_100k_1.5x", "(3)dragon_100k_1.5x", "Dragon"),
    ("Group_C4_happy_50k_0.75x", "(4)happy_50k_0.75x", "Happy"),
    ("Group_C5_lucy_50k", "(5)lucy_50k", "Lucy"),
]

for extra in (str(PROJECT_ROOT / "python_src"), str(CURA_CLI_SRC)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from SupportFlowTensorField.sftf_v2 import (  # noqa: E402
    SFTFV2Config,
    deterministic_surface_samples,
    evaluate_sftf_v2,
)
from cura_cli import mesh_rotation  # noqa: E402
from cura_cli.cura_slicer import CuraSlicer  # noqa: E402
from cura_cli.gcode_support import parse_gcode_support  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fibonacci_directions(count: int) -> np.ndarray:
    i = np.arange(int(count), dtype=np.float64)
    z = 1.0 - 2.0 * (i + 0.5) / float(count)
    angle = 2.0 * np.pi * i / ((1.0 + math.sqrt(5.0)) * 0.5)
    radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    return np.column_stack((radius * np.cos(angle), radius * np.sin(angle), z))


def grid_direction_vectors(yaw_deg: np.ndarray, pitch_deg: np.ndarray) -> np.ndarray:
    yaw = np.deg2rad(np.rint(np.asarray(yaw_deg, dtype=np.float64)))[None, :]
    pitch = np.deg2rad(np.rint(np.asarray(pitch_deg, dtype=np.float64)))[:, None]
    sin_p = np.sin(pitch)
    cos_p = np.cos(pitch)
    sin_y = np.sin(yaw)
    cos_y = np.cos(yaw)
    x = np.broadcast_to(-sin_p, (len(pitch_deg), len(yaw_deg)))
    y = cos_p * sin_y
    z = cos_p * cos_y
    return np.stack((x, y, z), axis=-1).reshape(-1, 3)


def canonical_grid_cells(yaw_deg: np.ndarray, pitch_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    directions = grid_direction_vectors(yaw_deg, pitch_deg)
    _unique, first = np.unique(np.round(directions, 8), axis=0, return_index=True)
    flat = np.sort(first.astype(np.int64))
    return flat, directions[flat]


def nearest_grid_flat(direction: np.ndarray, yaw_deg: np.ndarray, pitch_deg: np.ndarray) -> int:
    unit = np.asarray(direction, dtype=np.float64)
    unit /= max(float(np.linalg.norm(unit)), 1.0e-15)
    pitch_target = (-math.degrees(math.asin(float(np.clip(unit[0], -1.0, 1.0))))) % 360.0
    yaw_target = math.degrees(math.atan2(float(unit[1]), float(unit[2]))) % 360.0

    def nearest(values: np.ndarray, target: float) -> int:
        delta = np.abs((np.asarray(values) - target + 180.0) % 360.0 - 180.0)
        return int(np.argmin(delta))

    return nearest(pitch_deg, pitch_target) * len(yaw_deg) + nearest(yaw_deg, yaw_target)


def nms_basins(directions: np.ndarray, scores: np.ndarray, *, count: int = 24,
               separation_deg: float = 12.0) -> np.ndarray:
    order = np.lexsort((np.arange(len(scores), dtype=np.int64), scores))
    cosine = math.cos(math.radians(float(separation_deg)))
    selected: list[int] = []
    for index in order:
        direction = directions[int(index)]
        if selected and np.max(directions[selected] @ direction) > cosine:
            continue
        selected.append(int(index))
        if len(selected) >= int(count):
            break
    return np.asarray(selected, dtype=np.int64)


def expand_around_basins(basin_directions: np.ndarray, canonical_flat: np.ndarray,
                         canonical_directions: np.ndarray, budget: int) -> np.ndarray:
    proximity = np.max(canonical_directions @ basin_directions.T, axis=1)
    order = np.lexsort((canonical_flat, -proximity))
    return canonical_flat[order[: int(budget)]]


def uniform_cells(yaw_deg: np.ndarray, pitch_deg: np.ndarray, budget: int) -> np.ndarray:
    selected: list[int] = []
    seen: set[int] = set()
    for count in (int(budget), int(budget) * 4, int(budget) * 8):
        for direction in fibonacci_directions(count):
            flat = nearest_grid_flat(direction, yaw_deg, pitch_deg)
            if flat in seen:
                continue
            seen.add(flat)
            selected.append(flat)
            if len(selected) >= int(budget):
                return np.asarray(selected, dtype=np.int64)
    raise RuntimeError(f"could not map {budget} unique uniform cells")


def evaluate_v2_arrays(mesh: trimesh.Trimesh, directions: np.ndarray,
                       sample_count: int) -> tuple[np.ndarray, np.ndarray, float]:
    config = SFTFV2Config(sample_count=int(sample_count), critical_angle_deg=60.0)
    surface = deterministic_surface_samples(mesh, int(sample_count))
    started = time.perf_counter()
    values = [
        evaluate_sftf_v2(mesh, direction, config=config, samples=surface)
        for direction in directions
    ]
    elapsed = time.perf_counter() - started
    return (
        np.asarray([value.score for value in values], dtype=np.float64),
        np.asarray([value.skew_ratio for value in values], dtype=np.float64),
        elapsed,
    )


def policy_value(grid_flat: np.ndarray, cells: np.ndarray) -> tuple[float, int]:
    values = grid_flat[np.asarray(cells, dtype=np.int64)]
    local = int(np.nanargmin(values))
    return float(values[local]), int(cells[local])


def panel_for_mesh(anchors_row: dict[str, Any], yaw: np.ndarray, pitch: np.ndarray,
                   tomo_grid: np.ndarray) -> list[dict[str, Any]]:
    by_flat: dict[int, dict[str, Any]] = {}

    def add(flat: int, source: str) -> None:
        flat = int(flat)
        if flat < 0 or flat >= len(yaw) * len(pitch):
            raise IndexError(flat)
        row = by_flat.setdefault(
            flat,
            {
                "direction_id": f"g{flat:06d}",
                "grid_flat": flat,
                "yaw_deg": float(yaw[flat % len(yaw)]),
                "pitch_deg": float(pitch[flat // len(yaw)]),
                "tomo_vss": float(tomo_grid.reshape(-1)[flat]),
                "sources": [],
            },
        )
        if source not in row["sources"]:
            row["sources"].append(source)

    for index, direction in enumerate(fibonacci_directions(FIXED_DIRECTIONS)):
        add(nearest_grid_flat(direction, yaw, pitch), f"fixed_fibonacci_{index:02d}")

    anchors = {
        "uniform_anchor": int(anchors_row["uniform_best_flat"]),
        "sftf_anchor": int(anchors_row["sftf_v2_best_flat"]),
        "selective_anchor": int(anchors_row["selective_best_flat"]),
    }
    for label, flat in anchors.items():
        add(flat, label)

    for label in ("uniform_anchor", "sftf_anchor"):
        flat = anchors[label]
        yi = flat % len(yaw)
        pi = flat // len(yaw)
        base_yaw = float(yaw[yi])
        base_pitch = float(pitch[pi])
        for suffix, dy, dp in (
            ("yaw_minus", -OFFSET_DEG, 0.0),
            ("yaw_plus", OFFSET_DEG, 0.0),
            ("pitch_minus", 0.0, -OFFSET_DEG),
            ("pitch_plus", 0.0, OFFSET_DEG),
        ):
            y_delta = np.abs((yaw - (base_yaw + dy) + 180.0) % 360.0 - 180.0)
            p_delta = np.abs((pitch - (base_pitch + dp) + 180.0) % 360.0 - 180.0)
            offset_flat = int(np.argmin(p_delta)) * len(yaw) + int(np.argmin(y_delta))
            add(offset_flat, f"{label}_{suffix}_{OFFSET_DEG:g}deg")

    return sorted(by_flat.values(), key=lambda item: int(item["grid_flat"]))


def run_prusa(stl: Path, gcode: Path) -> tuple[dict[str, float], float, str]:
    command = [
        str(PRUSA_EXE),
        "--load",
        str(PRUSA_PROFILE),
        "--support-material-threshold",
        str(float(PRUSA_THRESHOLD)),
        "--gcode-comments",
        "--dont-arrange",
        "--ensure-on-bed",
        "--export-gcode",
        "--output",
        str(gcode),
        str(stl),
    ]
    started = time.perf_counter()
    proc = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=1200,
    )
    elapsed = time.perf_counter() - started
    if proc.returncode != 0 or not gcode.is_file():
        diagnostic = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()
        return {}, elapsed, diagnostic[-1500:]
    return parse_gcode_support(gcode).as_dict(), elapsed, ""


def load_raw(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def append_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush()


def sftf_and_anchors(name: str) -> dict[str, Any]:
    """Candidate generation (cached) + anchor flats at the 2,400-cell budget."""
    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CANDIDATE_DIR / f"{name}.npz"
    grid_stub = dict(MESHES_BY_NAME[name].items())
    grid_path = GRID_DIR / f"{grid_stub['grid']}_tomo_int3_vss_grid_1deg_60deg.npz"
    with np.load(grid_path, allow_pickle=False) as data:
        yaw = np.asarray(data["yaw_values"], dtype=np.float64)
        pitch = np.asarray(data["pitch_values"], dtype=np.float64)
        grid = np.asarray(data["vss_grid"], dtype=np.float64)
    grid_flat = grid.reshape(-1)
    canonical_flat, canonical_directions = canonical_grid_cells(yaw, pitch)
    directions = fibonacci_directions(CANDIDATE_COUNT)

    if cache.is_file():
        with np.load(cache, allow_pickle=False) as data:
            scores_4096 = np.asarray(data["scores_4096"], dtype=np.float64)
            scores_8192 = np.asarray(data["scores_8192"], dtype=np.float64)
            skew_8192 = np.asarray(data["skew_8192"], dtype=np.float64)
            time_4096 = float(data["time_4096_s"])
            time_8192 = float(data["time_8192_s"])
    else:
        mesh = trimesh.load_mesh(str(MESH_DIR / f"{name}.ply"), force="mesh", process=False)
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)
        scores_4096, skew_4096, time_4096 = evaluate_v2_arrays(mesh, directions, 4096)
        scores_8192, skew_8192, time_8192 = evaluate_v2_arrays(mesh, directions, 8192)
        with cache.open("wb") as handle:
            np.savez_compressed(
                handle,
                directions=directions,
                scores_4096=scores_4096,
                scores_8192=scores_8192,
                skew_4096=skew_4096,
                skew_8192=skew_8192,
                time_4096_s=np.asarray(time_4096),
                time_8192_s=np.asarray(time_8192),
            )

    basin_ids_4096 = nms_basins(directions, scores_4096)
    basin_ids_8192 = nms_basins(directions, scores_8192)
    basins_4096 = directions[basin_ids_4096]
    basins_8192 = directions[basin_ids_8192]
    best_alignment = np.max(basins_8192 @ basins_4096.T, axis=1)
    stability_angle = float(np.degrees(np.mean(np.arccos(np.clip(best_alignment, -1.0, 1.0)))))
    score_median = float(np.median(scores_8192))
    score_dispersion = float(
        (np.percentile(scores_8192, 90) - np.percentile(scores_8192, 10))
        / max(abs(score_median), 1.0e-12)
    )
    top_skew = float(np.median(skew_8192[basin_ids_8192[:8]]))
    accepted = bool(stability_angle <= 15.0 and score_dispersion >= 0.08 and top_skew <= 1.0)

    sftf_cells = expand_around_basins(basins_8192, canonical_flat, canonical_directions, BUDGET)
    matched_uniform = uniform_cells(yaw, pitch, BUDGET)
    selective_cells = sftf_cells if accepted else matched_uniform

    uniform_value, uniform_flat = policy_value(grid_flat, matched_uniform)
    sftf_value, sftf_flat = policy_value(grid_flat, sftf_cells)
    selective_value, selective_flat = policy_value(grid_flat, selective_cells)

    return {
        "mesh": name,
        "sftf_k4096_wall_s": time_4096,
        "sftf_k8192_wall_s": time_8192,
        "gate_accepted": accepted,
        "stability_mean_angle_deg": stability_angle,
        "score_dispersion_q90_q10_over_median": score_dispersion,
        "top8_median_skew_ratio": top_skew,
        "uniform_best_flat": uniform_flat,
        "sftf_v2_best_flat": sftf_flat,
        "selective_best_flat": selective_flat,
        "uniform_vss": uniform_value,
        "sftf_v2_vss": sftf_value,
        "selective_vss": selective_value,
        "yaw": yaw,
        "pitch": pitch,
        "grid": grid,
    }


MESHES_BY_NAME = {name: {"grid": grid, "label": label} for name, grid, label in MESHES}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sftf-only", action="store_true")
    parser.add_argument("--summarize", action="store_true")
    args = parser.parse_args()

    anchor_rows: dict[str, dict[str, Any]] = {}
    if not args.summarize:
        for name, _grid, label in MESHES:
            row = sftf_and_anchors(name)
            anchor_rows[name] = row
            print(
                f"[sftf] {name}: k8192={row['sftf_k8192_wall_s']:.2f}s "
                f"k4096={row['sftf_k4096_wall_s']:.2f}s gate={row['gate_accepted']} "
                f"anchors u/s/sel={row['uniform_best_flat']}/{row['sftf_v2_best_flat']}"
                f"/{row['selective_best_flat']}",
                flush=True,
            )
        anchors_out = {
            name: {k: v for k, v in row.items() if k not in ("yaw", "pitch", "grid")}
            for name, row in anchor_rows.items()
        }
        (HERE / "groupc_sftf_anchors.json").write_text(
            json.dumps(anchors_out, indent=2), encoding="utf-8"
        )
        if args.sftf_only:
            return

        existing = load_raw(RAW_JSONL)
        completed = {
            (str(r["mesh"]), str(r["direction_id"]), str(r["engine"]))
            for r in existing
            if bool(r.get("ok"))
        }
        cura = CuraSlicer(engine="modern", critical_angle=CURA_ANGLE)
        for name, _grid, label in MESHES:
            row = anchor_rows[name]
            panel = panel_for_mesh(row, row["yaw"], row["pitch"], row["grid"])
            mesh = trimesh.load_mesh(str(MESH_DIR / f"{name}.ply"), force="mesh", process=False)
            if isinstance(mesh, trimesh.Scene):
                mesh = mesh.dump(concatenate=True)
            diagonal = float(np.linalg.norm(mesh.extents))
            mesh.apply_scale(TARGET_DIAGONAL_MM / diagonal)
            pending = [
                d for d in panel
                if not all(
                    (name, d["direction_id"], engine) in completed
                    for engine in ("cura_5_13", "prusa_2_9_6")
                )
            ]
            print(f"[panel] {name}: panel={len(panel)} pending={len(pending)}", flush=True)
            for index, direction in enumerate(pending, start=1):
                started_utc = utc_now()
                with tempfile.TemporaryDirectory(prefix=f"gc_{name}_{direction['direction_id']}_") as tmp:
                    work = Path(tmp)
                    stl = work / "oriented.stl"
                    mesh_rotation.write_oriented_stl(
                        mesh, float(direction["yaw_deg"]), float(direction["pitch_deg"]), stl
                    )
                    common = {
                        "mesh": name,
                        "direction_id": direction["direction_id"],
                        "grid_flat": int(direction["grid_flat"]),
                        "yaw_deg": float(direction["yaw_deg"]),
                        "pitch_deg": float(direction["pitch_deg"]),
                        "tomo_vss": float(direction["tomo_vss"]),
                        "sources": list(direction["sources"]),
                        "started_utc": started_utc,
                    }
                    cura_started = time.perf_counter()
                    cura_result = cura.slice_stl(stl)
                    cura_elapsed = time.perf_counter() - cura_started
                    rows = [
                        {
                            **common,
                            "engine": "cura_5_13",
                            "support_volume_mm3": float(cura_result.support_volume_mm3),
                            "total_volume_mm3": float(cura_result.total_volume_mm3),
                            "elapsed_wall_s": float(cura_elapsed),
                            "ok": bool(cura_result.ok),
                            "error": str(cura_result.error),
                            "completed_utc": utc_now(),
                        }
                    ]
                    prusa_report, prusa_elapsed, prusa_error = run_prusa(stl, work / "prusa.gcode")
                    rows.append(
                        {
                            **common,
                            "engine": "prusa_2_9_6",
                            "support_volume_mm3": float(prusa_report.get("support_volume_mm3", math.nan)),
                            "total_volume_mm3": float(prusa_report.get("total_volume_mm3", math.nan)),
                            "elapsed_wall_s": float(prusa_elapsed),
                            "ok": not bool(prusa_error),
                            "error": prusa_error,
                            "completed_utc": utc_now(),
                        }
                    )
                append_rows(RAW_JSONL, rows)
                for r in rows:
                    if bool(r.get("ok")):
                        completed.add((name, r["direction_id"], r["engine"]))
                if index == 1 or index % 10 == 0 or index == len(pending):
                    print(
                        f"  [{name}] {index}/{len(pending)} "
                        f"cura={rows[0]['elapsed_wall_s']:.1f}s ok={rows[0]['ok']} "
                        f"prusa={rows[1]['elapsed_wall_s']:.1f}s ok={rows[1]['ok']}",
                        flush=True,
                    )

    # ---- summary ----
    raw = load_raw(RAW_JSONL)
    anchors_out = json.loads((HERE / "groupc_sftf_anchors.json").read_text(encoding="utf-8"))
    summary: dict[str, Any] = {"created_utc": utc_now(), "meshes": {}}
    for name, _grid, label in MESHES:
        g5 = json.loads((G5_RESULT_DIR / f"{name}.json").read_text(encoding="utf-8"))
        mesh_rows = [r for r in raw if r["mesh"] == name and bool(r.get("ok"))]
        cura_rows = [r for r in mesh_rows if r["engine"] == "cura_5_13"]
        prusa_rows = [r for r in mesh_rows if r["engine"] == "prusa_2_9_6"]
        cura_ids = {r["direction_id"] for r in cura_rows}
        prusa_ids = {r["direction_id"] for r in prusa_rows}
        matched = cura_ids & prusa_ids
        summary["meshes"][name] = {
            "label": label,
            "face_count": int(g5["face_count"]),
            "sftf_k8192_wall_s": float(anchors_out[name]["sftf_k8192_wall_s"]),
            "dense_tomo_wall_s": float(g5["tomo_int3_dll_sec"]),
            "dense_tomo_source": "Experimental/G5Test retime 2026-07-05 (sequential, exclusive)",
            "panel_directions_matched": len(matched),
            "cura_panel_total_s": float(sum(r["elapsed_wall_s"] for r in cura_rows if r["direction_id"] in matched)),
            "prusa_panel_total_s": float(sum(r["elapsed_wall_s"] for r in prusa_rows if r["direction_id"] in matched)),
            "cura_per_direction_mean_s": float(np.mean([r["elapsed_wall_s"] for r in cura_rows if r["direction_id"] in matched])) if matched else math.nan,
            "prusa_per_direction_mean_s": float(np.mean([r["elapsed_wall_s"] for r in prusa_rows if r["direction_id"] in matched])) if matched else math.nan,
            "cura_failures": len([r for r in raw if r["mesh"] == name and r["engine"] == "cura_5_13" and not r.get("ok")]),
            "prusa_failures": len([r for r in raw if r["mesh"] == name and r["engine"] == "prusa_2_9_6" and not r.get("ok")]),
            "gate_accepted": bool(anchors_out[name]["gate_accepted"]),
        }
        print(json.dumps({name: summary["meshes"][name]}, indent=1))
    summary["protocol"] = {
        "budget_cells": BUDGET,
        "candidate_count": CANDIDATE_COUNT,
        "sample_count": 8192,
        "fixed_fibonacci_directions": FIXED_DIRECTIONS,
        "offset_deg": OFFSET_DEG,
        "target_diagonal_mm": TARGET_DIAGONAL_MM,
        "cura_angle_deg": CURA_ANGLE,
        "prusa_threshold_deg": PRUSA_THRESHOLD,
        "slicing_concurrency": 1,
        "prusa_profile": str(PRUSA_PROFILE),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("summary written:", SUMMARY_JSON)


if __name__ == "__main__":
    main()
