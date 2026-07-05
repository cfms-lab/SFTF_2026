"""Adaptive happy-method verification over saved TOMO_CPU grids.

The happy-method is an escalation policy, not a manually selected mesh label:

1. Run ordinary SFTF top-K local TOMO verification.
2. Detect low-confidence cases from verifier-visible signals only.
3. For triggered cases, add a wider SFTF/Pareto candidate set and re-verify.

All TOMO values are read from the saved exhaustive 1 degree grids.  Therefore
this script measures the decision policy deterministically without rerunning the
GPU/DLL backend.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    evaluate_support_flow_candidate_pool,
    load_mesh,
    support_flow_directions_from_candidate_pool,
)
from scripts.experiment_sftf_budget_curve import (  # noqa: E402
    _angle_delta_degrees,
    _mesh_path_for_grid,
    _window_cells,
)
from scripts.regenerate_sftf_vs_saved_tomo_summary import (  # noqa: E402
    GRID_SUFFIX,
    MESH_DIR,
    _signed_orientation,
    _tomo_best,
)

DEFAULT_BASE_TOP_K = 10
DEFAULT_ESCALATE_TOP_K = 30
DEFAULT_SEVERE_ESCALATE_TOP_K = 100
DEFAULT_PARETO_TOP_K = 10
DEFAULT_WINDOW_DEGREES = 10.0
DEFAULT_MIN_ANGLE_DEGREES = 3.0
DEFAULT_HIGH_SUPPORT_FRACTION = 0.03
DEFAULT_EDGE_MARGIN_DEGREES = 1.0
DEFAULT_LOW_GAIN = 1.5
DEFAULT_BOUNDARY_GAIN = 3.0


def _ratio(value: float, reference: float) -> float:
    return value / reference if reference > 1e-12 else float("inf")


def _bbox_volume(mesh) -> float:
    bounds = np.asarray(mesh.bounds, dtype=np.float64)
    extents = np.maximum(bounds[1] - bounds[0], 0.0)
    return max(float(np.prod(extents)), 1e-12)


def _ranked_centers(
    pool,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
    *,
    limit: int,
    min_angle_degrees: float,
    source: str,
    mesh=None,
    use_pareto: bool = False,
) -> list[dict[str, float | str]]:
    ranked = support_flow_directions_from_candidate_pool(
        pool,
        limit=limit,
        min_angle_degrees=min_angle_degrees,
        use_pareto=use_pareto,
        mesh=mesh,
    )
    centers: list[dict[str, float | str]] = []
    for item in ranked:
        _positive, signed = _signed_orientation(item.direction, yaw_values, pitch_values, vss_grid)
        centers.append(
            {
                "source": source,
                "rank": float(item.rank),
                "score": float(item.value),
                "yaw": float(signed["yaw"]),
                "pitch": float(signed["pitch"]),
                "vss": float(signed["vss"]),
                "alignment": float(signed["alignment"]),
            }
        )
    return centers


def _dedupe_centers(centers: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    seen: set[tuple[int, int]] = set()
    unique: list[dict[str, float | str]] = []
    for center in centers:
        key = (
            int(round(float(center["yaw"]))),
            int(round(float(center["pitch"]))),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(center)
    return unique


def _local_window_result(
    centers: list[dict[str, float | str]],
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
            cell_vss = float(vss_grid[pitch_id, yaw_id])
            if cell_vss < best["vss"]:
                best = {
                    "yaw": float(yaw_values[yaw_id]),
                    "pitch": float(pitch_values[pitch_id]),
                    "vss": cell_vss,
                }
    seed_best = min(centers, key=lambda item: float(item["vss"])) if centers else None
    return {
        "seed_best": seed_best,
        "local_best": best,
        "cell_count": int(len(visited_cells)),
    }


def _cell_on_window_boundary(
    centers: list[dict[str, float | str]],
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
    boundary_gain: float,
) -> tuple[bool, bool, list[str]]:
    reasons: list[str] = []
    high_support = normalized_local_vss >= high_support_fraction
    severe_boundary = boundary_hit and seed_to_local_gain >= boundary_gain
    if high_support:
        reasons.append("high_normalized_support")
    if boundary_hit:
        reasons.append("boundary_local_minimum")
    if seed_to_local_gain <= low_gain:
        reasons.append("low_seed_to_local_gain")
    if severe_boundary:
        reasons.append("large_boundary_seed_to_local_gain")
    trigger = bool((high_support and (boundary_hit or seed_to_local_gain <= low_gain)) or severe_boundary)
    return trigger, severe_boundary, reasons


def _row_from_result(
    *,
    mesh_name: str,
    stage: str,
    triggered: bool,
    trigger_reasons: list[str],
    centers: list[dict[str, float | str]],
    result: dict[str, object],
    tomo_best: dict[str, float],
    bbox_volume: float,
    full_grid_cells: int,
    window_degrees: float,
) -> dict[str, object]:
    seed_best = result["seed_best"]
    local_best = result["local_best"]
    seed_vss = float(seed_best["vss"]) if seed_best else float("inf")
    local_vss = float(local_best["vss"])
    local_cell_count = int(result["cell_count"])
    return {
        "mesh": mesh_name,
        "stage": stage,
        "triggered": bool(triggered),
        "trigger_reasons": ";".join(trigger_reasons),
        "candidate_center_count": int(len(centers)),
        "window_degrees": float(window_degrees),
        "full_grid_cells": int(full_grid_cells),
        "local_cell_count": local_cell_count,
        "local_budget_fraction": local_cell_count / max(1, full_grid_cells),
        "bbox_volume": float(bbox_volume),
        "tomo_best_yaw": float(tomo_best["yaw"]),
        "tomo_best_pitch": float(tomo_best["pitch"]),
        "tomo_best_vss": float(tomo_best["vss"]),
        "seed_best_source": str(seed_best["source"]) if seed_best else "",
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


def analyze_grid(
    grid_path: Path,
    *,
    base_top_k: int,
    escalate_top_k: int,
    severe_escalate_top_k: int,
    pareto_top_k: int,
    window_degrees: float,
    min_angle_degrees: float,
    high_support_fraction: float,
    edge_margin_degrees: float,
    low_gain: float,
    boundary_gain: float,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    data = np.load(grid_path, allow_pickle=True)
    yaw_values = np.asarray(data["yaw_values"], dtype=np.float64)
    pitch_values = np.asarray(data["pitch_values"], dtype=np.float64)
    vss_grid = np.asarray(data["vss_grid"], dtype=np.float64)
    tomo_best = _tomo_best(yaw_values, pitch_values, vss_grid)
    mesh_path = _mesh_path_for_grid(grid_path)

    start = time.perf_counter()
    mesh = load_mesh(str(mesh_path))
    pool = evaluate_support_flow_candidate_pool(mesh)
    elapsed = time.perf_counter() - start
    bbox_volume = _bbox_volume(mesh)

    baseline_centers = _ranked_centers(
        pool,
        yaw_values,
        pitch_values,
        vss_grid,
        limit=max(base_top_k, escalate_top_k, severe_escalate_top_k),
        min_angle_degrees=min_angle_degrees,
        source="sftf",
    )
    pareto_centers = (
        _ranked_centers(
            pool,
            yaw_values,
            pitch_values,
            vss_grid,
            limit=pareto_top_k,
            min_angle_degrees=min_angle_degrees,
            source="pareto",
            mesh=mesh,
            use_pareto=True,
        )
        if pareto_top_k > 0
        else []
    )

    base_centers = baseline_centers[:base_top_k]
    base_result = _local_window_result(
        base_centers,
        yaw_values,
        pitch_values,
        vss_grid,
        radius_degrees=window_degrees,
    )
    base_seed = base_result["seed_best"]
    base_local = base_result["local_best"]
    boundary_hit = _cell_on_window_boundary(
        base_centers,
        yaw=float(base_local["yaw"]),
        pitch=float(base_local["pitch"]),
        radius_degrees=window_degrees,
        edge_margin_degrees=edge_margin_degrees,
    )
    normalized_local_vss = float(base_local["vss"]) / bbox_volume
    seed_to_local_gain = (
        float(base_seed["vss"]) / float(base_local["vss"])
        if base_seed and float(base_local["vss"]) > 1e-12
        else float("inf")
    )
    triggered, severe_boundary, trigger_reasons = _detector_flags(
        normalized_local_vss=normalized_local_vss,
        seed_to_local_gain=seed_to_local_gain,
        boundary_hit=boundary_hit,
        high_support_fraction=high_support_fraction,
        low_gain=low_gain,
        boundary_gain=boundary_gain,
    )

    rows = [
        _row_from_result(
            mesh_name=mesh_path.name,
            stage="base_top_k",
            triggered=triggered,
            trigger_reasons=trigger_reasons,
            centers=base_centers,
            result=base_result,
            tomo_best=tomo_best,
            bbox_volume=bbox_volume,
            full_grid_cells=int(vss_grid.size),
            window_degrees=window_degrees,
        )
    ]

    final_centers = base_centers
    final_result = base_result
    if triggered:
        final_top_k = severe_escalate_top_k if severe_boundary else escalate_top_k
        final_centers = _dedupe_centers(baseline_centers[:final_top_k] + pareto_centers[:pareto_top_k])
        final_result = _local_window_result(
            final_centers,
            yaw_values,
            pitch_values,
            vss_grid,
            radius_degrees=window_degrees,
        )
        rows.append(
            _row_from_result(
                mesh_name=mesh_path.name,
                stage="happy_method",
                triggered=triggered,
                trigger_reasons=trigger_reasons,
                centers=final_centers,
                result=final_result,
                tomo_best=tomo_best,
                bbox_volume=bbox_volume,
                full_grid_cells=int(vss_grid.size),
                window_degrees=window_degrees,
            )
        )

    rows.append(
        _row_from_result(
            mesh_name=mesh_path.name,
            stage="adaptive_final",
            triggered=triggered,
            trigger_reasons=trigger_reasons,
            centers=final_centers,
            result=final_result,
            tomo_best=tomo_best,
            bbox_volume=bbox_volume,
            full_grid_cells=int(vss_grid.size),
            window_degrees=window_degrees,
        )
    )

    detail = {
        "mesh": mesh_path.name,
        "npz": str(grid_path.relative_to(PROJECT_ROOT)),
        "face_count": int(len(mesh.faces)),
        "candidate_pool_size": int(len(pool)),
        "elapsed_sec": elapsed,
        "bbox_volume": bbox_volume,
        "tomo_best": tomo_best,
        "triggered": triggered,
        "severe_boundary": severe_boundary,
        "trigger_reasons": trigger_reasons,
        "base_top_k": base_top_k,
        "escalate_top_k": escalate_top_k,
        "severe_escalate_top_k": severe_escalate_top_k,
        "pareto_top_k": pareto_top_k,
        "baseline_centers": baseline_centers[: max(escalate_top_k, severe_escalate_top_k)],
        "pareto_centers": pareto_centers,
    }
    return rows, detail


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    stages = sorted({str(row["stage"]) for row in rows})
    summary: list[dict[str, object]] = []
    for stage in stages:
        stage_rows = [row for row in rows if row["stage"] == stage]
        ratios = np.asarray([float(row["local_best_ratio"]) for row in stage_rows], dtype=np.float64)
        budgets = np.asarray([float(row["local_budget_fraction"]) for row in stage_rows], dtype=np.float64)
        cells = np.asarray([float(row["local_cell_count"]) for row in stage_rows], dtype=np.float64)
        summary.append(
            {
                "stage": stage,
                "mesh_count": int(len(stage_rows)),
                "triggered_count": int(sum(bool(row["triggered"]) for row in stage_rows)),
                "mean_local_ratio": float(np.mean(ratios)),
                "median_local_ratio": float(np.median(ratios)),
                "max_local_ratio": float(np.max(ratios)),
                "mean_local_cell_count": float(np.mean(cells)),
                "mean_local_budget_fraction": float(np.mean(budgets)),
                "count_ratio_le_1_25": int(np.sum(ratios <= 1.25)),
                "count_ratio_le_1_50": int(np.sum(ratios <= 1.50)),
                "count_ratio_le_2_00": int(np.sum(ratios <= 2.00)),
            }
        )
    return summary


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _parse_mesh_filters(filters: list[str], grid_paths: list[Path]) -> list[Path]:
    for needle in filters:
        grid_paths = [path for path in grid_paths if needle.lower() in path.name.lower()]
    return grid_paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-top-k", type=int, default=DEFAULT_BASE_TOP_K)
    parser.add_argument("--escalate-top-k", type=int, default=DEFAULT_ESCALATE_TOP_K)
    parser.add_argument("--severe-escalate-top-k", type=int, default=DEFAULT_SEVERE_ESCALATE_TOP_K)
    parser.add_argument("--pareto-top-k", type=int, default=DEFAULT_PARETO_TOP_K)
    parser.add_argument("--window-degrees", type=float, default=DEFAULT_WINDOW_DEGREES)
    parser.add_argument("--min-angle-degrees", type=float, default=DEFAULT_MIN_ANGLE_DEGREES)
    parser.add_argument("--high-support-fraction", type=float, default=DEFAULT_HIGH_SUPPORT_FRACTION)
    parser.add_argument("--edge-margin-degrees", type=float, default=DEFAULT_EDGE_MARGIN_DEGREES)
    parser.add_argument("--low-gain", type=float, default=DEFAULT_LOW_GAIN)
    parser.add_argument("--boundary-gain", type=float, default=DEFAULT_BOUNDARY_GAIN)
    parser.add_argument("--mesh-contains", action="append", default=[])
    parser.add_argument("--output-stem", default="sftf_happy_method_adaptive")
    args = parser.parse_args()

    if (
        args.base_top_k <= 0
        or args.escalate_top_k < args.base_top_k
        or args.severe_escalate_top_k < args.escalate_top_k
        or args.pareto_top_k < 0
    ):
        raise ValueError("expected 0 < base_top_k <= escalate_top_k <= severe_escalate_top_k and pareto_top_k >= 0")

    grid_paths = _parse_mesh_filters(args.mesh_contains, sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}")))
    if not grid_paths:
        raise FileNotFoundError(f"no saved TOMO grids found in {MESH_DIR}")

    rows: list[dict[str, object]] = []
    details: list[dict[str, object]] = []
    print(
        "happy-method adaptive verification: "
        f"base K={args.base_top_k}, escalation K={args.escalate_top_k}+Pareto{args.pareto_top_k}, "
        f"severe K={args.severe_escalate_top_k}, "
        f"window=+/-{args.window_degrees:g} deg",
        flush=True,
    )
    for index, grid_path in enumerate(grid_paths, start=1):
        print(f"[{index}/{len(grid_paths)}] {grid_path.name}", flush=True)
        mesh_rows, detail = analyze_grid(
            grid_path,
            base_top_k=args.base_top_k,
            escalate_top_k=args.escalate_top_k,
            severe_escalate_top_k=args.severe_escalate_top_k,
            pareto_top_k=args.pareto_top_k,
            window_degrees=args.window_degrees,
            min_angle_degrees=args.min_angle_degrees,
            high_support_fraction=args.high_support_fraction,
            edge_margin_degrees=args.edge_margin_degrees,
            low_gain=args.low_gain,
            boundary_gain=args.boundary_gain,
        )
        rows.extend(mesh_rows)
        details.append(detail)
        final = [row for row in mesh_rows if row["stage"] == "adaptive_final"][0]
        base = [row for row in mesh_rows if row["stage"] == "base_top_k"][0]
        print(
            f"  base={float(base['local_best_ratio']):.3f} "
            f"trigger={bool(base['triggered'])} final={float(final['local_best_ratio']):.3f} "
            f"budget={100.0 * float(final['local_budget_fraction']):.2f}%",
            flush=True,
        )

    summary = summarize(rows)
    csv_path = MESH_DIR / f"{args.output_stem}.csv"
    summary_path = MESH_DIR / f"{args.output_stem}_summary.csv"
    json_path = MESH_DIR / f"{args.output_stem}.json"
    _write_csv(csv_path, rows)
    _write_csv(summary_path, summary)
    json_path.write_text(
        json.dumps(
            {
                "config": {
                    "base_top_k": args.base_top_k,
                    "escalate_top_k": args.escalate_top_k,
                    "severe_escalate_top_k": args.severe_escalate_top_k,
                    "pareto_top_k": args.pareto_top_k,
                    "window_degrees": args.window_degrees,
                    "min_angle_degrees": args.min_angle_degrees,
                    "high_support_fraction": args.high_support_fraction,
                    "edge_margin_degrees": args.edge_margin_degrees,
                    "low_gain": args.low_gain,
                    "boundary_gain": args.boundary_gain,
                    "grid_suffix": GRID_SUFFIX,
                },
                "summary": summary,
                "rows": rows,
                "details": details,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\n=== summary ===")
    for row in summary:
        print(
            f"{row['stage']:<16} mean={row['mean_local_ratio']:.3f} "
            f"median={row['median_local_ratio']:.3f} max={row['max_local_ratio']:.3f} "
            f"budget={100.0 * row['mean_local_budget_fraction']:.2f}% "
            f"<=2.0={row['count_ratio_le_2_00']}/{row['mesh_count']}",
            flush=True,
        )
    print(
        "\nsaved: "
        + ", ".join(str(path.relative_to(PROJECT_ROOT)) for path in (csv_path, summary_path, json_path)),
        flush=True,
    )


if __name__ == "__main__":
    main()
