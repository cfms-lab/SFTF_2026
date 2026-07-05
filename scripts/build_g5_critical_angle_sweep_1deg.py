"""Build the 1 degree critical-angle sweep table for representative G5 meshes.

This script only computes the TOMO_CPU grids needed by Supplementary Table S3:
eight representative meshes over theta_c = 0, 30, 45, 60, 90 degrees.  Existing
``Experimental/G5Test/tomo_cpu_cache/*_1deg_*deg.npz`` caches are reused.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cpp_src.Tomo_GPU2026.tomo_cpu import (  # noqa: E402
    compute_tomo_cpu_vss_grid,
    tomo_best_row,
)

G5_ROOT = PROJECT_ROOT / "Experimental" / "G5Test"
from _mesh_paths import G5_RAW_MESH

MESH_DIR = G5_RAW_MESH
CACHE_DIR = G5_ROOT / "tomo_cpu_cache"
OUT_DIR = PROJECT_ROOT / "Experimental" / "etc"

ANGLE_STEP = 1.0
CRITICAL_ANGLES = [0.0, 30.0, 45.0, 60.0, 90.0]
REPRESENTATIVE_MESHES = [
    ("A1", "cube", "Group_A1_cube"),
    ("B2", "hook", "Group_B2_hook"),
    ("C1", r"\emph{Bunny 69k}", "Group_C1_Bunny_69k"),
    ("C3", r"\emph{Dragon 100k}", "Group_C3_dragon_100k_1.5x"),
    ("D1", "37009", "Group_D1_37009"),
    ("D6", "37111", "Group_D6_37111"),
    ("E1", "39507", "Group_E1_39507"),
    ("E7", "61384", "Group_E7_61384"),
]
MESH_EXTENSIONS = (".stl", ".obj", ".ply", ".off", ".3mf", ".glb")


def angle_tag(angle_deg: float) -> str:
    return f"{float(angle_deg):g}".replace("-", "m").replace(".", "p")


def cache_path(stem: str, angle_deg: float) -> Path:
    return CACHE_DIR / f"{stem}_tomo_cpu_{ANGLE_STEP:g}deg_{angle_tag(angle_deg)}deg.npz"


def mesh_path_for_stem(stem: str) -> Path:
    for suffix in MESH_EXTENSIONS:
        path = MESH_DIR / f"{stem}{suffix}"
        if path.exists():
            return path
    raise FileNotFoundError(f"no mesh file found for {stem} in {MESH_DIR}")


def load_or_run_grid(stem: str, angle_deg: float) -> tuple[dict[str, np.ndarray], float | None, bool]:
    path = cache_path(stem, angle_deg)
    if path.exists():
        data = np.load(path, allow_pickle=False)
        return (
            {
                "yaw_values": np.asarray(data["yaw_values"], dtype=np.float64),
                "pitch_values": np.asarray(data["pitch_values"], dtype=np.float64),
                "vss_grid": np.asarray(data["vss_grid"], dtype=np.float64),
            },
            float(data["dll_sec"]) if "dll_sec" in data.files else None,
            True,
        )

    mesh_path = mesh_path_for_stem(stem)
    start = time.perf_counter()
    grid = compute_tomo_cpu_vss_grid(
        mesh_path,
        critical_angle=float(angle_deg),
        angle_step=ANGLE_STEP,
    )
    elapsed = time.perf_counter() - start
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        yaw_values=np.asarray(grid["yaw_values"], dtype=np.float64),
        pitch_values=np.asarray(grid["pitch_values"], dtype=np.float64),
        vss_grid=np.asarray(grid["vss_grid"], dtype=np.float64),
        dll_sec=np.float64(elapsed),
    )
    return grid, elapsed, False


def latex_number(value: float) -> str:
    rounded = int(round(float(value)))
    text = f"{abs(rounded):,}".replace(",", "{,}")
    return f"$-{text}$" if rounded < 0 else text


def write_outputs(rows: list[dict[str, object]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "g5_critical_angle_sweep_1deg.csv"
    json_path = OUT_DIR / "g5_critical_angle_sweep_1deg.json"
    tex_path = OUT_DIR / "g5_critical_angle_sweep_1deg.tex"

    csv_fields = ["id", "mesh", "stem"]
    for angle in CRITICAL_ANGLES:
        tag = f"theta_{angle_tag(angle)}"
        csv_fields.extend([f"{tag}_vss", f"{tag}_yaw", f"{tag}_pitch", f"{tag}_cached", f"{tag}_dll_sec"])
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in csv_fields})

    json_path.write_text(
        json.dumps(
            {
                "angle_step_deg": ANGLE_STEP,
                "critical_angles_deg": CRITICAL_ANGLES,
                "rows": rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    lines = [
        r"\begin{table}[H]",
        r"\footnotesize",
        r"\centering",
        r"\caption{TOMO\_CPU global minimum $v_{ss}$ by critical angle (representative meshes, $1^\circ$ grid).",
        r"The support volume decreases monotonically as $\theta_c$ increases.",
        r"In the region of large $\theta_c$, almost all faces become self-supporting and support is essentially unnecessary,",
        r"in which case the numerical residual of the MSST decomposition $V_{ss}=V_{tc}-V_o-V_{nv}$ can make $v_{ss}$ appear as a small negative number (effectively $0$).}",
        r"\label{stab:critangle}",
        r"\begin{tabular}{llrrrrr}",
        r"\toprule",
        r"ID & Mesh & $\theta_c{=}0^\circ$ & $30^\circ$ & $45^\circ$ & $60^\circ$ & $90^\circ$\\",
        r"\midrule",
    ]
    for row in rows:
        values = []
        for angle in CRITICAL_ANGLES:
            values.append(latex_number(float(row[f"theta_{angle_tag(angle)}_vss"])))
        lines.append(f"{row['id']} & {row['mesh']} & " + " & ".join(values) + r"\\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
    )
    tex_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"saved: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"saved: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"saved: {tex_path.relative_to(PROJECT_ROOT)}")


def main() -> None:
    rows: list[dict[str, object]] = []
    total = len(REPRESENTATIVE_MESHES) * len(CRITICAL_ANGLES)
    done = 0
    for mesh_id, label, stem in REPRESENTATIVE_MESHES:
        row: dict[str, object] = {"id": mesh_id, "mesh": label, "stem": stem}
        for angle in CRITICAL_ANGLES:
            done += 1
            path = cache_path(stem, angle)
            status = "cached" if path.exists() else "compute"
            print(f"[{done}/{total}] {stem} theta={angle:g} ({status})", flush=True)
            grid, dll_sec, cached = load_or_run_grid(stem, angle)
            yaw_values = np.asarray(grid["yaw_values"], dtype=np.float64)
            pitch_values = np.asarray(grid["pitch_values"], dtype=np.float64)
            vss_grid = np.asarray(grid["vss_grid"], dtype=np.float64)
            best = tomo_best_row(yaw_values, pitch_values, vss_grid)
            tag = f"theta_{angle_tag(angle)}"
            row[f"{tag}_vss"] = float(best["vss"])
            row[f"{tag}_yaw"] = float(best["yaw"])
            row[f"{tag}_pitch"] = float(best["pitch"])
            row[f"{tag}_cached"] = bool(cached)
            row[f"{tag}_dll_sec"] = dll_sec
            print(
                f"  best vss={float(best['vss']):.6g} "
                f"yaw={float(best['yaw']):.1f} pitch={float(best['pitch']):.1f} "
                f"dll_sec={dll_sec if dll_sec is not None else float('nan'):.2f} "
                f"{'(cached)' if cached else ''}",
                flush=True,
            )
        rows.append(row)
    write_outputs(rows)


if __name__ == "__main__":
    main()
