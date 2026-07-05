"""Budget curve for SFTF top-K local TOMO verification.

This experiment turns the earlier best-of-3 result into a curve.  For each
mesh, it evaluates cumulative local TOMO windows around the ranked SFTF
candidates and records both the recovered TOMO ratio and the number of 1 degree
grid cells that would be checked by the local verifier.

The TOMO values are read from the saved exhaustive 1 degree grids, so this is a
deterministic proxy for the local verification budget rather than a DLL rerun.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

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

DEFAULT_MAX_TOP_K = 50
DEFAULT_WINDOW_DEGREES = 10.0
DEFAULT_MIN_ANGLE_DEGREES = 3.0
DEFAULT_REPORT_KS = (1, 2, 3, 5, 10, 20, 30, 50)


def _parse_int_list(value: str) -> list[int]:
    parsed = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not parsed or any(item <= 0 for item in parsed):
        raise argparse.ArgumentTypeError("expected a comma-separated list of positive integers")
    return sorted(set(parsed))


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


def _window_cells(
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    *,
    yaw: float,
    pitch: float,
    radius_degrees: float,
) -> list[tuple[int, int]]:
    yaw_ids = _grid_indices_within(yaw_values, yaw, radius_degrees)
    pitch_ids = _grid_indices_within(pitch_values, pitch, radius_degrees)
    return [(int(pitch_id), int(yaw_id)) for pitch_id in pitch_ids for yaw_id in yaw_ids]


def _pool_oracle_ratio(
    pool,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
    tomo_best_vss: float,
) -> tuple[float, float]:
    values = [
        float(_signed_orientation(result[5], yaw_values, pitch_values, vss_grid)[1]["vss"])
        for result in pool
    ]
    if not values:
        return float("inf"), float("inf")
    pool_best_vss = float(np.nanmin(np.asarray(values, dtype=np.float64)))
    return pool_best_vss, _ratio(pool_best_vss, tomo_best_vss)


def _ranked_centers(
    pool,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
    *,
    max_top_k: int,
    min_angle_degrees: float,
) -> list[dict[str, float]]:
    ranked = support_flow_directions_from_candidate_pool(
        pool,
        limit=max_top_k,
        min_angle_degrees=min_angle_degrees,
    )
    centers: list[dict[str, float]] = []
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
                "hit_count": float(item.hit_count),
                "rayleigh_score": float(item.rayleigh_score),
                "pair_score": float(item.pair_score),
                "bed_score": float(item.bed_score),
            }
        )
    return centers


def analyze_grid(
    grid_path: Path,
    *,
    max_top_k: int,
    window_degrees: float,
    min_angle_degrees: float,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    data = np.load(grid_path, allow_pickle=True)
    yaw_values = np.asarray(data["yaw_values"], dtype=np.float64)
    pitch_values = np.asarray(data["pitch_values"], dtype=np.float64)
    vss_grid = np.asarray(data["vss_grid"], dtype=np.float64)
    tomo_best = _tomo_best(yaw_values, pitch_values, vss_grid)
    tomo_best_vss = float(tomo_best["vss"])
    mesh_path = _mesh_path_for_grid(grid_path)

    start = time.perf_counter()
    mesh = load_mesh(str(mesh_path))
    pool = evaluate_support_flow_candidate_pool(mesh)
    elapsed = time.perf_counter() - start

    pool_oracle_vss, pool_oracle = _pool_oracle_ratio(
        pool,
        yaw_values,
        pitch_values,
        vss_grid,
        tomo_best_vss,
    )
    centers = _ranked_centers(
        pool,
        yaw_values,
        pitch_values,
        vss_grid,
        max_top_k=max_top_k,
        min_angle_degrees=min_angle_degrees,
    )

    full_grid_cells = int(vss_grid.size)
    visited_cells: set[tuple[int, int]] = set()
    best_local = {
        "yaw": float("nan"),
        "pitch": float("nan"),
        "vss": float("inf"),
    }
    best_seed = {
        "rank": None,
        "yaw": float("nan"),
        "pitch": float("nan"),
        "vss": float("inf"),
    }
    rows: list[dict[str, object]] = []

    for top_k, center in enumerate(centers, start=1):
        if center["vss"] < best_seed["vss"]:
            best_seed = {
                "rank": int(center["rank"]),
                "yaw": float(center["yaw"]),
                "pitch": float(center["pitch"]),
                "vss": float(center["vss"]),
            }

        for pitch_id, yaw_id in _window_cells(
            yaw_values,
            pitch_values,
            yaw=float(center["yaw"]),
            pitch=float(center["pitch"]),
            radius_degrees=window_degrees,
        ):
            cell = (pitch_id, yaw_id)
            if cell in visited_cells:
                continue
            visited_cells.add(cell)
            cell_vss = float(vss_grid[pitch_id, yaw_id])
            if cell_vss < best_local["vss"]:
                best_local = {
                    "yaw": float(yaw_values[yaw_id]),
                    "pitch": float(pitch_values[pitch_id]),
                    "vss": cell_vss,
                }

        local_cell_count = int(len(visited_cells))
        rows.append(
            {
                "mesh": mesh_path.name,
                "top_k": int(top_k),
                "window_degrees": float(window_degrees),
                "min_angle_degrees": float(min_angle_degrees),
                "face_count": int(len(mesh.faces)),
                "candidate_pool_size": int(len(pool)),
                "full_grid_cells": full_grid_cells,
                "local_cell_count": local_cell_count,
                "local_budget_fraction": local_cell_count / full_grid_cells,
                "candidate_budget_fraction": top_k / max(1, int(len(pool))),
                "tomo_best_yaw": float(tomo_best["yaw"]),
                "tomo_best_pitch": float(tomo_best["pitch"]),
                "tomo_best_vss": tomo_best_vss,
                "pool_oracle_vss": pool_oracle_vss,
                "pool_oracle_ratio": pool_oracle,
                "seed_best_rank": best_seed["rank"],
                "seed_best_yaw": float(best_seed["yaw"]),
                "seed_best_pitch": float(best_seed["pitch"]),
                "seed_best_vss": float(best_seed["vss"]),
                "seed_best_ratio": _ratio(float(best_seed["vss"]), tomo_best_vss),
                "local_best_yaw": float(best_local["yaw"]),
                "local_best_pitch": float(best_local["pitch"]),
                "local_best_vss": float(best_local["vss"]),
                "local_best_ratio": _ratio(float(best_local["vss"]), tomo_best_vss),
                "elapsed_sec": elapsed,
            }
        )

    detail = {
        "mesh": mesh_path.name,
        "npz": str(grid_path.relative_to(PROJECT_ROOT)),
        "face_count": int(len(mesh.faces)),
        "candidate_pool_size": int(len(pool)),
        "elapsed_sec": elapsed,
        "tomo_best": tomo_best,
        "pool_oracle_vss": pool_oracle_vss,
        "pool_oracle_ratio": pool_oracle,
        "top_candidates": centers,
    }
    return rows, detail


def summarize_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["top_k"])].append(row)

    summary: list[dict[str, object]] = []
    for top_k in sorted(grouped):
        group = grouped[top_k]
        ratios = np.asarray([float(row["local_best_ratio"]) for row in group], dtype=np.float64)
        seed_ratios = np.asarray([float(row["seed_best_ratio"]) for row in group], dtype=np.float64)
        budgets = np.asarray([float(row["local_budget_fraction"]) for row in group], dtype=np.float64)
        cell_counts = np.asarray([float(row["local_cell_count"]) for row in group], dtype=np.float64)
        no_happy = np.asarray(
            [
                float(row["local_best_ratio"])
                for row in group
                if "happy" not in str(row["mesh"]).lower()
            ],
            dtype=np.float64,
        )
        summary.append(
            {
                "top_k": int(top_k),
                "mesh_count": int(len(group)),
                "mean_local_ratio": float(np.mean(ratios)),
                "median_local_ratio": float(np.median(ratios)),
                "p80_local_ratio": float(np.percentile(ratios, 80)),
                "max_local_ratio": float(np.max(ratios)),
                "mean_seed_ratio": float(np.mean(seed_ratios)),
                "median_seed_ratio": float(np.median(seed_ratios)),
                "mean_local_ratio_without_happy": float(np.mean(no_happy)) if no_happy.size else float("nan"),
                "median_local_ratio_without_happy": float(np.median(no_happy)) if no_happy.size else float("nan"),
                "max_local_ratio_without_happy": float(np.max(no_happy)) if no_happy.size else float("nan"),
                "mean_local_cell_count": float(np.mean(cell_counts)),
                "median_local_cell_count": float(np.median(cell_counts)),
                "mean_local_budget_fraction": float(np.mean(budgets)),
                "median_local_budget_fraction": float(np.median(budgets)),
                "max_local_budget_fraction": float(np.max(budgets)),
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


def _mesh_label(mesh: str) -> str:
    label = Path(mesh).stem
    if label.startswith("Group_C"):
        label = label.split("_", 2)[-1]
    return label


def write_budget_plot(
    rows: list[dict[str, object]],
    summary: list[dict[str, object]],
    *,
    svg_path: Path,
    pdf_path: Path,
) -> None:
    by_mesh: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_mesh[str(row["mesh"])].append(row)
    for mesh_rows in by_mesh.values():
        mesh_rows.sort(key=lambda row: int(row["top_k"]))

    x_k = np.asarray([int(row["top_k"]) for row in summary], dtype=np.float64)
    mean_ratio = np.asarray([float(row["mean_local_ratio"]) for row in summary], dtype=np.float64)
    median_ratio = np.asarray([float(row["median_local_ratio"]) for row in summary], dtype=np.float64)
    mean_no_happy = np.asarray(
        [float(row["mean_local_ratio_without_happy"]) for row in summary],
        dtype=np.float64,
    )
    mean_budget_pct = np.asarray(
        [100.0 * float(row["mean_local_budget_fraction"]) for row in summary],
        dtype=np.float64,
    )

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.35), constrained_layout=True)
    colors = plt.get_cmap("tab10")

    for index, (mesh, mesh_rows) in enumerate(sorted(by_mesh.items())):
        mesh_k = [int(row["top_k"]) for row in mesh_rows]
        mesh_ratio = [float(row["local_best_ratio"]) for row in mesh_rows]
        mesh_budget = [100.0 * float(row["local_budget_fraction"]) for row in mesh_rows]
        label = _mesh_label(mesh)
        color = colors(index % 10)
        axes[0].plot(mesh_k, mesh_ratio, color=color, alpha=0.28, linewidth=1.0, label=label)
        axes[1].plot(mesh_budget, mesh_ratio, color=color, alpha=0.28, linewidth=1.0)

    axes[0].plot(x_k, mean_ratio, color="black", linewidth=2.0, label="mean")
    axes[0].plot(x_k, median_ratio, color="#d95f02", linewidth=2.0, label="median")
    axes[0].plot(x_k, mean_no_happy, color="#1b9e77", linewidth=1.8, linestyle="--", label="mean w/o happy")
    axes[1].plot(mean_budget_pct, mean_ratio, color="black", linewidth=2.0, label="mean")
    axes[1].plot(mean_budget_pct, median_ratio, color="#d95f02", linewidth=2.0, label="median")
    axes[1].plot(mean_budget_pct, mean_no_happy, color="#1b9e77", linewidth=1.8, linestyle="--", label="mean w/o happy")

    for axis in axes:
        axis.axhline(1.0, color="0.35", linewidth=0.8)
        axis.axhline(2.0, color="0.55", linewidth=0.8, linestyle=":")
        axis.set_ylabel("local TOMO ratio")
        axis.grid(True, color="0.88", linewidth=0.6)
        axis.set_ylim(bottom=0.9)

    axes[0].set_xlabel("Top-K SFTF candidates")
    axes[0].set_xlim(left=1, right=float(np.max(x_k)))
    axes[1].set_xlabel("Local TOMO cells (% of full grid)")
    axes[1].set_xlim(left=0)
    axes[0].legend(loc="upper right", fontsize=6.5, frameon=False, ncol=2)
    axes[1].legend(loc="upper right", fontsize=7.0, frameon=False)

    fig.suptitle("SFTF local TOMO budget curve", fontsize=11)
    fig.savefig(svg_path, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)


def _select_report_rows(summary: list[dict[str, object]], report_ks: list[int]) -> list[dict[str, object]]:
    by_top_k = {int(row["top_k"]): row for row in summary}
    return [by_top_k[top_k] for top_k in report_ks if top_k in by_top_k]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-top-k", type=int, default=DEFAULT_MAX_TOP_K)
    parser.add_argument("--window-degrees", type=float, default=DEFAULT_WINDOW_DEGREES)
    parser.add_argument("--min-angle-degrees", type=float, default=DEFAULT_MIN_ANGLE_DEGREES)
    parser.add_argument("--report-k-list", type=_parse_int_list, default=list(DEFAULT_REPORT_KS))
    parser.add_argument("--mesh-contains", action="append", default=[])
    parser.add_argument("--output-stem", default="sftf_budget_curve_topk_local_tomo")
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    if args.max_top_k <= 0:
        raise ValueError("--max-top-k must be positive")

    grid_paths = sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}"))
    for needle in args.mesh_contains:
        grid_paths = [path for path in grid_paths if needle.lower() in path.name.lower()]
    if not grid_paths:
        raise FileNotFoundError(f"no saved TOMO grids found under {MESH_DIR}")

    print(
        f"budget curve: K=1..{args.max_top_k}, window=+/-{args.window_degrees:g} deg, "
        f"min_angle={args.min_angle_degrees:g} deg",
        flush=True,
    )

    rows: list[dict[str, object]] = []
    details: list[dict[str, object]] = []
    for index, grid_path in enumerate(grid_paths, start=1):
        print(f"[{index}/{len(grid_paths)}] {grid_path.name}", flush=True)
        mesh_rows, detail = analyze_grid(
            grid_path,
            max_top_k=args.max_top_k,
            window_degrees=args.window_degrees,
            min_angle_degrees=args.min_angle_degrees,
        )
        rows.extend(mesh_rows)
        details.append(detail)
        by_top_k = {int(row["top_k"]): row for row in mesh_rows}
        report = [
            f"K={top_k}: {by_top_k[top_k]['local_best_ratio']:.2f}"
            for top_k in args.report_k_list
            if top_k in by_top_k
        ]
        print(
            "  "
            + " ".join(report)
            + f"  oracle={detail['pool_oracle_ratio']:.2f}  ({detail['elapsed_sec']:.2f}s)",
            flush=True,
        )

    summary = summarize_rows(rows)
    csv_path = MESH_DIR / f"{args.output_stem}.csv"
    summary_csv_path = MESH_DIR / f"{args.output_stem}_summary.csv"
    json_path = MESH_DIR / f"{args.output_stem}.json"
    svg_path = MESH_DIR / f"{args.output_stem}.svg"
    pdf_path = MESH_DIR / f"{args.output_stem}.pdf"

    _write_csv(csv_path, rows)
    _write_csv(summary_csv_path, summary)
    json_path.write_text(
        json.dumps(
            {
                "config": {
                    "max_top_k": args.max_top_k,
                    "window_degrees": args.window_degrees,
                    "min_angle_degrees": args.min_angle_degrees,
                    "grid_suffix": GRID_SUFFIX,
                    "mode": "saved_grid_cumulative_local_window",
                },
                "summary": summary,
                "report_rows": _select_report_rows(summary, args.report_k_list),
                "rows": rows,
                "details": details,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    if not args.no_plot:
        write_budget_plot(rows, summary, svg_path=svg_path, pdf_path=pdf_path)

    print("\n=== budget curve summary ===")
    for row in _select_report_rows(summary, args.report_k_list):
        print(
            f"K={row['top_k']:<3} mean={row['mean_local_ratio']:.3f} "
            f"median={row['median_local_ratio']:.3f} max={row['max_local_ratio']:.3f} "
            f"budget={100.0 * row['mean_local_budget_fraction']:.2f}% "
            f"<=2.0={row['count_ratio_le_2_00']}/{row['mesh_count']}",
            flush=True,
        )

    saved = [csv_path, summary_csv_path, json_path]
    if not args.no_plot:
        saved.extend([svg_path, pdf_path])
    print("\nsaved: " + ", ".join(str(path.relative_to(PROJECT_ROOT)) for path in saved), flush=True)


if __name__ == "__main__":
    main()
