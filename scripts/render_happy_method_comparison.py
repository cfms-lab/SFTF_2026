"""Render the happy-method before/after landscape comparison.

The figure reuses the saved 1-degree TOMO_CPU landscape for happy 50k and the
stored happy-method audit CSV. It does not rerun TOMO or SFTF; it only overlays
the selected local-verification result before and after adaptive escalation.

Run:  python scripts/render_happy_method_comparison.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_PATH = (
    PROJECT_ROOT
    / "Experimental"
    / "etc"
    / "(4)happy_50k_0.75x_tomo_int3_vss_grid_1deg_60deg.npz"
)
RESULTS_PATH = PROJECT_ROOT / "Experimental" / "etc" / "sftf_happy_method_adaptive_tiered.csv"
PRIMARY_OUT_DIR = PROJECT_ROOT / "draft" / "draft_v_1_0" / "pics"
LEGACY_OUT_DIR = PROJECT_ROOT / "draft" / "pics"


def read_stage_rows() -> dict[str, dict[str, str]]:
    with RESULTS_PATH.open(newline="", encoding="utf-8") as fh:
        rows = [row for row in csv.DictReader(fh) if "happy" in row["mesh"]]
    by_stage = {row["stage"]: row for row in rows}
    required = {"base_top_k", "adaptive_final"}
    missing = sorted(required - set(by_stage))
    if missing:
        raise RuntimeError(f"missing happy-method stages: {', '.join(missing)}")
    return by_stage


def stage_point(row: dict[str, str]) -> dict[str, float]:
    return {
        "yaw": float(row["local_best_yaw"]),
        "pitch": float(row["local_best_pitch"]),
        "vss": float(row["local_best_vss"]),
        "ratio": float(row["local_best_ratio"]),
        "cells": float(row["local_cell_count"]),
        "budget": float(row["local_budget_fraction"]),
        "centers": float(row["candidate_center_count"]),
    }


def tomo_point(row: dict[str, str]) -> dict[str, float]:
    return {
        "yaw": float(row["tomo_best_yaw"]),
        "pitch": float(row["tomo_best_pitch"]),
        "vss": float(row["tomo_best_vss"]),
        "ratio": 1.0,
    }


def setup_axes(ax) -> None:
    ax.set_xlim(-8, 368)
    ax.set_ylim(-8, 368)
    ax.set_xticks(range(0, 361, 60))
    ax.set_yticks(range(0, 361, 60))
    ax.set_xlabel("yaw (deg)")
    ax.set_ylabel("pitch (deg)")
    ax.set_aspect("equal")


def draw_panel(ax, yaw, pitch, grid, tomo, selected, *, title: str, marker_color: str):
    levels = np.linspace(float(np.nanmin(grid)), float(np.nanmax(grid)), 30)
    cf = ax.contourf(yaw, pitch, grid, levels=levels, cmap="RdBu_r")
    ax.contour(yaw, pitch, grid, levels=10, colors="k", linewidths=0.25, alpha=0.35)

    ax.scatter(
        [tomo["yaw"]],
        [tomo["pitch"]],
        marker="*",
        s=330,
        color="#08306b",
        edgecolor="white",
        linewidth=1.2,
        zorder=7,
        label="TOMO optimum",
    )
    ax.scatter(
        [selected["yaw"]],
        [selected["pitch"]],
        marker="o",
        s=180,
        facecolor=marker_color,
        edgecolor="white",
        linewidth=1.4,
        zorder=8,
        label="selected orientation",
    )
    ax.annotate(
        f"selected\nr={selected['ratio']:.2f}",
        (selected["yaw"], selected["pitch"]),
        textcoords="offset points",
        xytext=(8, 8),
        fontsize=8,
        fontweight="bold",
        color=marker_color,
        zorder=9,
    )
    ax.annotate(
        "TOMO\nopt.",
        (tomo["yaw"], tomo["pitch"]),
        textcoords="offset points",
        xytext=(8, -24),
        fontsize=8,
        fontweight="bold",
        color="#08306b",
        zorder=9,
    )
    setup_axes(ax)
    ax.set_title(title)
    return cf


def render() -> Path:
    data = np.load(DATA_PATH, allow_pickle=True)
    yaw = np.asarray(data["yaw_values"], dtype=np.float64)
    pitch = np.asarray(data["pitch_values"], dtype=np.float64)
    grid = np.asarray(data["vss_grid"], dtype=np.float64)

    rows = read_stage_rows()
    base = stage_point(rows["base_top_k"])
    final = stage_point(rows["adaptive_final"])
    tomo = tomo_point(rows["base_top_k"])

    fig = plt.figure(figsize=(13.6, 5.9))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.0, 0.04], wspace=0.16)
    axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])]
    cax = fig.add_subplot(gs[0, 2])
    cf = draw_panel(
        axes[0],
        yaw,
        pitch,
        grid,
        tomo,
        base,
        title=(
            "Without happy-method: top-10 local verification\n"
            f"{int(base['cells'])} cells, {100.0 * base['budget']:.2f}% grid"
        ),
        marker_color="#b2182b",
    )
    draw_panel(
        axes[1],
        yaw,
        pitch,
        grid,
        tomo,
        final,
        title=(
            "With happy-method: adaptive escalation\n"
            f"{int(final['cells'])} cells, {100.0 * final['budget']:.2f}% grid"
        ),
        marker_color="#1a9850",
    )

    cbar = fig.colorbar(cf, cax=cax)
    cbar.set_label(r"TOMO_CPU $v_{ss}$")

    handles = [
        Line2D(
            [0],
            [0],
            marker="*",
            linestyle="None",
            markersize=14,
            markerfacecolor="#08306b",
            markeredgecolor="white",
            label="TOMO optimum",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markersize=10,
            markerfacecolor="#b2182b",
            markeredgecolor="white",
            label="base top-10 selected",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markersize=10,
            markerfacecolor="#1a9850",
            markeredgecolor="white",
            label="happy-method selected",
        ),
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=3,
        fontsize=9,
        frameon=True,
        framealpha=0.95,
        bbox_to_anchor=(0.5, 0.01),
    )
    fig.suptitle("happy 50k: local verification before and after happy-method", fontsize=13)
    fig.subplots_adjust(left=0.055, right=0.94, bottom=0.18, top=0.84)

    PRIMARY_OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = PRIMARY_OUT_DIR / "appendix_contour_happy.pdf"
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(PRIMARY_OUT_DIR / "appendix_contour_happy.svg", bbox_inches="tight")
    fig.savefig(PRIMARY_OUT_DIR / "appendix_contour_happy.png", dpi=220, bbox_inches="tight")

    LEGACY_OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(LEGACY_OUT_DIR / "Figure9.pdf", bbox_inches="tight")
    fig.savefig(LEGACY_OUT_DIR / "Figure9.svg", bbox_inches="tight")
    fig.savefig(LEGACY_OUT_DIR / "Figure9.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    return pdf_path


def main() -> None:
    out_path = render()
    print(f"wrote {out_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
