"""Exploration for the S5-S9 landscape figures (does NOT touch draft/pics).

Part 1: re-render the five Group C landscapes with rank 1-5 markers
        (instead of the current 1-3).
Part 2: extract the TOMO grids of every Group D / Group E mesh from the saved
        Plotly HTML sweeps, render the same rank-5 figure, and rank all
        meshes by how similar the TOMO and SFTF optimal/worst marker
        distributions are (mean nearest-neighbour angle on the sphere).

Outputs go to this folder only.
"""

from __future__ import annotations

import base64
import csv
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
ETC = PROJECT_ROOT / "Experimental" / "etc"
G5 = PROJECT_ROOT / "Experimental" / "G5Test"
SFTF_RESULT = G5 / "SFTF_result"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

N_MARKERS = 5
NPZ_SUFFIX = "_tomo_int3_vss_grid_1deg_60deg.npz"
GROUP_C = [
    ("Group_C1_Bunny_69k", "(1)Bunny_69k", "Bunny 69k"),
    ("Group_C2_manikin", "(2)manikin", "manikin"),
    ("Group_C3_dragon_100k_1.5x", "(3)dragon_100k_1.5x", "dragon 100k"),
    ("Group_C4_happy_50k_0.75x", "(4)happy_50k_0.75x", "happy 50k"),
    ("Group_C5_lucy_50k", "(5)lucy_50k", "lucy 50k"),
]

MARKER_STYLES = {
    "cpu_opt": dict(marker="*", s=300, color="#08306b", label="TOMO_CPU grid optimal"),
    "cpu_worst": dict(marker="X", s=150, color="#3f007d", label="TOMO_CPU grid worst"),
    "sftf_opt": dict(marker="o", s=130, color="#1a9850", label="SFTF-score best candidate"),
    "sftf_worst": dict(marker="D", s=110, color="#c51b8a", label="SFTF-score worst candidate"),
}


# ---------- geometry helpers (mirrors scripts/plot_sftf_tomo_cpu_contours.py) ----------

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


def periodic_delta(a: float, b: float) -> float:
    return abs((float(a) - float(b) + 180.0) % 360.0 - 180.0)


def yaw_pitch_distance(a: dict, b: dict) -> float:
    return float(np.hypot(periodic_delta(a["yaw"], b["yaw"]), periodic_delta(a["pitch"], b["pitch"])))


def grid_basin_rows(grid, yaw_values, pitch_values, *, count, reverse,
                    min_distance_degrees=45.0):
    flat = np.asarray(grid, dtype=np.float64).reshape(-1)
    order = np.argsort(flat, kind="stable")
    if reverse:
        order = order[::-1]
    selected: list[dict] = []
    for flat_id in order[: count * 400]:
        pitch_id, yaw_id = np.unravel_index(int(flat_id), grid.shape)
        row = {
            "yaw": float(yaw_values[yaw_id]),
            "pitch": float(pitch_values[pitch_id]),
            "vss": float(flat[int(flat_id)]),
        }
        if any(yaw_pitch_distance(row, s) < min_distance_degrees for s in selected):
            continue
        row["direction"] = direction_from_yaw_pitch(row["yaw"], row["pitch"])
        selected.append(row)
        if len(selected) >= count:
            break
    return selected


def sftf_rank_rows(candidates_csv: Path, *, count, reverse, min_angle_degrees=12.0):
    rows = []
    with candidates_csv.open("r", newline="", encoding="utf-8") as handle:
        for r in csv.DictReader(handle):
            rows.append({
                "score": float(r["tuned_score"]),
                "direction": np.array([float(r["dir_x"]), float(r["dir_y"]), float(r["dir_z"])]),
            })
    min_dot = float(np.cos(np.deg2rad(min_angle_degrees)))
    selected: list[dict] = []
    for row in sorted(rows, key=lambda x: x["score"], reverse=reverse):
        d = row["direction"] / max(float(np.linalg.norm(row["direction"])), 1e-12)
        if any(float(np.dot(d, s["direction"])) >= min_dot for s in selected):
            continue
        yaw, pitch = yaw_pitch_from_direction(d)
        selected.append({"direction": d, "score": row["score"], "yaw": yaw, "pitch": pitch})
        if len(selected) >= count:
            break
    return selected


# ---------- plotly html grid extraction ----------

def decode_bdata(bdata: str) -> np.ndarray:
    raw = bdata.encode("utf-8").decode("unicode_escape")
    return np.frombuffer(base64.b64decode(raw), dtype="<f8")


def grid_from_html(html_path: Path):
    s = html_path.read_text(encoding="utf-8", errors="replace")
    def arr(key):
        m = re.search(r'"%s":\{"dtype":"f8","bdata":"([^"]+)"(?:,"shape":"([^"]+)")?\}' % key, s)
        if not m:
            raise RuntimeError(f"{html_path.name}: no {key} array")
        a = decode_bdata(m.group(1))
        if m.group(2):
            shape = tuple(int(v) for v in m.group(2).replace(" ", "").split(","))
            a = a.reshape(shape)
        return a
    x = arr("x")
    y = arr("y")
    z = arr("z")
    if z.ndim == 1:
        z = z.reshape(len(y), len(x))
    return x, y, z


# ---------- rendering ----------

def plot_markers(ax, rows, style_key, label_prefix):
    style = dict(MARKER_STYLES[style_key])
    label = style.pop("label")
    ax.scatter([r["yaw"] for r in rows], [r["pitch"] for r in rows],
               edgecolor="white", linewidth=1.1, zorder=6, label=label, **style)
    for rank, r in enumerate(rows, start=1):
        ax.annotate(f"{label_prefix}{rank}", (r["yaw"], r["pitch"]),
                    textcoords="offset points", xytext=(6, 5), fontsize=7,
                    fontweight="bold", color=style["color"], zorder=7)


