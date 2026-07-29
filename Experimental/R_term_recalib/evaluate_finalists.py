"""Evaluate frozen finalist calibrations on Groups D/E (not used for tuning).

Finalists were chosen on the Group C tuning set only:

    V0 current : S = R + 1.00*F_bm + F_bv                     (baseline)
    W_A        : S = R + 0.50*F_bm + F_bv + 2.00*F_hv          (best rho+basin24)
    W_B        : S = R + 0.50*F_bm + F_bv + 0.25*F_hv + 0.25*F_hm
    W_C        : S =     0.25*F_bm + F_bv            + 0.25*F_hm
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from extract_and_calibrate import OUT, mesh_names, nms_basins, spearman  # noqa: E402

FINALISTS = {
    "V0 current": dict(a_hv=0.0, a_hm=0.0, a_bm=1.0, a_R=1.0),
    "W_A": dict(a_hv=2.0, a_hm=0.0, a_bm=0.5, a_R=1.0),
    "W_B": dict(a_hv=0.25, a_hm=0.25, a_bm=0.5, a_R=1.0),
    "W_C": dict(a_hv=0.0, a_hm=0.25, a_bm=0.25, a_R=0.0),
}


def metrics(data, score):
    rho = spearman(score, data["vss"])
    order = np.lexsort((np.arange(len(score)), score))
    top1 = float(data["nrr"][order[0]])
    basins = nms_basins(data["directions"], score)
    return rho, top1, float(np.min(data["nrr"][basins]))


def main() -> None:
    for group in ("D", "E", "C"):
        names = [n for n in mesh_names(group) if (OUT / f"{n}_features.npz").exists()]
        if not names:
            print(f"[no features] group {group}")
            continue
        print(f"== Group {group} ({len(names)} meshes){' — TUNING SET' if group == 'C' else ' — held out from tuning'} ==")
        table = {label: [] for label in FINALISTS}
        for name in names:
            d = np.load(OUT / f"{name}_features.npz", allow_pickle=False)
            for label, c in FINALISTS.items():
                s = (c["a_hv"] * d["F_hv"] + d["F_bv"]
                     + c["a_hm"] * d["F_hm"] + c["a_bm"] * d["F_bm"] + c["a_R"] * d["R"])
                table[label].append(metrics(d, s))
        for label, ms in table.items():
            rho = [m[0] for m in ms]; top1 = [m[1] for m in ms]; basin = [m[2] for m in ms]
            print(f"  {label:11s} rho {np.mean(rho):+.3f} (min {np.min(rho):+.3f})  "
                  f"top1 {np.mean(top1):.3f} (max {np.max(top1):.3f})  "
                  f"basin24 {np.mean(basin):.4f} (max {np.max(basin):.4f})")
        print()


if __name__ == "__main__":
    main()
