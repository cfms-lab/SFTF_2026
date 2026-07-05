"""Unified method comparison table for the SFTF paper.

Puts every orientation method on the same footing: best-of-3 signed support
volume ratio against the TOMO_CPU global optimum (lower is better), using the
saved 1-deg grids (no GPU). Methods:

  * PCA            -- principal axes of the area-weighted face-center covariance
  * SupportTensor  -- eigenvectors of M = sum A_i m_i m_i^T (paper section 2)
  * SFTF-untuned   -- candidates ranked by the raw objective J(n)
  * SFTF-tuned*    -- rank tuning, evaluated HONESTLY by leave-one-mesh-out CV
  * oracle         -- best candidate actually present in the SFTF pool (ceiling)

The SFTF-tuned column is the cross-validated number, NOT the in-sample
calibrated number, so it is a fair generalization estimate. happy is excluded
by default (candidate-generation limited); pass --include-happy to keep it.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField.support_flow_tensor_field import load_mesh  # noqa: E402
from scripts.cross_validate_sftf_tuning import (  # noqa: E402
    HAPPY_NAME,
    RIDGE_ALPHA,
    build_mesh_record,
    ratio_for_weights,
    ridge_fit,
)
from scripts.regenerate_sftf_vs_saved_tomo_summary import (  # noqa: E402
    GRID_SUFFIX,
    MESH_DIR,
    _resolve_mesh_path,
    _signed_orientation,
)


def _axis_best_ratio(axes: np.ndarray, yaw, pitch, grid, tomo_best_vss: float) -> float:
    """Smallest signed v_ss over a small set of candidate axes / TOMO optimum."""
    vsss = [_signed_orientation(ax, yaw, pitch, grid)[1]["vss"] for ax in axes]
    return float(np.min(vsss)) / tomo_best_vss if abs(tomo_best_vss) > 1e-12 else float("inf")


def _pca_axes(mesh) -> np.ndarray:
    centers = np.asarray(mesh.triangles_center, dtype=np.float64)
    areas = np.asarray(mesh.area_faces, dtype=np.float64)
    valid = np.isfinite(areas) & (areas > 0.0) & np.all(np.isfinite(centers), axis=1)
    centers, areas = centers[valid], areas[valid]
    centroid = np.average(centers, axis=0, weights=areas)
    centered = centers - centroid
    cov = np.einsum("i,ij,ik->jk", areas, centered, centered) / float(np.sum(areas))
    return np.linalg.eigh(cov)[1].T  # 3 eigenvector rows


def _support_tensor_axes(mesh) -> np.ndarray:
    normals = np.asarray(mesh.face_normals, dtype=np.float64)
    areas = np.asarray(mesh.area_faces, dtype=np.float64)
    valid = np.isfinite(areas) & (areas > 0.0) & np.all(np.isfinite(normals), axis=1)
    normals, areas = normals[valid], areas[valid]
    m = np.einsum("i,ij,ik->jk", areas, normals, normals)
    return np.linalg.eigh(m)[1].T


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-happy", action="store_true")
    parser.add_argument("--alpha", type=float, default=RIDGE_ALPHA)
    args = parser.parse_args()

    grid_paths = sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}"))
    records = []
    for grid_path in grid_paths:
        rec = build_mesh_record(grid_path)
        if not args.include_happy and rec["mesh"] == HAPPY_NAME:
            continue
        data = np.load(grid_path, allow_pickle=True)
        mesh = load_mesh(str(_resolve_mesh_path(grid_path.name[: -len(GRID_SUFFIX)])))
        rec["pca_ratio"] = _axis_best_ratio(
            _pca_axes(mesh), data["yaw_values"], data["pitch_values"], data["vss_grid"], rec["tomo_best_vss"]
        )
        rec["support_tensor_ratio"] = _axis_best_ratio(
            _support_tensor_axes(mesh), data["yaw_values"], data["pitch_values"], data["vss_grid"], rec["tomo_best_vss"]
        )
        records.append(rec)

    rows = []
    for held in records:
        train = [r for r in records if r["mesh"] != held["mesh"]]
        lomo_w = ridge_fit(train, args.alpha)
        rows.append(
            {
                "mesh": held["mesh"],
                "PCA": float(held["pca_ratio"]),
                "SupportTensor": float(held["support_tensor_ratio"]),
                "SFTF_untuned": float(held["untuned_ratio"]),
                "SFTF_tuned_LOMO": float(ratio_for_weights(held, lomo_w)),
                "SFTF_oracle": float(held["oracle_ratio"]),
            }
        )

    methods = ["PCA", "SupportTensor", "SFTF_untuned", "SFTF_tuned_LOMO", "SFTF_oracle"]
    print(f"meshes: {[r['mesh'] for r in rows]}\n")
    print("=== best-of-3 signed v_ss ratio vs TOMO optimum (lower is better) ===")
    print(f"{'mesh':<12}" + "".join(f"{m:>17}" for m in methods))
    for row in rows:
        short = row["mesh"].split(")")[-1].replace(".ply", "")[:10]
        print(f"{short:<12}" + "".join(f"{row[m]:>17.2f}" for m in methods))
    mean = {m: float(np.mean([row[m] for row in rows])) for m in methods}
    print(f"{'MEAN':<12}" + "".join(f"{mean[m]:>17.2f}" for m in methods))

    out_json = MESH_DIR / "sftf_unified_comparison.json"
    out_csv = MESH_DIR / "sftf_unified_comparison.csv"
    out_json.write_text(json.dumps({"rows": rows, "mean": mean}, indent=2, ensure_ascii=False), encoding="utf-8")
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["mesh"] + methods)
        writer.writeheader()
        writer.writerows(rows)
        writer.writerow({"mesh": "MEAN", **mean})
    print(f"\nsaved: {out_csv.name}, {out_json.name}")


if __name__ == "__main__":
    main()
