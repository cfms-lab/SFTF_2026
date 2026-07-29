"""Render the ESM landscape figures (S5-S9) with paper-protocol SFTF markers.

Differences from the legacy ``render_appendix_contours.py``:

1. SFTF markers come from the evaluated dimensionless v2 score (2,048
   Fibonacci directions, K=8,192; the cached sweeps written by
   ``Experimental/GroupC_runtime_tdp_submit3/run_groupc_runtime.py``), not
   from the legacy rank-tuned G5 score.
2. The yaw-pitch parameterization maps every physical direction to TWO grid
   cells: (yaw, pitch) and ((yaw+180) mod 360, (180-pitch) mod 360).  Every
   marker is therefore drawn at both equivalent cells, and the TOMO basin
   pick deduplicates by physical direction (30 deg separation) so the same
   basin is not reported twice.

Outputs overwrite the canonical copies in draft/TDP_v2.1/pics/ (PNG + PDF).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ETC = PROJECT_ROOT / "Experimental" / "etc"
V2_CACHE = PROJECT_ROOT / "Experimental" / "GroupC_runtime_tdp_submit3" / "candidates"
ANCHORS = PROJECT_ROOT / "Experimental" / "GroupC_runtime_tdp_submit3" / "groupc_sftf_anchors.json"
OUT_DIR = PROJECT_ROOT / "draft" / "TDP_v2.1" / "pics"
NPZ_SUFFIX = "_tomo_int3_vss_grid_1deg_60deg.npz"
N_MARKERS = 3
TOMO_SEP_DEG = 30.0
SFTF_SEP_DEG = 12.0

MESHES = [
    ("Group_C1_Bunny_69k", "(1)Bunny_69k", "Bunny 69k", "bunny"),
    ("Group_C2_manikin", "(2)manikin", "manikin", "manikin"),
    ("Group_C3_dragon_100k_1.5x", "(3)dragon_100k_1.5x", "dragon 100k", "dragon"),
    ("Group_C4_happy_50k_0.75x", "(4)happy_50k_0.75x", "happy 50k", "happy"),
    ("Group_C5_lucy_50k", "(5)lucy_50k", "lucy 50k", "lucy"),
]

# Shapes encode best/worst (circle/diamond); color encodes the method
# (blue family = TOMO reference, green family = SFTF score). The rank number
# is printed inside each marker.
MARKER_STYLES = {
    "cpu_opt": dict(marker="o", s=210, color="#2b6cb8", label="TOMO grid optimal"),
    "cpu_worst": dict(marker="D", s=185, color="#08306b", label="TOMO grid worst"),
    "sftf_opt": dict(marker="o", s=210, color="#2f9e57", label="SFTF best candidate"),
    "sftf_worst": dict(marker="D", s=185, color="#0e6b3c", label="SFTF worst candidate"),
}


def direction_from_yaw_pitch(yaw: float, pitch: float) -> np.ndarray:
    yr, pr = np.deg2rad(float(yaw)), np.deg2rad(float(pitch))
    d = np.array([-np.sin(pr), np.cos(pr) * np.sin(yr), np.cos(pr) * np.cos(yr)])
    return d / max(float(np.linalg.norm(d)), 1e-12)


def yaw_pitch_from_direction(direction: np.ndarray) -> tuple[float, float]:
    d = np.asarray(direction, dtype=np.float64)
    d = d / max(float(np.linalg.norm(d)), 1e-12)
    pitch = (-np.degrees(np.arcsin(np.clip(d[0], -1.0, 1.0)))) % 360.0
    yaw = np.degrees(np.arctan2(d[1], d[2])) % 360.0
    return float(yaw), float(pitch)


def mirror_cell(yaw: float, pitch: float) -> tuple[float, float]:
    return ((yaw + 180.0) % 360.0, (180.0 - pitch) % 360.0)


def tomo_basins(grid, yaw_values, pitch_values, *, count, reverse):
    """Grid extrema deduplicated by PHYSICAL direction (not yaw-pitch cell)."""
    flat = np.asarray(grid, dtype=np.float64).reshape(-1)
    order = np.argsort(flat, kind="stable")
    if reverse:
        order = order[::-1]
    min_dot = float(np.cos(np.deg2rad(TOMO_SEP_DEG)))
    selected: list[dict] = []
    for flat_id in order[: count * 800]:
        pitch_id, yaw_id = np.unravel_index(int(flat_id), grid.shape)
        yaw = float(yaw_values[yaw_id])
        pitch = float(pitch_values[pitch_id])
        d = direction_from_yaw_pitch(yaw, pitch)
        if any(float(np.dot(d, s["direction"])) >= min_dot for s in selected):
            continue
        selected.append({"yaw": yaw, "pitch": pitch, "direction": d,
                         "vss": float(flat[int(flat_id)])})
        if len(selected) >= count:
            break
    return selected


def grid_direction_vectors(yaw_deg, pitch_deg):
    yaw = np.deg2rad(np.rint(np.asarray(yaw_deg, dtype=np.float64)))[None, :]
    pitch = np.deg2rad(np.rint(np.asarray(pitch_deg, dtype=np.float64)))[:, None]
    sin_p, cos_p = np.sin(pitch), np.cos(pitch)
    sin_y, cos_y = np.sin(yaw), np.cos(yaw)
    x = np.broadcast_to(-sin_p, (len(pitch_deg), len(yaw_deg)))
    return np.stack((x, cos_p * sin_y, cos_p * cos_y), axis=-1).reshape(-1, 3)


def budget_region_mask(cache_path: Path, yaw, pitch, budget=2400):
    """Boolean (pitch, yaw) mask of the 2,400-cell verification expansion of
    the 24 NMS basins (paper pipeline), drawn at both equivalent cells."""
    cache = np.load(cache_path, allow_pickle=False)
    directions = np.asarray(cache["directions"], dtype=np.float64)
    scores = np.asarray(cache["scores_8192"], dtype=np.float64)
    order = np.lexsort((np.arange(len(scores)), scores))
    min_dot = float(np.cos(np.deg2rad(SFTF_SEP_DEG)))
    basin_ids: list[int] = []
    for idx in order:
        d = directions[int(idx)]
        if basin_ids and np.max(directions[basin_ids] @ d) > min_dot:
            continue
        basin_ids.append(int(idx))
        if len(basin_ids) >= 24:
            break
    basins = directions[basin_ids]

    all_dirs = grid_direction_vectors(yaw, pitch)
    _u, first = np.unique(np.round(all_dirs, 8), axis=0, return_index=True)
    canonical_flat = np.sort(first.astype(np.int64))
    canonical_dirs = all_dirs[canonical_flat]
    proximity = np.max(canonical_dirs @ basins.T, axis=1)
    order2 = np.lexsort((canonical_flat, -proximity))
    cells = canonical_flat[order2[:budget]]

    mask = np.zeros((len(pitch), len(yaw)), dtype=bool)
    for flat in cells:
        p, y = int(flat) // len(yaw), int(flat) % len(yaw)
        mask[p, y] = True
        my, mp = mirror_cell(float(yaw[y]), float(pitch[p]))
        mask[int(round(mp)) % len(pitch), int(round(my)) % len(yaw)] = True
    return mask


def sftf_v2_basins(cache_path: Path, *, count, reverse):
    cache = np.load(cache_path, allow_pickle=False)
    directions = np.asarray(cache["directions"], dtype=np.float64)
    scores = np.asarray(cache["scores_8192"], dtype=np.float64)
    order = np.lexsort((np.arange(len(scores)), scores))
    if reverse:
        order = order[::-1]
    min_dot = float(np.cos(np.deg2rad(SFTF_SEP_DEG)))
    selected: list[dict] = []
    for idx in order:
        d = directions[int(idx)]
        if any(float(np.dot(d, s["direction"])) >= min_dot for s in selected):
            continue
        yaw, pitch = yaw_pitch_from_direction(d)
        selected.append({"yaw": yaw, "pitch": pitch, "direction": d,
                         "score": float(scores[int(idx)])})
        if len(selected) >= count:
            break
    return selected


def plot_markers(ax, rows, style_key, label_prefix, zbase):
    """Marker sets are layered: a later set covers the rank digits of an
    earlier set where markers coincide, so overlapping cells stay readable."""
    style = dict(MARKER_STYLES[style_key])
    label = style.pop("label")
    xs, ys = [], []
    for r in rows:
        xs.append(r["yaw"]); ys.append(r["pitch"])
        mx, my = mirror_cell(r["yaw"], r["pitch"])
        xs.append(mx); ys.append(my)
    ax.scatter(xs, ys, edgecolor="white", linewidth=1.2, zorder=zbase, label=label, **style)
    for rank, r in enumerate(rows, start=1):
        for x, y in ((r["yaw"], r["pitch"]), mirror_cell(r["yaw"], r["pitch"])):
            ax.annotate(str(rank), (x, y), ha="center", va="center",
                        fontsize=7.5, fontweight="bold", color="white",
                        zorder=zbase + 0.5)


def render(name: str, npz_stem: str, display_name: str, out_stem: str) -> Path:
    data = np.load(ETC / f"{npz_stem}{NPZ_SUFFIX}", allow_pickle=False)
    yaw = np.asarray(data["yaw_values"], dtype=np.float64)
    pitch = np.asarray(data["pitch_values"], dtype=np.float64)
    grid = np.asarray(data["vss_grid"], dtype=np.float64)

    cpu_opt = tomo_basins(grid, yaw, pitch, count=N_MARKERS, reverse=False)
    cpu_worst = tomo_basins(grid, yaw, pitch, count=N_MARKERS, reverse=True)
    sftf_opt = sftf_v2_basins(V2_CACHE / f"{name}.npz", count=N_MARKERS, reverse=False)
    sftf_worst = sftf_v2_basins(V2_CACHE / f"{name}.npz", count=N_MARKERS, reverse=True)

    fig, ax = plt.subplots(figsize=(6.2, 5.9))
    levels = np.linspace(grid.min(), grid.max(), 30)
    cf = ax.contourf(yaw, pitch, grid, levels=levels, cmap="RdBu_r")
    ax.contour(yaw, pitch, grid, levels=10, colors="k", linewidths=0.25, alpha=0.35)
    cbar = fig.colorbar(cf, ax=ax, shrink=0.92, pad=0.02)
    cbar.set_label(r"$v_{ss}$")

    plot_markers(ax, cpu_opt, "cpu_opt", "Io", zbase=6)
    plot_markers(ax, cpu_worst, "cpu_worst", "Iw", zbase=7)
    plot_markers(ax, sftf_opt, "sftf_opt", "So", zbase=8)
    plot_markers(ax, sftf_worst, "sftf_worst", "Sw", zbase=9)

    # Pipeline output: the minimum-v_ss cell inside the 2,400-cell verification
    # expansion of the 24 NMS basins (paper protocol; precomputed anchors).
    anchors = json.loads(ANCHORS.read_text(encoding="utf-8"))
    flat = int(anchors[name]["sftf_v2_best_flat"])
    v_yaw = float(yaw[flat % len(yaw)])
    v_pitch = float(pitch[flat // len(yaw)])
    pts = [(v_yaw, v_pitch), mirror_cell(v_yaw, v_pitch)]
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], marker="*", s=430,
               color="#0e6b3c", edgecolor="white", linewidth=1.4, zorder=10,
               label="SFTF verified pick (2,400-cell budget)")

    ax.set_xlim(0, 360)
    ax.set_ylim(0, 360)
    ax.set_xticks(range(0, 361, 60))
    ax.set_yticks(range(0, 361, 60))
    ax.set_xlabel("yaw (deg)")
    ax.set_ylabel("pitch (deg)")
    ax.set_aspect("equal")
    ax.set_title(f"{display_name}: TOMO_INT3 $v_{{ss}}$ vs TOMO/SFTF optimal & worst")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=8.5,
              frameon=True, framealpha=0.95, handletextpad=0.3, columnspacing=0.9)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"appendix_contour_{out_stem}.png"
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    fig.savefig(OUT_DIR / f"appendix_contour_{out_stem}.pdf", bbox_inches="tight")
    plt.close(fig)
    return out_path


def main() -> None:
    for name, npz_stem, display_name, out_stem in MESHES:
        out_path = render(name, npz_stem, display_name, out_stem)
        print(f"wrote {out_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
