from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "obsolete"))
TOMO_ROOT = ROOT / "cpp_src" / "Tomo_GPU2026"
MESH_DIR = ROOT / "Experimental" / "etc"

from python_src.tse6_config import (
    COOLWARM_COLORSCALE,
    compute_v_ss,
    find_v_ss_extreme_orientations,
    make_tse6_config,
    print_array,
)
from python_src.VisFacePair import VisFacePair


OUT_DIR = ROOT / "comparison_outputs"
OUT_BASE = OUT_DIR / "bunny1k_vss_trend_cpu_vs_tse6_10deg_coarse_false"
CPU_ORIGINAL_PLY = MESH_DIR / "Bunny_1k.ply"
CPU_REFERENCE_BY_STEP = {
    1.0: OUT_DIR / "Bunny_1k_tomo_cpu_vss_1deg_theta60.npz",
    5.0: OUT_DIR / "Bunny_1k_tomo_cpu_vss_5deg_theta60.npz",
    10.0: OUT_DIR / "Bunny_1k_tomo_cpu_vss_10deg_theta60.npz",
}
DEFAULT_FBO_VOXEL_SIZE = 64
CPU_COMP_KEYS = {
    "v_tc": ("cpu_vtc", "v_tc", "vtc"),
    "v_o": ("cpu_vo", "v_o", "vo"),
    "v_nv": ("cpu_vnv", "v_nv", "vnv"),
}


