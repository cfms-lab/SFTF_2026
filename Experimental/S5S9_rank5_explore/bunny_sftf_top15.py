"""Bunny 69k: SFTF optimal candidates rank 1-15 on the TOMO landscape.

Only SFTF optimal markers (green circles, ranks 1-15 after the same 12-degree
basin separation used everywhere else) plus the TOMO grid optima (stars) for
reference. Output stays in this exploration folder.
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
    grid_basin_rows, sftf_rank_rows,
)

data = np.load(ETC / f"(1)Bunny_69k{NPZ_SUFFIX}", allow_pickle=False)
yaw = np.asarray(data["yaw_values"], dtype=np.float64)
pitch = np.asarray(data["pitch_values"], dtype=np.float64)
grid = np.asarray(data["vss_grid"], dtype=np.float64)

cpu_opt = grid_basin_rows(grid, yaw, pitch, count=5, reverse=False)
sftf_opt = sftf_rank_rows(SFTF_RESULT / "Group_C1_Bunny_69k_candidates.csv",
                          count=15, reverse=False)

fig, ax = plt.subplots(figsize=(7.4, 6.6))
levels = np.linspace(grid.min(), grid.max(), 30)
cf = ax.contourf(yaw, pitch, grid, levels=levels, cmap="RdBu_r")
ax.contour(yaw, pitch, grid, levels=10, colors="k", linewidths=0.25, alpha=0.35)
cbar = fig.colorbar(cf, ax=ax, shrink=0.92, pad=0.02)
cbar.set_label(r"$v_{ss}$")

ax.scatter([r["yaw"] for r in cpu_opt], [r["pitch"] for r in cpu_opt],
           marker="*", s=340, color="#08306b", edgecolor="white", linewidth=1.2,
           zorder=6, label="TOMO_CPU grid optimal (1-5)")
for rank, r in enumerate(cpu_opt, start=1):
    ax.annotate(f"Io{rank}", (r["yaw"], r["pitch"]), textcoords="offset points",
                xytext=(7, 6), fontsize=8, fontweight="bold", color="#08306b", zorder=7)

ax.scatter([r["yaw"] for r in sftf_opt], [r["pitch"] for r in sftf_opt],
           marker="o", s=150, color="#1a9850", edgecolor="white", linewidth=1.2,
           zorder=6, label="SFTF-score best candidates (1-15)")
for rank, r in enumerate(sftf_opt, start=1):
    ax.annotate(str(rank), (r["yaw"], r["pitch"]), ha="center", va="center",
                fontsize=6.5, fontweight="bold", color="white", zorder=7)

ax.set_xlim(0, 360); ax.set_ylim(0, 360)
ax.set_xticks(range(0, 361, 60)); ax.set_yticks(range(0, 361, 60))
ax.set_xlabel("yaw (deg)"); ax.set_ylabel("pitch (deg)")
ax.set_aspect("equal")
ax.set_title("Bunny 69k: TOMO_INT3 $v_{ss}$ with SFTF optimal ranks 1-15")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=2, fontsize=9,
          frameon=True, framealpha=0.95)
fig.savefig(OUT / "bunny_sftf_top15.png", bbox_inches="tight", dpi=180)
print("wrote", OUT / "bunny_sftf_top15.png")
for rank, r in enumerate(sftf_opt, start=1):
    yi = int(np.argmin(np.abs((yaw - r["yaw"] + 180.0) % 360.0 - 180.0)))
    pi = int(np.argmin(np.abs((pitch - r["pitch"] + 180.0) % 360.0 - 180.0)))
    nrr = (float(grid[pi, yi]) - grid.min()) / (grid.max() - grid.min())
    print(f"  rank {rank:2d}: yaw {r['yaw']:6.1f} pitch {r['pitch']:6.1f} "
          f"score {r['score']:8.4f} grid-NRR {nrr:.3f}")
