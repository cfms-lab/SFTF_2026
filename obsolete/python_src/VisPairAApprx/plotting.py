from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from python_src.tse6_config import COOLWARM_COLORSCALE
from python_src.VisPairAApprx import VisPairAApprx


def make_merged_vss_contour_figure(
    label: str,
    angles_yaw: np.ndarray,
    angles_pitch: np.ndarray,
    merged_vss: np.ndarray,
    pair_count: int,
    critical_angle: float,
    approximation_order: int,
) -> go.Figure:
    fig = go.Figure(
        data=go.Contour(
            x=angles_yaw,
            y=angles_pitch,
            z=merged_vss,
            colorscale=COOLWARM_COLORSCALE,
            contours=dict(showlabels=True),
            colorbar=dict(title="merged v_ss"),
            hovertemplate="yaw=%{x:.1f}<br>pitch=%{y:.1f}<br>merged v_ss=%{z:.6g}<extra></extra>",
        )
    )
    fig.update_layout(
        title=(
            f"{label} merged visible-face pair v_ss<br>"
            f"<sup>{pair_count} visible pairs, critical angle={critical_angle:.1f} deg, "
            f"approximation order={approximation_order}</sup>"
        ),
        width=900,
        height=520,
    )
    fig.update_xaxes(
        title_text="Yaw angle (deg)",
        range=[float(np.min(angles_yaw)), float(np.max(angles_yaw))],
        constrain="domain",
    )
    fig.update_yaxes(
        title_text="Pitch angle (deg)",
        range=[float(np.min(angles_pitch)), float(np.max(angles_pitch))],
        scaleanchor="x",
        scaleratio=1.0,
        constrain="domain",
    )
    return fig


def make_regression_vss_contour_figure(
    label: str,
    angles_yaw: np.ndarray,
    angles_pitch: np.ndarray,
    v_ss_rg: np.ndarray,
    pair_count: int,
) -> go.Figure:
    fig = go.Figure(
        data=go.Contour(
            x=angles_yaw,
            y=angles_pitch,
            z=v_ss_rg,
            colorscale=COOLWARM_COLORSCALE,
            contours=dict(showlabels=True),
            colorbar=dict(title="regression v_ss"),
            hovertemplate="yaw=%{x:.1f}<br>pitch=%{y:.1f}<br>regression v_ss=%{z:.6g}<extra></extra>",
        )
    )
    fig.update_layout(
        title=(
            f"{label} regression visible-face pair v_ss<br>"
            f"<sup>{pair_count} visible pairs, loaded model={VisPairAApprx.MODEL_PATH}</sup>"
        ),
        width=900,
        height=520,
    )
    fig.update_xaxes(
        title_text="Yaw angle (deg)",
        range=[float(np.min(angles_yaw)), float(np.max(angles_yaw))],
        constrain="domain",
    )
    fig.update_yaxes(
        title_text="Pitch angle (deg)",
        range=[float(np.min(angles_pitch)), float(np.max(angles_pitch))],
        scaleanchor="x",
        scaleratio=1.0,
        constrain="domain",
    )
    return fig


