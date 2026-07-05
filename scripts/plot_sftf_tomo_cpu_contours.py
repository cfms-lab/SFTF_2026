from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField.support_flow_tensor_field import (
    evaluate_support_flow_candidate_pool,
    load_mesh,
)
from cpp_src.Tomo_GPU2026.tomo_cpu import (
    ANGLE_STEP,
    CRITICAL_ANGLE,
    compute_tomo_cpu_batch_mss as compute_tomo_cpu_batch_mss_local,
    compute_tomo_cpu_vss_grid,
    tomo_best_row,
)

NPZ_SUFFIX = "_tomo_int3_vss_grid_1deg_60deg.npz"
DEFAULT_MESH_GLOB = "([1-5])*"
DEFAULT_TOMO_ROOT = PROJECT_ROOT / "cpp_src" / "Tomo_GPU2026"
PLOT_BASIN_COUNT = 3
SFTF_SOURCE_BASIN_COUNT = 40
BASIN_MIN_ANGLE_DEGREES = 12.0
PLOT_BASIN_MIN_YAW_PITCH_DEGREES = 45.0


def mesh_path_for_npz(npz_path: Path) -> Path:
    stem = npz_path.name[: -len(NPZ_SUFFIX)]
    for suffix in (".ply", ".stl", ".obj"):
        candidate = npz_path.with_name(stem + suffix)
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"no mesh file found for {npz_path}")


def tomo_npz_path_for_mesh(mesh_path: Path) -> Path:
    return mesh_path.with_name(f"{mesh_path.stem}{NPZ_SUFFIX}")


def ensure_tomo_npz(mesh_path: Path, *, tomo_root: Path = DEFAULT_TOMO_ROOT) -> Path:
    npz_path = tomo_npz_path_for_mesh(mesh_path)
    if npz_path.exists():
        return npz_path

    tomo = compute_tomo_cpu_vss_grid(
        mesh_path,
        critical_angle=CRITICAL_ANGLE,
        angle_step=ANGLE_STEP,
    )
    yaw_values = np.asarray(tomo["yaw_values"], dtype=np.float64)
    pitch_values = np.asarray(tomo["pitch_values"], dtype=np.float64)
    vss_grid = np.asarray(tomo["vss_grid"], dtype=np.float64)
    tomo_best = tomo_best_row(yaw_values, pitch_values, vss_grid)
    np.savez_compressed(
        npz_path,
        yaw_values=yaw_values,
        pitch_values=pitch_values,
        vss_grid=vss_grid,
        tomo_best=np.asarray(
            [tomo_best["yaw"], tomo_best["pitch"], tomo_best["vss"]],
            dtype=np.float64,
        ),
    )
    return npz_path


def direction_from_tomo_yaw_pitch(yaw: float, pitch: float) -> np.ndarray:
    yaw_rad = np.deg2rad(float(yaw))
    pitch_rad = np.deg2rad(float(pitch))
    direction = np.array(
        [
            -np.sin(pitch_rad),
            np.cos(pitch_rad) * np.sin(yaw_rad),
            np.cos(pitch_rad) * np.cos(yaw_rad),
        ],
        dtype=np.float64,
    )
    return direction / max(float(np.linalg.norm(direction)), 1e-12)


def select_basin_representatives(
    rows: list[dict[str, float]],
    *,
    value_key: str,
    count: int,
    reverse: bool,
    min_angle_degrees: float = BASIN_MIN_ANGLE_DEGREES,
) -> list[dict[str, float]]:
    selected = []
    min_dot = float(np.cos(np.deg2rad(min_angle_degrees)))
    for row in sorted(rows, key=lambda item: item[value_key], reverse=reverse):
        direction = np.asarray(row["direction"], dtype=np.float64)
        if any(float(np.dot(direction, existing["direction"])) >= min_dot for existing in selected):
            continue
        selected.append(row)
        if len(selected) >= count:
            break
    return [dict(row, rank=rank) for rank, row in enumerate(selected, start=1)]


def periodic_angle_delta(a: float, b: float) -> float:
    return abs((float(a) - float(b) + 180.0) % 360.0 - 180.0)


def yaw_pitch_distance(row_a: dict[str, float], row_b: dict[str, float]) -> float:
    dyaw = periodic_angle_delta(row_a["yaw"], row_b["yaw"])
    dpitch = periodic_angle_delta(row_a["pitch"], row_b["pitch"])
    return float(np.hypot(dyaw, dpitch))


