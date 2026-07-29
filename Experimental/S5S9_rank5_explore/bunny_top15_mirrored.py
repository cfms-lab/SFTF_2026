"""Verify the yaw-pitch double-cover hypothesis on Bunny 69k.

The TOMO grid parameterization maps every physical direction to TWO cells:
(yaw, pitch) and ((yaw+180) mod 360, (180-pitch) mod 360).  This script
(1) prints the physical angles between the five 'distinct' Io basins and
(2) re-renders the SFTF top-15 figure with each candidate drawn at BOTH
representations (hollow circle = mirror copy).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from explore_rank5_contours import (  # noqa: E402
    ETC, NPZ_SUFFIX, OUT, SFTF_RESULT,
    direction_from_yaw_pitch, grid_basin_rows, sftf_rank_rows,
)

data = np.load(ETC / f"(1)Bunny_69k{NPZ_SUFFIX}", allow_pickle=False)
yaw_v = np.asarray(data["yaw_values"], dtype=np.float64)
pitch_v = np.asarray(data["pitch_values"], dtype=np.float64)
grid = np.asarray(data["vss_grid"], dtype=np.float64)

io = grid_basin_rows(grid, yaw_v, pitch_v, count=5, reverse=False)
print("physical angles between Io basins (deg):")
for i in range(5):
    for j in range(i + 1, 5):
        a = float(np.degrees(np.arccos(np.clip(
            float(np.dot(io[i]["direction"], io[j]["direction"])), -1, 1))))
        print(f"  Io{i+1}-Io{j+1}: {a:6.2f}")

def mirror(yaw, pitch):
    return ((yaw + 180.0) % 360.0, (180.0 - pitch) % 360.0)

sftf_opt = sftf_rank_rows(SFTF_RESULT / "Group_C1_Bunny_69k_candidates.csv",
                          count=15, reverse=False)

fig, ax = plt.subplots(figsize=(7.4, 6.6))
levels = np.linspace(grid.min(), grid.max(), 30)
cf = ax.contourf(yaw_v, pitch_v, grid, levels=levels, cmap="RdBu_r")
ax.contour(yaw_v, pitch_v, grid, levels=10, colors="k", linewidths=0.25, alpha=0.35)
cbar = fig.colorbar(cf, ax=ax, shrink=0.92, pad=0.02)
cbar.set_label(r"$v_{ss}$")

ax.scatter([r["yaw"] for r in io], [r["pitch"] for r in io],
           marker="*", s=340, color="#08306b", edgecolor="white", linewidth=1.2,
           zorder=6, label="TOMO_CPU grid optimal (1-5)")
for rank, r in enumerate(io, start=1):
    ax.annotate(f"Io{rank}", (r["yaw"], r["pitch"]), textcoords="offset points",
                xytext=(7, 6), fontsize=8, fontweight="bold", color="#08306b", zorder=7)

xs = [r["yaw"] for r in sftf_opt]
ys = [r["pitch"] for r in sftf_opt]
ax.scatter(xs, ys, marker="o", s=150, color="#1a9850", edgecolor="white",
           linewidth=1.2, zorder=6, label="SFTF best 1-15")
mx, my = zip(*(mirror(r["yaw"], r["pitch"]) for r in sftf_opt))
ax.scatter(mx, my, marker="o", s=150, facecolor="none", edgecolor="#1a9850",
           linewidth=2.0, zorder=6, label="same candidates, mirror cell")
for rank, r in enumerate(sftf_opt, start=1):
    ax.annotate(str(rank), (r["yaw"], r["pitch"]), ha="center", va="center",
                fontsize=6.5, fontweight="bold", color="white", zorder=7)
    mxy = mirror(r["yaw"], r["pitch"])
    ax.annotate(str(rank), mxy, ha="center", va="center",
                fontsize=6.5, fontweight="bold", color="#1a9850", zorder=7)

ax.set_xlim(0, 360); ax.set_ylim(0, 360)
ax.set_xticks(range(0, 361, 60)); ax.set_yticks(range(0, 361, 60))
ax.set_xlabel("yaw (deg)"); ax.set_ylabel("pitch (deg)")
ax.set_aspect("equal")
ax.set_title("Bunny 69k: SFTF ranks 1-15 drawn at BOTH grid representations")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=3, fontsize=8.5,
          frameon=True, framealpha=0.95)
fig.savefig(OUT / "bunny_sftf_top15_mirrored.png", bbox_inches="tight", dpi=180)
print("wrote", OUT / "bunny_sftf_top15_mirrored.png")
