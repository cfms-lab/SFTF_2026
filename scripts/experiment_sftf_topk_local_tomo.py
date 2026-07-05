"""Local TOMO verification around the top-K SFTF candidates.

This experiment asks whether SFTF already places good directions close enough
to its top-ranked candidates that a small local TOMO search can recover them.

By default it reuses the saved 1 degree TOMO_CPU grids in Experimental/etc.
That makes this a deterministic, no-DLL proxy for the proposed verification
stage: the local search reads TOMO values that were already computed
exhaustively and only restricts which yaw/pitch cells are allowed.
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
from scripts.regenerate_sftf_vs_saved_tomo_summary import (  # noqa: E402
    GRID_SUFFIX,
    MESH_DIR,
    _signed_orientation,
    _tomo_best,
)
from scripts._mesh_paths import G5_RAW_MESH

DEFAULT_TOP_K_LIST = (3, 5, 10, 20)
DEFAULT_WINDOW_DEGREES = 10.0
DEFAULT_MIN_ANGLE_DEGREES = 3.0


def _ratio(value: float, reference: float) -> float:
    return value / reference if abs(reference) > 1e-12 else float("inf")


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


def _parse_top_k_list(value: str) -> list[int]:
    parsed = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not parsed or any(item <= 0 for item in parsed):
        raise argparse.ArgumentTypeError("top-K list must contain positive integers")
    return sorted(set(parsed))


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
        yaw_ids = _grid_indices_within(yaw_values, float(center["signed_yaw"]), radius_degrees)
        pitch_ids = _grid_indices_within(pitch_values, float(center["signed_pitch"]), radius_degrees)
        for pitch_id in pitch_ids:
            for yaw_id in yaw_ids:
                cells.add((int(pitch_id), int(yaw_id)))

    if not cells:
        return {
            "yaw": float("nan"),
            "pitch": float("nan"),
            "vss": float("inf"),
            "cell_count": 0,
        }

    best_pitch_id, best_yaw_id = min(cells, key=lambda idx: float(vss_grid[idx[0], idx[1]]))
    return {
        "yaw": float(yaw_values[best_yaw_id]),
        "pitch": float(pitch_values[best_pitch_id]),
        "vss": float(vss_grid[best_pitch_id, best_yaw_id]),
        "cell_count": len(cells),
    }


def _candidate_rows(
    pool,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
    *,
    top_k: int,
    min_angle_degrees: float,
) -> list[dict[str, object]]:
    directions = support_flow_directions_from_candidate_pool(
        pool,
        limit=top_k,
        min_angle_degrees=min_angle_degrees,
    )
    rows = []
    for item in directions:
        _positive, signed = _signed_orientation(item.direction, yaw_values, pitch_values, vss_grid)
        rows.append(
            {
                "rank": int(item.rank),
                "score": float(item.value),
                "direction": np.asarray(item.direction, dtype=np.float64).tolist(),
                "signed_yaw": float(signed["yaw"]),
                "signed_pitch": float(signed["pitch"]),
                "signed_alignment": float(signed["alignment"]),
                "signed_vss": float(signed["vss"]),
                "hit_count": int(item.hit_count),
                "rayleigh_score": float(item.rayleigh_score),
                "pair_score": float(item.pair_score),
                "bed_score": float(item.bed_score),
            }
        )
    return rows


def _pool_oracle_ratio(pool, yaw_values: np.ndarray, pitch_values: np.ndarray, vss_grid: np.ndarray, tomo_best_vss: float) -> float:
    values = [
        _signed_orientation(result[5], yaw_values, pitch_values, vss_grid)[1]["vss"]
        for result in pool
    ]
    return _ratio(float(np.min(values)), tomo_best_vss) if values else float("inf")


def analyze_grid(
    grid_path: Path,
    *,
    top_k_list: list[int],
    window_degrees: float,
    min_angle_degrees: float,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    mesh_path = _mesh_path_for_grid(grid_path)
    data = np.load(grid_path, allow_pickle=True)
    yaw_values = np.asarray(data["yaw_values"], dtype=np.float64)
    pitch_values = np.asarray(data["pitch_values"], dtype=np.float64)
    vss_grid = np.asarray(data["vss_grid"], dtype=np.float64)
    tomo_best = _tomo_best(yaw_values, pitch_values, vss_grid)

    start = time.perf_counter()
    mesh = load_mesh(str(mesh_path))
    pool = evaluate_support_flow_candidate_pool(mesh)
    elapsed = time.perf_counter() - start

    oracle_ratio = _pool_oracle_ratio(pool, yaw_values, pitch_values, vss_grid, float(tomo_best["vss"]))
    max_k = max(top_k_list)
    all_top_rows = _candidate_rows(
        pool,
        yaw_values,
        pitch_values,
        vss_grid,
        top_k=max_k,
        min_angle_degrees=min_angle_degrees,
    )

    rows = []
    detail = {
        "mesh": mesh_path.name,
        "npz": str(grid_path.relative_to(PROJECT_ROOT)),
        "face_count": int(len(mesh.faces)),
        "candidate_pool_size": int(len(pool)),
        "elapsed_sec": elapsed,
        "tomo_best": tomo_best,
        "pool_oracle_ratio": oracle_ratio,
        "top_candidates": all_top_rows,
        "local_results": [],
    }

    for top_k in top_k_list:
        top_rows = all_top_rows[:top_k]
        seed_best = min(top_rows, key=lambda item: float(item["signed_vss"])) if top_rows else None
        local_best = _local_window_best(
            top_rows,
            yaw_values,
            pitch_values,
            vss_grid,
            radius_degrees=window_degrees,
        )
        row = {
            "mesh": mesh_path.name,
            "top_k": int(top_k),
            "window_degrees": float(window_degrees),
            "face_count": int(len(mesh.faces)),
            "candidate_pool_size": int(len(pool)),
            "tomo_best_yaw": float(tomo_best["yaw"]),
            "tomo_best_pitch": float(tomo_best["pitch"]),
            "tomo_best_vss": float(tomo_best["vss"]),
            "pool_oracle_ratio": float(oracle_ratio),
            "seed_best_rank": int(seed_best["rank"]) if seed_best else None,
            "seed_best_yaw": float(seed_best["signed_yaw"]) if seed_best else float("nan"),
            "seed_best_pitch": float(seed_best["signed_pitch"]) if seed_best else float("nan"),
            "seed_best_vss": float(seed_best["signed_vss"]) if seed_best else float("inf"),
            "seed_best_ratio": _ratio(float(seed_best["signed_vss"]), float(tomo_best["vss"])) if seed_best else float("inf"),
            "local_cell_count": int(local_best["cell_count"]),
            "local_best_yaw": float(local_best["yaw"]),
            "local_best_pitch": float(local_best["pitch"]),
            "local_best_vss": float(local_best["vss"]),
            "local_best_ratio": _ratio(float(local_best["vss"]), float(tomo_best["vss"])),
            "elapsed_sec": elapsed,
        }
        rows.append(row)
        detail["local_results"].append(row)

    return rows, detail


def _mean_ratio(rows: list[dict[str, object]], top_k: int, *, exclude_happy: bool = False) -> float:
    values = [
        float(row["local_best_ratio"])
        for row in rows
        if int(row["top_k"]) == top_k and (not exclude_happy or "happy" not in str(row["mesh"]).lower())
    ]
    return float(np.mean(values)) if values else float("nan")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-k-list", type=_parse_top_k_list, default=list(DEFAULT_TOP_K_LIST))
    parser.add_argument("--window-degrees", type=float, default=DEFAULT_WINDOW_DEGREES)
    parser.add_argument("--min-angle-degrees", type=float, default=DEFAULT_MIN_ANGLE_DEGREES)
    parser.add_argument("--mesh-contains", action="append", default=[], help="Only run grids whose filename contains this substring.")
    parser.add_argument(
        "--output-stem",
        default="sftf_topk_local_tomo_verification",
        help="Output basename under Experimental/etc.",
    )
    args = parser.parse_args()

    grid_paths = sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}"))
    for needle in args.mesh_contains:
        grid_paths = [path for path in grid_paths if needle.lower() in path.name.lower()]
    if not grid_paths:
        raise FileNotFoundError(f"no saved TOMO grids found under {MESH_DIR}")

    print(
        f"local TOMO proxy: top-K={args.top_k_list}, window=+/-{args.window_degrees:g} deg, "
        f"min_angle={args.min_angle_degrees:g} deg",
        flush=True,
    )
    rows: list[dict[str, object]] = []
    details: list[dict[str, object]] = []
    for index, grid_path in enumerate(grid_paths, start=1):
        print(f"[{index}/{len(grid_paths)}] {grid_path.name}", flush=True)
        grid_rows, detail = analyze_grid(
            grid_path,
            top_k_list=args.top_k_list,
            window_degrees=args.window_degrees,
            min_angle_degrees=args.min_angle_degrees,
        )
        rows.extend(grid_rows)
        details.append(detail)
        last = {int(row["top_k"]): row for row in grid_rows}
        print(
            "  "
            + " ".join(
                f"K={k}: seed {last[k]['seed_best_ratio']:.2f} -> local {last[k]['local_best_ratio']:.2f}"
                for k in args.top_k_list
            )
            + f"  oracle={detail['pool_oracle_ratio']:.2f}  ({detail['elapsed_sec']:.2f}s)",
            flush=True,
        )

    csv_path = MESH_DIR / f"{args.output_stem}.csv"
    json_path = MESH_DIR / f"{args.output_stem}.json"
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "config": {
            "top_k_list": args.top_k_list,
            "window_degrees": args.window_degrees,
            "min_angle_degrees": args.min_angle_degrees,
            "grid_suffix": GRID_SUFFIX,
            "mode": "saved_grid_local_window",
        },
        "mean_local_ratio_by_top_k": {str(k): _mean_ratio(rows, k) for k in args.top_k_list},
        "mean_local_ratio_without_happy_by_top_k": {
            str(k): _mean_ratio(rows, k, exclude_happy=True) for k in args.top_k_list
        },
        "rows": rows,
        "details": details,
    }
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== mean local best ratio ===")
    for top_k in args.top_k_list:
        print(
            f"K={top_k:<3} all={_mean_ratio(rows, top_k):.2f}  "
            f"without happy={_mean_ratio(rows, top_k, exclude_happy=True):.2f}",
            flush=True,
        )
    print(f"\nsaved: {csv_path.relative_to(PROJECT_ROOT)}, {json_path.relative_to(PROJECT_ROOT)}", flush=True)


if __name__ == "__main__":
    main()
