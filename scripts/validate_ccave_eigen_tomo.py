from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField import SupportFlowTensorField, analyze_concave_eigen_directions
from python_src.SupportFlowTensorField.support_flow_tensor_field import load_mesh


DEFAULT_TOMO_ROOT = PROJECT_ROOT / "cpp_src" / "Tomo_GPU2026"
DEFAULT_MESH_DIR = PROJECT_ROOT / "Experimental" / "etc"
DEFAULT_MESH_GLOB = "([1-5])*"
ANGLE_STEP = 1.0
CRITICAL_ANGLE = 60.0


def load_tomo_gpu2026_modules(tomo_project_root: Path | None = None):
    from cpp_src.Tomo_GPU2026 import tomo_shell_cpp, tomo_shell_io

    return tomo_shell_cpp, tomo_shell_io


def tomo_cpu_printer_settings() -> dict[str, float | bool]:
    return {
        "wall_thickness": 0.8,
        "PLA_density": 0.00121,
        "Fclad": 1.0,
        "Fcore": 0.15,
        "Fss": 0.2,
        "Css": 1.0,
        "dVoxel": 1.0,
        "nVoxel": 256,
        "bUseExplicitSS": False,
    }


def configure_tomo_cpu_printer(tomo, tomo_io, critical_angle: float) -> None:
    settings = tomo_cpu_printer_settings()
    tomo.wall_thickness = settings["wall_thickness"]
    tomo.PLA_density = settings["PLA_density"]
    tomo.Fclad = settings["Fclad"]
    tomo.Fcore = settings["Fcore"]
    tomo.Fss = settings["Fss"]
    tomo.Css = settings["Css"]
    tomo.dVoxel = settings["dVoxel"]
    tomo.nVoxel = settings["nVoxel"]
    tomo.theta_c = tomo_io.toRadian(critical_angle)
    tomo.bUseExplicitSS = settings["bUseExplicitSS"]
    tomo.BedType = (tomo_io.enumBedType.ebtRaft, 0, 2, 0.3 + 0.27 + 2 * 0.2)


def tomo_mss_to_support_volume(mss: np.ndarray, settings: dict[str, float | bool]) -> np.ndarray:
    mss = np.asarray(mss, dtype=np.float64)
    density = float(settings["PLA_density"])
    divisor = float(settings["Fss"]) * float(settings["Css"]) * density
    return np.divide(mss, divisor, out=np.zeros_like(mss), where=abs(divisor) > 1e-12)


def compute_tomo_cpu_vss_grid(
    mesh_path: Path,
    *,
    tomo_project_root: Path,
    critical_angle: float,
    angle_step: float,
) -> dict[str, object]:
    tomo_cpp, tomo_io = load_tomo_gpu2026_modules(tomo_project_root)
    mesh_path = mesh_path.resolve()

    previous_cwd = Path.cwd()
    try:
        os.chdir(tomo_project_root)
        tomo = tomo_cpp.TomoShellCpp((str(mesh_path), 0, 0, 0), angle_step, bVerbose=False)
        configure_tomo_cpu_printer(tomo, tomo_io, critical_angle)
        tomo.Run(cpp_function_name="TomoSh_INT3")
    finally:
        os.chdir(previous_cwd)

    grid_shape = (int(tomo.nYPR_Intervals), int(tomo.nYPR_Intervals))
    settings = tomo_cpu_printer_settings()
    vss_grid = tomo_mss_to_support_volume(np.asarray(tomo.Mss3D, dtype=np.float64), settings).reshape(grid_shape)
    yaw_values = np.asarray(tomo_io.toDegree(tomo.yaw_range), dtype=np.float64)
    pitch_values = np.asarray(tomo_io.toDegree(tomo.pitch_range), dtype=np.float64)

    return {
        "yaw_values": yaw_values,
        "pitch_values": pitch_values,
        "vss_grid": vss_grid,
        "tomo_internal_mesh_scale": float(getattr(tomo, "mesh_scale", 1.0)),
        "tomo_io": tomo_io,
    }


