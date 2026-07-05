"""Render the combined two-panel appendix figures (Figure 7-11) for Group C.

For each Group C mesh (Bunny, manikin, dragon, happy, lucy) this builds a single
side-by-side figure:

  Left panel  : SFTF candidate cost landscape, plotted in the SAME TOMO yaw/pitch
                coordinates as the right panel (each candidate direction mapped to
                its nearest TOMO grid cell), colored by tuned score (blue = better).
  Right panel : TOMO_CPU v_ss landscape with CPU/SFTF optimal & worst markers.

Because both panels share the yaw/pitch axes and the SFTF directions are mapped
the same way, the SFTF optimal/worst markers land at the *same* position in both
panels. Both panels use aspect ratio 1 (ax.set_aspect("equal")).

Output (the copies kept in pics/ for the draft): draft/pics/Figure<N>.{pdf,svg}
where N is the LaTeX figure number (Bunny=7, manikin=8, dragon=9, happy=10,
lucy=11).

Run:  python scripts/render_groupC_combined.py
"""

from __future__ import annotations

import csv
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
from scripts.render_appendix_contours import plot_markers  # noqa: E402

EXPERIMENTAL_ROOT = PROJECT_ROOT / "Experimental"
EXPERIMENTAL_DATA_DIR = EXPERIMENTAL_ROOT / "etc"
SFTF_RESULT_DIR = EXPERIMENTAL_ROOT / "G5Test" / "SFTF_result"
OUT_DIR = PROJECT_ROOT / "draft" / "pics"
NPZ_SUFFIX = "_tomo_int3_vss_grid_1deg_60deg.npz"
N_MARKERS = 3

# (group index C-N, npz stem, display name, LaTeX figure number)
MESHES = [
    (1, "(1)Bunny_69k", "Bunny 69k", 7),
    (2, "(2)manikin", "manikin", 8),
    (3, "(3)dragon_100k_1.5x", "dragon 100k", 9),
    (4, "(4)happy_50k_0.75x", "happy 50k", 10),
    (5, "(5)lucy_50k", "lucy 50k", 11),
]


def signed_nearest_grid_row(direction, yaw, pitch, grid) -> dict:
    """Place a build *axis* at the better of its two antipodal grid cells.

    A build direction n and its reversal -n describe the same axis, so the
    main-text comparison (\\S\\ref{sec:protocol}) evaluates both and keeps the
    smaller v_ss ("signed axis" convention). We mirror that here so the figure
    markers sit at the same grid cells -- and hence the same v_ss / ratio -- as
    the tables, instead of at the raw direction's nearest cell.
    """
    direction = np.asarray(direction, dtype=np.float64)
    pos = nearest_tomo_grid_row(direction, yaw, pitch, grid)
    neg = nearest_tomo_grid_row(-direction, yaw, pitch, grid)
    return pos if pos["vss"] <= neg["vss"] else neg


def sftf_marker_rows(json_path: Path, key: str, yaw, pitch, grid) -> list[dict]:
    record = json.loads(json_path.read_text(encoding="utf-8"))
    rows = []
    for entry in (record.get(key) or [])[:N_MARKERS]:
        direction = np.asarray(entry["direction"], dtype=np.float64)
        rows.append(signed_nearest_grid_row(direction, yaw, pitch, grid))
    return rows


def load_candidates_yaw_pitch(csv_path: Path, yaw, pitch, grid):
    """Map every candidate direction to its signed-axis nearest TOMO grid cell."""
    yaws, pitches, scores = [], [], []
    with csv_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            direction = np.array(
                [float(row["dir_x"]), float(row["dir_y"]), float(row["dir_z"])],
                dtype=np.float64,
            )
            if not np.any(direction):
                continue
            cell = signed_nearest_grid_row(direction, yaw, pitch, grid)
            yaws.append(cell["yaw"])
            pitches.append(cell["pitch"])
            scores.append(float(row["tuned_score"]))
    return np.asarray(yaws), np.asarray(pitches), np.asarray(scores)