def select_yaw_pitch_basin_representatives(
    rows: list[dict[str, float]],
    *,
    value_key: str,
    count: int,
    reverse: bool,
    min_distance_degrees: float = PLOT_BASIN_MIN_YAW_PITCH_DEGREES,
) -> list[dict[str, float]]:
    selected = []
    for row in sorted(rows, key=lambda item: item[value_key], reverse=reverse):
        if any(yaw_pitch_distance(row, existing) < min_distance_degrees for existing in selected):
            continue
        selected.append(row)
        if len(selected) >= count:
            break
    return [dict(row, rank=rank) for rank, row in enumerate(selected, start=1)]


def smallest_basin_rows(
    grid: np.ndarray,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    *,
    count: int,
) -> list[dict[str, float]]:
    return grid_basin_rows(grid, yaw_values, pitch_values, count=count, reverse=False)


def largest_basin_rows(
    grid: np.ndarray,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    *,
    count: int,
) -> list[dict[str, float]]:
    return grid_basin_rows(grid, yaw_values, pitch_values, count=count, reverse=True)


def grid_basin_rows(
    grid: np.ndarray,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    *,
    count: int,
    reverse: bool,
) -> list[dict[str, float]]:
    flat = np.asarray(grid, dtype=np.float64).reshape(-1)
    order = np.argsort(flat, kind="stable")
    if reverse:
        order = order[::-1]

    candidate_rows = []
    for flat_id in order:
        pitch_id, yaw_id = np.unravel_index(int(flat_id), grid.shape)
        yaw = float(yaw_values[yaw_id])
        pitch = float(pitch_values[pitch_id])
        candidate_rows.append(
            {
                "yaw": yaw,
                "pitch": pitch,
                "vss": float(flat[int(flat_id)]),
                "direction": direction_from_tomo_yaw_pitch(yaw, pitch),
            }
        )
        if len(candidate_rows) >= max(count * 400, count):
            break
    return select_yaw_pitch_basin_representatives(
        candidate_rows,
        value_key="vss",
        count=count,
        reverse=reverse,
    )


def grid_rows(
    flat_ids: np.ndarray,
    flat_values: np.ndarray,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    grid_shape: tuple[int, int],
) -> list[dict[str, float]]:
    rows = []
    for rank, flat_id in enumerate(flat_ids, start=1):
        pitch_id, yaw_id = np.unravel_index(int(flat_id), grid_shape)
        rows.append(
            {
                "rank": rank,
                "yaw": float(yaw_values[yaw_id]),
                "pitch": float(pitch_values[pitch_id]),
                "vss": float(flat_values[int(flat_id)]),
            }
        )
    return rows


def nearest_tomo_grid_row(
    direction: np.ndarray,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
) -> dict[str, float]:
    direction = np.asarray(direction, dtype=np.float64)
    direction /= max(float(np.linalg.norm(direction)), 1e-12)

    yaw = np.deg2rad(np.asarray(yaw_values, dtype=np.float64))
    pitch = np.deg2rad(np.asarray(pitch_values, dtype=np.float64))
    sin_y = np.sin(yaw)[None, :]
    cos_y = np.cos(yaw)[None, :]
    sin_p = np.sin(pitch)[:, None]
    cos_p = np.cos(pitch)[:, None]
    alignment = (
        -sin_p * direction[0]
        + cos_p * sin_y * direction[1]
        + cos_p * cos_y * direction[2]
    )
    pitch_id, yaw_id = np.unravel_index(int(np.nanargmax(alignment)), alignment.shape)
    return {
        "yaw": float(yaw_values[yaw_id]),
        "pitch": float(pitch_values[pitch_id]),
        "vss": float(vss_grid[pitch_id, yaw_id]),
        "alignment": float(alignment[pitch_id, yaw_id]),
    }


def candidate_basin_results_from_pool(tuned_results):
    optimal = rank_support_flow_basin_results(
        tuned_results,
        limit=SFTF_SOURCE_BASIN_COUNT,
        min_angle_degrees=BASIN_MIN_ANGLE_DEGREES,
        reverse=False,
    )
    worst = rank_support_flow_basin_results(
        tuned_results,
        limit=SFTF_SOURCE_BASIN_COUNT,
        min_angle_degrees=BASIN_MIN_ANGLE_DEGREES,
        reverse=True,
    )
    return optimal, worst


