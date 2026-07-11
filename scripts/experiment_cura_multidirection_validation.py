"""Multi-direction TOMO--Cura validation on the eight organic G5 meshes.

The primary ranking panel is deliberately independent of TOMO scores: the same
16 spherical-Fibonacci build directions are evaluated for every mesh.  Two
mesh-specific anchors are then added (with exact grid-cell de-duplication):

* the orientation selected by the deployed ``rank -> route -> verify ->
  escalate`` pipeline; and
* the exhaustive optimum of the cached 1-degree TOMO ``v_ss`` grid.

Spearman, Kendall tau-b, and top-k agreement are computed on the fixed panel,
so the correlations are not inflated by selecting candidates from TOMO.  The
TOMO-global anchor is compared with the best Cura support volume among *all*
evaluated directions to report real-slicer regret.  Lower is better for both
TOMO ``v_ss`` and Cura support extrusion volume.

The script writes a resumable JSON after every CuraEngine call, plus raw-record
and per-mesh-summary CSV files.  It records the executable/profile/parser
hashes, every legacy engine setting, mesh/grid hashes, units, scaling, and the
candidate-generation rule needed to reproduce the run.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.stats import kendalltau, spearmanr


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURA_CLI_ROOT = PROJECT_ROOT.parent / "_Cura_CLI"
CURA_CLI_SRC = CURA_CLI_ROOT / "python" / "src"
for _path in (str(PROJECT_ROOT), str(CURA_CLI_SRC)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from cura_cli import config as cura_config  # noqa: E402
from cura_cli import legacy_profile, mesh_rotation  # noqa: E402
from cura_cli.cura_slicer import CuraSlicer  # noqa: E402
from scripts._mesh_paths import G5_RAW_MESH  # noqa: E402
from scripts.regenerate_sftf_vs_saved_tomo_summary import (  # noqa: E402
    _nearest_grid_orientation,
)


G5_ROOT = PROJECT_ROOT / "Experimental" / "G5Test"
CACHE_DIR = G5_ROOT / "tomo_int3_cache"
GRID_SUFFIX = "_tomo_int3_1deg_60deg.npz"
DEPLOYED_PIPELINE_JSON = (
    PROJECT_ROOT / "Experimental" / "etc" / "sftf_deployed_pipeline_g5.json"
)
OUTPUT_DIR = PROJECT_ROOT / "Experimental" / "etc"

ORGANIC_MESHES = (
    "Group_C1_Bunny_69k",
    "Group_C2_manikin",
    "Group_C3_dragon_100k_1.5x",
    "Group_C4_happy_50k_0.75x",
    "Group_C5_lucy_50k",
    "Group_C6_nefertiti_100k",
    "Group_C7_liver_19k",
    "Group_C8_kidney_12k",
)

DEFAULT_PANEL_SIZE = 16
DEFAULT_TARGET_AABB_DIAGONAL_MM = 140.0
DEFAULT_OUTPUT_STEM = "sftf_cura_multidirection_validation"
TOP_K_VALUES = (3, 5)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _json_hash(value: object) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _mesh_path(stem: str) -> Path:
    matches = sorted(G5_RAW_MESH.glob(stem + ".*"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"expected exactly one mesh for {stem!r} under {G5_RAW_MESH}, got {matches}"
        )
    return matches[0]


def _canonical_grid_arrays(data: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Drop the duplicated 360-degree endpoints from a saved periodic grid."""
    yaw = np.asarray(data["yaw_values"], dtype=np.float64)
    pitch = np.asarray(data["pitch_values"], dtype=np.float64)
    vss = np.asarray(data["vss_grid"], dtype=np.float64)
    if len(yaw) > 1 and math.isclose(float(yaw[-1] - yaw[0]), 360.0, abs_tol=0.05):
        yaw = yaw[:-1]
        vss = vss[:, :-1]
    if len(pitch) > 1 and math.isclose(float(pitch[-1] - pitch[0]), 360.0, abs_tol=0.05):
        pitch = pitch[:-1]
        vss = vss[:-1, :]
    if vss.shape != (len(pitch), len(yaw)):
        raise ValueError(
            f"grid shape {vss.shape} does not match pitch/yaw {(len(pitch), len(yaw))}"
        )
    return yaw, pitch, vss


