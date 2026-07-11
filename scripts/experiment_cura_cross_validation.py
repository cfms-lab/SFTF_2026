"""Two-direction real-slicer cross-check of the TOMO screening proxy.

This limited experiment does not validate global ranking.  It slices with the
legacy CuraEngine 15.04.6 with the translated DP103 PLA profile (support angle
60 degrees, support placement everywhere, lines pattern), two directions per
organic mesh:

  * the direction chosen by the deployed pipeline (routed branch local-window
    best: SFTF branch for meshes the router sends to SFTF, uniform-axis branch
    for the two held-out meshes it routes to uniform), and
  * the TOMO global-optimum direction from the cached 1 degree / 60 degree grid,

and compares the measured support-only extrusion-volume ratio against the
TOMO-predicted v_ss ratio.  The multi-direction ranking experiment in
``experiment_cura_multidirection_validation.py`` is the stronger validation.
Uses the _Cura_CLI pipeline and its high-water-mark G-code parser.

Every mesh is uniformly pre-scaled to a 140 mm bounding-sphere diameter so
any orientation fits the DP103 build volume; support-volume ratios between
two orientations of the same mesh are invariant to this uniform scaling.

Runtime: 8 meshes x 2 directions, one CuraEngine call each (~seconds/slice).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURA_CLI_SRC = PROJECT_ROOT.parent / "_Cura_CLI" / "python" / "src"
for p in (str(PROJECT_ROOT), str(CURA_CLI_SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    SUPPORT_FLOW_COARSE_DIRECTION_COUNT,
    _spherical_sample_directions,
)
from scripts.experiment_budget_matched_local_baselines import (  # noqa: E402
    _centers_from_directions,
    _evaluate_window_order,
    _farthest_axis_order,
    _precompute_windows,
    _unique_axis_directions,
)
from scripts.experiment_happy_method_g5_audit import (  # noqa: E402
    _read_candidate_csv,
    _ranked_centers,
    _local_window_result,
)
from scripts.regenerate_sftf_vs_saved_tomo_summary import _tomo_best  # noqa: E402
from scripts._mesh_paths import G5_RAW_MESH  # noqa: E402

from cura_cli.cura_slicer import CuraSlicer  # noqa: E402
from cura_cli import mesh_rotation  # noqa: E402

G5_ROOT = PROJECT_ROOT / "Experimental" / "G5Test"
CACHE_DIR = G5_ROOT / "tomo_int3_cache"
CAND_DIR = G5_ROOT / "SFTF_result"
GRID_SUFFIX = "_tomo_int3_1deg_60deg.npz"

# organic set: five calibration meshes + three retrospective test meshes; routed branch per the
# fixed routing rule of the manuscript (C6/C7 -> uniform, all others -> SFTF)
MESHES = [
    ("Group_C1_Bunny_69k", "sftf"),
    ("Group_C2_manikin", "sftf"),
    ("Group_C3_dragon_100k_1.5x", "sftf"),
    ("Group_C4_happy_50k_0.75x", "sftf"),
    ("Group_C5_lucy_50k", "sftf"),
    ("Group_C6_nefertiti_100k", "uniform"),
    ("Group_C7_liver_19k", "uniform"),
    ("Group_C8_kidney_12k", "sftf"),
]

TARGET_DIAG_MM = 140.0
TOP_K = 20
WINDOW_DEG = 10.0
NMS_DEG = 3.0


def _deployed_direction(stem: str, branch: str, yaw, pitch, vss) -> tuple[float, float, float]:
    """(yaw, pitch, tomo_vss) of the routed-branch local-window best."""
    cands = _read_candidate_csv(CAND_DIR / f"{stem}_candidates.csv")
    centers = _ranked_centers(cands, yaw, pitch, vss, limit=TOP_K, min_angle_degrees=NMS_DEG)
    res = _local_window_result(centers, yaw, pitch, vss, radius_degrees=WINDOW_DEG)
    if branch == "sftf":
        best = res["local_best"]
        return float(best["yaw"]), float(best["pitch"]), float(best["vss"])
    # uniform branch at the same per-mesh budget cap as SFTF top-20
    cap = int(res["cell_count"])
    directions = _unique_axis_directions(_spherical_sample_directions(SUPPORT_FLOW_COARSE_DIRECTION_COUNT))
    order = _farthest_axis_order(directions)
    ucenters = _centers_from_directions(directions, yaw, pitch, vss)
    windows = _precompute_windows(ucenters, yaw, pitch, radius_degrees=WINDOW_DEG, yaw_count=len(yaw))
    row = _evaluate_window_order(
        policy="uniform", mesh=stem, trial=0, order=order, centers=ucenters,
        windows=windows, vss_flat=vss.reshape(-1), yaw_values=yaw, pitch_values=pitch,
        tomo_best_vss=1.0, full_grid_cells=int(vss.size), budget_cap_cells=cap)
    return float(row["local_best_yaw"]), float(row["local_best_pitch"]), float(row["local_best_vss"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--critical-angle", type=float, default=60.0)
    ap.add_argument("--target-diag-mm", type=float, default=TARGET_DIAG_MM)
    ap.add_argument("--output-stem", default="sftf_cura_cross_validation")
    args = ap.parse_args()

    slicer = CuraSlicer(engine="legacy", critical_angle=args.critical_angle,
                        support_placement="everywhere")
    rows: list[dict[str, object]] = []
    for stem, branch in MESHES:
        grid_path = CACHE_DIR / f"{stem}{GRID_SUFFIX}"
        d = np.load(grid_path, allow_pickle=False)
        yaw = np.asarray(d["yaw_values"], float)
        pitch = np.asarray(d["pitch_values"], float)
        vss = np.asarray(d["vss_grid"], float)
        tb = _tomo_best(yaw, pitch, vss)
        dep_yaw, dep_pitch, dep_vss = _deployed_direction(stem, branch, yaw, pitch, vss)
        tomo_ratio = dep_vss / float(tb["vss"])

        mesh_path = next(G5_RAW_MESH.glob(stem + ".*"))
        mesh = mesh_rotation.load_mesh(mesh_path)
        diag = float(np.linalg.norm(mesh.extents))
        scale = args.target_diag_mm / diag
        mesh.apply_scale(scale)

        res_dep = slicer.slice_orientation(mesh, dep_yaw, dep_pitch)
        res_opt = slicer.slice_orientation(mesh, float(tb["yaw"]), float(tb["pitch"]))
        if not (res_dep.ok and res_opt.ok):
            print(f"{stem}: SLICE FAILED dep={res_dep.error!r} opt={res_opt.error!r}", flush=True)
            continue
        cura_ratio = (res_dep.support_volume_mm3 / res_opt.support_volume_mm3
                      if res_opt.support_volume_mm3 > 1e-9 else float("inf"))
        rows.append({
            "mesh": stem, "branch": branch, "scale": scale,
            "deployed_yaw": dep_yaw, "deployed_pitch": dep_pitch,
            "tomo_best_yaw": float(tb["yaw"]), "tomo_best_pitch": float(tb["pitch"]),
            "tomo_ratio_predicted": tomo_ratio,
            "cura_support_deployed_mm3": float(res_dep.support_volume_mm3),
            "cura_support_tomo_best_mm3": float(res_opt.support_volume_mm3),
            "cura_ratio_measured": float(cura_ratio),
        })
        print(f"{stem:<28}{branch:<8} tomo_ratio={tomo_ratio:6.2f}  "
              f"cura_ratio={cura_ratio:6.2f}  "
              f"support(dep/opt)={res_dep.support_volume_mm3:8.0f}/{res_opt.support_volume_mm3:8.0f} mm^3",
              flush=True)

    pred = np.asarray([r["tomo_ratio_predicted"] for r in rows], float)
    meas = np.asarray([r["cura_ratio_measured"] for r in rows], float)
    from scipy.stats import spearmanr, pearsonr
    sp = float(spearmanr(pred, meas).statistic) if len(rows) > 2 else float("nan")
    pe = float(pearsonr(pred, meas).statistic) if len(rows) > 2 else float("nan")

    out = PROJECT_ROOT / "Experimental" / "etc"
    payload = {
        "config": {"engine": "legacy CuraEngine 15.04 (DP103 profile)",
                   "critical_angle": args.critical_angle,
                   "support_placement": "everywhere", "pattern": "lines",
                   "target_diag_mm": args.target_diag_mm,
                   "top_k": TOP_K, "window_degrees": WINDOW_DEG},
        "spearman_pred_vs_measured": sp, "pearson_pred_vs_measured": pe,
        "rows": rows,
    }
    (out / f"{args.output_stem}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    with (out / f"{args.output_stem}.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    print(f"\nTOMO-predicted vs Cura-measured direction-pair ratios: "
          f"Spearman={sp:.3f} Pearson={pe:.3f} (n={len(rows)})")
    print(f"saved: Experimental/etc/{args.output_stem}{{.json,.csv}}")


if __name__ == "__main__":
    main()
