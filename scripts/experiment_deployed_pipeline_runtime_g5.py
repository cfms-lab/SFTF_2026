"""Measure the deployed G5 pipeline without conflating cache replay and TOMO.

The historical timing tables measured candidate generation and exhaustive
TOMO sweeps separately.  This runner measures the control path itself, one
mesh at a time, and keeps three kinds of time in separate fields:

* current cached replay: candidate/grid/mesh input, ranking, routing, sign
  resolution, local-grid lookup, AVE decision, and escalation lookup;
* historical component timings copied from the original per-mesh SFTF JSON
  and the TOMO ``.npz`` metadata (never added to the replay time);
* optional current fresh Python candidate generation and physical TOMO_CPU
  batch evaluation (``--fresh-candidates --physical-tomo``).

The sign of every candidate axis is selected by comparing +n and -n with the
TOMO verifier before a local window is formed.  The original local-cell budget
does not count the rejected sign probes.  This runner therefore reports both
the original local-window count and the corrected union of sign-resolution and
local-window cells.

By default all 41 evaluable 1-degree/60-degree records are included: 26 with a
positive exhaustive optimum and 15 with a nonpositive optimum.  The latter
have no ratio; absolute and bounding-box-normalized excess are reported.
Three stored grids whose source mesh is no longer present are listed as
skipped.

Examples
--------
Cached replay only (fast)::

    uv run python scripts/experiment_deployed_pipeline_runtime_g5.py

Fresh candidates plus physical TOMO_CPU verification (slow; checkpointed)::

    uv run python scripts/experiment_deployed_pipeline_runtime_g5.py \
        --fresh-candidates --physical-tomo --resume
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# The optional physical verifier must use the same critical angle as the cache.
# This environment variable is read when tomo_cpu is imported.
os.environ["TOMO_CRITICAL_ANGLE"] = "60"

from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    SUPPORT_FLOW_COARSE_DIRECTION_COUNT,
    _spherical_sample_directions,
    evaluate_support_flow_candidate_pool,
    load_mesh,
)
from scripts.experiment_budget_matched_local_baselines import (  # noqa: E402
    _farthest_axis_order,
    _unique_axis_directions,
)
from scripts.experiment_happy_method_g5_audit import (  # noqa: E402
    DEFAULT_BASE_TOP_K,
    DEFAULT_BOUNDARY_GAIN,
    DEFAULT_EDGE_MARGIN_DEGREES,
    DEFAULT_ESCALATE_TOP_K,
    DEFAULT_HIGH_GAIN,
    DEFAULT_HIGH_SUPPORT_FRACTION,
    DEFAULT_LOW_GAIN,
    DEFAULT_MIN_ANGLE_DEGREES,
    DEFAULT_SEVERE_ESCALATE_TOP_K,
    DEFAULT_WINDOW_DEGREES,
    G5_CACHE_DIR,
    G5_CANDIDATE_DIR,
    G5_CANDIDATE_SUFFIX,
    _bbox_volume,
    _cell_on_window_boundary,
    _detector_flags,
    _mesh_path_for_stem,
    _rank_candidates,
    _read_candidate_csv,
    _record_group_from_name,
)
from scripts.experiment_routing_rule_g5 import (  # noqa: E402
    DEFAULT_FLOOR_FACTOR,
    DEFAULT_NMS_DEG,
    DEFAULT_TOP_K,
    FIXED_T1,
    FIXED_T2,
    _route,
)
from scripts.experiment_sftf_budget_curve import _window_cells  # noqa: E402
from scripts.regenerate_sftf_vs_saved_tomo_summary import (  # noqa: E402
    _nearest_grid_orientation,
    _tomo_best,
)

ETC = PROJECT_ROOT / "Experimental" / "etc"
GRID_SUFFIX = "_tomo_int3_1deg_60deg.npz"
EXPECTED_PIPELINE_CSV = ETC / "sftf_deployed_pipeline_g5_records.csv"
DEFAULT_OUTPUT_STEM = "sftf_deployed_pipeline_runtime_g5"
SELECTION_LOGIC_VERSION = "2026-07-11-fresh-uniform200-direct-wall-full41-v2"
EXPECTED_RECORD_COUNT = 41
EXPECTED_RATIO_VALID_COUNT = 26
EXPECTED_NONPOSITIVE_COUNT = 15
EXPECTED_STALE_MESHES: set[str] = set()


def _sha256(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _json_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _seconds(start: float) -> float:
    return float(time.perf_counter() - start)


def _finite(value: float | None) -> float | None:
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _same_periodic_degree(a: float, b: float, *, atol: float = 1e-9) -> bool:
    return abs((float(a) - float(b) + 180.0) % 360.0 - 180.0) <= atol


def _pool_to_candidates(pool: list[tuple]) -> list[dict[str, object]]:
    return [
        {
            "score": float(row[0]),
            "rayleigh": float(row[1]),
            "pair": float(row[2]),
            "bed": float(row[3]),
            "hit": int(row[4]),
            "direction": np.asarray(row[5], dtype=np.float64),
        }
        for row in pool
    ]


def _read_expected_pipeline() -> dict[str, dict[str, str]]:
    if not EXPECTED_PIPELINE_CSV.exists():
        return {}
    with EXPECTED_PIPELINE_CSV.open(newline="", encoding="utf-8") as handle:
        return {row["mesh"]: row for row in csv.DictReader(handle)}


def _load_grid(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, float | None, float]:
    started = time.perf_counter()
    with np.load(path, allow_pickle=False) as data:
        yaw = np.asarray(data["yaw_values"], dtype=np.float64).copy()
        pitch = np.asarray(data["pitch_values"], dtype=np.float64).copy()
        vss = np.asarray(data["vss_grid"], dtype=np.float64).copy()
        historical_dll_s = float(data["dll_sec"]) if "dll_sec" in data.files else None
    return yaw, pitch, vss, historical_dll_s, _seconds(started)


def _historical_candidate_times(mesh: str) -> tuple[float | None, float | None]:
    path = G5_CANDIDATE_DIR / f"{mesh}.json"
    if not path.exists():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    elapsed = data.get("elapsed_sec")
    cpp_ms = data.get("sftf_cpp_ms")
    return (
        float(elapsed) if elapsed is not None else None,
        float(cpp_ms) if cpp_ms is not None else None,
    )


def _rank_and_route(
    candidates: list[dict[str, object]],
) -> tuple[str, dict[str, float | int], list[dict[str, object]], float, float]:
    started = time.perf_counter()
    top = _rank_candidates(
        candidates,
        limit=DEFAULT_TOP_K,
        min_angle_degrees=DEFAULT_NMS_DEG,
    )
    ranking_s = _seconds(started)

    started = time.perf_counter()
    directions = np.asarray([row["direction"] for row in top], dtype=np.float64)
    directions /= np.maximum(np.linalg.norm(directions, axis=1, keepdims=True), 1e-12)
    dot = np.abs(directions @ directions.T)
    np.fill_diagonal(dot, -1.0)
    nearest_angle = np.degrees(np.arccos(np.clip(dot.max(axis=1), -1.0, 1.0)))
    scores = np.asarray([float(row["score"]) for row in top], dtype=np.float64)
    signals: dict[str, float | int] = {
        "nn_frac": float(np.mean(nearest_angle <= DEFAULT_FLOOR_FACTOR * DEFAULT_NMS_DEG)),
        "nn_mean_deg": float(np.mean(nearest_angle)),
        "score_cv": float(np.std(scores) / max(abs(float(np.mean(scores))), 1e-12)),
        "top_k_used": int(len(top)),
    }
    route = _route(signals, FIXED_T1, FIXED_T2).lower()
    routing_s = _seconds(started)
    return route, signals, top, ranking_s, routing_s


def _cell_id(yaw: np.ndarray, pitch: np.ndarray, orientation: dict[str, float]) -> tuple[int, int]:
    yaw_id = int(np.argmin(np.abs(yaw - float(orientation["yaw"]))))
    pitch_id = int(np.argmin(np.abs(pitch - float(orientation["pitch"]))))
    return pitch_id, yaw_id


def _seed_specs(
    route: str,
    candidates: list[dict[str, object]],
    uniform_directions: np.ndarray,
    uniform_order: list[int],
    yaw: np.ndarray,
    pitch: np.ndarray,
) -> tuple[list[dict[str, object]], float]:
    """Map axis candidates to +n/-n grid cells without consulting VSS."""
    started = time.perf_counter()
    if route == "sftf":
        ranked = _rank_candidates(
            candidates,
            limit=DEFAULT_SEVERE_ESCALATE_TOP_K,
            min_angle_degrees=DEFAULT_MIN_ANGLE_DEGREES,
        )
        rows = [
            (np.asarray(row["direction"], dtype=np.float64), float(row["score"]))
            for row in ranked
        ]
    else:
        # AVE can never consume more than the severe tier.  Resolving signs for
        # additional axes cannot affect selection and would inflate budget/time.
        ordered = uniform_directions[
            np.asarray(uniform_order[:DEFAULT_SEVERE_ESCALATE_TOP_K], dtype=np.int64)
        ]
        rows = [(np.asarray(direction, dtype=np.float64), None) for direction in ordered]

    dummy = np.zeros((len(pitch), len(yaw)), dtype=np.float64)
    specs: list[dict[str, object]] = []
    for rank, (direction, score) in enumerate(rows, start=1):
        positive = _nearest_grid_orientation(direction, yaw, pitch, dummy)
        negative = _nearest_grid_orientation(-direction, yaw, pitch, dummy)
        specs.append(
            {
                "rank": rank,
                "score": score,
                "positive_cell": _cell_id(yaw, pitch, positive),
                "negative_cell": _cell_id(yaw, pitch, negative),
                "positive_alignment": float(positive["alignment"]),
                "negative_alignment": float(negative["alignment"]),
            }
        )
    return specs, _seconds(started)


def _centers_from_specs(
    specs: list[dict[str, object]],
    values: dict[tuple[int, int], float],
    yaw: np.ndarray,
    pitch: np.ndarray,
) -> list[dict[str, object]]:
    centers: list[dict[str, object]] = []
    for spec in specs:
        positive_cell = tuple(spec["positive_cell"])
        negative_cell = tuple(spec["negative_cell"])
        positive_vss = float(values[positive_cell])
        negative_vss = float(values[negative_cell])
        if positive_vss <= negative_vss:
            cell = positive_cell
            alignment = float(spec["positive_alignment"])
        else:
            cell = negative_cell
            alignment = float(spec["negative_alignment"])
        pitch_id, yaw_id = cell
        centers.append(
            {
                "rank": int(spec["rank"]),
                "score": spec["score"],
                "yaw": float(yaw[yaw_id]),
                "pitch": float(pitch[pitch_id]),
                "vss": float(values[cell]),
                "alignment": alignment,
                "cell": cell,
            }
        )
    return centers


def _sign_cells(specs: list[dict[str, object]]) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for spec in specs:
        cells.add(tuple(spec["positive_cell"]))
        cells.add(tuple(spec["negative_cell"]))
    return cells


def _window_cells_ordered(
    centers: list[dict[str, object]],
    yaw: np.ndarray,
    pitch: np.ndarray,
    *,
    limit: int,
) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for center in centers[:limit]:
        for pitch_id, yaw_id in _window_cells(
            yaw,
            pitch,
            yaw=float(center["yaw"]),
            pitch=float(center["pitch"]),
            radius_degrees=DEFAULT_WINDOW_DEGREES,
        ):
            cell = (int(pitch_id), int(yaw_id))
            if cell not in seen:
                seen.add(cell)
                cells.append(cell)
    return cells


def _result_from_cells(
    centers: list[dict[str, object]],
    cells: Iterable[tuple[int, int]],
    values: dict[tuple[int, int], float],
    yaw: np.ndarray,
    pitch: np.ndarray,
) -> dict[str, object]:
    ordered = list(cells)
    if not ordered:
        raise ValueError("empty verification-cell set")
    # ``min`` is stable: ties retain the first cell visited by the declared
    # center/window order, matching ``_local_window_result`` exactly.
    best_cell = min(ordered, key=lambda cell: float(values[cell]))
    pitch_id, yaw_id = best_cell
    return {
        "seed_best": min(centers, key=lambda row: float(row["vss"])),
        "local_best": {
            "yaw": float(yaw[yaw_id]),
            "pitch": float(pitch[pitch_id]),
            "vss": float(values[best_cell]),
            "cell": best_cell,
        },
        "cell_count": int(len(ordered)),
    }


def _ave_decision(
    centers: list[dict[str, object]],
    base_result: dict[str, object],
    bbox_volume: float,
) -> tuple[bool, bool, list[str]]:
    seed = base_result["seed_best"]
    local = base_result["local_best"]
    local_vss = float(local["vss"])
    gain = float(seed["vss"]) / local_vss if local_vss > 1e-12 else float("inf")
    boundary = _cell_on_window_boundary(
        centers[:DEFAULT_BASE_TOP_K],
        yaw=float(local["yaw"]),
        pitch=float(local["pitch"]),
        radius_degrees=DEFAULT_WINDOW_DEGREES,
        edge_margin_degrees=DEFAULT_EDGE_MARGIN_DEGREES,
    )
    return _detector_flags(
        normalized_local_vss=local_vss / bbox_volume,
        seed_to_local_gain=gain,
        boundary_hit=boundary,
        high_support_fraction=DEFAULT_HIGH_SUPPORT_FRACTION,
        low_gain=DEFAULT_LOW_GAIN,
        high_gain=DEFAULT_HIGH_GAIN,
        boundary_gain=DEFAULT_BOUNDARY_GAIN,
    )


def _run_control_path(
    centers: list[dict[str, object]],
    values: dict[tuple[int, int], float],
    yaw: np.ndarray,
    pitch: np.ndarray,
    bbox_volume: float,
) -> tuple[dict[str, object], dict[str, float]]:
    timings: dict[str, float] = {}
    started = time.perf_counter()
    base_cells = _window_cells_ordered(
        centers, yaw, pitch, limit=DEFAULT_BASE_TOP_K
    )
    base_result = _result_from_cells(
        centers[:DEFAULT_BASE_TOP_K], base_cells, values, yaw, pitch
    )
    timings["base_verification_wall_s"] = _seconds(started)

    started = time.perf_counter()
    triggered, severe, reasons = _ave_decision(centers, base_result, bbox_volume)
    timings["ave_decision_wall_s"] = _seconds(started)

    final_k = DEFAULT_BASE_TOP_K
    final_cells = base_cells
    final_result = base_result
    timings["escalation_verification_wall_s"] = 0.0
    if triggered:
        final_k = DEFAULT_SEVERE_ESCALATE_TOP_K if severe else DEFAULT_ESCALATE_TOP_K
        started = time.perf_counter()
        final_cells = _window_cells_ordered(centers, yaw, pitch, limit=final_k)
        final_result = _result_from_cells(centers[:final_k], final_cells, values, yaw, pitch)
        timings["escalation_verification_wall_s"] = _seconds(started)

    return {
        "triggered": bool(triggered),
        "severe": bool(severe),
        "trigger_reasons": reasons,
        "final_k": int(final_k),
        "base_cells": base_cells,
        "final_cells": final_cells,
        "base_result": base_result,
        "final_result": final_result,
    }, timings


def _physical_values(
    mesh_path: Path,
    cells: Iterable[tuple[int, int]],
    yaw: np.ndarray,
    pitch: np.ndarray,
) -> tuple[dict[tuple[int, int], float], float]:
    ordered = sorted(set(cells))
    if not ordered:
        return {}, 0.0
    rows = [
        {"yaw": float(yaw[yaw_id]), "pitch": float(pitch[pitch_id])}
        for pitch_id, yaw_id in ordered
    ]
    from cpp_src.Tomo_GPU2026.tomo_cpu import compute_tomo_cpu_batch_mss

    started = time.perf_counter()
    output = compute_tomo_cpu_batch_mss(mesh_path, rows)
    elapsed = _seconds(started)
    if len(output) != len(ordered):
        raise RuntimeError(f"physical TOMO returned {len(output)} values for {len(ordered)} cells")
    return {cell: float(pair[1]) for cell, pair in zip(ordered, output)}, elapsed


def _run_physical_control_path(
    mesh_path: Path,
    specs: list[dict[str, object]],
    yaw: np.ndarray,
    pitch: np.ndarray,
    reference_grid: np.ndarray,
    bbox_volume: float,
) -> dict[str, object]:
    sign = _sign_cells(specs)
    values, sign_s = _physical_values(mesh_path, sign, yaw, pitch)
    centers = _centers_from_specs(specs, values, yaw, pitch)

    base_cells = _window_cells_ordered(centers, yaw, pitch, limit=DEFAULT_BASE_TOP_K)
    base_missing = set(base_cells) - set(values)
    extra, base_s = _physical_values(mesh_path, base_missing, yaw, pitch)
    values.update(extra)
    base_result = _result_from_cells(
        centers[:DEFAULT_BASE_TOP_K], base_cells, values, yaw, pitch
    )

    started = time.perf_counter()
    triggered, severe, reasons = _ave_decision(centers, base_result, bbox_volume)
    decision_s = _seconds(started)

    final_k = DEFAULT_BASE_TOP_K
    final_cells = base_cells
    final_result = base_result
    escalation_s = 0.0
    escalation_new_count = 0
    if triggered:
        final_k = DEFAULT_SEVERE_ESCALATE_TOP_K if severe else DEFAULT_ESCALATE_TOP_K
        final_cells = _window_cells_ordered(centers, yaw, pitch, limit=final_k)
        missing = set(final_cells) - set(values)
        escalation_new_count = len(missing)
        extra, escalation_s = _physical_values(mesh_path, missing, yaw, pitch)
        values.update(extra)
        final_result = _result_from_cells(centers[:final_k], final_cells, values, yaw, pitch)

    validation_started = time.perf_counter()
    deltas = [abs(float(value) - float(reference_grid[cell])) for cell, value in values.items()]
    relative = [
        delta / max(abs(float(reference_grid[cell])), 1e-12)
        for (cell, _value), delta in zip(values.items(), deltas)
    ]
    cache_validation_s = _seconds(validation_started)
    return {
        "physical_tomo_executed": True,
        "physical_sign_resolution_wall_s": sign_s,
        "physical_base_verification_wall_s": base_s,
        "physical_ave_decision_wall_s": decision_s,
        "physical_escalation_verification_wall_s": escalation_s,
        "physical_tomo_total_wall_s": sign_s + base_s + escalation_s,
        "physical_sign_unique_cell_count": len(sign),
        "physical_base_new_cell_count": len(base_missing),
        "physical_escalation_new_cell_count": escalation_new_count,
        "physical_total_unique_cell_count": len(values),
        "physical_triggered": bool(triggered),
        "physical_severe": bool(severe),
        "physical_trigger_reasons": ";".join(reasons),
        "physical_final_candidate_center_count": int(final_k),
        "physical_final_yaw_deg": float(final_result["local_best"]["yaw"]),
        "physical_final_pitch_deg": float(final_result["local_best"]["pitch"]),
        "physical_final_support_tomo_vss": float(final_result["local_best"]["vss"]),
        "physical_max_abs_cache_delta": max(deltas, default=0.0),
        "physical_max_rel_cache_delta": max(relative, default=0.0),
        "physical_cache_validation_wall_s": cache_validation_s,
    }


def _candidate_validation(
    candidates: list[dict[str, object]], stored: list[dict[str, object]]
) -> tuple[bool, float | None]:
    if len(candidates) != len(stored):
        return False, None
    score_delta = max(
        abs(float(current["score"]) - float(previous["score"]))
        for current, previous in zip(candidates, stored)
    )
    direction_ok = all(
        np.allclose(current["direction"], previous["direction"], rtol=0.0, atol=1e-12)
        for current, previous in zip(candidates, stored)
    )
    return bool(direction_ok and score_delta <= 1e-12), float(score_delta)


def _process_mesh(
    grid_path: Path,
    *,
    uniform_directions: np.ndarray,
    uniform_order: list[int],
    expected: dict[str, dict[str, str]],
    fresh_candidates: bool,
    physical_tomo: bool,
    selection_fingerprint: str,
) -> dict[str, object]:
    if physical_tomo and not fresh_candidates:
        raise ValueError("physical TOMO timing requires fresh candidates")
    mesh = grid_path.name[: -len(GRID_SUFFIX)]
    group = _record_group_from_name(mesh)
    mesh_path = _mesh_path_for_stem(mesh)
    candidate_path = G5_CANDIDATE_DIR / f"{mesh}{G5_CANDIDATE_SUFFIX}"
    record_started = time.perf_counter()

    historical_python_s, historical_cpp_ms = _historical_candidate_times(mesh)
    yaw, pitch, grid, historical_full_grid_s, grid_io_s = _load_grid(grid_path)

    fresh_mesh_load_s: float | None = None
    fresh_candidate_generation_s: float | None = None
    candidate_csv_io_s: float | None = None
    candidate_validation_match: bool | None = None
    candidate_validation_max_score_delta: float | None = None
    stored_candidate_route: str | None = None
    physical: dict[str, object] | None = None
    physical_selection_direct_s: float | None = None
    if fresh_candidates:
        selection_started = time.perf_counter()
        started = time.perf_counter()
        mesh_object = load_mesh(str(mesh_path))
        fresh_mesh_load_s = _seconds(started)
        started = time.perf_counter()
        candidates = _pool_to_candidates(evaluate_support_flow_candidate_pool(mesh_object))
        fresh_candidate_generation_s = _seconds(started)
        bbox = np.asarray(mesh_object.bounds, dtype=np.float64)
        bbox_volume = max(float(np.prod(np.maximum(bbox[1] - bbox[0], 0.0))), 1e-12)
        face_count = int(len(mesh_object.faces))
    else:
        started = time.perf_counter()
        candidates = _read_candidate_csv(candidate_path)
        candidate_csv_io_s = _seconds(started)
        started = time.perf_counter()
        bbox_volume, face_count = _bbox_volume(mesh_path)
        fresh_mesh_load_s = _seconds(started)

    route, signals, _top, ranking_s, routing_s = _rank_and_route(candidates)
    specs, seed_mapping_s = _seed_specs(
        route, candidates, uniform_directions, uniform_order, yaw, pitch
    )

    # The direct deployment timer excludes reference-grid loading and the
    # stored-candidate comparison.  The latter are evaluation-only.  Cache-delta
    # validation performed inside the physical path is also subtracted.
    if physical_tomo:
        physical = _run_physical_control_path(
            mesh_path, specs, yaw, pitch, grid, bbox_volume
        )
        physical_selection_direct_s = max(
            0.0,
            _seconds(selection_started) - float(physical["physical_cache_validation_wall_s"]),
        )

    if fresh_candidates:
        started = time.perf_counter()
        stored_candidates = _read_candidate_csv(candidate_path)
        candidate_csv_io_s = _seconds(started)
        candidate_validation_match, candidate_validation_max_score_delta = _candidate_validation(
            candidates, stored_candidates
        )
        stored_candidate_route, _stored_signals, _stored_top, _stored_rank_s, _stored_route_s = (
            _rank_and_route(stored_candidates)
        )
    else:
        stored_candidate_route = route

    cache_values = {
        (pitch_id, yaw_id): float(grid[pitch_id, yaw_id])
        for pitch_id in range(grid.shape[0])
        for yaw_id in range(grid.shape[1])
    }
    started = time.perf_counter()
    centers = _centers_from_specs(specs, cache_values, yaw, pitch)
    cache_sign_s = _seconds(started)
    control, control_times = _run_control_path(
        centers, cache_values, yaw, pitch, bbox_volume
    )

    sign_cells = _sign_cells(specs)
    local_cells = control["final_cells"]
    local_cell_set = set(local_cells)
    corrected_cells = sign_cells | local_cell_set
    optimum = _tomo_best(yaw, pitch, grid)
    optimum_vss = float(optimum["vss"])
    ratio_valid = optimum_vss > 1e-12
    final = control["final_result"]["local_best"]
    final_vss = float(final["vss"])
    excess = final_vss - optimum_vss
    expected_row = expected.get(mesh)

    replay_matches: bool | None = None
    replay_policy_result_matches: bool | None = None
    replay_cell_count_matches: bool | None = None
    if expected_row is not None:
        replay_policy_result_matches = bool(
            route == expected_row["route"].lower()
            and bool(control["triggered"]) == (expected_row["escalated"].lower() == "true")
            and int(control["final_k"]) == int(expected_row["verification_count"])
            and math.isclose(final_vss, float(expected_row["final_support_tomo_vss"]), rel_tol=0.0, abs_tol=1e-9)
            and _same_periodic_degree(final["yaw"], expected_row["final_yaw_deg"])
            and _same_periodic_degree(final["pitch"], expected_row["final_pitch_deg"])
        )
        replay_cell_count_matches = len(local_cells) == int(expected_row["verified_grid_cells"])
        replay_matches = bool(replay_policy_result_matches and replay_cell_count_matches)

    row: dict[str, object] = {
        "mesh": mesh,
        "group": group,
        "mesh_path": str(mesh_path.resolve()),
        "mesh_size_bytes": mesh_path.stat().st_size,
        "mesh_mtime_ns": mesh_path.stat().st_mtime_ns,
        "selection_fingerprint": selection_fingerprint,
        "face_count": face_count,
        "route": route,
        "initial_candidate_source": (
            "calibrated SFTF axes (up to 200)"
            if route == "sftf" else "first 200 farthest-point uniform axes"
        ),
        "ratio_valid": ratio_valid,
        "reference_optimum_yaw_deg": float(optimum["yaw"]),
        "reference_optimum_pitch_deg": float(optimum["pitch"]),
        "reference_optimum_vss": optimum_vss,
        "final_candidate_center_count": int(control["final_k"]),
        "escalated": bool(control["triggered"]),
        "severe_escalation": bool(control["severe"]),
        "trigger_reasons": ";".join(control["trigger_reasons"]),
        "final_yaw_deg": float(final["yaw"]),
        "final_pitch_deg": float(final["pitch"]),
        "final_support_tomo_vss": final_vss,
        "ratio_to_exhaustive_optimum": final_vss / optimum_vss if ratio_valid else None,
        "absolute_excess_support": excess,
        "normalized_excess_support": excess / bbox_volume,
        "candidate_pool_size": len(candidates),
        "router_nn_frac": float(signals["nn_frac"]),
        "router_nn_mean_deg": float(signals["nn_mean_deg"]),
        "router_score_cv": float(signals["score_cv"]),
        "local_window_grid_cell_count": len(local_cells),
        "local_window_budget_fraction": len(local_cells) / int(grid.size),
        "sign_resolution_raw_probe_count": 2 * len(specs),
        "sign_resolution_unique_grid_cell_count": len(sign_cells),
        "sign_cells_already_in_local_window": len(sign_cells & local_cell_set),
        "corrected_total_unique_grid_cell_count": len(corrected_cells),
        "corrected_total_budget_fraction": len(corrected_cells) / int(grid.size),
        "corrected_added_unique_grid_cell_count": len(corrected_cells) - len(local_cells),
        "candidate_csv_io_wall_s": candidate_csv_io_s,
        "reference_grid_io_wall_s": grid_io_s,
        "mesh_load_or_metadata_wall_s": fresh_mesh_load_s,
        "fresh_candidate_generation_wall_s": fresh_candidate_generation_s,
        "ranking_wall_s": ranking_s,
        "routing_wall_s": routing_s,
        "seed_axis_to_grid_mapping_wall_s": seed_mapping_s,
        "cache_sign_resolution_lookup_wall_s": cache_sign_s,
        "cache_base_verification_lookup_wall_s": control_times["base_verification_wall_s"],
        "cache_ave_decision_wall_s": control_times["ave_decision_wall_s"],
        "cache_escalation_lookup_wall_s": control_times["escalation_verification_wall_s"],
        "historical_python_sftf_elapsed_s": historical_python_s,
        "historical_sftf_cpp_compute_ms": historical_cpp_ms,
        "historical_exhaustive_tomo_cpu_dll_s": historical_full_grid_s,
        "fresh_candidates_used": fresh_candidates,
        "fresh_candidates_match_stored": candidate_validation_match,
        "fresh_candidates_max_score_delta": candidate_validation_max_score_delta,
        "stored_candidate_route": stored_candidate_route,
        "fresh_route_matches_stored": route == stored_candidate_route,
        "cache_replay_policy_result_matches_existing_24": replay_policy_result_matches,
        "cache_replay_cell_count_matches_existing_24": replay_cell_count_matches,
        "cache_replay_matches_existing_24_record_output": replay_matches,
        "physical_tomo_executed": False,
    }
    row["cache_replay_selection_component_sum_s"] = (
        float(candidate_csv_io_s or 0.0)
        + grid_io_s
        + float(fresh_mesh_load_s or 0.0)
        + ranking_s
        + routing_s
        + seed_mapping_s
        + cache_sign_s
        + control_times["base_verification_wall_s"]
        + control_times["ave_decision_wall_s"]
        + control_times["escalation_verification_wall_s"]
    )
    row["evaluation_only_reference_io_wall_s"] = (
        grid_io_s + (float(candidate_csv_io_s or 0.0) if fresh_candidates else 0.0)
    )
    if physical is not None:
        row.update(physical)
        row["physical_selection_direct_wall_s"] = physical_selection_direct_s
        row["physical_selection_direct_scope"] = (
            "direct timer from mesh load through fresh candidate generation, ranking, routing, "
            "axis mapping, cold-batch physical TOMO sign/base/escalation, AVE decision, window "
            "construction, and final selection; excludes reference-grid I/O, stored-candidate "
            "validation, cache-delta validation, and checkpoint output"
        )
        physical_vss = float(row["physical_final_support_tomo_vss"])
        row["physical_ratio_to_exhaustive_optimum"] = (
            physical_vss / optimum_vss if ratio_valid else None
        )
        row["physical_absolute_excess_support"] = physical_vss - optimum_vss
        row["physical_normalized_excess_support"] = (physical_vss - optimum_vss) / bbox_volume
        component_sum = (
            float(fresh_mesh_load_s or 0.0)
            + float(fresh_candidate_generation_s or 0.0)
            + ranking_s
            + routing_s
            + seed_mapping_s
            + float(row["physical_tomo_total_wall_s"])
            + float(row["physical_ave_decision_wall_s"])
        )
        row["fresh_candidate_plus_physical_component_sum_s"] = component_sum
        row["physical_selection_component_sum_s"] = component_sum
        row["physical_selection_component_scope"] = (
            "diagnostic sum of individually timed components; the direct selection timer is "
            "authoritative because it also captures orchestration overhead"
        )
        row["physical_trigger_matches_cache"] = bool(row["physical_triggered"]) == bool(row["escalated"])
        row["physical_severity_matches_cache"] = bool(row["physical_severe"]) == bool(row["severe_escalation"])
        row["physical_k_matches_cache"] = (
            int(row["physical_final_candidate_center_count"]) == int(row["final_candidate_center_count"])
        )
        row["physical_orientation_matches_cache"] = (
            _same_periodic_degree(row["physical_final_yaw_deg"], row["final_yaw_deg"])
            and _same_periodic_degree(row["physical_final_pitch_deg"], row["final_pitch_deg"])
        )

    row["record_wall_s_before_checkpoint_io"] = _seconds(record_started)
    return row


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return _finite(float(value))
    return value


def _dedupe_skipped(skipped: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in skipped:
        key = (str(row.get("mesh", "")), str(row.get("reason", "")))
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    return deduped


def _run_status(
    records: list[dict[str, object]],
    skipped: list[dict[str, str]],
    config: dict[str, object],
) -> str:
    if not bool(config.get("full_scope")):
        return "filtered"
    meshes = [str(row["mesh"]) for row in records]
    stale = {
        str(row.get("mesh"))
        for row in skipped
        if row.get("reason") == "missing_mesh_file"
    }
    unexpected_skips = [
        row for row in skipped
        if row.get("reason") != "missing_mesh_file" or str(row.get("mesh")) not in EXPECTED_STALE_MESHES
    ]
    population_complete = (
        len(meshes) == EXPECTED_RECORD_COUNT
        and len(set(meshes)) == EXPECTED_RECORD_COUNT
        and sum(bool(row["ratio_valid"]) for row in records) == EXPECTED_RATIO_VALID_COUNT
        and sum(not bool(row["ratio_valid"]) for row in records) == EXPECTED_NONPOSITIVE_COUNT
        and stale == EXPECTED_STALE_MESHES
        and not unexpected_skips
    )
    physical_complete = (
        not bool(config.get("physical_tomo"))
        or all(bool(row.get("physical_tomo_executed")) for row in records)
    )
    fresh_complete = (
        not bool(config.get("fresh_candidates"))
        or all(bool(row.get("fresh_candidates_used")) for row in records)
    )
    fingerprint_complete = all(
        row.get("selection_fingerprint") == config.get("selection_fingerprint")
        for row in records
    )
    return "complete" if (
        population_complete and physical_complete and fresh_complete and fingerprint_complete
    ) else "partial"


def _summary(
    records: list[dict[str, object]],
    *,
    skipped: list[dict[str, str]],
    run_wall_s: float,
    uniform_setup_s: float,
    config: dict[str, object],
) -> dict[str, object]:
    skipped = _dedupe_skipped(skipped)
    valid = [row for row in records if bool(row["ratio_valid"])]
    nonpositive = [row for row in records if not bool(row["ratio_valid"])]
    ratios = np.asarray(
        [float(row["ratio_to_exhaustive_optimum"]) for row in valid], dtype=np.float64
    )
    local_budget = np.asarray(
        [float(row["local_window_budget_fraction"]) for row in records], dtype=np.float64
    )
    corrected_budget = np.asarray(
        [float(row["corrected_total_budget_fraction"]) for row in records], dtype=np.float64
    )
    replay_matches = [
        row["cache_replay_matches_existing_24_record_output"]
        for row in records
        if row["cache_replay_matches_existing_24_record_output"] is not None
    ]
    physical = [row for row in records if bool(row.get("physical_tomo_executed"))]
    record_wall = np.asarray(
        [
            float(row["end_to_end_wall_s_including_checkpoint_io"])
            for row in records
            if row.get("end_to_end_wall_s_including_checkpoint_io") is not None
        ],
        dtype=np.float64,
    )
    physical_components = np.asarray(
        [float(row["physical_selection_component_sum_s"]) for row in physical],
        dtype=np.float64,
    )
    physical_direct = np.asarray(
        [
            float(row["physical_selection_direct_wall_s"])
            for row in physical
            if row.get("physical_selection_direct_wall_s") is not None
        ],
        dtype=np.float64,
    )
    physical_direct_with_checkpoint = np.asarray(
        [
            float(row["physical_selection_plus_primary_checkpoint_wall_s"])
            for row in physical
            if row.get("physical_selection_plus_primary_checkpoint_wall_s") is not None
        ],
        dtype=np.float64,
    )
    physical_valid = [row for row in physical if bool(row["ratio_valid"])]
    physical_ratios = np.asarray(
        [float(row["physical_ratio_to_exhaustive_optimum"]) for row in physical_valid],
        dtype=np.float64,
    )
    fresh_validated = [
        row for row in records if row.get("fresh_candidates_match_stored") is not None
    ]
    policy_matches = [
        row["cache_replay_policy_result_matches_existing_24"]
        for row in records
        if row.get("cache_replay_policy_result_matches_existing_24") is not None
    ]
    cell_matches = [
        row["cache_replay_cell_count_matches_existing_24"]
        for row in records
        if row.get("cache_replay_cell_count_matches_existing_24") is not None
    ]
    missing_mesh_skips = [row for row in skipped if row.get("reason") == "missing_mesh_file"]
    unexpected_skips = [
        row for row in skipped
        if row.get("reason") != "missing_mesh_file"
        or str(row.get("mesh")) not in EXPECTED_STALE_MESHES
    ]
    summary: dict[str, object] = {
        "status": _run_status(records, skipped, config),
        "record_count": len(records),
        "ratio_valid_record_count": len(valid),
        "nonpositive_optimum_record_count": len(nonpositive),
        "missing_mesh_grid_count": len(missing_mesh_skips),
        "unexpected_skipped_count": len(unexpected_skips),
        "route_sftf_count": sum(row["route"] == "sftf" for row in records),
        "route_uniform_count": sum(row["route"] == "uniform" for row in records),
        "escalated_count": sum(bool(row["escalated"]) for row in records),
        "mean_ratio_positive_optimum": float(np.mean(ratios)) if ratios.size else None,
        "max_ratio_positive_optimum": float(np.max(ratios)) if ratios.size else None,
        "count_ratio_le_2_positive_optimum": int(np.sum(ratios <= 2.0)) if ratios.size else 0,
        "mean_original_local_budget_fraction": float(np.mean(local_budget)) if local_budget.size else None,
        "mean_corrected_budget_fraction": float(np.mean(corrected_budget)) if corrected_budget.size else None,
        "mean_sign_budget_increment_fraction": (
            float(np.mean(corrected_budget - local_budget)) if corrected_budget.size else None
        ),
        "mean_original_local_budget_fraction_ratio_valid": float(
            np.mean([float(row["local_window_budget_fraction"]) for row in valid])
        ) if valid else None,
        "mean_corrected_budget_fraction_ratio_valid": float(
            np.mean([float(row["corrected_total_budget_fraction"]) for row in valid])
        ) if valid else None,
        "cache_replay_matches_existing_count": sum(value is True for value in replay_matches),
        "cache_replay_expected_record_count": len(replay_matches),
        "cache_policy_result_matches_existing_count": sum(value is True for value in policy_matches),
        "cache_policy_result_expected_record_count": len(policy_matches),
        "cache_cell_count_matches_existing_count": sum(value is True for value in cell_matches),
        "cache_cell_count_expected_record_count": len(cell_matches),
        "sum_record_wall_s_including_evaluation_and_checkpoint": (
            float(np.sum(record_wall)) if record_wall.size else None
        ),
        "mean_record_wall_s_including_evaluation_and_checkpoint": (
            float(np.mean(record_wall)) if record_wall.size else None
        ),
        "median_record_wall_s_including_evaluation_and_checkpoint": (
            float(np.median(record_wall)) if record_wall.size else None
        ),
        "max_record_wall_s_including_evaluation_and_checkpoint": (
            float(np.max(record_wall)) if record_wall.size else None
        ),
        "physical_tomo_record_count": len(physical),
        "physical_tomo_total_wall_s": sum(
            float(row.get("physical_tomo_total_wall_s", 0.0)) for row in physical
        ),
        "physical_selection_component_sum_all_records_s": (
            float(np.sum(physical_components)) if physical_components.size else None
        ),
        "physical_selection_component_mean_per_record_s": (
            float(np.mean(physical_components)) if physical_components.size else None
        ),
        "physical_selection_direct_sum_s": (
            float(np.sum(physical_direct)) if physical_direct.size else None
        ),
        "physical_selection_direct_mean_s": (
            float(np.mean(physical_direct)) if physical_direct.size else None
        ),
        "physical_selection_including_checkpoint_sum_s": (
            float(np.sum(physical_direct_with_checkpoint))
            if physical_direct_with_checkpoint.size else None
        ),
        "physical_selection_including_checkpoint_mean_s": (
            float(np.mean(physical_direct_with_checkpoint))
            if physical_direct_with_checkpoint.size else None
        ),
        "physical_selection_including_checkpoint_median_s": (
            float(np.median(physical_direct_with_checkpoint))
            if physical_direct_with_checkpoint.size else None
        ),
        "physical_selection_including_checkpoint_max_s": (
            float(np.max(physical_direct_with_checkpoint))
            if physical_direct_with_checkpoint.size else None
        ),
        "physical_mean_ratio_positive_optimum": (
            float(np.mean(physical_ratios)) if physical_ratios.size else None
        ),
        "physical_max_ratio_positive_optimum": (
            float(np.max(physical_ratios)) if physical_ratios.size else None
        ),
        "physical_count_ratio_le_2_positive_optimum": (
            int(np.sum(physical_ratios <= 2.0)) if physical_ratios.size else 0
        ),
        "physical_trigger_matches_cache_count": sum(
            bool(row.get("physical_trigger_matches_cache")) for row in physical
        ),
        "physical_final_orientation_matches_cache_count": sum(
            bool(row.get("physical_orientation_matches_cache")) for row in physical
        ),
        "physical_k_matches_cache_count": sum(bool(row.get("physical_k_matches_cache")) for row in physical),
        "physical_severity_matches_cache_count": sum(
            bool(row.get("physical_severity_matches_cache")) for row in physical
        ),
        "fresh_candidate_validation_record_count": len(fresh_validated),
        "fresh_candidate_exact_match_count": sum(
            bool(row["fresh_candidates_match_stored"]) for row in fresh_validated
        ),
        "fresh_candidate_max_score_delta": max(
            (
                float(row["fresh_candidates_max_score_delta"])
                for row in fresh_validated
                if row.get("fresh_candidates_max_score_delta") is not None
            ),
            default=None,
        ),
        "fresh_route_matches_stored_count": sum(
            bool(row.get("fresh_route_matches_stored")) for row in fresh_validated
        ),
        "current_invocation_wall_s": run_wall_s,
        "global_uniform_seed_setup_wall_s": uniform_setup_s,
        "runtime_scope": (
            "Authoritative physical time is a direct per-mesh selection timer plus the primary "
            "aggregate JSON/CSV checkpoint. Reference-grid evaluation, stored-candidate "
            "comparison, cache-delta validation, and the timing-metadata rewrite are excluded."
        ),
        "complete_pipeline_speedup_reported": False,
        "warnings": [
            "The original local-window budget omits TOMO lookups used to choose +n versus -n; corrected fields include their unique-cell union.",
            "Historical exhaustive TOMO time is not a local-verification time and is never added to cached replay.",
            "Sign, base, and escalation verification are separate cold TOMO batches; each reconstructs the backend and reloads the mesh.",
            "Fresh candidate pools are authoritative; stored pools are comparison-only and exact-match differences are reported.",
            "Nonpositive exhaustive optima have ratio=null; use absolute_excess_support and normalized_excess_support.",
        ],
    }
    if len(records) == EXPECTED_RECORD_COUNT:
        summary.update({
            "mean_original_local_budget_fraction_all_41": summary["mean_original_local_budget_fraction"],
            "mean_corrected_budget_fraction_all_41": summary["mean_corrected_budget_fraction"],
            "mean_sign_budget_increment_fraction_all_41": summary["mean_sign_budget_increment_fraction"],
        })
    if len(valid) == EXPECTED_RATIO_VALID_COUNT:
        summary.update({
            "mean_original_local_budget_fraction_positive_26": summary[
                "mean_original_local_budget_fraction_ratio_valid"
            ],
            "mean_corrected_budget_fraction_positive_26": summary[
                "mean_corrected_budget_fraction_ratio_valid"
            ],
        })
    return summary


def _write_outputs(
    stem: Path,
    records: list[dict[str, object]],
    skipped: list[dict[str, str]],
    config: dict[str, object],
    *,
    run_wall_s: float,
    uniform_setup_s: float,
) -> float:
    started = time.perf_counter()
    records = sorted(records, key=lambda row: str(row["mesh"]))
    skipped = _dedupe_skipped(skipped)
    summary = _summary(
        records,
        skipped=skipped,
        run_wall_s=run_wall_s,
        uniform_setup_s=uniform_setup_s,
        config=config,
    )
    payload = {
        "status": summary["status"],
        "config": config,
        "summary": summary,
        "records": records,
        "skipped": skipped,
    }
    json_path = stem.with_suffix(".json")
    csv_path = Path(str(stem) + "_records.csv")
    json_tmp = Path(str(json_path) + ".tmp")
    csv_tmp = Path(str(csv_path) + ".tmp")
    json_tmp.write_text(
        json.dumps(_json_safe(payload), indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    if records:
        fieldnames: list[str] = []
        for row in records:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        with csv_tmp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(_json_safe(records))
        # JSON is the checkpoint commit marker: publish CSV first, then JSON.
        csv_tmp.replace(csv_path)
    json_tmp.replace(json_path)
    return _seconds(started)


def _selection_source_provenance() -> dict[str, dict[str, object]]:
    relative_paths = [
        Path("scripts/experiment_deployed_pipeline_runtime_g5.py"),
        Path("python_src/SupportFlowTensorField/support_flow_tensor_field.py"),
        Path("scripts/experiment_happy_method_g5_audit.py"),
        Path("scripts/experiment_routing_rule_g5.py"),
        Path("scripts/experiment_sftf_budget_curve.py"),
        Path("scripts/experiment_budget_matched_local_baselines.py"),
        Path("scripts/regenerate_sftf_vs_saved_tomo_summary.py"),
        Path("cpp_src/Tomo_GPU2026/tomo_cpu.py"),
        Path("cpp_src/Tomo_GPU2026/tomo_shell_cpp.py"),
        Path("cpp_src/Tomo_GPU2026/tomo_shell_io.py"),
        Path("cpp_src/Tomo_GPU2026/Tomo_Shell2026.dll"),
    ]
    provenance: dict[str, dict[str, object]] = {}
    for relative in relative_paths:
        path = PROJECT_ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"selection dependency missing: {path}")
        provenance[relative.as_posix()] = {
            "path": str(path.resolve()),
            "size_bytes": path.stat().st_size,
            "mtime_ns": path.stat().st_mtime_ns,
            "sha256": _sha256(path),
        }
    return provenance


def _file_provenance(path: Path) -> dict[str, object]:
    return {
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "mtime_ns": path.stat().st_mtime_ns,
        "sha256": _sha256(path),
    }


def _selection_input_provenance(grid_paths: list[Path]) -> dict[str, dict[str, object]]:
    provenance: dict[str, dict[str, object]] = {}
    for grid_path in grid_paths:
        mesh = grid_path.name[: -len(GRID_SUFFIX)]
        candidate_path = G5_CANDIDATE_DIR / f"{mesh}{G5_CANDIDATE_SUFFIX}"
        row: dict[str, object] = {"grid": _file_provenance(grid_path)}
        if candidate_path.is_file():
            row["stored_candidate_comparison"] = _file_provenance(candidate_path)
        try:
            mesh_path = _mesh_path_for_stem(mesh)
        except FileNotFoundError:
            row["mesh"] = None
        else:
            row["mesh"] = _file_provenance(mesh_path)
        provenance[mesh] = row
    return provenance


def _row_has_checkpoint_fields(row: dict[str, object], *, physical_tomo: bool) -> bool:
    required = {
        "checkpoint_output_io_wall_s",
        "end_to_end_wall_s_including_checkpoint_io",
        "cache_replay_selection_component_sum_including_checkpoint_io_s",
    }
    if physical_tomo:
        required.update({
            "physical_selection_direct_wall_s",
            "physical_selection_plus_primary_checkpoint_wall_s",
        })
    return all(row.get(key) is not None for key in required)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh-candidates", action="store_true")
    parser.add_argument("--physical-tomo", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--ratio-valid-only", action="store_true")
    parser.add_argument("--mesh", action="append", default=[], help="exact mesh stem; repeatable")
    parser.add_argument("--output-stem", default=DEFAULT_OUTPUT_STEM)
    args = parser.parse_args()
    if args.physical_tomo and not args.fresh_candidates:
        parser.error("--physical-tomo requires --fresh-candidates for authoritative runtime")

    run_started = time.perf_counter()
    started = time.perf_counter()
    uniform_directions = _unique_axis_directions(
        _spherical_sample_directions(SUPPORT_FLOW_COARSE_DIRECTION_COUNT)
    )
    uniform_order = _farthest_axis_order(uniform_directions)
    uniform_setup_s = _seconds(started)
    expected = _read_expected_pipeline()
    stem = ETC / args.output_stem

    grid_paths = sorted(G5_CACHE_DIR.glob(f"*{GRID_SUFFIX}"))
    if args.mesh:
        requested = set(args.mesh)
        grid_paths = [
            path for path in grid_paths
            if path.name[: -len(GRID_SUFFIX)] in requested
        ]
    if args.ratio_valid_only:
        grid_paths = [
            path for path in grid_paths
            if path.name[: -len(GRID_SUFFIX)] in expected
        ]

    full_scope = not args.mesh and not args.ratio_valid_only
    config_base: dict[str, object] = {
        "selection_logic_version": SELECTION_LOGIC_VERSION,
        "grid_suffix": GRID_SUFFIX,
        "critical_angle_deg": 60.0,
        "angle_step_deg": 1.0,
        "base_top_k": DEFAULT_BASE_TOP_K,
        "escalate_top_k": DEFAULT_ESCALATE_TOP_K,
        "severe_escalate_top_k": DEFAULT_SEVERE_ESCALATE_TOP_K,
        "window_degrees": DEFAULT_WINDOW_DEGREES,
        "routing_threshold_nn_frac_min": FIXED_T1,
        "routing_threshold_score_cv_max": FIXED_T2,
        "fresh_candidates": bool(args.fresh_candidates),
        "physical_tomo": bool(args.physical_tomo),
        "ratio_valid_only": bool(args.ratio_valid_only),
        "selected_meshes": list(args.mesh),
        "selected_grid_stems": [path.name[: -len(GRID_SUFFIX)] for path in grid_paths],
        "full_scope": full_scope,
        "uniform_axis_count_generated": len(uniform_directions),
        "uniform_axis_count_available_to_ave": min(
            len(uniform_directions), DEFAULT_SEVERE_ESCALATE_TOP_K
        ),
        "physical_tomo_batch_mode": (
            "cold sign/base/escalation batches; each call reconstructs backend and reloads mesh"
        ),
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "source_provenance": _selection_source_provenance(),
        "input_provenance": _selection_input_provenance(grid_paths),
        "expected_pipeline_comparison": _file_provenance(EXPECTED_PIPELINE_CSV),
    }
    selection_fingerprint = _json_hash(config_base)
    config = dict(config_base)
    config["selection_fingerprint"] = selection_fingerprint

    records: list[dict[str, object]] = []
    skipped: list[dict[str, str]] = []
    if args.resume and stem.with_suffix(".json").exists():
        prior = json.loads(stem.with_suffix(".json").read_text(encoding="utf-8"))
        prior_fingerprint = prior.get("config", {}).get("selection_fingerprint")
        if prior_fingerprint != selection_fingerprint:
            raise RuntimeError(
                "resume refused: selection fingerprint changed; start without --resume or use "
                "a new --output-stem"
            )
        records = list(prior.get("records", []))
        skipped = list(prior.get("skipped", []))
        if any(row.get("selection_fingerprint") != selection_fingerprint for row in records):
            raise RuntimeError("resume refused: one or more rows have incompatible provenance")
        if any(bool(row.get("fresh_candidates_used")) != bool(args.fresh_candidates) for row in records):
            raise RuntimeError("resume refused: fresh-candidate mode differs from prior rows")
        if any(bool(row.get("physical_tomo_executed")) != bool(args.physical_tomo) for row in records):
            raise RuntimeError("resume refused: physical-TOMO mode differs from prior rows")
        incomplete_meshes = {
            str(row["mesh"])
            for row in records
            if not _row_has_checkpoint_fields(row, physical_tomo=bool(args.physical_tomo))
        }
        if incomplete_meshes:
            print(
                "resume will rerun rows interrupted before timing metadata was persisted: "
                + ", ".join(sorted(incomplete_meshes)),
                flush=True,
            )
            records = [row for row in records if str(row["mesh"]) not in incomplete_meshes]
            skipped = [row for row in skipped if str(row.get("mesh")) not in incomplete_meshes]
    completed = {str(row["mesh"]) for row in records}

    selected_count = 0
    for grid_path in grid_paths:
        mesh = grid_path.name[: -len(GRID_SUFFIX)]
        if mesh in completed:
            print(f"skip {mesh}: checkpoint complete", flush=True)
            continue
        candidate_path = G5_CANDIDATE_DIR / f"{mesh}{G5_CANDIDATE_SUFFIX}"
        if not candidate_path.exists():
            skipped.append({"mesh": mesh, "reason": "missing_candidate_csv"})
            continue
        mesh_wall_started = time.perf_counter()
        try:
            _mesh_path_for_stem(mesh)
        except FileNotFoundError:
            skipped.append({"mesh": mesh, "reason": "missing_mesh_file"})
            continue
        selected_count += 1
        print(
            f"[{selected_count}] {mesh} "
            f"fresh_candidates={int(args.fresh_candidates)} physical_tomo={int(args.physical_tomo)}",
            flush=True,
        )
        try:
            row = _process_mesh(
                grid_path,
                uniform_directions=uniform_directions,
                uniform_order=uniform_order,
                expected=expected,
                fresh_candidates=args.fresh_candidates,
                physical_tomo=args.physical_tomo,
                selection_fingerprint=selection_fingerprint,
            )
        except Exception as exc:
            skipped.append({"mesh": mesh, "reason": f"runtime_error:{type(exc).__name__}:{exc}"})
            print(f"  FAILED: {type(exc).__name__}: {exc}", flush=True)
            _write_outputs(
                stem, records, skipped, config,
                run_wall_s=_seconds(run_started), uniform_setup_s=uniform_setup_s,
            )
            continue
        records = [record for record in records if record["mesh"] != mesh]
        records.append(row)
        skipped = [item for item in skipped if item.get("mesh") != mesh]
        print(
            f"  route={row['route']} trigger={int(row['escalated'])} "
            f"local={row['local_window_grid_cell_count']} "
            f"corrected={row['corrected_total_unique_grid_cell_count']} "
            f"ratio={row['ratio_to_exhaustive_optimum']}",
            flush=True,
        )
        checkpoint_io_s = _write_outputs(
            stem, records, skipped, config,
            run_wall_s=_seconds(run_started), uniform_setup_s=uniform_setup_s,
        )
        # The primary aggregate JSON/CSV write is part of the reported selection
        # path.  The following rewrite only persists timing metadata and is
        # instrumentation overhead, deliberately excluded from deployment time.
        row["checkpoint_output_io_wall_s"] = checkpoint_io_s
        row["end_to_end_wall_s_including_checkpoint_io"] = _seconds(mesh_wall_started)
        row["cache_replay_selection_component_sum_including_checkpoint_io_s"] = (
            float(row["cache_replay_selection_component_sum_s"]) + checkpoint_io_s
        )
        if row.get("physical_selection_component_sum_s") is not None:
            row["physical_selection_component_sum_including_checkpoint_io_s"] = (
                float(row["physical_selection_component_sum_s"]) + checkpoint_io_s
            )
        if row.get("physical_selection_direct_wall_s") is not None:
            row["physical_selection_plus_primary_checkpoint_wall_s"] = (
                float(row["physical_selection_direct_wall_s"]) + checkpoint_io_s
            )
        rewrite_io_s = _write_outputs(
            stem, records, skipped, config,
            run_wall_s=_seconds(run_started), uniform_setup_s=uniform_setup_s,
        )
        row["checkpoint_timing_metadata_rewrite_wall_s"] = rewrite_io_s

    final_report_io_s = _write_outputs(
        stem, records, skipped, config,
        run_wall_s=_seconds(run_started), uniform_setup_s=uniform_setup_s,
    )
    summary = _summary(
        records,
        skipped=skipped,
        run_wall_s=_seconds(run_started),
        uniform_setup_s=uniform_setup_s,
        config=config,
    )
    print("\n=== deployed-pipeline runtime summary ===")
    print(json.dumps(_json_safe(summary), indent=2, ensure_ascii=False, allow_nan=False))
    print(f"saved: {stem.with_suffix('.json').relative_to(PROJECT_ROOT)}")
    print(f"saved: {Path(str(stem) + '_records.csv').relative_to(PROJECT_ROOT)}")
    print(f"final reporting write (excluded from selection time): {final_report_io_s:.6f}s")
    if full_scope and summary["status"] != "complete":
        raise SystemExit("incomplete full-scope run; see output status/skipped records")


if __name__ == "__main__":
    main()