def candidate_basin_results_for_mesh(mesh_path: Path):
    mesh = load_mesh(str(mesh_path))
    mesh = mesh.copy()
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals()
    return candidate_basin_results_from_pool(evaluate_support_flow_candidate_pool(mesh))


def rank_support_flow_basin_results(results, *, limit: int, min_angle_degrees: float, reverse: bool):
    ranked = []
    min_dot = float(np.cos(np.deg2rad(min_angle_degrees)))
    for result in sorted(results, key=lambda item: item[0], reverse=reverse):
        direction = result[5]
        if any(float(np.dot(direction, existing[5])) >= min_dot for existing in ranked):
            continue
        ranked.append(result)
        if len(ranked) >= limit:
            break
    return ranked


def sftf_marker_rows(results, yaw_values, pitch_values, vss_grid, *, marker_kind: str) -> list[dict[str, float]]:
    rows = []
    for rank, result in enumerate(results, start=1):
        score = float(result[0])
        direction = np.asarray(result[5], dtype=np.float64)
        row = nearest_tomo_grid_row(direction, yaw_values, pitch_values, vss_grid)
        row["rank"] = rank
        row["score"] = score
        row["kind"] = marker_kind
        rows.append(row)
    return rows


def compute_tomo_cpu_single_mss(mesh_path: Path, yaw: float, pitch: float, *, tomo_root: Path) -> tuple[float, float]:
    return compute_tomo_cpu_batch_mss(mesh_path, [{"yaw": yaw, "pitch": pitch}], tomo_root=tomo_root)[0]


def compute_tomo_cpu_batch_mss(mesh_path: Path, rows: list[dict[str, float]], *, tomo_root: Path) -> list[tuple[float, float]]:
    return compute_tomo_cpu_batch_mss_local(mesh_path, rows)


def measured_sftf_marker_rows(
    mesh_path: Path,
    low_score_results,
    high_score_results,
    yaw_values,
    pitch_values,
    vss_grid,
    *,
    tomo_root: Path,
) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    candidate_rows = []
    for source_kind, results in (("low-score", low_score_results), ("high-score", high_score_results)):
        for source_rank, result in enumerate(results, start=1):
            score = float(result[0])
            direction = np.asarray(result[5], dtype=np.float64)
            row = nearest_tomo_grid_row(direction, yaw_values, pitch_values, vss_grid)
            row["source_rank"] = source_rank
            row["source_kind"] = source_kind
            row["score"] = score
            row["direction"] = direction_from_tomo_yaw_pitch(row["yaw"], row["pitch"])
            candidate_rows.append(row)

    candidate_rows = select_yaw_pitch_basin_representatives(
        candidate_rows,
        value_key="score",
        count=len(candidate_rows),
        reverse=False,
        min_distance_degrees=PLOT_BASIN_MIN_YAW_PITCH_DEGREES * 0.35,
    )
    for row, (tomo_mss, tomo_vss) in zip(
        candidate_rows,
        compute_tomo_cpu_batch_mss(mesh_path, candidate_rows, tomo_root=tomo_root),
    ):
        row["tomo_mss"] = tomo_mss
        row["tomo_vss"] = tomo_vss

    optimal = select_yaw_pitch_basin_representatives(
        candidate_rows,
        value_key="tomo_mss",
        count=PLOT_BASIN_COUNT,
        reverse=False,
    )
    worst = select_yaw_pitch_basin_representatives(
        candidate_rows,
        value_key="tomo_mss",
        count=PLOT_BASIN_COUNT,
        reverse=True,
    )
    optimal = [dict(item, kind="optimal") for item in optimal]
    worst = [dict(item, kind="worst") for item in worst]
    return optimal, worst


def add_contour(fig, row, col, yaw_values, pitch_values, vss_grid, *, title: str, showscale: bool):
    fig.add_trace(
        go.Contour(
            x=yaw_values,
            y=pitch_values,
            z=vss_grid,
            colorscale="RdBu_r",
            contours=dict(showlabels=True),
            colorbar=dict(title="v_ss") if showscale else None,
            showscale=showscale,
            hovertemplate=(
                f"{title}<br>yaw=%{{x:.1f}}<br>pitch=%{{y:.1f}}"
                "<br>v_ss=%{z:.6g}<extra></extra>"
            ),
        ),
        row=row,
        col=col,
    )


