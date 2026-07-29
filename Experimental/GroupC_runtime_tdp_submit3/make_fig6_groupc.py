"""Render the per-mesh Group C runtime figure that replaces main-text Figure 6.

Reads groupc_summary.json (written by run_groupc_runtime.py --summarize) and
draws a grouped log-scale bar chart: five development meshes x four measured
workloads.  Colors keep the workload hue families of the previous runtime
figure (green/red/blue/orange) but use CVD-validated steps; every bar carries
a direct value label, so identity is never color-alone.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
SUMMARY = HERE / "groupc_summary.json"
OUT_PNG = HERE / "tdp_submit3_runtime_groupc.png"

ORDER = [
    "Group_C1_Bunny_69k",
    "Group_C2_manikin",
    "Group_C3_dragon_100k_1.5x",
    "Group_C4_happy_50k_0.75x",
    "Group_C5_lucy_50k",
]
SERIES = [
    ("cura_panel_total_s", "Cura panel total", "#1f77b4"),
    ("prusa_panel_total_s", "Prusa panel total", "#e07b00"),
    ("dense_tomo_wall_s", "Dense TOMO sweep (130,321 cells)", "#a01820"),
    ("sftf_k8192_wall_s", "SFTF candidate generation", "#5fb75f"),
]


def short_faces(count: int) -> str:
    return f"{count / 1000:.0f}k faces"


def main() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    meshes = [summary["meshes"][name] for name in ORDER]
    labels = [f"{m['label']}\n({short_faces(m['face_count'])})" for m in meshes]

    fig, ax = plt.subplots(figsize=(11.1, 6.0), dpi=200)
    x = np.arange(len(meshes), dtype=float)
    width = 0.19
    for series_index, (key, label, color) in enumerate(SERIES):
        values = np.asarray([float(m[key]) for m in meshes])
        offset = (series_index - (len(SERIES) - 1) / 2.0) * (width + 0.015)
        bars = ax.bar(x + offset, values, width=width, label=label, color=color, zorder=3)
        for rect, value in zip(bars, values):
            text = f"{value:.2f}" if value < 10 else f"{value:.1f}" if value < 100 else f"{value:.0f}"
            ax.annotate(
                text,
                (rect.get_x() + rect.get_width() / 2.0, rect.get_height()),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                rotation=90,
                fontsize=9,
                color="#222222",
            )

    ax.set_yscale("log")
    ax.set_ylim(1.0, 4000.0)
    ax.set_ylabel("Wall time (s, logarithmic scale)", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12)
    ax.tick_params(axis="y", labelsize=11)
    ax.grid(axis="y", which="major", color="#dddddd", linewidth=0.8, zorder=0)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(fontsize=10.5, ncol=2, loc="lower left",
              bbox_to_anchor=(0.0, 1.01, 1.0, 0.12), frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_PNG)
    print("wrote", OUT_PNG)


if __name__ == "__main__":
    main()
