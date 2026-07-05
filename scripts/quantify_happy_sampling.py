"""Quantify the candidate-generation limit (happy) vs coarse sampling density.

happy fails because its near-optimal build direction is not present in the
candidate pool (oracle ratio >> 1), not because of scoring. This sweeps the
coarse Fibonacci-sphere direction count and reports, per mesh, the oracle
(best-in-pool) ratio -- the lower bound any scoring rule could reach -- and the
untuned best-of-3 ratio. No GPU is needed (saved grids reused).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import python_src.SupportFlowTensorField.support_flow_tensor_field as sftf  # noqa: E402
from scripts.cross_validate_sftf_tuning import build_mesh_record  # noqa: E402
from scripts.regenerate_sftf_vs_saved_tomo_summary import GRID_SUFFIX, MESH_DIR  # noqa: E402

COARSE_COUNTS = [512, 1024, 2048, 4096]


def main() -> None:
    grid_paths = sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}"))
    names = [p.name.split(")")[-1].replace(GRID_SUFFIX, "")[:10] for p in grid_paths]

    default_coarse = sftf.SUPPORT_FLOW_COARSE_DIRECTION_COUNT
    oracle_rows, untuned_rows, pool_rows = {}, {}, {}
    for count in COARSE_COUNTS:
        sftf.SUPPORT_FLOW_COARSE_DIRECTION_COUNT = count
        oracle, untuned, pool = [], [], []
        for grid_path in grid_paths:
            rec = build_mesh_record(grid_path)
            oracle.append(float(rec["oracle_ratio"]))
            untuned.append(float(rec["untuned_ratio"]))
            pool.append(int(rec["rank_features"].shape[0]))
        oracle_rows[count] = oracle
        untuned_rows[count] = untuned
        pool_rows[count] = pool
    sftf.SUPPORT_FLOW_COARSE_DIRECTION_COUNT = default_coarse

    print("=== oracle (best-in-pool) ratio vs coarse direction count (lower is better) ===")
    print(f"{'coarse':>8}" + "".join(f"{n:>11}" for n in names))
    for count in COARSE_COUNTS:
        print(f"{count:>8}" + "".join(f"{v:>11.2f}" for v in oracle_rows[count]))

    print("\n=== untuned J best-of-3 ratio vs coarse direction count ===")
    print(f"{'coarse':>8}" + "".join(f"{n:>11}" for n in names))
    for count in COARSE_COUNTS:
        print(f"{count:>8}" + "".join(f"{v:>11.2f}" for v in untuned_rows[count]))

    print("\n=== candidate pool size ===")
    print(f"{'coarse':>8}" + "".join(f"{n:>11}" for n in names))
    for count in COARSE_COUNTS:
        print(f"{count:>8}" + "".join(f"{v:>11d}" for v in pool_rows[count]))


if __name__ == "__main__":
    main()