def normalize_grid(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(values)
    if not np.any(finite):
        raise ValueError("cannot normalize a grid with no finite values")
    lo = float(np.nanmin(values[finite]))
    hi = float(np.nanmax(values[finite]))
    if np.isclose(hi, lo):
        return np.zeros_like(values, dtype=np.float64)
    return (values - lo) / (hi - lo)


def overlap_fraction(a: np.ndarray, b: np.ndarray, fraction: float, *, smallest: bool) -> float:
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    b = np.asarray(b, dtype=np.float64).reshape(-1)
    finite = np.isfinite(a) & np.isfinite(b)
    ids = np.flatnonzero(finite)
    if ids.size == 0:
        return float("nan")

    count = max(int(round(ids.size * fraction)), 1)
    a_order = np.argsort(a[ids], kind="stable")
    b_order = np.argsort(b[ids], kind="stable")
    if not smallest:
        a_order = a_order[::-1]
        b_order = b_order[::-1]
    a_set = set(ids[a_order[:count]])
    b_set = set(ids[b_order[:count]])
    return len(a_set & b_set) / count


def top_k_overlap(a: np.ndarray, b: np.ndarray, k: int, *, smallest: bool = True) -> float:
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    b = np.asarray(b, dtype=np.float64).reshape(-1)
    finite = np.isfinite(a) & np.isfinite(b)
    ids = np.flatnonzero(finite)
    if ids.size == 0:
        return float("nan")

    k = max(min(int(k), ids.size), 1)
    a_order = np.argsort(a[ids], kind="stable")
    b_order = np.argsort(b[ids], kind="stable")
    if not smallest:
        a_order = a_order[::-1]
        b_order = b_order[::-1]
    return len(set(ids[a_order[:k]]) & set(ids[b_order[:k]])) / k


def optimal_row(yaw: np.ndarray, pitch: np.ndarray, values: np.ndarray, *, smallest: bool = True) -> dict[str, float]:
    values = np.asarray(values, dtype=np.float64)
    flat = values.reshape(-1)
    flat_id = int(np.nanargmin(flat) if smallest else np.nanargmax(flat))
    pitch_id, yaw_id = np.unravel_index(flat_id, values.shape)
    return {
        "yaw": float(yaw[yaw_id]),
        "pitch": float(pitch[pitch_id]),
        "value": float(values[pitch_id, yaw_id]),
    }


def optional_cpu_component(reference: np.lib.npyio.NpzFile, logical_key: str) -> np.ndarray | None:
    for key in CPU_COMP_KEYS[logical_key]:
        if key in reference.files:
            return np.asarray(reference[key], dtype=np.float64)
    return None


def step_label(angle_step: float) -> str:
    if float(angle_step).is_integer():
        return f"{int(angle_step)}deg"
    return f"{str(float(angle_step)).replace('.', 'p')}deg"


def sanitize_label(label: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", label.strip())
    clean = clean.strip("._-")
    return clean or "mesh"


def mesh_label_from_path(mesh_path: Path) -> str:
    return sanitize_label(mesh_path.stem)


def default_out_base(angle_step: float, mesh_label: str = "Bunny_1k") -> Path:
    if mesh_label == "Bunny_1k" and np.isclose(float(angle_step), 10.0):
        return OUT_BASE
    return OUT_DIR / f"{sanitize_label(mesh_label)}_vss_trend_cpu_vs_tse6_{step_label(angle_step)}_coarse_false"


def default_reference(angle_step: float) -> Path:
    for step, path in CPU_REFERENCE_BY_STEP.items():
        if np.isclose(float(angle_step), step):
            return path
    return OUT_DIR / f"Bunny_1k_tomo_cpu_vss_{step_label(angle_step)}_theta60.npz"


def cpu_reference_for_mesh(mesh_label: str, angle_step: float) -> Path:
    return OUT_DIR / f"{sanitize_label(mesh_label)}_tomo_cpu_vss_{step_label(angle_step)}_theta60.npz"


def gpu_python_executable() -> Path:
    return Path(sys.executable)


def write_tomo_cpu_reference(mesh_path: Path, mesh_label: str, angle_step: float) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reference_path = cpu_reference_for_mesh(mesh_label, angle_step)
    code = r"""
from pathlib import Path
import sys
import numpy as np

mesh_path = Path(sys.argv[1]).resolve()
angle_step = float(sys.argv[2])
out_path = Path(sys.argv[3]).resolve()

from cpp_src.Tomo_GPU2026.tomo_shell_cpp import TomoShellCpp
from cpp_src.Tomo_GPU2026.tomo_shell_io import enumBedType, toDegree, toRadian

tomo = TomoShellCpp((str(mesh_path), 0, 0, 0), angle_step, bVerbose=False)
tomo.wall_thickness = 0.8
tomo.PLA_density = 0.00121
tomo.Fclad = 1.0
tomo.Fcore = 0.15
tomo.Fss = 0.2
tomo.Css = 1.0
tomo.dVoxel = 1.0
tomo.nVoxel = 256
tomo.theta_c = toRadian(60.0)
tomo.bUseExplicitSS = False
tomo.BedType = (enumBedType.ebtRaft, 0, 2, 0.3 + 0.27 + 2 * 0.2)
tomo.Run(cpp_function_name="TomoSh_INT3")

shape = (tomo.nYPR_Intervals, tomo.nYPR_Intervals)
np.savez_compressed(
    out_path,
    yaw=np.asarray(toDegree(tomo.yaw_range), dtype=np.float64),
    pitch=np.asarray(toDegree(tomo.pitch_range), dtype=np.float64),
    cpu_vss=np.asarray(tomo.Mtotal3D, dtype=np.float64).reshape(shape),
    cpu_mo=np.asarray(tomo.Mo3D, dtype=np.float64).reshape(shape),
    cpu_mss=np.asarray(tomo.Mss3D, dtype=np.float64).reshape(shape),
    cpu_vtc=np.asarray(tomo.Vtc, dtype=np.float64).reshape(shape),
    mesh_path=str(mesh_path),
    angle_step=angle_step,
    critical_angle_deg=60.0,
    n_voxel=int(tomo.nVoxel),
    source="Tomo_GPU2026:TOMO_CPU",
)
print(f"wrote: {out_path}")
"""
    completed = subprocess.run(
        [str(gpu_python_executable()), "-c", code, str(mesh_path), str(angle_step), str(reference_path)],
        cwd=str(ROOT),
        check=True,
        text=True,
        capture_output=True,
    )
    if completed.stdout:
        print(completed.stdout.strip())
    if completed.stderr:
        print(completed.stderr.strip(), file=sys.stderr)
    return reference_path


def reference_matches_mesh(reference: np.lib.npyio.NpzFile, mesh_path: Path) -> bool | None:
    if "mesh_path" not in reference.files:
        return None
    saved = Path(str(reference["mesh_path"])).resolve()
    return saved == mesh_path.resolve()


def load_or_compute_cpu_vss(
    reference_path: Path | None,
    mesh_path: Path,
    mesh_label: str,
    angle_step: float,
) -> tuple[np.lib.npyio.NpzFile, np.ndarray, Path]:
    if reference_path is None:
        reference_path = write_tomo_cpu_reference(mesh_path, mesh_label, angle_step)
    reference, cpu_vss = load_cpu_vss(reference_path)
    matches = reference_matches_mesh(reference, mesh_path)
    if matches is False:
        saved = str(reference["mesh_path"])
        raise ValueError(f"CPU reference mesh mismatch: reference has {saved!r}, requested {str(mesh_path)!r}")
    return reference, cpu_vss, reference_path


def load_cpu_vss(reference_path: Path) -> tuple[np.lib.npyio.NpzFile, np.ndarray]:
    reference = np.load(reference_path)
    if "cpu_vss" in reference.files:
        return reference, np.asarray(reference["cpu_vss"], dtype=np.float64)
    if "vss" in reference.files:
        return reference, np.asarray(reference["vss"], dtype=np.float64)
    if "vss_grid" in reference.files:
        return reference, np.asarray(reference["vss_grid"], dtype=np.float64)
    raise KeyError(f"{reference_path} does not contain 'cpu_vss', 'vss', or 'vss_grid'.")


def add_extreme_markers(
    fig: go.Figure,
    yaw: np.ndarray,
    pitch: np.ndarray,
    values: np.ndarray,
    *,
    row: int,
    col: int,
    prefix: str,
    value_label: str,
) -> None:
    min_rows, max_rows = find_v_ss_extreme_orientations(
        np.asarray(values, dtype=np.float64),
        np.asarray(yaw, dtype=np.float64),
        np.asarray(pitch, dtype=np.float64),
        count=3,
    )
    fig.add_trace(
        go.Scatter(
            x=[item["yaw"] for item in min_rows],
            y=[item["pitch"] for item in min_rows],
            mode="markers+text",
            name=f"{prefix} optimals",
            text=[f"o{rank}" for rank in range(1, len(min_rows) + 1)],
            textposition="top center",
            marker=dict(symbol="circle", size=12, color="#1874d1", line=dict(color="#ffffff", width=2)),
            customdata=[item["value"] for item in min_rows],
            hovertemplate=(
                f"{prefix} optimal %{{text}}<br>"
                "yaw=%{x:.1f}<br>pitch=%{y:.1f}<br>"
                f"{value_label}=%{{customdata:.6g}}<extra></extra>"
            ),
        ),
        row=row,
        col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=[item["yaw"] for item in max_rows],
            y=[item["pitch"] for item in max_rows],
            mode="markers+text",
            name=f"{prefix} worsts",
            text=[f"w{rank}" for rank in range(1, len(max_rows) + 1)],
            textposition="bottom center",
            marker=dict(symbol="x", size=14, color="#d9472b", line=dict(color="#ffffff", width=2)),
            customdata=[item["value"] for item in max_rows],
            hovertemplate=(
                f"{prefix} worst %{{text}}<br>"
                "yaw=%{x:.1f}<br>pitch=%{y:.1f}<br>"
                f"{value_label}=%{{customdata:.6g}}<extra></extra>"
            ),
        ),
        row=row,
        col=col,
    )


def build_comparison_figure(
    yaw: np.ndarray,
    pitch: np.ndarray,
    cpu_vss: np.ndarray,
    tse_vss: np.ndarray,
    cpu_norm: np.ndarray,
    tse_norm: np.ndarray,
    *,
    angle_step: float = 10.0,
    mesh_label: str = "Bunny_1k",
) -> tuple[go.Figure, dict[str, float]]:
    diff = tse_norm - cpu_norm
    finite = np.isfinite(cpu_norm) & np.isfinite(tse_norm)
    rmse = float(np.sqrt(np.mean(diff[finite] ** 2)))
    pearson = float(pearsonr(cpu_norm[finite].reshape(-1), tse_norm[finite].reshape(-1)).statistic)
    spearman = float(spearmanr(cpu_norm[finite].reshape(-1), tse_norm[finite].reshape(-1)).statistic)
    bottom10 = overlap_fraction(cpu_norm, tse_norm, 0.10, smallest=True)
    top10 = overlap_fraction(cpu_norm, tse_norm, 0.10, smallest=False)
    opt_cpu = optimal_row(yaw, pitch, cpu_vss)
    opt_tse = optimal_row(yaw, pitch, tse_vss)

    fig = make_subplots(
        rows=2,
        cols=2,
        horizontal_spacing=0.08,
        vertical_spacing=0.12,
        subplot_titles=[
            "TOMO_CPU Vss normalized",
            "TSE6 Vss normalized",
            "Normalized difference: TSE6 - CPU",
            f"Scatter, Pearson={pearson:.3f}, Spearman={spearman:.3f}",
        ],
    )
    fig.add_trace(
        go.Contour(x=yaw, y=pitch, z=cpu_norm, colorscale=COOLWARM_COLORSCALE, colorbar=dict(title="CPU")),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Contour(x=yaw, y=pitch, z=tse_norm, colorscale=COOLWARM_COLORSCALE, colorbar=dict(title="TSE6")),
        row=1,
        col=2,
    )
    fig.add_trace(
        go.Contour(
            x=yaw,
            y=pitch,
            z=diff,
            colorscale=COOLWARM_COLORSCALE,
            zmid=0,
            colorbar=dict(title="TSE6-CPU"),
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scattergl(
            x=cpu_norm[finite].reshape(-1),
            y=tse_norm[finite].reshape(-1),
            mode="markers",
            marker=dict(size=4, opacity=0.55),
            showlegend=False,
        ),
        row=2,
        col=2,
    )
    fig.add_trace(
        go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color="black", dash="dash"), showlegend=False),
        row=2,
        col=2,
    )
    add_extreme_markers(fig, yaw, pitch, cpu_vss, row=1, col=1, prefix="CPU", value_label="v_ss")
    add_extreme_markers(fig, yaw, pitch, tse_vss, row=1, col=2, prefix="TSE6", value_label="v_ss")

    fig.update_xaxes(title_text="Yaw (deg)", range=[0, 360], constrain="domain", row=1, col=1)
    fig.update_yaxes(
        title_text="Pitch (deg)",
        range=[0, 360],
        scaleanchor="x",
        scaleratio=1,
        constrain="domain",
        row=1,
        col=1,
    )
    fig.update_xaxes(title_text="Yaw (deg)", range=[0, 360], constrain="domain", row=1, col=2)
    fig.update_yaxes(
        title_text="Pitch (deg)",
        range=[0, 360],
        scaleanchor="x2",
        scaleratio=1,
        constrain="domain",
        row=1,
        col=2,
    )
    fig.update_xaxes(title_text="Yaw (deg)", range=[0, 360], constrain="domain", row=2, col=1)
    fig.update_yaxes(
        title_text="Pitch (deg)",
        range=[0, 360],
        scaleanchor="x3",
        scaleratio=1,
        constrain="domain",
        row=2,
        col=1,
    )
    fig.update_xaxes(title_text="CPU normalized Vss", range=[0, 1], constrain="domain", row=2, col=2)
    fig.update_yaxes(
        title_text="TSE6 normalized Vss",
        range=[0, 1],
        scaleanchor="x4",
        scaleratio=1,
        constrain="domain",
        row=2,
        col=2,
    )
    fig.update_layout(
        title=(
            f"{mesh_label} Vss Trend Comparison, TOMO_CPU vs TSE6, {angle_step:g} deg grid<br>"
            f"normalized RMSE={rmse:.3f}, "
            f"bottom10 overlap={bottom10:.3f}, top10 overlap={top10:.3f}"
        ),
        width=1250,
        height=950,
    )
    return fig, {
        "rmse": rmse,
        "pearson": pearson,
        "spearman": spearman,
        "bottom10": bottom10,
        "top10": top10,
        "top1_overlap": top_k_overlap(cpu_norm, tse_norm, 1),
        "top5_overlap": top_k_overlap(cpu_norm, tse_norm, 5),
        "top10_rank_overlap": top_k_overlap(cpu_norm, tse_norm, 10),
        "cpu_opt_yaw": opt_cpu["yaw"],
        "cpu_opt_pitch": opt_cpu["pitch"],
        "cpu_opt_value": opt_cpu["value"],
        "tse_opt_yaw": opt_tse["yaw"],
        "tse_opt_pitch": opt_tse["pitch"],
        "tse_opt_value": opt_tse["value"],
    }