def render_landscape(yaw, pitch, grid, markers, title, out_path):
    fig, ax = plt.subplots(figsize=(6.2, 5.9))
    levels = np.linspace(grid.min(), grid.max(), 30)
    cf = ax.contourf(yaw, pitch, grid, levels=levels, cmap="RdBu_r")
    ax.contour(yaw, pitch, grid, levels=10, colors="k", linewidths=0.25, alpha=0.35)
    cbar = fig.colorbar(cf, ax=ax, shrink=0.92, pad=0.02)
    cbar.set_label(r"$v_{ss}$")
    for rows, style_key, prefix in markers:
        plot_markers(ax, rows, style_key, prefix)
    ax.set_xlim(0, 360); ax.set_ylim(0, 360)
    ax.set_xticks(range(0, 361, 60)); ax.set_yticks(range(0, 361, 60))
    ax.set_xlabel("yaw (deg)"); ax.set_ylabel("pitch (deg)")
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, fontsize=8.2,
              frameon=True, framealpha=0.95, handletextpad=0.3, columnspacing=1.0)
    fig.savefig(out_path, bbox_inches="tight", dpi=170)
    plt.close(fig)


# ---------- agreement metric ----------

def mean_nearest_angle(rows_a, rows_b) -> float:
    """Mean over rows_a of the angle (deg) to the nearest direction in rows_b."""
    angles = []
    for a in rows_a:
        dots = [float(np.dot(a["direction"], b["direction"])) for b in rows_b]
        angles.append(float(np.degrees(np.arccos(np.clip(max(dots), -1.0, 1.0)))))
    return float(np.mean(angles))


def process(name: str, display: str, yaw, pitch, grid) -> dict:
    csv_path = SFTF_RESULT / f"{name}_candidates.csv"
    cpu_opt = grid_basin_rows(grid, yaw, pitch, count=N_MARKERS, reverse=False)
    cpu_worst = grid_basin_rows(grid, yaw, pitch, count=N_MARKERS, reverse=True)
    sftf_opt = sftf_rank_rows(csv_path, count=N_MARKERS, reverse=False)
    sftf_worst = sftf_rank_rows(csv_path, count=N_MARKERS, reverse=True)

    opt_angle = mean_nearest_angle(sftf_opt, cpu_opt)
    worst_angle = mean_nearest_angle(sftf_worst, cpu_worst)
    # NRR of SFTF rank-1 on the grid (how good the single best candidate is)
    flat = grid.reshape(-1)
    gmin, gmax = float(flat.min()), float(flat.max())
    yaw0, pitch0 = sftf_opt[0]["yaw"], sftf_opt[0]["pitch"]
    yi = int(np.argmin(np.abs((yaw - yaw0 + 180.0) % 360.0 - 180.0)))
    pi = int(np.argmin(np.abs((pitch - pitch0 + 180.0) % 360.0 - 180.0)))
    nrr1 = (float(grid[pi, yi]) - gmin) / max(gmax - gmin, 1e-12)

    render_landscape(
        yaw, pitch, grid,
        [(cpu_opt, "cpu_opt", "Io"), (cpu_worst, "cpu_worst", "Iw"),
         (sftf_opt, "sftf_opt", "So"), (sftf_worst, "sftf_worst", "Sw")],
        f"{display}: TOMO_INT3 $v_{{ss}}$ vs INT3/SFTF optimal & worst (rank 1-5)",
        OUT / f"rank5_{name}.png",
    )
    return {
        "mesh": name,
        "opt_mean_angle_deg": round(opt_angle, 1),
        "worst_mean_angle_deg": round(worst_angle, 1),
        "combined_deg": round((opt_angle + worst_angle) / 2.0, 1),
        "sftf_rank1_nrr": round(nrr1, 4),
    }


def main() -> None:
    results = []
    print("== Part 1: Group C, rank 1-5 ==")
    for name, npz_stem, display in GROUP_C:
        data = np.load(ETC / f"{npz_stem}{NPZ_SUFFIX}", allow_pickle=False)
        row = process(name, display, np.asarray(data["yaw_values"]),
                      np.asarray(data["pitch_values"]), np.asarray(data["vss_grid"]))
        row["group"] = "C"
        results.append(row)
        print(" ", row)

    print("== Part 2: Groups D/E from saved HTML sweeps ==")
    for html in sorted(G5.glob("Group_[DE]*_tomo_int3.html")):
        name = html.name[: -len("_tomo_int3.html")]
        if not (SFTF_RESULT / f"{name}_candidates.csv").exists():
            print(f"  [skip] {name}: no candidates csv")
            continue
        try:
            x, y, z = grid_from_html(html)
        except Exception as exc:
            print(f"  [skip] {name}: {exc}")
            continue
        row = process(name, name, x, y, z)
        row["group"] = name.split("_")[1][0]
        results.append(row)
        print(" ", row)

    results_de = sorted([r for r in results if r["group"] in "DE"], key=lambda r: r["combined_deg"])
    print()
    print("== D/E ranked by TOMO-SFTF marker agreement (smaller = more similar) ==")
    for r in results_de:
        print(f"  {r['mesh']:28s} opt {r['opt_mean_angle_deg']:6.1f}  worst {r['worst_mean_angle_deg']:6.1f}  "
              f"combined {r['combined_deg']:6.1f}  rank1-NRR {r['sftf_rank1_nrr']:.4f}")
    (OUT / "agreement_ranking.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("written:", OUT / "agreement_ranking.json")


if __name__ == "__main__":
    main()
