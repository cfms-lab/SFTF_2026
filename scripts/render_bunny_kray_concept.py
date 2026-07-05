"""Render Bunny 69k K_ray source sampling and SFTF landscapes.

The script writes three fixed/adaptive K_ray variants into draft/pics and
draft/draft_v_1_0/pics:

    Bunny69k_kray500_concept
    Bunny69k_kray1394_concept
    Bunny69k_kray3000_concept

Run:  .venv\\Scripts\\python.exe scripts\\render_bunny_kray_concept.py
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.patches import FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python_src.SupportFlowTensorField.support_flow_tensor_field import (
    _adaptive_k_ray,
    _sample_ray_face_ids,
    _triangle_surface_data,
    evaluate_support_flow_candidate_pool,
)
from scripts.plot_sftf_tomo_cpu_contours import nearest_tomo_grid_row
from scripts._mesh_paths import G5_RAW_MESH

MESH_PATH = G5_RAW_MESH / "Group_C1_Bunny_69k.ply"
GRID_PATH = ROOT / "Experimental" / "etc" / "(1)Bunny_69k_tomo_int3_vss_grid_1deg_60deg.npz"
SUMMARY_PATH = ROOT / "Experimental" / "etc" / "bunny_69k_kray_sweep_summary.csv"
OUT_DIRS = (
    ROOT / "draft" / "pics",
    ROOT / "draft" / "draft_v_1_0" / "pics",
)

BUILD_DIRECTION = np.array([0.0, 0.0, 1.0], dtype=np.float64)
RNG_SEED = 42
BACKGROUND_COUNT = 5200
SOURCE_POOL_COUNT = 4300
RAY_ARROW_COUNT = 85


@dataclass(frozen=True)
class KrayVariant:
    key: str
    requested_k_ray: int | None
    output_stem: str
    extra_stems: tuple[str, ...] = ()


@dataclass
class KrayFigureData:
    variant: KrayVariant
    k_ray: int
    source_count: int
    selected_count: int
    selected_mesh_fraction: float
    selected_source_fraction: float
    selected_weight_fraction: float
    background_ids: np.ndarray
    source_pool_ids: np.ndarray
    selected_ids: np.ndarray
    arrow_ids: np.ndarray
    candidate_yaw: np.ndarray
    candidate_pitch: np.ndarray
    candidate_score: np.ndarray


VARIANTS = (
    KrayVariant("500", 500, "Bunny69k_kray500_concept"),
    KrayVariant("1394", None, "Bunny69k_kray1394_concept", ("Bunny69k_kray_concept",)),
    KrayVariant("3000", 3000, "Bunny69k_kray3000_concept"),
)


def choose(ids: np.ndarray, count: int, rng: np.random.Generator) -> np.ndarray:
    ids = np.asarray(ids, dtype=np.int64)
    if ids.size <= count:
        return ids
    return np.sort(rng.choice(ids, size=count, replace=False))


def tex_int(value: int) -> str:
    return f"{int(value):,}".replace(",", "{,}")


def signed_nearest_grid_row(direction, yaw, pitch, grid) -> dict:
    direction = np.asarray(direction, dtype=np.float64)
    pos = nearest_tomo_grid_row(direction, yaw, pitch, grid)
    neg = nearest_tomo_grid_row(-direction, yaw, pitch, grid)
    return pos if pos["vss"] <= neg["vss"] else neg


def style_yaw_pitch_axes(ax) -> None:
    margin = 12
    ax.set_xlim(-margin, 360 + margin)
    ax.set_ylim(-margin, 360 + margin)
    ax.set_xticks(range(0, 361, 60))
    ax.set_yticks(range(0, 361, 60))
    ax.set_xlabel("yaw (deg)")
    ax.set_ylabel("pitch (deg)")
    ax.set_aspect("equal")


def load_tomo_grid() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    grid_data = np.load(GRID_PATH, allow_pickle=True)
    return (
        np.asarray(grid_data["yaw_values"], dtype=np.float64),
        np.asarray(grid_data["pitch_values"], dtype=np.float64),
        np.asarray(grid_data["vss_grid"], dtype=np.float64),
    )


def sftf_landscape(mesh: trimesh.Trimesh, k_ray: int, yaw, pitch, grid) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pool = evaluate_support_flow_candidate_pool(mesh, k_ray=k_ray)
    rows = []
    for score, _rayleigh, _pair, _bed, _hit, direction, _flow, _singular_values in pool:
        cell = signed_nearest_grid_row(direction, yaw, pitch, grid)
        rows.append((cell["yaw"], cell["pitch"], float(score)))
    if not rows:
        return np.empty(0), np.empty(0), np.empty(0)
    values = np.asarray(rows, dtype=np.float64)
    return values[:, 0], values[:, 1], values[:, 2]


def compute_variant_data(mesh, surface_data, variant: KrayVariant, yaw, pitch, grid) -> KrayFigureData:
    face_count = len(surface_data.areas)
    k_ray = _adaptive_k_ray(face_count) if variant.requested_k_ray is None else int(variant.requested_k_ray)

    overhang = np.maximum(0.0, -(surface_data.normals @ BUILD_DIRECTION))
    weights = surface_data.areas * overhang
    valid_ids = np.flatnonzero(weights > 0.0)
    selected_ids = _sample_ray_face_ids(surface_data.areas, overhang, k_ray)

    rng = np.random.default_rng(RNG_SEED + k_ray)
    all_ids = np.arange(face_count, dtype=np.int64)
    background_ids = choose(all_ids, BACKGROUND_COUNT, rng)
    source_pool_ids = choose(valid_ids, SOURCE_POOL_COUNT, rng)
    arrow_ids = choose(selected_ids, RAY_ARROW_COUNT, rng)

    selected_weight = float(np.sum(weights[selected_ids])) if selected_ids.size else 0.0
    source_weight = float(np.sum(weights[valid_ids])) if valid_ids.size else 0.0
    candidate_yaw, candidate_pitch, candidate_score = sftf_landscape(mesh, k_ray, yaw, pitch, grid)

    return KrayFigureData(
        variant=variant,
        k_ray=k_ray,
        source_count=int(valid_ids.size),
        selected_count=int(selected_ids.size),
        selected_mesh_fraction=float(selected_ids.size / face_count) if face_count else 0.0,
        selected_source_fraction=float(selected_ids.size / valid_ids.size) if valid_ids.size else 0.0,
        selected_weight_fraction=float(selected_weight / source_weight) if source_weight > 0.0 else 0.0,
        background_ids=background_ids,
        source_pool_ids=source_pool_ids,
        selected_ids=selected_ids,
        arrow_ids=arrow_ids,
        candidate_yaw=candidate_yaw,
        candidate_pitch=candidate_pitch,
        candidate_score=candidate_score,
    )


def render_variant(mesh, surface_data, figure_data: KrayFigureData, score_vmin: float, score_vmax: float) -> list[Path]:
    centers = surface_data.centers
    x = centers[:, 0]
    z = centers[:, 2]
    z_span = float(np.ptp(z))
    arrow_len = 0.075 * z_span

    fig, (ax_mesh, ax_sftf) = plt.subplots(1, 2, figsize=(12.8, 6.1), gridspec_kw={"wspace": 0.18})

    ax_mesh.scatter(
        x[figure_data.background_ids],
        z[figure_data.background_ids],
        s=1.6,
        c="#b8c1ca",
        alpha=0.32,
        linewidths=0,
        label="mesh faces",
    )
    ax_mesh.scatter(
        x[figure_data.source_pool_ids],
        z[figure_data.source_pool_ids],
        s=2.3,
        c="#e9a94d",
        alpha=0.32,
        linewidths=0,
        label=r"$A_iO_i(n)>0$",
    )
    ax_mesh.scatter(
        x[figure_data.selected_ids],
        z[figure_data.selected_ids],
        s=5.0,
        c="#b23b2e",
        alpha=0.82,
        linewidths=0,
        label=rf"$K_{{ray}}={tex_int(figure_data.k_ray)}$",
    )
    for idx in figure_data.arrow_ids:
        start = (float(x[idx]), float(z[idx]) - 0.005 * z_span)
        end = (float(x[idx]), float(z[idx]) - arrow_len)
        ax_mesh.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=6.5,
                lw=0.55,
                color="#8f211c",
                alpha=0.40,
                zorder=4,
            )
        )

    bounds = mesh.bounds
    ax_mesh.annotate(
        "$n$",
        xy=(bounds[0, 0] - 4.5, bounds[0, 2] + 0.45 * z_span),
        xytext=(bounds[0, 0] - 4.5, bounds[0, 2] + 0.70 * z_span),
        arrowprops=dict(arrowstyle="<|-", lw=1.2, color="#333333"),
        ha="center",
        va="center",
        fontsize=14,
        color="#333333",
    )
    ax_mesh.set_title(
        rf"Bunny 69k: $K_{{ray}}={tex_int(figure_data.k_ray)}$",
        loc="left",
        fontsize=14,
        weight="bold",
    )
    ax_mesh.set_xlabel("x")
    ax_mesh.set_ylabel("z")
    ax_mesh.set_aspect("equal", adjustable="box")
    ax_mesh.grid(color="#d7dce0", lw=0.4, alpha=0.7)
    ax_mesh.legend(loc="lower right", frameon=True, framealpha=0.92, fontsize=9, markerscale=2.4)

    sc = ax_sftf.scatter(
        figure_data.candidate_yaw,
        figure_data.candidate_pitch,
        c=figure_data.candidate_score,
        cmap="RdBu_r",
        vmin=score_vmin,
        vmax=score_vmax,
        s=22,
        edgecolor="none",
        alpha=0.9,
    )
    if figure_data.candidate_score.size:
        top = np.argsort(figure_data.candidate_score)[:3]
        ax_sftf.scatter(
            figure_data.candidate_yaw[top],
            figure_data.candidate_pitch[top],
            marker="*",
            s=170,
            c="#08306b",
            edgecolor="white",
            linewidth=1.0,
            zorder=5,
            label="top-3",
        )
    cbar = fig.colorbar(sc, ax=ax_sftf, shrink=0.91, pad=0.02)
    cbar.set_label("SFTF tuned score")
    style_yaw_pitch_axes(ax_sftf)
    ax_sftf.set_title("SFTF score landscape", fontsize=13, weight="bold")
    ax_sftf.legend(loc="lower right", frameon=True, framealpha=0.92, fontsize=9)

    saved_paths: list[Path] = []
    stems = (figure_data.variant.output_stem,) + figure_data.variant.extra_stems
    for out_dir in OUT_DIRS:
        out_dir.mkdir(parents=True, exist_ok=True)
        for stem in stems:
            pdf_path = out_dir / f"{stem}.pdf"
            fig.savefig(pdf_path, bbox_inches="tight")
            fig.savefig(out_dir / f"{stem}.svg", bbox_inches="tight")
            fig.savefig(out_dir / f"{stem}.png", dpi=220, bbox_inches="tight")
            saved_paths.append(pdf_path)
    plt.close(fig)
    return saved_paths


def write_summary(rows: list[KrayFigureData]) -> None:
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "k_ray",
                "source_faces",
                "selected_faces",
                "selected_mesh_fraction",
                "selected_source_fraction",
                "selected_weight_fraction",
                "candidate_count",
                "score_min",
                "score_median",
                "score_max",
                "top3_yaw_pitch_score",
            ],
        )
        writer.writeheader()
        for row in rows:
            top = np.argsort(row.candidate_score)[:3] if row.candidate_score.size else []
            top_text = "; ".join(
                f"({row.candidate_yaw[i]:.1f},{row.candidate_pitch[i]:.1f},{row.candidate_score[i]:.6f})"
                for i in top
            )
            writer.writerow(
                {
                    "k_ray": row.k_ray,
                    "source_faces": row.source_count,
                    "selected_faces": row.selected_count,
                    "selected_mesh_fraction": f"{row.selected_mesh_fraction:.6f}",
                    "selected_source_fraction": f"{row.selected_source_fraction:.6f}",
                    "selected_weight_fraction": f"{row.selected_weight_fraction:.6f}",
                    "candidate_count": int(row.candidate_score.size),
                    "score_min": f"{float(np.min(row.candidate_score)):.6f}" if row.candidate_score.size else "",
                    "score_median": f"{float(np.median(row.candidate_score)):.6f}" if row.candidate_score.size else "",
                    "score_max": f"{float(np.max(row.candidate_score)):.6f}" if row.candidate_score.size else "",
                    "top3_yaw_pitch_score": top_text,
                }
            )


def main() -> None:
    mesh = trimesh.load_mesh(MESH_PATH, process=False)
    surface_data = _triangle_surface_data(mesh)
    yaw, pitch, grid = load_tomo_grid()

    figure_rows = [compute_variant_data(mesh, surface_data, variant, yaw, pitch, grid) for variant in VARIANTS]
    score_values = np.concatenate([row.candidate_score for row in figure_rows if row.candidate_score.size])
    score_vmin = float(np.min(score_values))
    score_vmax = float(np.max(score_values))

    saved_paths: list[Path] = []
    for figure_data in figure_rows:
        saved_paths.extend(render_variant(mesh, surface_data, figure_data, score_vmin, score_vmax))
    write_summary(figure_rows)

    for path in saved_paths:
        if path.parent == OUT_DIRS[0]:
            print(path.relative_to(ROOT))
    print(SUMMARY_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