def write_component_comparison_figures(
    reference: np.lib.npyio.NpzFile,
    yaw: np.ndarray,
    pitch: np.ndarray,
    components: dict[str, np.ndarray],
    *,
    out_base: Path = OUT_BASE,
    angle_step: float = 10.0,
    mesh_label: str = "Bunny_1k",
) -> list[Path]:
    written = []
    for logical_key, tse_values in components.items():
        cpu_values = optional_cpu_component(reference, logical_key)
        if cpu_values is None:
            continue
        if cpu_values.shape != tse_values.shape:
            print(f"skipping {logical_key} component comparison: CPU {cpu_values.shape} vs TSE6 {tse_values.shape}")
            continue

        cpu_norm = normalize_grid(cpu_values)
        tse_norm = normalize_grid(tse_values)
        fig, metrics = build_comparison_figure(
            yaw,
            pitch,
            cpu_values,
            tse_values,
            cpu_norm,
            tse_norm,
            angle_step=angle_step,
            mesh_label=mesh_label,
        )
        fig.update_layout(
            title=(
                f"{mesh_label} {logical_key} Component Comparison, TOMO_CPU vs TSE6, {angle_step:g} deg grid<br>"
                f"normalized RMSE={metrics['rmse']:.3f}, bottom10 overlap={metrics['bottom10']:.3f}, "
                f"top10 overlap={metrics['top10']:.3f}"
            )
        )
        out = out_base.with_name(f"{out_base.name}_{logical_key}").with_suffix(".html")
        fig.write_html(out, include_plotlyjs="cdn")
        written.append(out)
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare TOMO_CPU and TSE6 v_ss grids.")
    parser.add_argument("--angle-step", type=float, default=10.0, help="Yaw/pitch grid step in degrees.")
    parser.add_argument("--fbo-voxel-size", type=int, default=DEFAULT_FBO_VOXEL_SIZE)
    parser.add_argument(
        "--reference",
        type=Path,
        default=None,
        help="Existing CPU reference NPZ path. If omitted, TOMO_CPU is run for --mesh-path.",
    )
    parser.add_argument("--out-base", type=Path, default=None, help="Output path without suffix.")
    parser.add_argument("--mesh-path", type=Path, default=CPU_ORIGINAL_PLY, help="Mesh path used for TSE6 calculation.")
    parser.add_argument("--mesh-label", default=None, help="Label used in Plotly figure titles and default filenames.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    angle_step = float(args.angle_step)
    mesh_path = args.mesh_path.resolve()
    mesh_label = args.mesh_label if args.mesh_label is not None else mesh_label_from_path(mesh_path)
    if mesh_path == CPU_ORIGINAL_PLY and args.mesh_label is None:
        mesh_label = "Bunny_1k"
    out_base = args.out_base if args.out_base is not None else default_out_base(angle_step, mesh_label)
    reference, cpu_vss, reference_path = load_or_compute_cpu_vss(
        args.reference,
        mesh_path,
        mesh_label,
        angle_step,
    )

    config = make_tse6_config(
        renderer=None,
        mesh_path=str(mesh_path),
        angle_step=angle_step,
        critical_angle=60.0,
        fbo_voxel_size=int(args.fbo_voxel_size),
        deduplicate_orientations=True,
    )
    vis_pairs = VisFacePair(config).run()
    computed = compute_v_ss(config, vis_pairs)
    if len(computed) != 5:
        raise ValueError(f"compute_v_ss returned {len(computed)} values; expected 5")
    _f_vtc, second, third, fourth, tse_vss = computed
    sh_volumes = getattr(getattr(second, "result", None), "volumes", {})
    if sh_volumes:
        v_tc = third
        v_o = fourth
        v_nv = sh_volumes.get("V_nv")
        if v_nv is None:
            v_nv = v_tc - v_o - tse_vss
    else:
        v_tc = second
        v_o = third
        v_nv = fourth
    print_array("v_ss", tse_vss)

    yaw = np.asarray(config.angles_yaw, dtype=np.float64)
    pitch = np.asarray(config.angles_pitch, dtype=np.float64)
    if cpu_vss.shape != tse_vss.shape:
        raise ValueError(f"CPU and TSE6 grids differ: {cpu_vss.shape} vs {tse_vss.shape}")

    cpu_norm = normalize_grid(cpu_vss)
    tse_norm = normalize_grid(tse_vss)
    fig, metrics = build_comparison_figure(
        yaw,
        pitch,
        cpu_vss,
        tse_vss,
        cpu_norm,
        tse_norm,
        angle_step=angle_step,
        mesh_label=mesh_label,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out_base.with_suffix(".npz"),
        yaw=yaw,
        pitch=pitch,
        cpu_vss=cpu_vss,
        tse_vss=tse_vss,
        tse_vtc=v_tc,
        tse_vo=v_o,
        tse_vnv=v_nv,
        cpu_norm=cpu_norm,
        tse_norm=tse_norm,
        mesh_path=str(mesh_path),
        mesh_label=mesh_label,
        reference_path=str(reference_path),
        rmse=metrics["rmse"],
        pearson=metrics["pearson"],
        spearman=metrics["spearman"],
        bottom10_overlap=metrics["bottom10"],
        top10_overlap=metrics["top10"],
        top1_overlap=metrics["top1_overlap"],
        top5_overlap=metrics["top5_overlap"],
        top10_rank_overlap=metrics["top10_rank_overlap"],
        cpu_opt_yaw=metrics["cpu_opt_yaw"],
        cpu_opt_pitch=metrics["cpu_opt_pitch"],
        cpu_opt_value=metrics["cpu_opt_value"],
        tse_opt_yaw=metrics["tse_opt_yaw"],
        tse_opt_pitch=metrics["tse_opt_pitch"],
        tse_opt_value=metrics["tse_opt_value"],
    )
    fig.write_html(out_base.with_suffix(".html"), include_plotlyjs="cdn")
    component_outputs = write_component_comparison_figures(
        reference,
        yaw,
        pitch,
        {
            "v_tc": v_tc,
            "v_o": v_o,
            "v_nv": v_nv,
        },
        out_base=out_base,
        angle_step=angle_step,
        mesh_label=mesh_label,
    )
    print(f"wrote: {out_base.with_suffix('.npz')}")
    print(f"wrote: {out_base.with_suffix('.html')}")
    for output in component_outputs:
        print(f"wrote: {output}")


if __name__ == "__main__":
    main()
