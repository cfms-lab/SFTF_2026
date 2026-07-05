"""Budget-matched local TOMO baselines for SFTF warm-start verification.

This experiment answers a reviewer-style control question: if SFTF top-K local
verification spends only a few percent of the TOMO grid, would a non-adaptive
uniform or random set of local windows do just as well?

The script uses the saved 1 degree TOMO_CPU grids and the already generated
SFTF budget-curve CSV.  For each mesh, the SFTF top-K unique grid-cell count is
used as the hard budget cap.  Uniform/random baselines may add +/- window
verification windows only while staying within that same per-mesh cap.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    SUPPORT_FLOW_COARSE_DIRECTION_COUNT,
    _spherical_sample_directions,
)
from scripts.experiment_sftf_budget_curve import (  # noqa: E402
    _mesh_path_for_grid,
    _ratio,
    _window_cells,
)
from scripts.regenerate_sftf_vs_saved_tomo_summary import (  # noqa: E402
    GRID_SUFFIX,
    MESH_DIR,
    _signed_orientation,
    _tomo_best,
)


DEFAULT_SFTF_BUDGET_CSV = MESH_DIR / "sftf_budget_curve_topk_local_tomo.csv"
DEFAULT_OUTPUT_STEM = "sftf_budget_matched_local_baselines"
DEFAULT_TOP_K = 20
DEFAULT_WINDOW_DEGREES = 10.0
DEFAULT_RANDOM_TRIALS = 500
DEFAULT_RANDOM_SEED = 20260625


def _read_sftf_caps(path: Path, *, top_k: int) -> dict[str, dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(f"missing SFTF budget curve CSV: {path}")
    caps: dict[str, dict[str, object]] = {}
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if int(row["top_k"]) != int(top_k):
                continue
            mesh = str(row["mesh"])
            caps[mesh] = {
                "mesh": mesh,
                "local_cell_count": int(float(row["local_cell_count"])),
                "local_budget_fraction": float(row["local_budget_fraction"]),
                "local_best_yaw": float(row["local_best_yaw"]),
                "local_best_pitch": float(row["local_best_pitch"]),
                "local_best_vss": float(row["local_best_vss"]),
                "local_best_ratio": float(row["local_best_ratio"]),
                "full_grid_cells": int(float(row["full_grid_cells"])),
            }
    if not caps:
        raise ValueError(f"no top_k={top_k} rows found in {path}")
    return caps


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _axis_key(direction: np.ndarray) -> tuple[float, float, float]:
    unit = np.asarray(direction, dtype=np.float64)
    unit = unit / max(float(np.linalg.norm(unit)), 1e-12)
    dominant = int(np.argmax(np.abs(unit)))
    if unit[dominant] < 0.0:
        unit = -unit
    return tuple(np.round(unit, 12).tolist())


def _unique_axis_directions(directions: np.ndarray) -> np.ndarray:
    seen: set[tuple[float, float, float]] = set()
    unique: list[np.ndarray] = []
    for direction in np.asarray(directions, dtype=np.float64):
        key = _axis_key(direction)
        if key in seen:
            continue
        seen.add(key)
        unique.append(direction / max(float(np.linalg.norm(direction)), 1e-12))
    return np.asarray(unique, dtype=np.float64)


def _farthest_axis_order(directions: np.ndarray) -> list[int]:
    """Purely geometric progressive order for a quasi-uniform axis set."""
    dirs = np.asarray(directions, dtype=np.float64)
    if len(dirs) == 0:
        return []

    order = [int(np.argmax(dirs[:, 2]))]
    selected = np.zeros(len(dirs), dtype=bool)
    selected[order[0]] = True
    # Axis distance treats n and -n as equivalent, matching signed build axes.
    nearest_similarity = np.abs(dirs @ dirs[order[0]])
    while len(order) < len(dirs):
        scores = np.where(selected, np.inf, nearest_similarity)
        next_id = int(np.argmin(scores))
        order.append(next_id)
        selected[next_id] = True
        nearest_similarity = np.maximum(nearest_similarity, np.abs(dirs @ dirs[next_id]))
    return order


def _centers_from_directions(
    directions: np.ndarray,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
) -> list[dict[str, float]]:
    centers: list[dict[str, float]] = []
    for direction in directions:
        _positive, signed = _signed_orientation(direction, yaw_values, pitch_values, vss_grid)
        centers.append(
            {
                "yaw": float(signed["yaw"]),
                "pitch": float(signed["pitch"]),
                "vss": float(signed["vss"]),
                "alignment": float(signed["alignment"]),
            }
        )
    return centers


def _precompute_windows(
    centers: list[dict[str, float]],
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    *,
    radius_degrees: float,
    yaw_count: int,
) -> list[np.ndarray]:
    windows: list[np.ndarray] = []
    for center in centers:
        cells = _window_cells(
            yaw_values,
            pitch_values,
            yaw=float(center["yaw"]),
            pitch=float(center["pitch"]),
            radius_degrees=radius_degrees,
        )
        flat = np.asarray([pitch_id * yaw_count + yaw_id for pitch_id, yaw_id in cells], dtype=np.int64)
        windows.append(np.unique(flat))
    return windows


def _evaluate_window_order(
    *,
    policy: str,
    mesh: str,
    trial: int,
    order: Iterable[int],
    centers: list[dict[str, float]],
    windows: list[np.ndarray],
    vss_flat: np.ndarray,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    tomo_best_vss: float,
    full_grid_cells: int,
    budget_cap_cells: int,
) -> dict[str, object]:
    visited = np.zeros(full_grid_cells, dtype=bool)
    best_vss = float("inf")
    best_flat = -1
    selected_windows = 0

    for center_id in order:
        window = windows[int(center_id)]
        if window.size == 0:
            continue
        new_cells = window[~visited[window]]
        if new_cells.size == 0:
            continue
        if int(np.count_nonzero(visited)) + int(new_cells.size) > int(budget_cap_cells):
            continue

        visited[new_cells] = True
        selected_windows += 1
        local_values = vss_flat[new_cells]
        local_best_id = int(np.nanargmin(local_values))
        local_best_vss = float(local_values[local_best_id])
        if local_best_vss < best_vss:
            best_vss = local_best_vss
            best_flat = int(new_cells[local_best_id])

        if int(np.count_nonzero(visited)) >= int(budget_cap_cells):
            break

    used_cells = int(np.count_nonzero(visited))
    if best_flat >= 0:
        pitch_id, yaw_id = divmod(best_flat, len(yaw_values))
        best_yaw = float(yaw_values[yaw_id])
        best_pitch = float(pitch_values[pitch_id])
    else:
        best_yaw = float("nan")
        best_pitch = float("nan")

    first_center = centers[int(next(iter(order), 0))] if centers else {"yaw": float("nan"), "pitch": float("nan")}
    return {
        "policy": policy,
        "mesh": mesh,
        "trial": int(trial),
        "selected_windows": int(selected_windows),
        "budget_cap_cells": int(budget_cap_cells),
        "local_cell_count": used_cells,
        "local_budget_fraction": used_cells / max(1, int(full_grid_cells)),
        "unused_budget_cells": int(budget_cap_cells) - used_cells,
        "tomo_best_vss": float(tomo_best_vss),
        "local_best_yaw": best_yaw,
        "local_best_pitch": best_pitch,
        "local_best_vss": best_vss,
        "local_best_ratio": _ratio(best_vss, tomo_best_vss),
        "first_seed_yaw": float(first_center["yaw"]),
        "first_seed_pitch": float(first_center["pitch"]),
    }


def _sftf_rows_from_caps(caps: dict[str, dict[str, object]], *, top_k: int) -> list[dict[str, object]]:
    rows = []
    for mesh, cap in sorted(caps.items()):
        rows.append(
            {
                "policy": f"SFTF top-{top_k} local",
                "mesh": mesh,
                "trial": 0,
                "selected_windows": int(top_k),
                "budget_cap_cells": int(cap["local_cell_count"]),
                "local_cell_count": int(cap["local_cell_count"]),
                "local_budget_fraction": float(cap["local_budget_fraction"]),
                "unused_budget_cells": 0,
                "tomo_best_vss": float("nan"),
                "local_best_yaw": float(cap["local_best_yaw"]),
                "local_best_pitch": float(cap["local_best_pitch"]),
                "local_best_vss": float(cap["local_best_vss"]),
                "local_best_ratio": float(cap["local_best_ratio"]),
                "first_seed_yaw": float("nan"),
                "first_seed_pitch": float("nan"),
            }
        )
    return rows


def _stable_mesh_seed(mesh: str) -> int:
    digest = hashlib.sha256(mesh.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _summarize_policy_rows(policy: str, rows: list[dict[str, object]]) -> dict[str, object]:
    ratios = np.asarray([float(row["local_best_ratio"]) for row in rows], dtype=np.float64)
    budgets = np.asarray([float(row["local_budget_fraction"]) for row in rows], dtype=np.float64)
    cells = np.asarray([float(row["local_cell_count"]) for row in rows], dtype=np.float64)
    return {
        "policy": policy,
        "mesh_count": int(len(rows)),
        "mean_local_ratio": float(np.mean(ratios)),
        "median_local_ratio": float(np.median(ratios)),
        "p80_local_ratio": float(np.percentile(ratios, 80)),
        "max_local_ratio": float(np.max(ratios)),
        "mean_local_cell_count": float(np.mean(cells)),
        "mean_local_budget_fraction": float(np.mean(budgets)),
        "median_local_budget_fraction": float(np.median(budgets)),
        "count_ratio_le_1_25": int(np.sum(ratios <= 1.25)),
        "count_ratio_le_1_50": int(np.sum(ratios <= 1.50)),
        "count_ratio_le_2_00": int(np.sum(ratios <= 2.00)),
    }


def _random_mesh_medians(random_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_mesh: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in random_rows:
        by_mesh[str(row["mesh"])].append(row)

    medians: list[dict[str, object]] = []
    for mesh, rows in sorted(by_mesh.items()):
        rows_sorted = sorted(rows, key=lambda row: float(row["local_best_ratio"]))
        median = dict(rows_sorted[len(rows_sorted) // 2])
        ratios = np.asarray([float(row["local_best_ratio"]) for row in rows], dtype=np.float64)
        median["policy"] = "Random matched local (median)"
        median["trial"] = -1
        median["random_p20_ratio"] = float(np.percentile(ratios, 20))
        median["random_p80_ratio"] = float(np.percentile(ratios, 80))
        medians.append(median)
    return medians


def analyze_grid(
    grid_path: Path,
    *,
    cap: dict[str, object],
    directions: np.ndarray,
    uniform_order: list[int],
    random_trials: int,
    random_seed: int,
    window_degrees: float,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    data = np.load(grid_path, allow_pickle=True)
    yaw_values = np.asarray(data["yaw_values"], dtype=np.float64)
    pitch_values = np.asarray(data["pitch_values"], dtype=np.float64)
    vss_grid = np.asarray(data["vss_grid"], dtype=np.float64)
    vss_flat = vss_grid.reshape(-1)
    tomo_best = _tomo_best(yaw_values, pitch_values, vss_grid)
    tomo_best_vss = float(tomo_best["vss"])
    mesh = str(cap["mesh"])
    full_grid_cells = int(vss_grid.size)
    budget_cap_cells = int(cap["local_cell_count"])

    centers = _centers_from_directions(directions, yaw_values, pitch_values, vss_grid)
    windows = _precompute_windows(
        centers,
        yaw_values,
        pitch_values,
        radius_degrees=window_degrees,
        yaw_count=len(yaw_values),
    )

    rows: list[dict[str, object]] = []
    uniform_row = _evaluate_window_order(
        policy="Uniform matched local",
        mesh=mesh,
        trial=0,
        order=uniform_order,
        centers=centers,
        windows=windows,
        vss_flat=vss_flat,
        yaw_values=yaw_values,
        pitch_values=pitch_values,
        tomo_best_vss=tomo_best_vss,
        full_grid_cells=full_grid_cells,
        budget_cap_cells=budget_cap_cells,
    )
    rows.append(uniform_row)

    rng = np.random.default_rng(int(random_seed) + _stable_mesh_seed(mesh))
    random_rows: list[dict[str, object]] = []
    base_order = np.arange(len(directions), dtype=np.int64)
    for trial in range(int(random_trials)):
        order = base_order.copy()
        rng.shuffle(order)
        row = _evaluate_window_order(
            policy="Random matched local",
            mesh=mesh,
            trial=trial,
            order=order.tolist(),
            centers=centers,
            windows=windows,
            vss_flat=vss_flat,
            yaw_values=yaw_values,
            pitch_values=pitch_values,
            tomo_best_vss=tomo_best_vss,
            full_grid_cells=full_grid_cells,
            budget_cap_cells=budget_cap_cells,
        )
        random_rows.append(row)

    rows.extend(random_rows)
    return rows, [uniform_row] + _random_mesh_medians(random_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sftf-budget-csv", type=Path, default=DEFAULT_SFTF_BUDGET_CSV)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--window-degrees", type=float, default=DEFAULT_WINDOW_DEGREES)
    parser.add_argument("--coarse-directions", type=int, default=SUPPORT_FLOW_COARSE_DIRECTION_COUNT)
    parser.add_argument("--random-trials", type=int, default=DEFAULT_RANDOM_TRIALS)
    parser.add_argument("--random-seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--output-stem", default=DEFAULT_OUTPUT_STEM)
    args = parser.parse_args()

    caps = _read_sftf_caps(args.sftf_budget_csv, top_k=args.top_k)
    directions = _unique_axis_directions(_spherical_sample_directions(args.coarse_directions))
    uniform_order = _farthest_axis_order(directions)

    detail_rows: list[dict[str, object]] = []
    sftf_policy = f"SFTF top-{args.top_k} local"
    aggregate_rows = _sftf_rows_from_caps(caps, top_k=args.top_k)

    grid_paths = sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}"))
    for grid_path in grid_paths:
        mesh_path = _mesh_path_for_grid(grid_path)
        mesh = mesh_path.name
        if mesh not in caps:
            continue
        print(f"{mesh}: cap={caps[mesh]['local_cell_count']} cells", flush=True)
        rows, aggregate = analyze_grid(
            grid_path,
            cap=caps[mesh],
            directions=directions,
            uniform_order=uniform_order,
            random_trials=args.random_trials,
            random_seed=args.random_seed,
            window_degrees=args.window_degrees,
        )
        detail_rows.extend(rows)
        aggregate_rows.extend(aggregate)

    if not detail_rows:
        raise RuntimeError("no matching grids were analyzed")

    summary = []
    by_policy: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in aggregate_rows:
        by_policy[str(row["policy"])].append(row)
    for policy in (sftf_policy, "Uniform matched local", "Random matched local (median)"):
        if policy in by_policy:
            summary.append(_summarize_policy_rows(policy, by_policy[policy]))

    csv_path = MESH_DIR / f"{args.output_stem}.csv"
    aggregate_csv_path = MESH_DIR / f"{args.output_stem}_aggregate.csv"
    summary_csv_path = MESH_DIR / f"{args.output_stem}_summary.csv"
    json_path = MESH_DIR / f"{args.output_stem}.json"
    _write_csv(csv_path, detail_rows)
    _write_csv(aggregate_csv_path, aggregate_rows)
    _write_csv(summary_csv_path, summary)
    json_path.write_text(
        json.dumps(
            {
                "config": {
                    "top_k": int(args.top_k),
                    "window_degrees": float(args.window_degrees),
                    "coarse_directions": int(args.coarse_directions),
                    "unique_axis_directions": int(len(directions)),
                    "random_trials": int(args.random_trials),
                    "random_seed": int(args.random_seed),
                    "sftf_budget_csv": str(args.sftf_budget_csv.relative_to(PROJECT_ROOT)),
                    "budget_rule": "per-mesh SFTF top-K unique grid-cell cap",
                },
                "summary": summary,
                "aggregate_rows": aggregate_rows,
                "detail_rows": detail_rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\n=== budget-matched baseline summary ===")
    for row in summary:
        print(
            f"{row['policy']:<30} mean={row['mean_local_ratio']:.3f} "
            f"median={row['median_local_ratio']:.3f} max={row['max_local_ratio']:.3f} "
            f"budget={100.0 * row['mean_local_budget_fraction']:.2f}% "
            f"<=2.0={row['count_ratio_le_2_00']}/{row['mesh_count']}",
            flush=True,
        )
    print(
        "\nsaved: "
        + ", ".join(
            str(path.relative_to(PROJECT_ROOT))
            for path in (csv_path, aggregate_csv_path, summary_csv_path, json_path)
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