def add_marker_trace(fig, row, col, rows, *, name: str, symbol: str, color: str, label_prefix: str, showlegend: bool):
    fig.add_trace(
        go.Scatter(
            x=[item["yaw"] for item in rows],
            y=[item["pitch"] for item in rows],
            mode="markers+text",
            name=name,
            legendgroup=name,
            showlegend=showlegend,
            text=[f"{label_prefix}{item['rank']}" for item in rows],
            textposition="top center" if "optimal" in name.lower() else "bottom center",
            marker=dict(symbol=symbol, size=12, color=color, line=dict(color="#ffffff", width=1)),
            customdata=[
                [
                    item["vss"],
                    item.get("tomo_mss", np.nan),
                    item.get("tomo_vss", np.nan),
                    item.get("score", np.nan),
                    item.get("alignment", np.nan),
                    item.get("source_rank", np.nan),
                    item.get("source_kind", ""),
                ]
                for item in rows
            ],
            hovertemplate=(
                f"{name} %{{text}}<br>yaw=%{{x:.1f}}<br>pitch=%{{y:.1f}}"
                "<br>contour v_ss=%{customdata[0]:.6g}"
                "<br>TOMO Mss=%{customdata[1]:.6g}"
                "<br>TOMO v_ss=%{customdata[2]:.6g}"
                "<br>SFTF score=%{customdata[3]:.6g}"
                "<br>align=%{customdata[4]:.6g}"
                "<br>source rank=%{customdata[5]}"
                "<br>source=%{customdata[6]}<extra></extra>"
            ),
        ),
        row=row,
        col=col,
    )


def build_figure(mesh_npz_pairs, *, tomo_root: Path) -> go.Figure:
    # One contour per mesh: the TOMO_CPU v_ss grid is drawn once and both the
    # TOMO_CPU and the SFTF optimal/worst basins are overlaid on the same axes.
    subplot_titles = [
        f"{record[0].name}: TOMO_CPU v_ss with TOMO_CPU & SFTF optimal/worst"
        for record in mesh_npz_pairs
    ]
    fig = make_subplots(
        rows=len(mesh_npz_pairs),
        cols=1,
        subplot_titles=subplot_titles,
        vertical_spacing=0.08,
    )

    for row_id, record in enumerate(mesh_npz_pairs, start=1):
        mesh_path, npz_path = record[0], record[1]
        support_candidate_results = record[2] if len(record) > 2 else None
        data = np.load(npz_path, allow_pickle=True)
        yaw_values = np.asarray(data["yaw_values"], dtype=np.float64)
        pitch_values = np.asarray(data["pitch_values"], dtype=np.float64)
        vss_grid = np.asarray(data["vss_grid"], dtype=np.float64)

        tomo_optimal = smallest_basin_rows(vss_grid, yaw_values, pitch_values, count=PLOT_BASIN_COUNT)
        tomo_worst = largest_basin_rows(vss_grid, yaw_values, pitch_values, count=PLOT_BASIN_COUNT)
        if support_candidate_results is None:
            sftf_low_score_results, sftf_high_score_results = candidate_basin_results_for_mesh(mesh_path)
        else:
            sftf_low_score_results, sftf_high_score_results = candidate_basin_results_from_pool(support_candidate_results)
        sftf_optimal, sftf_worst = measured_sftf_marker_rows(
            mesh_path,
            sftf_low_score_results,
            sftf_high_score_results,
            yaw_values,
            pitch_values,
            vss_grid,
            tomo_root=tomo_root,
        )

        add_contour(
            fig,
            row_id,
            1,
            yaw_values,
            pitch_values,
            vss_grid,
            title="TOMO_CPU",
            showscale=row_id == len(mesh_npz_pairs),
        )
        # TOMO_CPU grid optimal/worst basins and SFTF candidate optimal/worst
        # (remeasured by TOMO_CPU Mss), all on the single shared contour.
        for marker_rows, name, symbol, color, label_prefix in (
            (tomo_optimal, "TOMO optimal", "star", "#1664d8", "To"),
            (tomo_worst, "TOMO worst", "x", "#d93f21", "Tw"),
            (sftf_optimal, "Measured optimal", "circle", "#0b8f5a", "So"),
            (sftf_worst, "Measured worst", "diamond", "#8d46d6", "Sw"),
        ):
            add_marker_trace(
                fig,
                row_id,
                1,
                marker_rows,
                name=name,
                symbol=symbol,
                color=color,
                label_prefix=label_prefix,
                showlegend=row_id == 1,
            )

        fig.update_xaxes(title_text="Yaw (deg)", row=row_id, col=1)
        fig.update_yaxes(title_text="Pitch (deg)", scaleanchor=f"x{row_id}", scaleratio=1, row=row_id, col=1)

    fig.update_layout(
        title="TOMO_CPU v_ss Contours with TOMO_CPU and SFTF Optimal/Worst Orientations",
        height=max(620 * len(mesh_npz_pairs), 720),
        width=1180,
        margin=dict(t=80, r=210),
        # Vertical legend parked in the right margin so it never overlaps the
        # figure title or the optimal/worst markers on the contour.
        legend=dict(
            orientation="v",
            x=1.02,
            xanchor="left",
            y=1.0,
            yanchor="top",
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="rgba(80,80,80,0.25)",
            borderwidth=1,
        ),
    )
    return fig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mesh",
        action="append",
        type=Path,
        help="Specific mesh path to plot. Can be passed multiple times.",
    )
    parser.add_argument("--mesh-dir", type=Path, default=PROJECT_ROOT / "Experimental" / "etc")
    parser.add_argument("--mesh-glob", default=DEFAULT_MESH_GLOB)
    parser.add_argument("--tomo-root", type=Path, default=DEFAULT_TOMO_ROOT)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "Experimental" / "etc" / "tomo_cpu_sftf_contour_comparison.html",
    )
    return parser.parse_args()