def _nearest_periodic_index(values: np.ndarray, angle_deg: float) -> int:
    angle = float(angle_deg) % 360.0
    delta = np.abs(((np.asarray(values, float) - angle + 180.0) % 360.0) - 180.0)
    return int(np.argmin(delta))


def _fibonacci_directions(count: int) -> np.ndarray:
    """Deterministic, approximately equal-area directed points on S^2."""
    if count < 3:
        raise ValueError("panel size must be at least 3")
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    directions: list[list[float]] = []
    for index in range(count):
        z = 1.0 - 2.0 * (index + 0.5) / count
        radius = math.sqrt(max(0.0, 1.0 - z * z))
        azimuth = index * golden_angle
        directions.append(
            [radius * math.cos(azimuth), radius * math.sin(azimuth), z]
        )
    return np.asarray(directions, dtype=np.float64)


def _load_deployed_records(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records", payload.get("rows", []))
    result = {str(row["mesh"]): dict(row) for row in records}
    missing = [stem for stem in ORGANIC_MESHES if stem not in result]
    if missing:
        raise ValueError(f"deployed-pipeline JSON lacks organic meshes: {missing}")
    return result


def _add_candidate(
    candidates: dict[tuple[int, int], dict[str, Any]],
    *,
    yaw_index: int,
    pitch_index: int,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
    source: str,
    panel_index: int | None = None,
) -> None:
    key = (int(pitch_index), int(yaw_index))
    if key not in candidates:
        candidates[key] = {
            "candidate_id": source,
            "sources": [source],
            "fixed_panel": panel_index is not None,
            "panel_index": panel_index,
            "yaw_index": int(yaw_index),
            "pitch_index": int(pitch_index),
            "yaw_deg": float(yaw_values[yaw_index]),
            "pitch_deg": float(pitch_values[pitch_index]),
            "tomo_vss": float(vss_grid[pitch_index, yaw_index]),
        }
        return
    row = candidates[key]
    if source not in row["sources"]:
        row["sources"].append(source)
    if panel_index is not None:
        row["fixed_panel"] = True
        row["panel_index"] = panel_index


def _candidate_set(
    *,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
    deployed: dict[str, Any],
    panel_size: int,
) -> list[dict[str, Any]]:
    """Fixed TOMO-independent panel, followed by deployed/global anchors."""
    candidates: dict[tuple[int, int], dict[str, Any]] = {}
    for panel_index, direction in enumerate(_fibonacci_directions(panel_size)):
        mapped = _nearest_grid_orientation(direction, yaw_values, pitch_values, vss_grid)
        yaw_index = _nearest_periodic_index(yaw_values, float(mapped["yaw"]))
        pitch_index = _nearest_periodic_index(pitch_values, float(mapped["pitch"]))
        _add_candidate(
            candidates,
            yaw_index=yaw_index,
            pitch_index=pitch_index,
            yaw_values=yaw_values,
            pitch_values=pitch_values,
            vss_grid=vss_grid,
            source=f"fibonacci_{panel_index:02d}",
            panel_index=panel_index,
        )

    deployed_yaw = float(deployed["final_yaw_deg"])
    deployed_pitch = float(deployed["final_pitch_deg"])
    _add_candidate(
        candidates,
        yaw_index=_nearest_periodic_index(yaw_values, deployed_yaw),
        pitch_index=_nearest_periodic_index(pitch_values, deployed_pitch),
        yaw_values=yaw_values,
        pitch_values=pitch_values,
        vss_grid=vss_grid,
        source="deployed_pipeline",
    )

    optimum_flat = int(np.nanargmin(vss_grid.reshape(-1)))
    optimum_pitch, optimum_yaw = np.unravel_index(optimum_flat, vss_grid.shape)
    _add_candidate(
        candidates,
        yaw_index=int(optimum_yaw),
        pitch_index=int(optimum_pitch),
        yaw_values=yaw_values,
        pitch_values=pitch_values,
        vss_grid=vss_grid,
        source="tomo_global_optimum",
    )

    rows = list(candidates.values())
    source_order = {f"fibonacci_{i:02d}": i for i in range(panel_size)}

    def order_key(row: dict[str, Any]) -> tuple[int, int, str]:
        if row["fixed_panel"]:
            return (0, int(row["panel_index"]), str(row["candidate_id"]))
        if "deployed_pipeline" in row["sources"]:
            return (1, 0, str(row["candidate_id"]))
        return (2, 0, str(row["candidate_id"]))

    rows.sort(key=order_key)
    for row in rows:
        # If an anchor coincides with a panel cell, keep the stable panel ID and
        # expose every semantic role through ``sources``.
        row["sources"] = sorted(
            row["sources"], key=lambda x: (source_order.get(x, panel_size + 1), x)
        )
    return rows


def _direction_from_orientation(yaw_deg: float, pitch_deg: float) -> np.ndarray:
    rotation = np.asarray(mesh_rotation.rotation_matrix(yaw_deg, pitch_deg), float)
    direction = rotation.T @ np.asarray([0.0, 0.0, 1.0])
    return direction / max(float(np.linalg.norm(direction)), 1e-12)


def _angular_distance_degrees(a: dict[str, Any], b: dict[str, Any]) -> float:
    da = _direction_from_orientation(float(a["yaw_deg"]), float(a["pitch_deg"]))
    db = _direction_from_orientation(float(b["yaw_deg"]), float(b["pitch_deg"]))
    return math.degrees(math.acos(float(np.clip(np.dot(da, db), -1.0, 1.0))))


def _stable_top_ids(rows: list[dict[str, Any]], metric: str, k: int) -> list[str]:
    ordered = sorted(rows, key=lambda row: (float(row[metric]), str(row["candidate_id"])))
    return [str(row["candidate_id"]) for row in ordered[: min(k, len(ordered))]]


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator > 1e-12:
        return numerator / denominator
    if abs(numerator) <= 1e-12:
        return 1.0
    return float("inf")


def _summarize_mesh(stem: str, records: list[dict[str, Any]]) -> dict[str, Any] | None:
    successful = [row for row in records if row.get("ok")]
    panel = [row for row in successful if row.get("fixed_panel")]
    if len(panel) < 3:
        return None

    tomo = np.asarray([row["tomo_vss"] for row in panel], dtype=np.float64)
    cura = np.asarray([row["cura_support_volume_mm3"] for row in panel], dtype=np.float64)
    spearman = float(spearmanr(tomo, cura).statistic)
    kendall = float(kendalltau(tomo, cura, variant="b").statistic)
    tomo_best_panel = min(panel, key=lambda row: (float(row["tomo_vss"]), row["candidate_id"]))
    cura_best_panel = min(
        panel, key=lambda row: (float(row["cura_support_volume_mm3"]), row["candidate_id"])
    )
    tomo_global = next(
        (row for row in successful if "tomo_global_optimum" in row["sources"]), None
    )
    if tomo_global is None:
        return None
    cura_best_all = min(
        successful,
        key=lambda row: (float(row["cura_support_volume_mm3"]), row["candidate_id"]),
    )
    global_regret_ratio = _safe_ratio(
        float(tomo_global["cura_support_volume_mm3"]),
        float(cura_best_all["cura_support_volume_mm3"]),
    )
    deployed = next(
        (row for row in successful if "deployed_pipeline" in row["sources"]), None
    )

    result: dict[str, Any] = {
        "mesh": stem,
        "fixed_panel_count": len(panel),
        "all_evaluated_count": len(successful),
        "fixed_panel_spearman": spearman,
        "fixed_panel_kendall_tau_b": kendall,
        "fixed_panel_tomo_best_candidate": tomo_best_panel["candidate_id"],
        "fixed_panel_cura_best_candidate": cura_best_panel["candidate_id"],
        "fixed_panel_best_exact_agreement": (
            tomo_best_panel["candidate_id"] == cura_best_panel["candidate_id"]
        ),
        "fixed_panel_best_angular_difference_deg": _angular_distance_degrees(
            tomo_best_panel, cura_best_panel
        ),
        "tomo_global_yaw_deg": float(tomo_global["yaw_deg"]),
        "tomo_global_pitch_deg": float(tomo_global["pitch_deg"]),
        "tomo_global_cura_support_mm3": float(tomo_global["cura_support_volume_mm3"]),
        "cura_best_evaluated_candidate": cura_best_all["candidate_id"],
        "cura_best_evaluated_yaw_deg": float(cura_best_all["yaw_deg"]),
        "cura_best_evaluated_pitch_deg": float(cura_best_all["pitch_deg"]),
        "cura_best_evaluated_support_mm3": float(cura_best_all["cura_support_volume_mm3"]),
        "tomo_global_is_cura_best_evaluated": (
            tomo_global["candidate_id"] == cura_best_all["candidate_id"]
        ),
        "tomo_global_cura_regret_ratio": global_regret_ratio,
        "tomo_global_cura_regret_percent": 100.0 * (global_regret_ratio - 1.0),
        "tomo_global_to_cura_best_angle_deg": _angular_distance_degrees(
            tomo_global, cura_best_all
        ),
    }
    for k in TOP_K_VALUES:
        tomo_ids = _stable_top_ids(panel, "tomo_vss", k)
        cura_ids = _stable_top_ids(panel, "cura_support_volume_mm3", k)
        denominator = max(1, min(k, len(panel)))
        overlap = len(set(tomo_ids) & set(cura_ids))
        result[f"fixed_panel_top{k}_overlap_count"] = overlap
        result[f"fixed_panel_top{k}_agreement_fraction"] = overlap / denominator
        result[f"fixed_panel_tomo_top{k}"] = ";".join(tomo_ids)
        result[f"fixed_panel_cura_top{k}"] = ";".join(cura_ids)
    if deployed is not None:
        deployed_regret = _safe_ratio(
            float(deployed["cura_support_volume_mm3"]),
            float(cura_best_all["cura_support_volume_mm3"]),
        )
        result.update(
            {
                "deployed_route": deployed["deployed_route"],
                "deployed_yaw_deg": float(deployed["yaw_deg"]),
                "deployed_pitch_deg": float(deployed["pitch_deg"]),
                "deployed_cura_support_mm3": float(deployed["cura_support_volume_mm3"]),
                "deployed_cura_regret_ratio": deployed_regret,
                "deployed_cura_regret_percent": 100.0 * (deployed_regret - 1.0),
            }
        )
    return result


def _finite_mean(values: Iterable[float]) -> float:
    array = np.asarray(list(values), dtype=np.float64)
    array = array[np.isfinite(array)]
    return float(np.mean(array)) if len(array) else float("nan")


def _overall_summary(mesh_rows: list[dict[str, Any]], records: list[dict[str, Any]]) -> dict[str, Any]:
    regrets = np.asarray(
        [row["tomo_global_cura_regret_ratio"] for row in mesh_rows], dtype=np.float64
    )
    successful = [row for row in records if row.get("ok")]
    return {
        "mesh_count": len(mesh_rows),
        "successful_slice_count": len(successful),
        "failed_slice_count": sum(not bool(row.get("ok")) for row in records),
        "fixed_panel_spearman_macro_mean": _finite_mean(
            row["fixed_panel_spearman"] for row in mesh_rows
        ),
        "fixed_panel_kendall_tau_b_macro_mean": _finite_mean(
            row["fixed_panel_kendall_tau_b"] for row in mesh_rows
        ),
        "fixed_panel_top3_agreement_macro_mean": _finite_mean(
            row["fixed_panel_top3_agreement_fraction"] for row in mesh_rows
        ),
        "fixed_panel_top5_agreement_macro_mean": _finite_mean(
            row["fixed_panel_top5_agreement_fraction"] for row in mesh_rows
        ),
        "fixed_panel_best_exact_agreement_count": sum(
            bool(row["fixed_panel_best_exact_agreement"]) for row in mesh_rows
        ),
        "tomo_global_is_cura_best_evaluated_count": sum(
            bool(row["tomo_global_is_cura_best_evaluated"]) for row in mesh_rows
        ),
        "tomo_global_cura_regret_ratio_mean": float(np.mean(regrets)) if len(regrets) else float("nan"),
        "tomo_global_cura_regret_ratio_median": (
            float(np.median(regrets)) if len(regrets) else float("nan")
        ),
        "tomo_global_cura_regret_ratio_max": float(np.max(regrets)) if len(regrets) else float("nan"),
        "total_cura_wall_clock_s": float(
            sum(float(row.get("cura_wall_clock_s", 0.0)) for row in records)
        ),
    }


def _configuration(
    *,
    slicer: CuraSlicer,
    critical_angle: float,
    target_diagonal: float,
    panel_size: int,
    selected_meshes: list[str],
    max_candidates: int | None,
) -> dict[str, Any]:
    engine = Path(slicer.curaengine).resolve()
    legacy_path = Path(legacy_profile.__file__).resolve()
    parser_path = CURA_CLI_SRC / "cura_cli" / "gcode_support.py"
    rotation_path = Path(mesh_rotation.__file__).resolve()
    settings = {key: str(value) for key, value in sorted(slicer.settings.items())}
    return {
        "engine": {
            "generation": "legacy CuraEngine 15.04.6",
            "executable": str(engine),
            "sha256": _sha256(engine),
            "size_bytes": engine.stat().st_size,
            "mtime_utc": datetime.fromtimestamp(
                engine.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
            "command_shape": "CuraEngine -s camelCaseKey=value ... -o out.gcode oriented.stl",
        },
        "profile": {
            "name": "Sindoh DP103 PLA translated from the official 3DWOX profile",
            "source_module": str(legacy_path),
            "source_sha256": _sha256(legacy_path),
            "legacy_engine_settings": settings,
            "human_units": {
                "layer_height_mm": legacy_profile.LAYER_HEIGHT_MM,
                "initial_layer_height_mm": (
                    legacy_profile.LAYER0_THICKNESS_MM
                    if legacy_profile.LAYER0_THICKNESS_MM > 0
                    else legacy_profile.LAYER_HEIGHT_MM
                ),
                "nozzle_diameter_mm": legacy_profile.NOZZLE_SIZE_MM,
                "wall_thickness_mm": legacy_profile.WALL_THICKNESS_MM,
                "solid_layer_thickness_mm": legacy_profile.SOLID_LAYER_THICKNESS_MM,
                "infill_density_percent": legacy_profile.FILL_DENSITY_PCT,
                "infill_pattern": "lines",
                "filament_diameter_mm": legacy_profile.FILAMENT_DIAMETER_MM,
                "support_enabled": True,
                "support_placement": "everywhere",
                "support_angle_deg": critical_angle,
                "support_pattern": "lines (legacy supportType=1)",
                "support_fill_rate_percent": legacy_profile.SUPPORT_FILL_RATE_PCT,
                "support_xy_distance_mm": legacy_profile.SUPPORT_XY_DISTANCE_MM,
                "support_z_distance_mm": legacy_profile.SUPPORT_Z_DISTANCE_MM,
                "bed_adhesion": "one DP103 skirt line; excluded from support-only metric",
            },
        },
        "build_plate": {
            "width_mm": cura_config.DEFAULT_BED_WIDTH_MM,
            "depth_mm": cura_config.DEFAULT_BED_DEPTH_MM,
            "mesh_placement": "AABB centred at (width/2, depth/2), minimum z=0",
        },
        "mesh_scaling": {
            "rule": "uniform scale to target axis-aligned bounding-box diagonal",
            "target_aabb_diagonal_mm": target_diagonal,
        },
        "metrics": {
            "cura": "support-only extruded filament volume",
            "cura_unit": "mm^3",
            "cura_parser": str(parser_path),
            "cura_parser_sha256": _sha256(parser_path),
            "cura_parser_method": "TYPE:SUPPORT segments with E high-water-mark correction",
            "tomo": "cached TOMO_CPU v_ss at 1-degree resolution and 60-degree critical angle",
            "tomo_unit": "native v_ss proxy units (rank comparisons only)",
            "direction_convention_module": str(rotation_path),
            "direction_convention_sha256": _sha256(rotation_path),
        },
        "candidate_rule": {
            "ranking_panel": (
                f"same {panel_size}-point directed spherical-Fibonacci panel for every mesh; "
                "independent of TOMO scores"
            ),
            "anchors": ["deployed_pipeline", "tomo_global_optimum"],
            "deduplication": "exact canonical 1-degree yaw/pitch grid cell; 360-degree endpoints removed",
            "ranking_metrics_scope": "fixed Fibonacci panel only",
            "regret_scope": "TOMO global optimum versus best Cura support among all sliced panel+anchor directions",
            "top_k_definition": "set overlap fraction |TOMO top-k intersect Cura top-k| / k",
            "tie_break": "candidate_id lexical order after metric value",
            "panel_size": panel_size,
            "max_candidates_debug_limit": max_candidates,
        },
        "selected_meshes": selected_meshes,
    }


def _save_outputs(
    *,
    json_path: Path,
    records_path: Path,
    summary_path: Path,
    started_utc: str,
    config: dict[str, Any],
    fingerprint: str,
    inputs: list[dict[str, Any]],
    records: list[dict[str, Any]],
    expected_count: int,
) -> dict[str, Any]:
    mesh_rows = [
        summary
        for stem in config["selected_meshes"]
        if (
            summary := _summarize_mesh(
                stem, [row for row in records if row["mesh"] == stem]
            )
        )
        is not None
    ]
    successful_keys = {
        (row["mesh"], row["candidate_id"]) for row in records if row.get("ok")
    }
    complete = len(successful_keys) == expected_count
    overall = _overall_summary(mesh_rows, records) if mesh_rows else None
    payload = {
        "status": "complete" if complete else "incomplete",
        "started_utc": started_utc,
        "updated_utc": _utc_now(),
        "completed_utc": _utc_now() if complete else None,
        "configuration_fingerprint": fingerprint,
        "config": config,
        "inputs": inputs,
        "expected_slice_count": expected_count,
        "completed_slice_count": len(successful_keys),
        "summary": overall,
        "mesh_summaries": mesh_rows,
        "records": records,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    flat_records = []
    for row in records:
        flat = dict(row)
        flat["sources"] = ";".join(row["sources"])
        flat_records.append(flat)
    flat_summaries = []
    for row in mesh_rows:
        flat_summaries.append(dict(row))
    _write_csv(records_path, flat_records)
    _write_csv(summary_path, flat_summaries)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--critical-angle", type=float, default=60.0)
    parser.add_argument(
        "--target-aabb-diagonal-mm", type=float, default=DEFAULT_TARGET_AABB_DIAGONAL_MM
    )
    parser.add_argument("--panel-size", type=int, default=DEFAULT_PANEL_SIZE)
    parser.add_argument(
        "--mesh",
        dest="meshes",
        action="append",
        choices=ORGANIC_MESHES,
        help="restrict to one or more mesh stems (repeat option)",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=None,
        help="debug/smoke limit after deterministic candidate construction",
    )
    parser.add_argument("--output-stem", default=DEFAULT_OUTPUT_STEM)
    parser.add_argument("--force", action="store_true", help="discard matching output cache")
    parser.add_argument(
        "--refresh-metadata",
        action="store_true",
        help=(
            "reuse successful slices only when inputs, settings, and executable hash are "
            "unchanged apart from descriptive engine-generation metadata"
        ),
    )
    parser.add_argument("--plan-only", action="store_true", help="write the plan without slicing")
    args = parser.parse_args()

    selected_meshes = list(args.meshes or ORGANIC_MESHES)
    if len(set(selected_meshes)) != len(selected_meshes):
        raise ValueError("duplicate --mesh values are not allowed")
    if args.max_candidates is not None and args.max_candidates < 1:
        raise ValueError("--max-candidates must be positive")

    slicer = CuraSlicer(
        engine="legacy",
        critical_angle=args.critical_angle,
        support_placement="everywhere",
    )
    deployed_records = _load_deployed_records(DEPLOYED_PIPELINE_JSON)
    config = _configuration(
        slicer=slicer,
        critical_angle=args.critical_angle,
        target_diagonal=args.target_aabb_diagonal_mm,
        panel_size=args.panel_size,
        selected_meshes=selected_meshes,
        max_candidates=args.max_candidates,
    )

    inputs: list[dict[str, Any]] = []
    candidates_by_mesh: dict[str, list[dict[str, Any]]] = {}
    mesh_objects: dict[str, Any] = {}
    for stem in selected_meshes:
        mesh_path = _mesh_path(stem)
        grid_path = CACHE_DIR / f"{stem}{GRID_SUFFIX}"
        if not grid_path.is_file():
            raise FileNotFoundError(f"missing TOMO grid: {grid_path}")
        with np.load(grid_path, allow_pickle=False) as data:
            yaw, pitch, vss = _canonical_grid_arrays(data)
            candidates = _candidate_set(
                yaw_values=yaw,
                pitch_values=pitch,
                vss_grid=vss,
                deployed=deployed_records[stem],
                panel_size=args.panel_size,
            )
        if args.max_candidates is not None:
            candidates = candidates[: args.max_candidates]
        candidates_by_mesh[stem] = candidates
        mesh = mesh_rotation.load_mesh(mesh_path)
        original_diagonal = float(np.linalg.norm(mesh.extents))
        scale = args.target_aabb_diagonal_mm / original_diagonal
        mesh.apply_scale(scale)
        mesh_objects[stem] = mesh
        inputs.append(
            {
                "mesh": stem,
                "mesh_path": str(mesh_path.resolve()),
                "mesh_sha256": _sha256(mesh_path),
                "grid_path": str(grid_path.resolve()),
                "grid_sha256": _sha256(grid_path),
                "grid_shape_canonical": [len(pitch), len(yaw)],
                "original_aabb_diagonal_mesh_units": original_diagonal,
                "uniform_scale_to_mm": scale,
                "deployed_route": deployed_records[stem]["route"],
                "deployed_verification_count": deployed_records[stem]["verification_count"],
                "deployed_escalated": deployed_records[stem]["escalated"],
                "candidate_count": len(candidates),
                "candidates": candidates,
            }
        )

    fingerprint_material = {
        "config": config,
        "inputs": inputs,
        "deployed_pipeline_sha256": _sha256(DEPLOYED_PIPELINE_JSON),
    }
    fingerprint = _json_hash(fingerprint_material)
    expected_count = sum(len(candidates) for candidates in candidates_by_mesh.values())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / f"{args.output_stem}.json"
    records_path = OUTPUT_DIR / f"{args.output_stem}_records.csv"
    summary_path = OUTPUT_DIR / f"{args.output_stem}_mesh_summary.csv"
    started_utc = _utc_now()
    records: list[dict[str, Any]] = []
    if json_path.is_file() and not args.force:
        previous = json.loads(json_path.read_text(encoding="utf-8"))
        previous_fingerprint = previous.get("configuration_fingerprint")
        if previous_fingerprint != fingerprint:
            if not args.refresh_metadata:
                raise RuntimeError(
                    f"existing {json_path.name} has a different configuration; "
                    "use another --output-stem, pass --force, or use --refresh-metadata "
                    "for a metadata-only label correction"
                )
            previous_config = json.loads(json.dumps(previous.get("config", {})))
            try:
                previous_config["engine"]["generation"] = config["engine"]["generation"]
            except (KeyError, TypeError) as exc:
                raise RuntimeError("previous output lacks engine metadata") from exc
            if previous_config != config or previous.get("inputs") != inputs:
                raise RuntimeError(
                    "--refresh-metadata refused: settings, executable/input hashes, or "
                    "candidate definitions changed"
                )
        started_utc = str(previous.get("started_utc") or started_utc)
        records = list(previous.get("records", []))
    elif args.force:
        records = []

    cached = {
        (str(row["mesh"]), str(row["candidate_id"])): row
        for row in records
        if row.get("ok")
    }
    print(
        f"configuration={fingerprint[:12]} meshes={len(selected_meshes)} "
        f"expected_slices={expected_count} cached={len(cached)}",
        flush=True,
    )
    for item in inputs:
        print(
            f"plan {item['mesh']}: candidates={item['candidate_count']} "
            f"panel={sum(bool(row['fixed_panel']) for row in item['candidates'])} "
            f"scale={item['uniform_scale_to_mm']:.9g}",
            flush=True,
        )

    payload = _save_outputs(
        json_path=json_path,
        records_path=records_path,
        summary_path=summary_path,
        started_utc=started_utc,
        config=config,
        fingerprint=fingerprint,
        inputs=inputs,
        records=records,
        expected_count=expected_count,
    )
    if args.plan_only:
        print(f"plan written: {json_path}", flush=True)
        return

    deployed_by_mesh = deployed_records
    for stem in selected_meshes:
        mesh = mesh_objects[stem]
        for candidate in candidates_by_mesh[stem]:
            key = (stem, str(candidate["candidate_id"]))
            if key in cached:
                continue
            # Replace any earlier failed attempt for the same key before retrying.
            records = [
                row
                for row in records
                if (str(row["mesh"]), str(row["candidate_id"])) != key
            ]
            started = time.perf_counter()
            result = slicer.slice_orientation(
                mesh, float(candidate["yaw_deg"]), float(candidate["pitch_deg"])
            )
            elapsed = time.perf_counter() - started
            row = {
                "mesh": stem,
                "candidate_id": candidate["candidate_id"],
                "sources": list(candidate["sources"]),
                "fixed_panel": bool(candidate["fixed_panel"]),
                "panel_index": candidate["panel_index"],
                "yaw_deg": float(candidate["yaw_deg"]),
                "pitch_deg": float(candidate["pitch_deg"]),
                "tomo_vss": float(candidate["tomo_vss"]),
                "deployed_route": deployed_by_mesh[stem]["route"],
                "cura_support_volume_mm3": float(result.support_volume_mm3),
                "cura_total_volume_mm3": float(result.total_volume_mm3),
                "cura_support_length_mm": float(result.support_length_mm),
                "cura_wall_clock_s": elapsed,
                "ok": bool(result.ok),
                "error": str(result.error),
            }
            records.append(row)
            cached[key] = row if result.ok else None
            payload = _save_outputs(
                json_path=json_path,
                records_path=records_path,
                summary_path=summary_path,
                started_utc=started_utc,
                config=config,
                fingerprint=fingerprint,
                inputs=inputs,
                records=records,
                expected_count=expected_count,
            )
            print(
                f"[{len([r for r in records if r.get('ok')]):3d}/{expected_count}] "
                f"{stem:<30} {candidate['candidate_id']:<22} "
                f"yaw={candidate['yaw_deg']:7.2f} pitch={candidate['pitch_deg']:7.2f} "
                f"TOMO={candidate['tomo_vss']:12.4g} "
                f"Cura={result.support_volume_mm3:11.3f} mm^3 "
                f"time={elapsed:6.2f}s ok={result.ok}",
                flush=True,
            )
            if not result.ok:
                print(f"  error: {result.error}", flush=True)

    payload = _save_outputs(
        json_path=json_path,
        records_path=records_path,
        summary_path=summary_path,
        started_utc=started_utc,
        config=config,
        fingerprint=fingerprint,
        inputs=inputs,
        records=records,
        expected_count=expected_count,
    )
    print(f"status={payload['status']} saved={json_path}", flush=True)
    if payload.get("summary"):
        print(json.dumps(payload["summary"], indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
