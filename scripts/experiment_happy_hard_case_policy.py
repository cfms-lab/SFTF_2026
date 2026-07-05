"""Separate happy-like candidate-generation failures from ordinary ranking.

This script sweeps SFTF coarse sampling density and evaluates three quantities
against the saved 1 degree TOMO_CPU grids:

* seed best-of-K ratio: best TOMO value among the SFTF top-K candidate centers.
* pool oracle ratio: best TOMO value at any candidate center in the pool.
* local top-K ratio: best TOMO value inside +/- window around the SFTF top-K.

The goal is to treat happy-like failures as a distinct search-policy issue:
if top-3/local verification still misses the narrow basin, widen K or increase
the coarse sampling density instead of blaming the rank-tuning model alone.
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

import python_src.SupportFlowTensorField.support_flow_tensor_field as sftf  # noqa: E402
from scripts.regenerate_sftf_vs_saved_tomo_summary import (  # noqa: E402
    GRID_SUFFIX,
    MESH_DIR,
    _signed_orientation,
    _tomo_best,
)
from scripts._mesh_paths import G5_RAW_MESH

DEFAULT_COARSE_COUNTS = (512, 1024, 2048, 4096)
DEFAULT_TOP_K_LIST = (3, 10, 20)
DEFAULT_WINDOW_DEGREES = 10.0
DEFAULT_HARD_RATIO = 2.0


def _parse_int_list(value: str) -> list[int]:
    out = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not out or any(item <= 0 for item in out):
        raise argparse.ArgumentTypeError("expected a comma-separated list of positive integers")
    return sorted(set(out))


def _ratio(value: float, reference: float) -> float:
    return value / reference if reference > 1e-12 else float("inf")


def _angle_delta_degrees(values: np.ndarray, center: float) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    return np.abs((values - float(center) + 180.0) % 360.0 - 180.0)


def _grid_indices_within(values: np.ndarray, center: float, radius_degrees: float) -> np.ndarray:
    return np.flatnonzero(_angle_delta_degrees(values, center) <= float(radius_degrees) + 1e-9)


def _mesh_path_for_grid(grid_path: Path) -> Path:
    stem = grid_path.name[: -len(GRID_SUFFIX)]
    local_mesh_path = grid_path.with_name(stem + ".ply")
    candidates = [local_mesh_path]
    if stem.startswith("(") and ")" in stem:
        mesh_id, plain = stem[1:].split(")", 1)
        candidates.append(G5_RAW_MESH / f"Group_C{mesh_id}_{plain}.ply")
    for mesh_path in candidates:
        if mesh_path.exists():
            return mesh_path
        for suffix in (".obj", ".stl"):
            candidate = mesh_path.with_suffix(suffix)
            if candidate.exists():
                return candidate
    raise FileNotFoundError(f"could not find mesh for {grid_path.name}")


def _local_window_best(
    centers: list[dict[str, float]],
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
    *,
    radius_degrees: float,
) -> dict[str, float | int]:
    cells: set[tuple[int, int]] = set()
    for center in centers:
        yaw_ids = _grid_indices_within(yaw_values, center["yaw"], radius_degrees)
        pitch_ids = _grid_indices_within(pitch_values, center["pitch"], radius_degrees)
        for pitch_id in pitch_ids:
            for yaw_id in yaw_ids:
                cells.add((int(pitch_id), int(yaw_id)))

    if not cells:
        return {"yaw": float("nan"), "pitch": float("nan"), "vss": float("inf"), "cell_count": 0}

    best_pitch_id, best_yaw_id = min(cells, key=lambda item: float(vss_grid[item[0], item[1]]))
    return {
        "yaw": float(yaw_values[best_yaw_id]),
        "pitch": float(pitch_values[best_pitch_id]),
        "vss": float(vss_grid[best_pitch_id, best_yaw_id]),
        "cell_count": len(cells),
    }


def _ranked_centers(
    pool,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
    *,
    top_k: int,
    min_angle_degrees: float,
) -> list[dict[str, float]]:
    ranked = sftf.support_flow_directions_from_candidate_pool(
        pool,
        limit=top_k,
        min_angle_degrees=min_angle_degrees,
    )
    centers = []
    for item in ranked:
        _positive, signed = _signed_orientation(item.direction, yaw_values, pitch_values, vss_grid)
        centers.append(
            {
                "rank": float(item.rank),
                "score": float(item.value),
                "yaw": float(signed["yaw"]),
                "pitch": float(signed["pitch"]),
                "vss": float(signed["vss"]),
                "alignment": float(signed["alignment"]),
            }
        )
    return centers


def analyze_mesh(
    grid_path: Path,
    *,
    coarse_counts: list[int],
    top_k_list: list[int],
    window_degrees: float,
    min_angle_degrees: float,
    hard_ratio: float,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    data = np.load(grid_path, allow_pickle=True)
    yaw_values = np.asarray(data["yaw_values"], dtype=np.float64)
    pitch_values = np.asarray(data["pitch_values"], dtype=np.float64)
    vss_grid = np.asarray(data["vss_grid"], dtype=np.float64)
    tomo_best = _tomo_best(yaw_values, pitch_values, vss_grid)
    mesh_path = _mesh_path_for_grid(grid_path)
    mesh = sftf.load_mesh(str(mesh_path))

    rows: list[dict[str, object]] = []
    detail: dict[str, object] = {
        "mesh": mesh_path.name,
        "npz": str(grid_path.relative_to(PROJECT_ROOT)),
        "tomo_best": tomo_best,
        "coarse_results": [],
    }
    for coarse_count in coarse_counts:
        start = time.perf_counter()
        sftf.SUPPORT_FLOW_COARSE_DIRECTION_COUNT = int(coarse_count)
        pool = sftf.evaluate_support_flow_candidate_pool(mesh)
        elapsed = time.perf_counter() - start

        signed_values = np.asarray(
            [_signed_orientation(result[5], yaw_values, pitch_values, vss_grid)[1]["vss"] for result in pool],
            dtype=np.float64,
        )
        pool_oracle_vss = float(np.nanmin(signed_values)) if signed_values.size else float("inf")
        pool_oracle_ratio = _ratio(pool_oracle_vss, float(tomo_best["vss"]))
        coarse_detail = {
            "coarse_count": int(coarse_count),
            "candidate_pool_size": int(len(pool)),
            "elapsed_sec": elapsed,
            "pool_oracle_vss": pool_oracle_vss,
            "pool_oracle_ratio": pool_oracle_ratio,
            "top_k_results": [],
        }
        detail["coarse_results"].append(coarse_detail)

        max_top_k = max(top_k_list)
        centers = _ranked_centers(
            pool,
            yaw_values,
            pitch_values,
            vss_grid,
            top_k=max_top_k,
            min_angle_degrees=min_angle_degrees,
        )
        for top_k in top_k_list:
            selected = centers[:top_k]
            seed_best = min(selected, key=lambda item: item["vss"]) if selected else None
            local_best = _local_window_best(
                selected,
                yaw_values,
                pitch_values,
                vss_grid,
                radius_degrees=window_degrees,
            )
            row = {
                "mesh": mesh_path.name,
                "coarse_count": int(coarse_count),
                "top_k": int(top_k),
                "window_degrees": float(window_degrees),
                "candidate_pool_size": int(len(pool)),
                "elapsed_sec": elapsed,
                "tomo_best_yaw": float(tomo_best["yaw"]),
                "tomo_best_pitch": float(tomo_best["pitch"]),
                "tomo_best_vss": float(tomo_best["vss"]),
                "pool_oracle_vss": pool_oracle_vss,
                "pool_oracle_ratio": pool_oracle_ratio,
                "pool_hard_case": bool(pool_oracle_ratio > hard_ratio),
                "seed_best_rank": int(seed_best["rank"]) if seed_best else None,
                "seed_best_yaw": float(seed_best["yaw"]) if seed_best else float("nan"),
                "seed_best_pitch": float(seed_best["pitch"]) if seed_best else float("nan"),
                "seed_best_vss": float(seed_best["vss"]) if seed_best else float("inf"),
                "seed_best_ratio": _ratio(float(seed_best["vss"]), float(tomo_best["vss"])) if seed_best else float("inf"),
                "local_cell_count": int(local_best["cell_count"]),
                "local_best_yaw": float(local_best["yaw"]),
                "local_best_pitch": float(local_best["pitch"]),
                "local_best_vss": float(local_best["vss"]),
                "local_best_ratio": _ratio(float(local_best["vss"]), float(tomo_best["vss"])),
                "local_hard_case": bool(_ratio(float(local_best["vss"]), float(tomo_best["vss"])) > hard_ratio),
            }
            rows.append(row)
            coarse_detail["top_k_results"].append(row)

    return rows, detail


def _policy_rows(rows: list[dict[str, object]], *, hard_ratio: float) -> list[dict[str, object]]:
    policies = []
    meshes = sorted({str(row["mesh"]) for row in rows})
    for mesh in meshes:
        mesh_rows = [row for row in rows if row["mesh"] == mesh]
        candidate = min(
            (row for row in mesh_rows if float(row["local_best_ratio"]) <= hard_ratio),
            key=lambda row: (int(row["coarse_count"]), int(row["top_k"])),
            default=None,
        )
        if candidate is None:
            candidate = min(mesh_rows, key=lambda row: float(row["local_best_ratio"]))
            status = "unresolved"
        else:
            status = "resolved"
        policies.append(
            {
                "mesh": mesh,
                "status": status,
                "coarse_count": int(candidate["coarse_count"]),
                "top_k": int(candidate["top_k"]),
                "local_best_ratio": float(candidate["local_best_ratio"]),
                "pool_oracle_ratio": float(candidate["pool_oracle_ratio"]),
                "local_cell_count": int(candidate["local_cell_count"]),
            }
        )
    return policies


def _parse_mesh_filters(filters: list[str], grid_paths: list[Path]) -> list[Path]:
    for needle in filters:
        grid_paths = [path for path in grid_paths if needle.lower() in path.name.lower()]
    return grid_paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coarse-counts", type=_parse_int_list, default=list(DEFAULT_COARSE_COUNTS))
    parser.add_argument("--top-k-list", type=_parse_int_list, default=list(DEFAULT_TOP_K_LIST))
    parser.add_argument("--window-degrees", type=float, default=DEFAULT_WINDOW_DEGREES)
    parser.add_argument("--min-angle-degrees", type=float, default=3.0)
    parser.add_argument("--hard-ratio", type=float, default=DEFAULT_HARD_RATIO)
    parser.add_argument("--mesh-contains", action="append", default=[])
    parser.add_argument("--output-stem", default="sftf_happy_hard_case_policy")
    args = parser.parse_args()

    grid_paths = _parse_mesh_filters(
        args.mesh_contains,
        sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}")),
    )
    if not grid_paths:
        raise FileNotFoundError(f"no saved TOMO grids found in {MESH_DIR}")

    default_coarse = sftf.SUPPORT_FLOW_COARSE_DIRECTION_COUNT
    rows: list[dict[str, object]] = []
    details: list[dict[str, object]] = []
    try:
        print(
            f"hard-case sweep: coarse={args.coarse_counts}, topK={args.top_k_list}, "
            f"window=+/-{args.window_degrees:g} deg, hard_ratio>{args.hard_ratio:g}",
            flush=True,
        )
        for index, grid_path in enumerate(grid_paths, start=1):
            print(f"[{index}/{len(grid_paths)}] {grid_path.name}", flush=True)
            mesh_rows, detail = analyze_mesh(
                grid_path,
                coarse_counts=args.coarse_counts,
                top_k_list=args.top_k_list,
                window_degrees=args.window_degrees,
                min_angle_degrees=args.min_angle_degrees,
                hard_ratio=args.hard_ratio,
            )
            rows.extend(mesh_rows)
            details.append(detail)
            happy_line = " ".join(
                f"{int(row['coarse_count'])}/K{int(row['top_k'])}:{float(row['local_best_ratio']):.2f}"
                for row in mesh_rows
                if int(row["top_k"]) == max(args.top_k_list)
            )
            print(f"  {happy_line}", flush=True)
    finally:
        sftf.SUPPORT_FLOW_COARSE_DIRECTION_COUNT = default_coarse

    policy = _policy_rows(rows, hard_ratio=args.hard_ratio)
    csv_path = MESH_DIR / f"{args.output_stem}.csv"
    json_path = MESH_DIR / f"{args.output_stem}.json"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    result = {
        "config": {
            "coarse_counts": args.coarse_counts,
            "top_k_list": args.top_k_list,
            "window_degrees": args.window_degrees,
            "min_angle_degrees": args.min_angle_degrees,
            "hard_ratio": args.hard_ratio,
            "grid_suffix": GRID_SUFFIX,
        },
        "policy": policy,
        "rows": rows,
        "details": details,
    }
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== first policy step with local ratio below threshold ===")
    for item in policy:
        print(
            f"{item['mesh']:<34} {item['status']:<10} "
            f"coarse={item['coarse_count']:<4} K={item['top_k']:<3} "
            f"local={item['local_best_ratio']:.2f} pool={item['pool_oracle_ratio']:.2f}",
            flush=True,
        )
    print(f"\nsaved: {csv_path.relative_to(PROJECT_ROOT)}, {json_path.relative_to(PROJECT_ROOT)}", flush=True)


if __name__ == "__main__":
    main()