def save_vss_contour(
    mesh_path: Path,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
    *,
    tomo_best: dict[str, float],
    ccave_rows: list[dict[str, float]],
) -> Path:
    fig = go.Figure()
    fig.add_trace(
        go.Contour(
            x=yaw_values,
            y=pitch_values,
            z=vss_grid,
            colorscale="RdBu",
            contours=dict(showlabels=True),
            colorbar=dict(title="v_ss"),
            hovertemplate="yaw=%{x:.1f}<br>pitch=%{y:.1f}<br>v_ss=%{z:.6g}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[tomo_best["yaw"]],
            y=[tomo_best["pitch"]],
            mode="markers+text",
            name="TOMO best",
            text=["TOMO"],
            textposition="top center",
            marker=dict(symbol="star", size=14, color="#0b60d1", line=dict(color="#ffffff", width=1)),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[row["yaw"] for row in ccave_rows],
            y=[row["pitch"] for row in ccave_rows],
            mode="markers+text",
            name="SupportFlowTensorField",
            text=[f"C{row['score']}" for row in ccave_rows],
            textposition="bottom center",
            marker=dict(symbol="circle", size=10, color="#d85c17", line=dict(color="#ffffff", width=1)),
            customdata=[row["vss"] for row in ccave_rows],
            hovertemplate="SupportFlowTensorField %{text}<br>yaw=%{x:.1f}<br>pitch=%{y:.1f}<br>v_ss=%{customdata:.6g}<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"{mesh_path.name}: TOMO_CPU v_ss contour, 1 deg, critical angle 60 deg",
        xaxis_title="Yaw (deg)",
        yaxis_title="Pitch (deg)",
        width=980,
        height=860,
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)

    output_path = mesh_path.with_name(f"{mesh_path.stem}_tomo_cpu_vss_contour_1deg_60deg.html")
    fig.write_html(output_path, include_plotlyjs="cdn")
    return output_path


def tomo_rotation_matrix(tomo_io, yaw_deg: float, pitch_deg: float) -> np.ndarray:
    return np.asarray(
        tomo_io.getRotationMatrix(
            float(tomo_io.toRadian(yaw_deg)),
            float(tomo_io.toRadian(pitch_deg)),
            0.0,
        )[:3, :3],
        dtype=np.float64,
    )


def nearest_tomo_orientation_for_direction(
    direction: np.ndarray,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    tomo_io,
) -> dict[str, float]:
    direction = np.asarray(direction, dtype=np.float64)
    direction /= max(float(np.linalg.norm(direction)), 1e-12)

    best = {"yaw": 0.0, "pitch": 0.0, "alignment": -np.inf}
    target = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    for pitch in pitch_values:
        for yaw in yaw_values:
            rotated_direction = tomo_rotation_matrix(tomo_io, float(yaw), float(pitch)) @ direction
            alignment = float(np.dot(rotated_direction, target))
            if alignment > best["alignment"]:
                best = {"yaw": float(yaw), "pitch": float(pitch), "alignment": alignment}
    return best


def grid_value_at(yaw: float, pitch: float, yaw_values: np.ndarray, pitch_values: np.ndarray, grid: np.ndarray) -> float:
    yaw_id = int(np.argmin(np.abs(yaw_values - yaw)))
    pitch_id = int(np.argmin(np.abs(pitch_values - pitch)))
    return float(grid[pitch_id, yaw_id])


def tomo_best_row(yaw_values: np.ndarray, pitch_values: np.ndarray, vss_grid: np.ndarray) -> dict[str, float]:
    flat_id = int(np.nanargmin(vss_grid.reshape(-1)))
    pitch_id, yaw_id = np.unravel_index(flat_id, vss_grid.shape)
    return {
        "yaw": float(yaw_values[yaw_id]),
        "pitch": float(pitch_values[pitch_id]),
        "vss": float(vss_grid[pitch_id, yaw_id]),
    }


def analyze_ccave(mesh_path: Path, yaw_values: np.ndarray, pitch_values: np.ndarray, vss_grid: np.ndarray, tomo_io):
    mesh = load_mesh(str(mesh_path))
    ccave = SupportFlowTensorField(mesh, mesh.convex_hull)

    rows = []
    for score, item in enumerate(ccave.eigen_analysis.support_directions, start=1):
        positive = nearest_tomo_orientation_for_direction(item.direction, yaw_values, pitch_values, tomo_io)
        positive["vss"] = grid_value_at(positive["yaw"], positive["pitch"], yaw_values, pitch_values, vss_grid)
        negative = nearest_tomo_orientation_for_direction(-item.direction, yaw_values, pitch_values, tomo_io)
        negative["vss"] = grid_value_at(negative["yaw"], negative["pitch"], yaw_values, pitch_values, vss_grid)
        best_signed = positive if positive["vss"] <= negative["vss"] else negative
        rows.append(
            {
                "score": score,
                "eigenvalue": float(item.value),
                "flow_score": float(item.value),
                "singular_values": (
                    np.asarray(item.singular_values, dtype=np.float64).tolist()
                    if item.singular_values is not None
                    else []
                ),
                "yaw": positive["yaw"],
                "pitch": positive["pitch"],
                "alignment": positive["alignment"],
                "vss": positive["vss"],
                "signed_yaw": best_signed["yaw"],
                "signed_pitch": best_signed["pitch"],
                "signed_alignment": best_signed["alignment"],
                "signed_vss": best_signed["vss"],
            }
        )
    return rows


def write_summary(rows: list[dict[str, object]], mesh_dir: Path) -> tuple[Path, Path]:
    csv_path = mesh_dir / "support_flow_tensor_field_vs_tomo_cpu_summary_1deg_60deg.csv"
    json_path = mesh_dir / "support_flow_tensor_field_vs_tomo_cpu_summary_1deg_60deg.json"

    fieldnames = [
        "mesh",
        "tomo_best_yaw",
        "tomo_best_pitch",
        "tomo_best_vss",
        "ccave_score1_yaw",
        "ccave_score1_pitch",
        "ccave_score1_vss",
        "ccave_score1_ratio",
        "ccave_score1_signed_yaw",
        "ccave_score1_signed_pitch",
        "ccave_score1_signed_vss",
        "ccave_score1_signed_ratio",
        "ccave_best_of_3_score",
        "ccave_best_of_3_yaw",
        "ccave_best_of_3_pitch",
        "ccave_best_of_3_vss",
        "ccave_best_of_3_ratio",
        "ccave_best_of_3_signed_score",
        "ccave_best_of_3_signed_yaw",
        "ccave_best_of_3_signed_pitch",
        "ccave_best_of_3_signed_vss",
        "ccave_best_of_3_signed_ratio",
        "contour_html",
        "npz",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return csv_path, json_path


def run_validation(mesh_paths: list[Path], tomo_project_root: Path) -> list[dict[str, object]]:
    summary_rows = []
    for mesh_id, mesh_path in enumerate(mesh_paths, start=1):
        start = time.perf_counter()
        print(f"\n[{mesh_id}/{len(mesh_paths)}] {mesh_path.name}", flush=True)
        tomo = compute_tomo_cpu_vss_grid(
            mesh_path,
            tomo_project_root=tomo_project_root,
            critical_angle=CRITICAL_ANGLE,
            angle_step=ANGLE_STEP,
        )
        yaw_values = tomo["yaw_values"]
        pitch_values = tomo["pitch_values"]
        vss_grid = tomo["vss_grid"]
        tomo_best = tomo_best_row(yaw_values, pitch_values, vss_grid)
        ccave_rows = analyze_ccave(mesh_path, yaw_values, pitch_values, vss_grid, tomo["tomo_io"])
        score1 = ccave_rows[0]
        best_of_3 = min(ccave_rows, key=lambda row: float(row["vss"]))
        best_of_3_signed = min(ccave_rows, key=lambda row: float(row["signed_vss"]))

        contour_path = save_vss_contour(
            mesh_path,
            yaw_values,
            pitch_values,
            vss_grid,
            tomo_best=tomo_best,
            ccave_rows=ccave_rows,
        )
        npz_path = mesh_path.with_name(f"{mesh_path.stem}_tomo_cpu_vss_grid_1deg_60deg.npz")
        np.savez_compressed(
            npz_path,
            yaw_values=yaw_values,
            pitch_values=pitch_values,
            vss_grid=vss_grid,
            ccave_rows=np.asarray(ccave_rows, dtype=object),
            tomo_best=np.asarray([tomo_best["yaw"], tomo_best["pitch"], tomo_best["vss"]], dtype=np.float64),
        )

        ratio = score1["vss"] / tomo_best["vss"] if abs(tomo_best["vss"]) > 1e-12 else np.inf
        signed_ratio = score1["signed_vss"] / tomo_best["vss"] if abs(tomo_best["vss"]) > 1e-12 else np.inf
        best_of_3_ratio = best_of_3["vss"] / tomo_best["vss"] if abs(tomo_best["vss"]) > 1e-12 else np.inf
        best_of_3_signed_ratio = (
            best_of_3_signed["signed_vss"] / tomo_best["vss"]
            if abs(tomo_best["vss"]) > 1e-12
            else np.inf
        )
        row = {
            "mesh": mesh_path.name,
            "tomo_best_yaw": tomo_best["yaw"],
            "tomo_best_pitch": tomo_best["pitch"],
            "tomo_best_vss": tomo_best["vss"],
            "ccave_score1_yaw": score1["yaw"],
            "ccave_score1_pitch": score1["pitch"],
            "ccave_score1_vss": score1["vss"],
            "ccave_score1_ratio": ratio,
            "ccave_score1_signed_yaw": score1["signed_yaw"],
            "ccave_score1_signed_pitch": score1["signed_pitch"],
            "ccave_score1_signed_vss": score1["signed_vss"],
            "ccave_score1_signed_ratio": signed_ratio,
            "ccave_best_of_3_score": best_of_3["score"],
            "ccave_best_of_3_yaw": best_of_3["yaw"],
            "ccave_best_of_3_pitch": best_of_3["pitch"],
            "ccave_best_of_3_vss": best_of_3["vss"],
            "ccave_best_of_3_ratio": best_of_3_ratio,
            "ccave_best_of_3_signed_score": best_of_3_signed["score"],
            "ccave_best_of_3_signed_yaw": best_of_3_signed["signed_yaw"],
            "ccave_best_of_3_signed_pitch": best_of_3_signed["signed_pitch"],
            "ccave_best_of_3_signed_vss": best_of_3_signed["signed_vss"],
            "ccave_best_of_3_signed_ratio": best_of_3_signed_ratio,
            "contour_html": str(contour_path),
            "npz": str(npz_path),
        }
        summary_rows.append(row)
        print(
            "  TOMO best: "
            f"yaw={tomo_best['yaw']:.1f}, pitch={tomo_best['pitch']:.1f}, v_ss={tomo_best['vss']:.6g}",
            flush=True,
        )
        print(
            "  SupportFlowTensorField score1: "
            f"yaw={score1['yaw']:.1f}, pitch={score1['pitch']:.1f}, "
            f"v_ss={score1['vss']:.6g}, ratio={ratio:.4g}",
            flush=True,
        )
        print(
            "  SupportFlowTensorField score1 +/-: "
            f"yaw={score1['signed_yaw']:.1f}, pitch={score1['signed_pitch']:.1f}, "
            f"v_ss={score1['signed_vss']:.6g}, ratio={signed_ratio:.4g}",
            flush=True,
        )
        print(f"  saved: {contour_path.name}, {npz_path.name}", flush=True)
        print(f"  elapsed: {time.perf_counter() - start:.1f} s", flush=True)

    return summary_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh-dir", type=Path, default=DEFAULT_MESH_DIR)
    parser.add_argument("--tomo-root", type=Path, default=DEFAULT_TOMO_ROOT)
    parser.add_argument("--mesh-glob", default=DEFAULT_MESH_GLOB)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mesh_paths = sorted(
        path for path in args.mesh_dir.glob(args.mesh_glob)
        if path.is_file() and path.suffix.lower() in {".ply", ".obj", ".stl"}
    )
    if not mesh_paths:
        raise FileNotFoundError(f"no target meshes found in {args.mesh_dir} with glob {args.mesh_glob}")

    summary_rows = run_validation(mesh_paths, args.tomo_root.resolve())
    csv_path, json_path = write_summary(summary_rows, args.mesh_dir)
    print(f"\nsummary csv: {csv_path}", flush=True)
    print(f"summary json: {json_path}", flush=True)


if __name__ == "__main__":
    main()