def build_figure_for_meshes(mesh_paths: list[Path], *, tomo_root: Path) -> go.Figure:
    mesh_npz_pairs = [
        (mesh_path.resolve(), ensure_tomo_npz(mesh_path.resolve(), tomo_root=tomo_root.resolve()))
        for mesh_path in mesh_paths
    ]
    return build_figure(mesh_npz_pairs, tomo_root=tomo_root.resolve())


def build_figure_for_results(results: list[dict[str, object]], *, project_root: Path, tomo_root: Path) -> go.Figure:
    mesh_npz_pairs = []
    for result in results:
        raw_mesh_path = Path(str(result["mesh_path"]))
        mesh_path = raw_mesh_path if raw_mesh_path.is_absolute() else project_root / raw_mesh_path
        field = result.get("support_flow_tensor_field")
        support_candidate_results = None
        if field is not None:
            support_candidate_results = field.eigen_analysis.support_candidate_results
        mesh_npz_pairs.append(
            (
                mesh_path.resolve(),
                ensure_tomo_npz(mesh_path.resolve(), tomo_root=tomo_root.resolve()),
                support_candidate_results,
            )
        )
    return build_figure(mesh_npz_pairs, tomo_root=tomo_root.resolve())


def main() -> None:
    args = parse_args()
    mesh_dir = args.mesh_dir.resolve()

    if args.mesh:
        mesh_paths = [
            mesh_path if mesh_path.is_absolute() else PROJECT_ROOT / mesh_path
            for mesh_path in args.mesh
        ]
        mesh_npz_pairs = [
            (mesh_path.resolve(), ensure_tomo_npz(mesh_path.resolve(), tomo_root=args.tomo_root.resolve()))
            for mesh_path in mesh_paths
        ]
    else:
        mesh_paths = sorted(
            path
            for path in mesh_dir.glob(args.mesh_glob)
            if path.is_file() and path.suffix.lower() in {".ply", ".stl", ".obj"}
        )
        if not mesh_paths:
            raise FileNotFoundError(f"no TOMO npz or target meshes found in {mesh_dir}")
        mesh_npz_pairs = [
            (mesh_path, ensure_tomo_npz(mesh_path, tomo_root=args.tomo_root.resolve()))
            for mesh_path in mesh_paths
        ]

    fig = build_figure(mesh_npz_pairs, tomo_root=args.tomo_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(args.output, include_plotlyjs="cdn")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
