"""Audit happy-method escalation on the cached five-group TOMO_CPU set.

This is a post-hoc verification pass: it reads the saved G5 SFTF candidate CSVs
and cached 3 degree TOMO_CPU grids, then applies the same top-10 -> detector ->
top-30 happy-method policy used for the Stanford 1 degree meshes.  No TOMO DLL
or SFTF candidate recomputation is needed.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField.support_flow_tensor_field import load_mesh  # noqa: E402
from scripts.experiment_sftf_budget_curve import (  # noqa: E402
    _angle_delta_degrees,
    _window_cells,
)
from scripts.regenerate_sftf_vs_saved_tomo_summary import (  # noqa: E402
    _signed_orientation,
    _tomo_best,
)
from scripts._mesh_paths import G5_RAW_MESH

G5_ROOT = PROJECT_ROOT / "Experimental" / "G5Test"
# Stored grids kept the pre-rename naming (see the _tomo_int3_ rename commits).
G5_CACHE_DIR = G5_ROOT / "tomo_int3_cache"
G5_CANDIDATE_DIR = G5_ROOT / "SFTF_result"
G5_MESH_DIR = G5_RAW_MESH
G5_GRID_SUFFIX = "_tomo_int3_3deg_60deg.npz"
G5_CANDIDATE_SUFFIX = "_candidates.csv"

# Thresholds re-tuned on the int16-overflow-corrected TOMO grids (2026-07-04).
# The submitted values (K 10/30/100, high_support 0.03) were fit when the large
# E-group meshes were excluded by the overflow bug; once their v_ss is correct
# they enter the ratio-valid set and, being high-volume/low-support, never
# passed the old high_support>=0.03 gate, so AVE failed to escalate on the
# genuinely hard cases (E1/E7/E9). The corrected operating point ("config B")
# lowers the support gate, deepens escalation, and adds a big-jump trigger.
DEFAULT_BASE_TOP_K = 10
DEFAULT_ESCALATE_TOP_K = 50
DEFAULT_SEVERE_ESCALATE_TOP_K = 200
DEFAULT_WINDOW_DEGREES = 10.0
DEFAULT_MIN_ANGLE_DEGREES = 3.0
DEFAULT_HIGH_SUPPORT_FRACTION = 0.008
DEFAULT_EDGE_MARGIN_DEGREES = 1.0
DEFAULT_LOW_GAIN = 1.5
DEFAULT_HIGH_GAIN = 3.0
DEFAULT_BOUNDARY_GAIN = 3.0


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _ratio(value: float, reference: float) -> float:
    return value / reference if reference > 1e-12 else float("inf")


def _record_group_from_name(name: str) -> str:
    parts = name.split("_")
    return parts[1][0].upper() if len(parts) > 1 and parts[1] else "?"


def _mesh_path_for_stem(stem: str) -> Path:
    candidates = sorted(G5_MESH_DIR.glob(f"{stem}.*"))
    if not candidates:
        raise FileNotFoundError(f"no mesh found for {stem} in {G5_MESH_DIR}")
    return candidates[0]


def _bbox_volume(mesh_path: Path) -> tuple[float, int]:
    mesh = load_mesh(str(mesh_path))
    bounds = np.asarray(mesh.bounds, dtype=np.float64)
    extents = np.maximum(bounds[1] - bounds[0], 0.0)
    return max(float(np.prod(extents)), 1e-12), int(len(mesh.faces))


def _read_candidate_csv(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            direction = np.asarray(
                [float(row["dir_x"]), float(row["dir_y"]), float(row["dir_z"])],
                dtype=np.float64,
            )
            rows.append(
                {
                    "score": float(row["tuned_score"]),
                    "rayleigh": float(row["rayleigh"]),
                    "pair": float(row["pair"]),
                    "bed": float(row["bed"]),
                    "hit": int(float(row["hit"])),
                    "direction": direction,
                }
            )
    if not rows:
        raise ValueError(f"empty candidate CSV: {path}")
    return rows


def _rank_candidates(
    candidates: list[dict[str, object]],
    *,
    limit: int,
    min_angle_degrees: float,
) -> list[dict[str, object]]:
    ranked: list[dict[str, object]] = []
    min_dot = float(np.cos(np.deg2rad(min_angle_degrees)))
    for row in sorted(candidates, key=lambda item: float(item["score"])):
        direction = np.asarray(row["direction"], dtype=np.float64)
        if any(abs(float(np.dot(direction, np.asarray(existing["direction"], dtype=np.float64)))) >= min_dot for existing in ranked):
            continue
        ranked.append(row)
        if len(ranked) >= limit:
            break
    return ranked


def _ranked_centers(
    candidates: list[dict[str, object]],
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
    *,
    limit: int,
    min_angle_degrees: float,
) -> list[dict[str, object]]:
    centers: list[dict[str, object]] = []
    for rank, item in enumerate(
        _rank_candidates(candidates, limit=limit, min_angle_degrees=min_angle_degrees),
        start=1,
    ):
        _positive, signed = _signed_orientation(
            np.asarray(item["direction"], dtype=np.float64),
            yaw_values,
            pitch_values,
            vss_grid,
        )
        centers.append(
            {
                "rank": rank,
                "score": float(item["score"]),
                "yaw": float(signed["yaw"]),
                "pitch": float(signed["pitch"]),
                "vss": float(signed["vss"]),
                "alignment": float(signed["alignment"]),
            }
        )
    return centers


def _local_window_result(
    centers: list[dict[str, object]],
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
    *,
    radius_degrees: float,
) -> dict[str, object]:
    visited_cells: set[tuple[int, int]] = set()
    best = {"yaw": float("nan"), "pitch": float("nan"), "vss": float("inf")}
    for center in centers:
        for pitch_id, yaw_id in _window_cells(
            yaw_values,
            pitch_values,
            yaw=float(center["yaw"]),
            pitch=float(center["pitch"]),
            radius_degrees=radius_degrees,
        ):
            cell = (int(pitch_id), int(yaw_id))
            if cell in visited_cells:
                continue
            visited_cells.add(cell)
            value = float(vss_grid[pitch_id, yaw_id])
            if value < best["vss"]:
                best = {
                    "yaw": float(yaw_values[yaw_id]),
                    "pitch": float(pitch_values[pitch_id]),
                    "vss": value,
                }
    seed_best = min(centers, key=lambda item: float(item["vss"])) if centers else None
    return {
        "seed_best": seed_best,
        "local_best": best,
        "cell_count": int(len(visited_cells)),
    }


def _cell_on_window_boundary(
    centers: list[dict[str, object]],
    *,
    yaw: float,
    pitch: float,
    radius_degrees: float,
    edge_margin_degrees: float,
) -> bool:
    if not np.isfinite(yaw) or not np.isfinite(pitch):
        return False
    for center in centers:
        yaw_delta = float(_angle_delta_degrees(np.asarray([yaw]), float(center["yaw"]))[0])
        pitch_delta = float(_angle_delta_degrees(np.asarray([pitch]), float(center["pitch"]))[0])
        inside = yaw_delta <= radius_degrees + 1e-9 and pitch_delta <= radius_degrees + 1e-9
        if inside and max(yaw_delta, pitch_delta) >= radius_degrees - edge_margin_degrees:
            return True
    return False


def _detector_flags(
    *,
    normalized_local_vss: float,
    seed_to_local_gain: float,
    boundary_hit: bool,
    high_support_fraction: float,
    low_gain: float,
    high_gain: float,
    boundary_gain: float,
) -> tuple[bool, bool, list[str]]:
    reasons: list[str] = []
    high_support = normalized_local_vss >= high_support_fraction
    # window search barely improved on the seed -> seed sits on a plateau
    stuck = seed_to_local_gain <= low_gain
    # window search moved far from the seed -> the seed ranking was unreliable
    big_jump = seed_to_local_gain >= high_gain
    if high_support:
        reasons.append("high_normalized_support")
    if boundary_hit:
        reasons.append("boundary_local_minimum")
    if stuck:
        reasons.append("low_seed_to_local_gain")
    if big_jump:
        reasons.append("high_seed_to_local_gain")
    trigger = bool(high_support and (boundary_hit or stuck or big_jump))
    # a local minimum stuck on the window boundary means the true basin was
    # missed entirely -> route to deep (severe) escalation
    severe = bool(trigger and boundary_hit and stuck)
    if severe:
        reasons.append("boundary_plateau")
    return trigger, severe, reasons


def _stage_row(
    *,
    name: str,
    group: str,
    stage: str,
    triggered: bool,
    reasons: list[str],
    centers: list[dict[str, object]],
    result: dict[str, object],
    tomo_best: dict[str, float],
    bbox_volume: float,
    face_count: int,
    candidate_count: int,
    full_grid_cells: int,
    window_degrees: float,
) -> dict[str, object]:
    seed_best = result["seed_best"]
    local_best = result["local_best"]
    seed_vss = float(seed_best["vss"]) if seed_best else float("inf")
    local_vss = float(local_best["vss"])
    return {
        "mesh": name,
        "group": group,
        "stage": stage,
        "triggered": bool(triggered),
        "trigger_reasons": ";".join(reasons),
        "face_count": int(face_count),
        "candidate_count": int(candidate_count),
        "candidate_center_count": int(len(centers)),
        "window_degrees": float(window_degrees),
        "full_grid_cells": int(full_grid_cells),
        "local_cell_count": int(result["cell_count"]),
        "local_budget_fraction": int(result["cell_count"]) / max(1, int(full_grid_cells)),
        "bbox_volume": float(bbox_volume),
        "tomo_best_yaw": float(tomo_best["yaw"]),
        "tomo_best_pitch": float(tomo_best["pitch"]),
        "tomo_best_vss": float(tomo_best["vss"]),
        "seed_best_rank": int(seed_best["rank"]) if seed_best else 0,
        "seed_best_yaw": float(seed_best["yaw"]) if seed_best else float("nan"),
        "seed_best_pitch": float(seed_best["pitch"]) if seed_best else float("nan"),
        "seed_best_vss": seed_vss,
        "seed_best_ratio": _ratio(seed_vss, float(tomo_best["vss"])),
        "local_best_yaw": float(local_best["yaw"]),
        "local_best_pitch": float(local_best["pitch"]),
        "local_best_vss": local_vss,
        "local_best_ratio": _ratio(local_vss, float(tomo_best["vss"])),
        "normalized_local_vss": local_vss / bbox_volume,
        "seed_to_local_gain": seed_vss / local_vss if local_vss > 1e-12 else float("inf"),
    }


def analyze_condition(
    grid_path: Path,
    *,
    base_top_k: int,
    escalate_top_k: int,
    severe_escalate_top_k: int,
    window_degrees: float,
    min_angle_degrees: float,
    high_support_fraction: float,
    edge_margin_degrees: float,
    low_gain: float,
    high_gain: float,
    boundary_gain: float,
    include_nonpositive_best: bool,
) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    name = grid_path.name[: -len(G5_GRID_SUFFIX)]
    group = _record_group_from_name(name)
    candidate_path = G5_CANDIDATE_DIR / f"{name}{G5_CANDIDATE_SUFFIX}"
    if not candidate_path.exists():
        return [], {"mesh": name, "group": group, "skip_reason": "missing_candidate_csv"}

    grid_data = np.load(grid_path, allow_pickle=False)
    yaw_values = np.asarray(grid_data["yaw_values"], dtype=np.float64)
    pitch_values = np.asarray(grid_data["pitch_values"], dtype=np.float64)
    vss_grid = np.asarray(grid_data["vss_grid"], dtype=np.float64)
    tomo_best = _tomo_best(yaw_values, pitch_values, vss_grid)
    tomo_best_vss = float(tomo_best["vss"])
    if not include_nonpositive_best and tomo_best_vss <= 1e-12:
        return [], {"mesh": name, "group": group, "skip_reason": "nonpositive_tomo_best"}

    try:
        mesh_path = _mesh_path_for_stem(name)
    except FileNotFoundError:
        # A stored grid can outlive its mesh when the shared corpus is revised;
        # skip it instead of aborting the whole audit.
        return [], {"mesh": name, "group": group, "skip_reason": "missing_mesh_file"}
    bbox_volume, face_count = _bbox_volume(mesh_path)
    candidates = _read_candidate_csv(candidate_path)
    centers = _ranked_centers(
        candidates,
        yaw_values,
        pitch_values,
        vss_grid,
        limit=max(escalate_top_k, severe_escalate_top_k),
        min_angle_degrees=min_angle_degrees,
    )
    base_centers = centers[:base_top_k]
    base_result = _local_window_result(
        base_centers,
        yaw_values,
        pitch_values,
        vss_grid,
        radius_degrees=window_degrees,
    )
    base_seed = base_result["seed_best"]
    base_local = base_result["local_best"]
    seed_to_local_gain = (
        float(base_seed["vss"]) / float(base_local["vss"])
        if base_seed and float(base_local["vss"]) > 1e-12
        else float("inf")
    )
    normalized_local_vss = float(base_local["vss"]) / bbox_volume
    boundary_hit = _cell_on_window_boundary(
        base_centers,
        yaw=float(base_local["yaw"]),
        pitch=float(base_local["pitch"]),
        radius_degrees=window_degrees,
        edge_margin_degrees=edge_margin_degrees,
    )
    triggered, severe_boundary, reasons = _detector_flags(
        normalized_local_vss=normalized_local_vss,
        seed_to_local_gain=seed_to_local_gain,
        boundary_hit=boundary_hit,
        high_support_fraction=high_support_fraction,
        low_gain=low_gain,
        high_gain=high_gain,
        boundary_gain=boundary_gain,
    )

    rows = [
        _stage_row(
            name=name,
            group=group,
            stage="base_top_k",
            triggered=triggered,
            reasons=reasons,
            centers=base_centers,
            result=base_result,
            tomo_best=tomo_best,
            bbox_volume=bbox_volume,
            face_count=face_count,
            candidate_count=len(candidates),
            full_grid_cells=int(vss_grid.size),
            window_degrees=window_degrees,
        )
    ]
    final_centers = base_centers
    final_result = base_result
    if triggered:
        final_top_k = severe_escalate_top_k if severe_boundary else escalate_top_k
        final_centers = centers[:final_top_k]
        final_result = _local_window_result(
            final_centers,
            yaw_values,
            pitch_values,
            vss_grid,
            radius_degrees=window_degrees,
        )
        rows.append(
            _stage_row(
                name=name,
                group=group,
                stage="happy_method",
                triggered=triggered,
                reasons=reasons,
                centers=final_centers,
                result=final_result,
                tomo_best=tomo_best,
                bbox_volume=bbox_volume,
                face_count=face_count,
                candidate_count=len(candidates),
                full_grid_cells=int(vss_grid.size),
                window_degrees=window_degrees,
            )
        )

    rows.append(
        _stage_row(
            name=name,
            group=group,
            stage="adaptive_final",
            triggered=triggered,
            reasons=reasons,
            centers=final_centers,
            result=final_result,
            tomo_best=tomo_best,
            bbox_volume=bbox_volume,
            face_count=face_count,
            candidate_count=len(candidates),
            full_grid_cells=int(vss_grid.size),
            window_degrees=window_degrees,
        )
    )
    detail = {
        "mesh": name,
        "group": group,
        "grid_path": _display_path(grid_path),
        "candidate_path": _display_path(candidate_path),
        "mesh_path": _display_path(mesh_path),
        "face_count": face_count,
        "candidate_count": len(candidates),
        "bbox_volume": bbox_volume,
        "tomo_best": tomo_best,
        "triggered": triggered,
        "severe_boundary": severe_boundary,
        "trigger_reasons": reasons,
        "top_centers": centers[: max(escalate_top_k, severe_escalate_top_k)],
    }
    return rows, detail


def _summary_for(rows: list[dict[str, object]], *, group: str | None, stage: str) -> dict[str, object]:
    selected = [row for row in rows if row["stage"] == stage and (group is None or row["group"] == group)]
    ratios = np.asarray([float(row["local_best_ratio"]) for row in selected], dtype=np.float64)
    budgets = np.asarray([float(row["local_budget_fraction"]) for row in selected], dtype=np.float64)
    cells = np.asarray([float(row["local_cell_count"]) for row in selected], dtype=np.float64)
    triggers = np.asarray([bool(row["triggered"]) for row in selected], dtype=bool)
    return {
        "group": group if group is not None else "ALL",
        "stage": stage,
        "mesh_count": int(len(selected)),
        "triggered_count": int(np.sum(triggers)) if triggers.size else 0,
        "mean_local_ratio": float(np.mean(ratios)) if ratios.size else float("nan"),
        "median_local_ratio": float(np.median(ratios)) if ratios.size else float("nan"),
        "p80_local_ratio": float(np.percentile(ratios, 80)) if ratios.size else float("nan"),
        "max_local_ratio": float(np.max(ratios)) if ratios.size else float("nan"),
        "mean_local_cell_count": float(np.mean(cells)) if cells.size else float("nan"),
        "mean_local_budget_fraction": float(np.mean(budgets)) if budgets.size else float("nan"),
        "count_ratio_le_1_25": int(np.sum(ratios <= 1.25)) if ratios.size else 0,
        "count_ratio_le_1_50": int(np.sum(ratios <= 1.50)) if ratios.size else 0,
        "count_ratio_le_2_00": int(np.sum(ratios <= 2.00)) if ratios.size else 0,
    }


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups = sorted({str(row["group"]) for row in rows})
    stages = ["base_top_k", "adaptive_final", "happy_method"]
    summary = [_summary_for(rows, group=None, stage=stage) for stage in stages]
    for group in groups:
        summary.extend(_summary_for(rows, group=group, stage=stage) for stage in stages)
    return [row for row in summary if int(row["mesh_count"]) > 0]


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _parse_group_list(value: str) -> set[str]:
    groups = {item.strip().upper() for item in value.split(",") if item.strip()}
    invalid = groups - {"A", "B", "C", "D", "E"}
    if invalid:
        raise argparse.ArgumentTypeError(f"invalid groups: {sorted(invalid)}")
    return groups


def main() -> None:
    global G5_GRID_SUFFIX
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-top-k", type=int, default=DEFAULT_BASE_TOP_K)
    parser.add_argument("--escalate-top-k", type=int, default=DEFAULT_ESCALATE_TOP_K)
    parser.add_argument("--severe-escalate-top-k", type=int, default=DEFAULT_SEVERE_ESCALATE_TOP_K)
    parser.add_argument("--window-degrees", type=float, default=DEFAULT_WINDOW_DEGREES)
    parser.add_argument("--min-angle-degrees", type=float, default=DEFAULT_MIN_ANGLE_DEGREES)
    parser.add_argument("--high-support-fraction", type=float, default=DEFAULT_HIGH_SUPPORT_FRACTION)
    parser.add_argument("--edge-margin-degrees", type=float, default=DEFAULT_EDGE_MARGIN_DEGREES)
    parser.add_argument("--low-gain", type=float, default=DEFAULT_LOW_GAIN)
    parser.add_argument("--high-gain", type=float, default=DEFAULT_HIGH_GAIN)
    parser.add_argument("--boundary-gain", type=float, default=DEFAULT_BOUNDARY_GAIN)
    parser.add_argument("--groups", type=_parse_group_list, default={"A", "B", "C", "D", "E"})
    parser.add_argument("--include-nonpositive-best", action="store_true")
    parser.add_argument("--grid-suffix", default=G5_GRID_SUFFIX,
                        help="stored-grid filename suffix, e.g. _tomo_int3_1deg_60deg.npz")
    parser.add_argument("--output-stem", default="sftf_happy_method_g5_audit_3deg60")
    args = parser.parse_args()

    G5_GRID_SUFFIX = args.grid_suffix

    if args.base_top_k <= 0 or args.escalate_top_k < args.base_top_k or args.severe_escalate_top_k < args.escalate_top_k:
        raise ValueError("expected 0 < base_top_k <= escalate_top_k <= severe_escalate_top_k")

    grid_paths = [
        path
        for path in sorted(G5_CACHE_DIR.glob(f"*{G5_GRID_SUFFIX}"))
        if _record_group_from_name(path.name[: -len(G5_GRID_SUFFIX)]) in args.groups
    ]
    if not grid_paths:
        raise FileNotFoundError(f"no matching G5 grids found in {G5_CACHE_DIR}")

    print(
        "G5 happy-method audit: "
        f"{len(grid_paths)} grids, base K={args.base_top_k}, escalation K={args.escalate_top_k}, "
        f"severe K={args.severe_escalate_top_k}, "
        f"window=+/-{args.window_degrees:g} deg",
        flush=True,
    )
    rows: list[dict[str, object]] = []
    details: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    for index, grid_path in enumerate(grid_paths, start=1):
        name = grid_path.name[: -len(G5_GRID_SUFFIX)]
        print(f"[{index}/{len(grid_paths)}] {name}", flush=True)
        mesh_rows, detail = analyze_condition(
            grid_path,
            base_top_k=args.base_top_k,
            escalate_top_k=args.escalate_top_k,
            severe_escalate_top_k=args.severe_escalate_top_k,
            window_degrees=args.window_degrees,
            min_angle_degrees=args.min_angle_degrees,
            high_support_fraction=args.high_support_fraction,
            edge_margin_degrees=args.edge_margin_degrees,
            low_gain=args.low_gain,
            high_gain=args.high_gain,
            boundary_gain=args.boundary_gain,
            include_nonpositive_best=args.include_nonpositive_best,
        )
        if mesh_rows:
            rows.extend(mesh_rows)
            details.append(detail or {})
            base = next(row for row in mesh_rows if row["stage"] == "base_top_k")
            final = next(row for row in mesh_rows if row["stage"] == "adaptive_final")
            print(
                f"  base={float(base['local_best_ratio']):.3f} "
                f"trigger={bool(base['triggered'])} final={float(final['local_best_ratio']):.3f} "
                f"budget={100.0 * float(final['local_budget_fraction']):.2f}%",
                flush=True,
            )
        else:
            skipped.append(detail or {"mesh": name, "skip_reason": "unknown"})
            print(f"  skipped: {skipped[-1]['skip_reason']}", flush=True)

    if not rows:
        raise SystemExit("no usable G5 records")

    summary = summarize(rows)
    out_dir = PROJECT_ROOT / "Experimental" / "etc"
    csv_path = out_dir / f"{args.output_stem}.csv"
    summary_path = out_dir / f"{args.output_stem}_summary.csv"
    json_path = out_dir / f"{args.output_stem}.json"
    _write_csv(csv_path, rows)
    _write_csv(summary_path, summary)
    json_path.write_text(
        json.dumps(
            {
                "config": {
                    "base_top_k": args.base_top_k,
                    "escalate_top_k": args.escalate_top_k,
                    "severe_escalate_top_k": args.severe_escalate_top_k,
                    "window_degrees": args.window_degrees,
                    "min_angle_degrees": args.min_angle_degrees,
                    "high_support_fraction": args.high_support_fraction,
                    "edge_margin_degrees": args.edge_margin_degrees,
                    "low_gain": args.low_gain,
                    "high_gain": args.high_gain,
                    "boundary_gain": args.boundary_gain,
                    "groups": sorted(args.groups),
                    "grid_suffix": G5_GRID_SUFFIX,
                },
                "summary": summary,
                "rows": rows,
                "details": details,
                "skipped": skipped,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\n=== summary ===")
    for row in summary:
        if row["group"] == "ALL" or row["stage"] == "adaptive_final":
            print(
                f"{row['group']:<3} {row['stage']:<15} n={row['mesh_count']:<2} "
                f"trigger={row['triggered_count']:<2} mean={row['mean_local_ratio']:.3f} "
                f"median={row['median_local_ratio']:.3f} max={row['max_local_ratio']:.3f} "
                f"budget={100.0 * row['mean_local_budget_fraction']:.2f}% "
                f"<=2.0={row['count_ratio_le_2_00']}/{row['mesh_count']}",
                flush=True,
            )
    if skipped:
        print("\nskipped:")
        for item in skipped:
            print(f"  {item['mesh']}: {item['skip_reason']}", flush=True)
    print(
        "\nsaved: "
        + ", ".join(_display_path(path) for path in (csv_path, summary_path, json_path)),
        flush=True,
    )


if __name__ == "__main__":
    main()
