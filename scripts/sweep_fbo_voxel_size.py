from __future__ import annotations

from pathlib import Path
import csv
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_src.tse6_config import compute_v_ss, make_tse6_config
from python_src.VisFacePair import VisFacePair
from scripts.measure_tse6_false_compare import (
    OUT_DIR,
    default_reference,
    normalize_grid,
    optimal_row,
    top_k_overlap,
    overlap_fraction,
)


CPU_ORIGINAL_PLY = ROOT / "Experimental" / "etc" / "Bunny_1k.ply"
FBO_VOXEL_SIZES = (64, 128, 256)


def load_cpu_reference() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    reference = np.load(default_reference(10.0))
    return (
        np.asarray(reference["yaw"], dtype=np.float64),
        np.asarray(reference["pitch"], dtype=np.float64),
        np.asarray(reference["cpu_vss"], dtype=np.float64),
    )


def pearson_spearman(cpu_norm: np.ndarray, tse_norm: np.ndarray) -> tuple[float, float]:
    from scipy.stats import pearsonr, spearmanr

    finite = np.isfinite(cpu_norm) & np.isfinite(tse_norm)
    return (
        float(pearsonr(cpu_norm[finite].reshape(-1), tse_norm[finite].reshape(-1)).statistic),
        float(spearmanr(cpu_norm[finite].reshape(-1), tse_norm[finite].reshape(-1)).statistic),
    )


def run_one(fbo_voxel_size: int, cpu_vss: np.ndarray) -> dict[str, float | int]:
    config = make_tse6_config(
        renderer=None,
        mesh_path=str(CPU_ORIGINAL_PLY),
        angle_step=10.0,
        critical_angle=60.0,
        fbo_voxel_size=fbo_voxel_size,
        deduplicate_orientations=True,
    )
    start = time.perf_counter()
    vis_pairs = VisFacePair(config).run()
    _f_vtc, _sh_tensor, _v_tc, _v_o, tse_vss = compute_v_ss(config, vis_pairs)
    elapsed = time.perf_counter() - start

    yaw = np.asarray(config.angles_yaw, dtype=np.float64)
    pitch = np.asarray(config.angles_pitch, dtype=np.float64)
    cpu_norm = normalize_grid(cpu_vss)
    tse_norm = normalize_grid(tse_vss)
    diff = tse_norm - cpu_norm
    finite = np.isfinite(cpu_norm) & np.isfinite(tse_norm)
    pearson, spearman = pearson_spearman(cpu_norm, tse_norm)
    cpu_opt = optimal_row(yaw, pitch, cpu_vss)
    tse_opt = optimal_row(yaw, pitch, tse_vss)

    return {
        "fbo_voxel_size": int(fbo_voxel_size),
        "elapsed_sec": float(elapsed),
        "rmse": float(np.sqrt(np.mean(diff[finite] ** 2))),
        "pearson": pearson,
        "spearman": spearman,
        "bottom10_overlap": overlap_fraction(cpu_norm, tse_norm, 0.10, smallest=True),
        "top10_overlap": overlap_fraction(cpu_norm, tse_norm, 0.10, smallest=False),
        "top1_overlap": top_k_overlap(cpu_norm, tse_norm, 1),
        "top5_overlap": top_k_overlap(cpu_norm, tse_norm, 5),
        "top10_rank_overlap": top_k_overlap(cpu_norm, tse_norm, 10),
        "cpu_opt_yaw": cpu_opt["yaw"],
        "cpu_opt_pitch": cpu_opt["pitch"],
        "tse_opt_yaw": tse_opt["yaw"],
        "tse_opt_pitch": tse_opt["pitch"],
        "tse_min": float(np.nanmin(tse_vss)),
        "tse_max": float(np.nanmax(tse_vss)),
        "tse_mean": float(np.nanmean(tse_vss)),
    }


def choose_best(rows: list[dict[str, float | int]]) -> dict[str, float | int]:
    return max(
        rows,
        key=lambda row: (
            float(row["top10_rank_overlap"]),
            float(row["bottom10_overlap"]),
            float(row["spearman"]),
            -float(row["rmse"]),
        ),
    )


def write_outputs(rows: list[dict[str, float | int]], best: dict[str, float | int]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "fbo_voxel_sweep_cpu_ply.csv"
    md_path = OUT_DIR / "fbo_voxel_sweep_cpu_ply.md"
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# FBO Voxel Size Sweep, CPU Original PLY",
        "",
        f"Mesh: `{CPU_ORIGINAL_PLY}`",
        "Angle grid: `10 deg`",
        "Critical angle: `45 deg`",
        "",
        "| fbo | CPU opt | TSE6 opt | top10 rank | bottom10 | Spearman | RMSE | elapsed s |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {fbo_voxel_size} | ({cpu_opt_yaw:.1f}, {cpu_opt_pitch:.1f}) | "
            "({tse_opt_yaw:.1f}, {tse_opt_pitch:.1f}) | {top10_rank_overlap:.3f} | "
            "{bottom10_overlap:.3f} | {spearman:.3f} | {rmse:.3f} | {elapsed_sec:.2f} |".format(**row)
        )
    lines.extend(
        [
            "",
            "Best selection rule: maximize top10 rank overlap, then bottom10 overlap, then Spearman, then minimize RMSE.",
            "",
            f"Selected default `fbo_voxel_size`: `{int(best['fbo_voxel_size'])}`",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote: {csv_path}")
    print(f"wrote: {md_path}")


def main() -> None:
    if not CPU_ORIGINAL_PLY.exists():
        raise FileNotFoundError(f"CPU original PLY not found: {CPU_ORIGINAL_PLY}")
    _yaw, _pitch, cpu_vss = load_cpu_reference()
    rows = [run_one(size, cpu_vss) for size in FBO_VOXEL_SIZES]
    best = choose_best(rows)
    write_outputs(rows, best)
    print(f"BEST_FBO_VOXEL_SIZE={int(best['fbo_voxel_size'])}")


if __name__ == "__main__":
    main()