def make_tomo_vs_project_validation_contour_figure(
    label: str,
    angles_yaw: np.ndarray,
    angles_pitch: np.ndarray,
    tomo_vtc_grid: np.ndarray,
    tomo_vnv_grid: np.ndarray,
    tomo_vss_grid: np.ndarray,
    project_vtc_grid: np.ndarray,
    v_nv_bt: np.ndarray,
    v_nv_rg: np.ndarray,
    tse6_v_nv: np.ndarray,
    pair_count: int,
    critical_angle: float,
    angle_step: float,
) -> go.Figure:
    def extreme_points(grid: np.ndarray, count: int = 3) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
        values = np.asarray(grid, dtype=np.float64)
        flat = values.ravel()
        finite_ids = np.flatnonzero(np.isfinite(flat))
        if len(finite_ids) == 0:
            return [], []

        count = min(count, len(finite_ids))
        finite_values = flat[finite_ids]
        optimal_ids = finite_ids[np.argsort(finite_values)[:count]]
        worst_ids = finite_ids[np.argsort(finite_values)[-count:][::-1]]

        def rows(ids: np.ndarray) -> list[dict[str, float]]:
            points = []
            for flat_id in ids:
                pitch_id, yaw_id = np.unravel_index(int(flat_id), values.shape)
                points.append(
                    {
                        "yaw": float(angles_yaw[yaw_id]),
                        "pitch": float(angles_pitch[pitch_id]),
                        "value": float(values[pitch_id, yaw_id]),
                    }
                )
            return points

        return rows(optimal_ids), rows(worst_ids)

    fig = make_subplots(
        rows=2,
        cols=4,
        subplot_titles=(
            "TOMO_CPU V_tc",
            "TOMO_CPU V_nv",
            "TOMO_CPU V_ss",
            "",
            "TSE6 V_tc_bt",
            "v_nv_bt",
            "v_nv_rg",
            "tse6_v_nv",
        ),
        horizontal_spacing=0.06,
        vertical_spacing=0.14,
    )
    traces = (
        (1, 1, tomo_vtc_grid, "TOMO V_tc", "V_tc", 0.23),
        (1, 2, tomo_vnv_grid, "TOMO V_nv", "V_nv", 0.49),
        (1, 3, tomo_vss_grid, "TOMO V_ss", "V_ss", 0.75),
        (2, 1, project_vtc_grid, "TSE6 V_tc_bt", "V_tc_bt", 0.23),
        (2, 2, v_nv_bt, "v_nv_bt", "v_nv_bt", 0.49),
        (2, 3, v_nv_rg, "v_nv_rg", "v_nv_rg", 0.75),
        (2, 4, tse6_v_nv, "tse6_v_nv", "tse6_v_nv", 1.00),
    )
    for row, col, grid, title, hover_name, colorbar_x in traces:
        fig.add_trace(
            go.Contour(
                x=angles_yaw,
                y=angles_pitch,
                z=grid,
                colorscale=COOLWARM_COLORSCALE,
                contours=dict(showlabels=True),
                colorbar=dict(title=title, x=colorbar_x),
                hovertemplate=f"yaw=%{{x:.1f}}<br>pitch=%{{y:.1f}}<br>{hover_name}=%{{z:.6g}}<extra></extra>",
            ),
            row=row,
            col=col,
        )
        optimal_points, worst_points = extreme_points(grid, count=3)
        for point_type, points, color, symbol, prefix in (
            ("optimal", optimal_points, "rgb(220, 35, 35)", "circle", "o"),
            ("worst", worst_points, "rgb(30, 85, 220)", "x", "w"),
        ):
            if not points:
                continue
            fig.add_trace(
                go.Scatter(
                    x=[point["yaw"] for point in points],
                    y=[point["pitch"] for point in points],
                    mode="markers+text",
                    text=[f"{prefix}{idx}" for idx in range(1, len(points) + 1)],
                    textposition="top center",
                    marker=dict(
                        color=color,
                        size=11,
                        symbol=symbol,
                        line=dict(color="white", width=1),
                    ),
                    name=f"{title} {point_type}",
                    showlegend=False,
                    hovertemplate=(
                        f"{title} {point_type}<br>"
                        "yaw=%{x:.1f}<br>pitch=%{y:.1f}<br>"
                        f"{hover_name}=%{{customdata:.6g}}<extra></extra>"
                    ),
                    customdata=[point["value"] for point in points],
                ),
                row=row,
                col=col,
            )
    fig.update_layout(
        title=(
            f"{label}: TOMO_CPU components vs TSE6 components<br>"
            f"<sup>critical angle={critical_angle:.1f} deg, angle step={angle_step:.1f} deg, "
            f"{pair_count} visible pairs</sup>"
        ),
        width=1780,
        height=920,
    )
    fig.update_xaxes(
        title_text="Yaw angle (deg)",
        range=[float(np.min(angles_yaw)), float(np.max(angles_yaw))],
        constrain="domain",
    )
    fig.update_yaxes(
        title_text="Pitch angle (deg)",
        range=[float(np.min(angles_pitch)), float(np.max(angles_pitch))],
        scaleanchor="x",
        scaleratio=1.0,
        constrain="domain",
    )
    fig.update_yaxes(scaleanchor="x2", scaleratio=1.0, row=1, col=2)
    fig.update_yaxes(scaleanchor="x3", scaleratio=1.0, row=1, col=3)
    fig.update_yaxes(scaleanchor="x5", scaleratio=1.0, row=2, col=1)
    fig.update_yaxes(scaleanchor="x6", scaleratio=1.0, row=2, col=2)
    fig.update_yaxes(scaleanchor="x7", scaleratio=1.0, row=2, col=3)
    fig.update_yaxes(scaleanchor="x8", scaleratio=1.0, row=2, col=4)
    return fig


def write_merged_contour_figures(
    results: list[dict[str, object]],
    output_dir: Path,
    merged_contour_path: Path,
    regression_contour_path: Path,
    critical_angle: float,
    approximation_order: int,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []
    for result in results:
        label = str(result["label"])
        fig = make_merged_vss_contour_figure(
            label,
            np.asarray(result["angles_yaw"], dtype=np.float64),
            np.asarray(result["angles_pitch"], dtype=np.float64),
            np.asarray(result["merged_vss"], dtype=np.float64),
            len(result["visible_pair_infos"]),
            critical_angle,
            approximation_order,
        )
        output_path = merged_contour_path
        if len(results) > 1:
            output_path = merged_contour_path.with_name(f"{label}_{merged_contour_path.name}")
        fig.write_html(output_path)
        print(f"wrote {output_path.resolve()}")
        fig.show()
        output_paths.append(output_path)

        if result.get("v_ss_rg") is not None:
            regression_fig = make_regression_vss_contour_figure(
                label,
                np.asarray(result["angles_yaw"], dtype=np.float64),
                np.asarray(result["angles_pitch"], dtype=np.float64),
                np.asarray(result["v_ss_rg"], dtype=np.float64),
                len(result["visible_pair_infos"]),
            )
            regression_output_path = regression_contour_path
            if len(results) > 1:
                regression_output_path = regression_contour_path.with_name(
                    f"{label}_{regression_contour_path.name}"
                )
            regression_fig.write_html(regression_output_path)
            print(f"wrote {regression_output_path.resolve()}")
            regression_fig.show()
            output_paths.append(regression_output_path)
    return output_paths
