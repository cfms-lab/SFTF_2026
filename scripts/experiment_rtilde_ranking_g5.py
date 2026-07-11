"""Can the deployed ranking score be replaced by plain R-tilde = R + B?

Revision-plan item 2-2: the 7-weight tuned score invites an overfitting
critique (5 meshes, 7 weights, LOMO degrades 1.64 -> 1.71), while the paper's
own correlation table says the un-tuned tensor contraction R-tilde = R + B is
the most stable single predictor (mean Spearman 0.61) and the ground-node
identity justifies exactly that combination.

This experiment re-ranks the stored SFTF candidate pools by R-tilde
(rayleigh + bed, ascending) and pushes them through the *identical* deployed
pipeline (3 degree NMS, top-K, 10 degree local windows, cached 1 degree/60
degree TOMO_int3 grids) used by experiment_budget_matched_g5.py, sweeping K.
Decision rule from the plan, fixed before running:

  * R-tilde ties-or-beats the tuned ranking on the budget curve  ->  promote
    R-tilde to deployed score, demote the 7-weight version to a calibration
    ablation;
  * R-tilde is worse  ->  keep the tuned score, move the LOMO caveat forward.

Comparison scopes: ALL ratio-valid records and per-group (the branch-B paper
scopes ranking claims to organic group C, so C is the decisive scope).
No TOMO re-runs -- cached grids and stored candidate CSVs only.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.experiment_happy_method_g5_audit import (  # noqa: E402
    _read_candidate_csv,
    _record_group_from_name,
    _ranked_centers,
    _local_window_result,
)
from scripts.regenerate_sftf_vs_saved_tomo_summary import _tomo_best  # noqa: E402
from scripts._mesh_paths import G5_RAW_MESH  # noqa: E402

G5_ROOT = PROJECT_ROOT / "Experimental" / "G5Test"
CACHE_DIR = G5_ROOT / "tomo_int3_cache"
CAND_DIR = G5_ROOT / "SFTF_result"
MESH_DIR = G5_RAW_MESH
GRID_SUFFIX = "_tomo_int3_1deg_60deg.npz"
CAND_SUFFIX = "_candidates.csv"

RANKINGS = ("tuned", "rtilde")


def _mesh_exists(stem: str) -> bool:
    return any(MESH_DIR.glob(stem + ".*"))


def _with_score(cands: list[dict[str, object]], ranking: str) -> list[dict[str, object]]:
    """Return candidate dicts whose 'score' drives _rank_candidates (ascending)."""
    if ranking == "tuned":
        return cands
    out = []
    for c in cands:
        c2 = dict(c)
        c2["score"] = float(c["rayleigh"]) + float(c["bed"])  # R-tilde = R + B
        out.append(c2)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top-k-sweep", default="5,10,20")
    ap.add_argument("--window-degrees", type=float, default=10.0)
    ap.add_argument("--min-angle-degrees", type=float, default=3.0)
    ap.add_argument("--output-stem", default="sftf_rtilde_ranking_g5")
    args = ap.parse_args()

    top_ks = [int(x) for x in str(args.top_k_sweep).split(",") if x.strip()]

    rows: list[dict[str, object]] = []
    for grid in sorted(CACHE_DIR.glob(f"*{GRID_SUFFIX}")):
        stem = grid.name[: -len(GRID_SUFFIX)]
        cand_path = CAND_DIR / f"{stem}{CAND_SUFFIX}"
        if not cand_path.exists() or not _mesh_exists(stem):
            continue
        d = np.load(grid, allow_pickle=False)
        yaw = np.asarray(d["yaw_values"], float)
        pitch = np.asarray(d["pitch_values"], float)
        vss = np.asarray(d["vss_grid"], float)
        tb = _tomo_best(yaw, pitch, vss)
        if float(tb["vss"]) <= 1e-12:
            continue
        grp = _record_group_from_name(stem)
        full = int(vss.size)
        cands = _read_candidate_csv(cand_path)

        line = [f"{stem:<26}{grp}"]
        for ranking in RANKINGS:
            scored = _with_score(cands, ranking)
            for k in top_ks:
                centers = _ranked_centers(scored, yaw, pitch, vss, limit=k,
                                          min_angle_degrees=args.min_angle_degrees)
                res = _local_window_result(centers, yaw, pitch, vss,
                                           radius_degrees=args.window_degrees)
                ratio = float(res["local_best"]["vss"]) / float(tb["vss"])
                cells = int(res["cell_count"])
                rows.append({
                    "mesh": stem, "group": grp, "ranking": ranking, "top_k": k,
                    "local_cell_count": cells,
                    "local_budget_fraction": cells / max(1, full),
                    "tomo_best_vss": float(tb["vss"]),
                    "local_best_ratio": ratio,
                })
                if k == max(top_ks):
                    line.append(f"{ranking}@{k}={ratio:.3f}")
        print(" ".join(line), flush=True)

    # summaries per (ranking, top_k) x scope
    def summarize(sel: list[dict[str, object]], ranking: str, k: int, scope: str) -> dict[str, object]:
        arr = np.asarray([float(r["local_best_ratio"]) for r in sel], float)
        bud = np.asarray([float(r["local_budget_fraction"]) for r in sel], float)
        return {
            "ranking": ranking, "top_k": k, "scope": scope, "mesh_count": int(arr.size),
            "mean_ratio": float(arr.mean()), "median_ratio": float(np.median(arr)),
            "max_ratio": float(arr.max()),
            "count_ratio_le_2_00": int(np.sum(arr <= 2.0)),
            "mean_budget_fraction": float(bud.mean()),
        }

    groups = sorted({str(r["group"]) for r in rows})
    summary: list[dict[str, object]] = []
    for ranking in RANKINGS:
        for k in top_ks:
            sel = [r for r in rows if r["ranking"] == ranking and r["top_k"] == k]
            if sel:
                summary.append(summarize(sel, ranking, k, "ALL"))
            for g in groups:
                gsel = [r for r in sel if r["group"] == g]
                if gsel:
                    summary.append(summarize(gsel, ranking, k, g))

    out = PROJECT_ROOT / "Experimental" / "etc"
    (out / f"{args.output_stem}.json").write_text(json.dumps(
        {"config": {"top_k_sweep": top_ks, "window_degrees": float(args.window_degrees),
                    "min_angle_degrees": float(args.min_angle_degrees),
                    "rtilde": "rayleigh + bed, ascending"},
         "summary": summary, "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    with (out / f"{args.output_stem}_summary.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(summary[0].keys()))
        w.writeheader(); w.writerows(summary)
    with (out / f"{args.output_stem}_records.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    print("\n=== R-tilde vs tuned ranking (scope | ranking@K | mean max <=2.0 budget) ===")
    for s in summary:
        print(f"{s['scope']:<4} {s['ranking']:>6}@{s['top_k']:<3} mean={s['mean_ratio']:.3f} "
              f"median={s['median_ratio']:.3f} max={s['max_ratio']:.3f} "
              f"<=2.0={s['count_ratio_le_2_00']}/{s['mesh_count']} "
              f"bud={100*s['mean_budget_fraction']:.2f}%", flush=True)
    print(f"\nsaved: Experimental/etc/{args.output_stem}{{.json,_summary.csv,_records.csv}}")


if __name__ == "__main__":
    main()
