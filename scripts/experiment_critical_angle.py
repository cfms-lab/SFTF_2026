"""Experiment E: does reconciling the SFTF overhang with the TOMO critical angle help?

The SFTF overhang O_i(n) = max(0, -m_i . n) counts every downward-facing face,
whereas TOMO_CPU only requires support for faces below the critical angle
theta_c (60 deg). This script gates the overhang at theta_c (a face needs
support iff (-m . n) > cos(theta_c)) and measures the effect on the untuned
best-of-3 ratio and the oracle (best-in-pool) ratio for the 4 well-behaved
meshes. No GPU is needed (saved grids reused).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import python_src.SupportFlowTensorField.support_flow_tensor_field as sftf  # noqa: E402
from scripts.cross_validate_sftf_tuning import (  # noqa: E402
    HAPPY_NAME,
    RIDGE_ALPHA,
    build_mesh_record,
    lomo_mean_ratio,
    ratio_for_weights,
    ridge_fit,
)
from scripts.regenerate_sftf_vs_saved_tomo_summary import GRID_SUFFIX, MESH_DIR  # noqa: E402

SETTINGS = [
    ("baseline (no gate)", False, None),
    ("theta_c=30", True, 30.0),
    ("theta_c=45", True, 45.0),
    ("theta_c=60", True, 60.0),
]


def evaluate_setting(grid_paths: list[Path]) -> dict[str, list[dict[str, object]]]:
    records = []
    for grid_path in grid_paths:
        rec = build_mesh_record(grid_path)
        if rec["mesh"] != HAPPY_NAME:
            records.append(rec)
    return records


def main() -> None:
    grid_paths = sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}"))
    names = None
    print(f"{'setting':<22}{'mean untuned J':>16}{'mean oracle':>14}{'mean LOMO':>12}")
    summary = {}
    for label, use_gate, angle in SETTINGS:
        sftf.SUPPORT_OVERHANG_USE_CRITICAL_ANGLE = use_gate
        if angle is not None:
            sftf.SUPPORT_CRITICAL_ANGLE_DEG = angle
        records = evaluate_setting(grid_paths)
        if names is None:
            names = [r["mesh"].split(")")[-1].replace(".ply", "")[:10] for r in records]
        untuned = [float(r["untuned_ratio"]) for r in records]
        oracle = [float(r["oracle_ratio"]) for r in records]
        lomo = lomo_mean_ratio(records, RIDGE_ALPHA, None)
        summary[label] = {"untuned": untuned, "oracle": oracle, "lomo": lomo, "names": names}
        print(f"{label:<22}{np.mean(untuned):>16.2f}{np.mean(oracle):>14.2f}{lomo:>12.2f}")

    # restore default
    sftf.SUPPORT_OVERHANG_USE_CRITICAL_ANGLE = False
    sftf.SUPPORT_CRITICAL_ANGLE_DEG = 60.0

    print("\n=== per-mesh untuned J best-of-3 ratio ===")
    print(f"{'setting':<22}" + "".join(f"{n:>11}" for n in names))
    for label in summary:
        print(f"{label:<22}" + "".join(f"{v:>11.2f}" for v in summary[label]["untuned"]))
    print("\n=== per-mesh oracle (best-in-pool) ratio ===")
    print(f"{'setting':<22}" + "".join(f"{n:>11}" for n in names))
    for label in summary:
        print(f"{label:<22}" + "".join(f"{v:>11.2f}" for v in summary[label]["oracle"]))


if __name__ == "__main__":
    main()