def style_axes(ax):
    # small margin so markers/labels at the yaw/pitch boundary (0 or 360) are not
    # clipped -- the boundary itself is meaningful here because of periodicity.
    margin = 12
    ax.set_xlim(-margin, 360 + margin)
    ax.set_ylim(-margin, 360 + margin)
    ax.set_xticks(range(0, 361, 60))
    ax.set_yticks(range(0, 361, 60))
    ax.set_xlabel("yaw (deg)")
    ax.set_ylabel("pitch (deg)")
    ax.set_aspect("equal")  # aspect ratio = 1


def render(group_index: int, npz_stem: str, display_name: str, fig_number: int) -> Path:
    data = np.load(EXPERIMENTAL_DATA_DIR / f"{npz_stem}{NPZ_SUFFIX}", allow_pickle=True)
    yaw = np.asarray(data["yaw_values"], dtype=np.float64)
    pitch = np.asarray(data["pitch_values"], dtype=np.float64)
    grid = np.asarray(data["vss_grid"], dtype=np.float64)

    json_path = next(SFTF_RESULT_DIR.glob(f"Group_C{group_index}_*.json"))
    csv_path = next(SFTF_RESULT_DIR.glob(f"Group_C{group_index}_*_candidates.csv"))

    cpu_opt = smallest_basin_rows(grid, yaw, pitch, count=N_MARKERS)
    cpu_worst = largest_basin_rows(grid, yaw, pitch, count=N_MARKERS)
    sftf_opt = sftf_marker_rows(json_path, "sftf_cpp_optimal", yaw, pitch, grid)
    sftf_worst = sftf_marker_rows(json_path, "sftf_cpp_worst", yaw, pitch, grid)
    cand_yaw, cand_pitch, cand_score = load_candidates_yaw_pitch(csv_path, yaw, pitch, grid)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.6, 6.1))

    # ---- LEFT: SFTF candidate cost landscape in yaw/pitch ----
    sc = axL.scatter(
        cand_yaw, cand_pitch, c=cand_score, cmap="RdBu_r", s=22, edgecolor="none", alpha=0.9
    )
    cbarL = fig.colorbar(sc, ax=axL, shrink=0.92, pad=0.02)
    cbarL.set_label("SFTF tuned score (lower = better)")
    plot_markers(axL, sftf_opt, "sftf_opt", "So")
    plot_markers(axL, sftf_worst, "sftf_worst", "Sw")
    style_axes(axL)
    axL.set_title(f"{display_name}: SFTF candidate cost landscape")

    # ---- RIGHT: TOMO_CPU v_ss landscape with all markers ----
    levels = np.linspace(grid.min(), grid.max(), 30)
    cf = axR.contourf(yaw, pitch, grid, levels=levels, cmap="RdBu_r")
    axR.contour(yaw, pitch, grid, levels=10, colors="k", linewidths=0.25, alpha=0.35)
    cbarR = fig.colorbar(cf, ax=axR, shrink=0.92, pad=0.02)
    cbarR.set_label(r"$v_{ss}$")
    plot_markers(axR, cpu_opt, "cpu_opt", "Io")
    plot_markers(axR, cpu_worst, "cpu_worst", "Iw")
    plot_markers(axR, sftf_opt, "sftf_opt", "So")
    plot_markers(axR, sftf_worst, "sftf_worst", "Sw")
    style_axes(axR)
    axR.set_title(f"{display_name}: TOMO_CPU $v_{{ss}}$ landscape")

    handles, labels = axR.get_legend_handles_labels()
    fig.legend(
        handles, labels, loc="lower center", ncol=4, fontsize=9,
        frameon=True, framealpha=0.95, bbox_to_anchor=(0.5, -0.02),
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    out_pdf = OUT_DIR / f"Figure{fig_number}.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(OUT_DIR / f"Figure{fig_number}.svg", bbox_inches="tight")
    plt.close(fig)
    return out_pdf


def main() -> None:
    for group_index, npz_stem, display_name, fig_number in MESHES:
        out_path = render(group_index, npz_stem, display_name, fig_number)
        print(f"wrote {out_path.relative_to(PROJECT_ROOT)}  ({display_name})")


if __name__ == "__main__":
    main()
