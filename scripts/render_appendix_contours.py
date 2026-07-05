"""Render static (PDF) TOMO_CPU v_ss contour figures for the appendix.

Each figure shows the saved 1-deg / 60-deg TOMO_CPU v_ss landscape
(``Experimental/etc/(N)*_tomo_int3_vss_grid_1deg_60deg.npz``) for a Group C mesh, overlaid
with four sets of three markers each so the optimal/worst orientations of both
methods can be compared directly on the same axes:

    * TOMO_CPU optimal (3 distinct low-v_ss basins of the saved grid)
    * TOMO_CPU worst   (3 distinct high-v_ss basins of the saved grid)
    * SFTF optimal (top-3 SFTF_C++ directions, ``sftf_cpp_optimal`` in the
      Group_C*.json verification record, placed at their nearest grid cell)
    * SFTF worst   (bottom-3 SFTF_C++ directions, ``sftf_cpp_worst``)

The legend is placed below the plot so it never covers the landscape. All data is
read from saved files (npz grid + verification JSON); nothing is recomputed.

Output PDFs go to draft/pics/ so they can be edited later.

Run:  python scripts/render_appendix_contours.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.plot_sftf_tomo_cpu_contours import (  # noqa: E402
    largest_basin_rows,
    nearest_tomo_grid_row,
    smallest_basin_rows,
)

EXPERIMENTAL_ROOT = PROJECT_ROOT / "Experimental"
EXPERIMENTAL_DATA_DIR = EXPERIMENTAL_ROOT / "etc"
RESULT_DIR = EXPERIMENTAL_ROOT / "G5Test"
SFTF_RESULT_DIR = RESULT_DIR / "SFTF_result"
OUT_DIR = PROJECT_ROOT / "draft" / "pics"
NPZ_SUFFIX = "_tomo_int3_vss_grid_1deg_60deg.npz"
N_MARKERS = 3

# (group index C-N, npz stem, short display name, output stem)
MESHES = [
    (1, "(1)Bunny_69k", "Bunny 69k", "bunny"),
    (2, "(2)manikin", "manikin", "manikin"),
    (3, "(3)dragon_100k_1.5x", "dragon 100k", "dragon"),
    (4, "(4)happy_50k_0.75x", "happy 50k", "happy"),
    (5, "(5)lucy_50k", "lucy 50k", "lucy"),
]

MARKER_STYLES = {
    "cpu_opt": dict(marker="*", s=300, color="#08306b", label="TOMO_CPU grid optimal"),
    "cpu_worst": dict(marker="X", s=150, color="#3f007d", label="TOMO_CPU grid worst"),
    "sftf_opt": dict(marker="o", s=130, color="#1a9850", label="SFTF-score best candidate"),
    "sftf_worst": dict(marker="D", s=110, color="#c51b8a", label="SFTF-score worst candidate"),
}


def sftf_marker_rows(json_path: Path, key: str, yaw, pitch, grid) -> list[dict]:
    record = json.loads(json_path.read_text(encoding="utf-8"))
    rows = []
    for entry in (record.get(key) or [])[:N_MARKERS]:
        direction = np.asarray(entry["direction"], dtype=np.float64)
        rows.append(nearest_tomo_grid_row(direction, yaw, pitch, grid))
    return rows


def plot_markers(ax, rows, style_key, label_prefix):
    style = dict(MARKER_STYLES[style_key])
    label = style.pop("label")
    xs = [r["yaw"] for r in rows]
    ys = [r["pitch"] for r in rows]
    ax.scatter(
        xs,
        ys,
        edgecolor="white",
        linewidth=1.1,
        zorder=6,
        label=label,
        **style,
    )
    for rank, r in enumerate(rows, start=1):
        ax.annotate(
            f"{label_prefix}{rank}",
            (r["yaw"], r["pitch"]),
            textcoords="offset points",
            xytext=(6, 5),
            fontsize=7,
            fontweight="bold",
            color=style["color"],
            zorder=7,
        )


def render(group_index: int, npz_stem: str, display_name: str, out_stem: str) -> Path:
    data = np.load(EXPERIMENTAL_DATA_DIR / f"{npz_stem}{NPZ_SUFFIX}", allow_pickle=True)
    yaw = np.asarray(data["yaw_values"], dtype=np.float64)
    pitch = np.asarray(data["pitch_values"], dtype=np.float64)
    grid = np.asarray(data["vss_grid"], dtype=np.float64)

    cpu_opt = smallest_basin_rows(grid, yaw, pitch, count=N_MARKERS)
    cpu_worst = largest_basin_rows(grid, yaw, pitch, count=N_MARKERS)

    json_path = next(SFTF_RESULT_DIR.glob(f"Group_C{group_index}_*.json"))
    sftf_opt = sftf_marker_rows(json_path, "sftf_cpp_optimal", yaw, pitch, grid)
    sftf_worst = sftf_marker_rows(json_path, "sftf_cpp_worst", yaw, pitch, grid)

    fig, ax = plt.subplots(figsize=(6.2, 5.9))
    levels = np.linspace(grid.min(), grid.max(), 30)
    cf = ax.contourf(yaw, pitch, grid, levels=levels, cmap="RdBu_r")
    ax.contour(yaw, pitch, grid, levels=10, colors="k", linewidths=0.25, alpha=0.35)
    cbar = fig.colorbar(cf, ax=ax, shrink=0.92, pad=0.02)
    cbar.set_label(r"$v_{ss}$")

    plot_markers(ax, cpu_opt, "cpu_opt", "Io")
    plot_markers(ax, cpu_worst, "cpu_worst", "Iw")
    plot_markers(ax, sftf_opt, "sftf_opt", "So")
    plot_markers(ax, sftf_worst, "sftf_worst", "Sw")

    ax.set_xlim(0, 360)
    ax.set_ylim(0, 360)
    ax.set_xticks(range(0, 361, 60))
    ax.set_yticks(range(0, 361, 60))
    ax.set_xlabel("yaw (deg)")
    ax.set_ylabel("pitch (deg)")
    ax.set_aspect("equal")
    ax.set_title(f"{display_name}: TOMO_CPU $v_{{ss}}$ vs CPU/SFTF optimal & worst")
    # Legend below the plot so it never overlaps the landscape.
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=4,
        fontsize=9,
        frameon=True,
        framealpha=0.95,
        handletextpad=0.3,
        columnspacing=1.0,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"appendix_contour_{out_stem}.pdf"
    # PDF feeds the LaTeX \includegraphics; SVG is an editable vector copy.
    fig.savefig(out_path, bbox_inches="tight")
    fig.savefig(OUT_DIR / f"appendix_contour_{out_stem}.svg", bbox_inches="tight")
    plt.close(fig)
    return out_path


def main() -> None:
    for group_index, npz_stem, display_name, out_stem in MESHES:
        out_path = render(group_index, npz_stem, display_name, out_stem)
        print(f"wrote {out_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
