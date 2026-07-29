"""Coefficient search for the recalibrated score family, tuned on Group C only.

Family (scale fixed by a_bv = 1):

    S = a_hv*F_hv + F_bv + a_hm*F_hm + a_bm*F_bm + a_R*R

Stage 1: coarse grid on Group C, objective = mean Spearman with a top1-NRR
tie-break; report the Pareto edge.  Stage 2 (analyze_de): evaluate the frozen
winner on Groups D/E (not used for tuning) against the current V0 score.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from extract_and_calibrate import OUT, mesh_names, nms_basins, spearman  # noqa: E402

A_HV = [0.0, 0.25, 0.5, 1.0, 2.0]
A_HM = [0.0, 0.1, 0.25, 0.5, 1.0]
A_BM = [0.0, 0.1, 0.25, 0.5, 1.0]
A_R = [0.0, 1.0, 5.0]


def load(name):
    return np.load(OUT / f"{name}_features.npz", allow_pickle=False)


def metrics(data, score):
    rho = spearman(score, data["vss"])
    order = np.lexsort((np.arange(len(score)), score))
    top1 = float(data["nrr"][order[0]])
    basins = nms_basins(data["directions"], score)
    return rho, top1, float(np.min(data["nrr"][basins]))


def score_of(d, a_hv, a_hm, a_bm, a_r):
    return (a_hv * d["F_hv"] + d["F_bv"] + a_hm * d["F_hm"]
            + a_bm * d["F_bm"] + a_r * d["R"])


def main() -> None:
    tune = [load(n) for n in mesh_names("C")]
    results = []
    for a_hv, a_hm, a_bm, a_r in itertools.product(A_HV, A_HM, A_BM, A_R):
        ms = [metrics(d, score_of(d, a_hv, a_hm, a_bm, a_r)) for d in tune]
        results.append({
            "a_hv": a_hv, "a_hm": a_hm, "a_bm": a_bm, "a_R": a_r,
            "rho": float(np.mean([m[0] for m in ms])),
            "rho_min": float(np.min([m[0] for m in ms])),
            "top1": float(np.mean([m[1] for m in ms])),
            "top1_max": float(np.max([m[1] for m in ms])),
            "basin24": float(np.mean([m[2] for m in ms])),
        })

    print("== top 12 by mean Spearman (Group C tuning set) ==")
    for r in sorted(results, key=lambda x: -x["rho"])[:12]:
        print(f"  hv={r['a_hv']:<4} hm={r['a_hm']:<4} bm={r['a_bm']:<4} R={r['a_R']:<3} "
              f"| rho {r['rho']:+.3f} (min {r['rho_min']:+.3f})  top1 {r['top1']:.3f} "
              f"(max {r['top1_max']:.3f})  basin24 {r['basin24']:.4f}")
    print()
    print("== top 12 by mean top1-NRR ==")
    for r in sorted(results, key=lambda x: x["top1"])[:12]:
        print(f"  hv={r['a_hv']:<4} hm={r['a_hm']:<4} bm={r['a_bm']:<4} R={r['a_R']:<3} "
              f"| rho {r['rho']:+.3f} (min {r['rho_min']:+.3f})  top1 {r['top1']:.3f} "
              f"(max {r['top1_max']:.3f})  basin24 {r['basin24']:.4f}")
    print()
    print("== top 12 by mean basin24 ==")
    for r in sorted(results, key=lambda x: x["basin24"])[:12]:
        print(f"  hv={r['a_hv']:<4} hm={r['a_hm']:<4} bm={r['a_bm']:<4} R={r['a_R']:<3} "
              f"| rho {r['rho']:+.3f} (min {r['rho_min']:+.3f})  top1 {r['top1']:.3f} "
              f"(max {r['top1_max']:.3f})  basin24 {r['basin24']:.4f}")
    (HERE / "search_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
