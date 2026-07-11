"""Budget-fair AVE control: uniform-axis seeds under the identical escalation rule.

Revision-plan item 1-3: the manuscript's AVE audit (tab:ave-g5) reports
mean 1.14 / max 1.93 at a 13.94% mean budget, but the uniform-axis control is
only ever compared at the ~4% top-20 budget. A reviewer can fairly ask: "what
if the uniform seeding ran the *same* escalation policy and spent the same
kind of budget?" This experiment answers that before submission.

Protocol: identical to experiment_happy_method_g5_audit.py (same cached
1 degree / 60 degree TOMO_int3 grids, same 10 degree windows, same trigger
eq. (ave-trigger): eta >= 0.008 AND (edge OR gain <= 1.5 OR gain >= 3.0),
same tiers base 10 -> escalate 50 / severe 200), except the ranked SFTF
candidate centers are replaced by farthest-point-ordered uniform axis
directions (the same axis set as the budget-matched controls). Escalation
expands the window count along the same uniform order.

Output mirrors the audit summary (per group x stage) plus a per-mesh
side-by-side against the stored SFTF AVE run, so the comparison row for
Table ave-g5 / Supplementary can be lifted directly.
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

from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    SUPPORT_FLOW_COARSE_DIRECTION_COUNT,
    _spherical_sample_directions,
)
from scripts.experiment_budget_matched_local_baselines import (  # noqa: E402
    _centers_from_directions,
    _farthest_axis_order,
    _unique_axis_directions,
)
from scripts.experiment_happy_method_g5_audit import (  # noqa: E402
    DEFAULT_BASE_TOP_K,
    DEFAULT_ESCALATE_TOP_K,
    DEFAULT_SEVERE_ESCALATE_TOP_K,
    DEFAULT_WINDOW_DEGREES,
    DEFAULT_HIGH_SUPPORT_FRACTION,
    DEFAULT_EDGE_MARGIN_DEGREES,
    DEFAULT_LOW_GAIN,
    DEFAULT_HIGH_GAIN,
    DEFAULT_BOUNDARY_GAIN,
    G5_CACHE_DIR,
    _bbox_volume,
    _cell_on_window_boundary,
    _detector_flags,
    _local_window_result,
    _mesh_path_for_stem,
    _record_group_from_name,
    _stage_row,
)
from scripts.regenerate_sftf_vs_saved_tomo_summary import _tomo_best  # noqa: E402

GRID_SUFFIX = "_tomo_int3_1deg_60deg.npz"
DEFAULT_SFTF_AVE_CSV = PROJECT_ROOT / "Experimental" / "etc" / "sftf_happy_method_g5_audit_1deg60.csv"


def _uniform_centers(directions: np.ndarray, order: list[int],
                     yaw: np.ndarray, pitch: np.ndarray, vss: np.ndarray) -> list[dict[str, object]]:
    ordered = directions[np.asarray(order, dtype=np.int64)]
    centers = _centers_from_directions(ordered, yaw, pitch, vss)
    for rank, c in enumerate(centers, start=1):
        c["rank"] = rank  # farthest-point order plays the role of the SFTF rank
    return centers


def _summarize(rows: list[dict[str, object]], group: str, stage: str) -> dict[str, object]:
    ratios = np.asarray([float(r["local_best_ratio"]) for r in rows], float)
    budgets = np.asarray([float(r["local_budget_fraction"]) for r in rows], float)
    return {
        "group": group, "stage": stage, "mesh_count": int(len(rows)),
        "triggered_count": int(sum(bool(r["triggered"]) for r in rows)),
        "mean_local_ratio": float(ratios.mean()),
        "median_local_ratio": float(np.median(ratios)),
        "max_local_ratio": float(ratios.max()),
        "mean_local_budget_fraction": float(budgets.mean()),
        "count_ratio_le_2_00": int(np.sum(ratios <= 2.0)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-top-k", type=int, default=DEFAULT_BASE_TOP_K)
    ap.add_argument("--escalate-top-k", type=int, default=DEFAULT_ESCALATE_TOP_K)
    ap.add_argument("--severe-escalate-top-k", type=int, default=DEFAULT_SEVERE_ESCALATE_TOP_K)
    ap.add_argument("--window-degrees", type=float, default=DEFAULT_WINDOW_DEGREES)
    ap.add_argument("--high-support-fraction", type=float, default=DEFAULT_HIGH_SUPPORT_FRACTION)
    ap.add_argument("--edge-margin-degrees", type=float, default=DEFAULT_EDGE_MARGIN_DEGREES)
    ap.add_argument("--low-gain", type=float, default=DEFAULT_LOW_GAIN)
    ap.add_argument("--high-gain", type=float, default=DEFAULT_HIGH_GAIN)
    ap.add_argument("--boundary-gain", type=float, default=DEFAULT_BOUNDARY_GAIN)
    ap.add_argument("--sftf-ave-csv", type=Path, default=DEFAULT_SFTF_AVE_CSV)
    ap.add_argument("--output-stem", default="sftf_ave_uniform_control_1deg60")
    args = ap.parse_args()

    directions = _unique_axis_directions(_spherical_sample_directions(SUPPORT_FLOW_COARSE_DIRECTION_COUNT))
    order = _farthest_axis_order(directions)
    max_k = max(args.escalate_top_k, args.severe_escalate_top_k)
    if len(order) < max_k:
        raise ValueError(f"only {len(order)} unique axes < severe tier {max_k}")

    rows: list[dict[str, object]] = []
    for grid_path in sorted(G5_CACHE_DIR.glob(f"*{GRID_SUFFIX}")):
        name = grid_path.name[: -len(GRID_SUFFIX)]
        group = _record_group_from_name(name)
        d = np.load(grid_path, allow_pickle=False)
        yaw = np.asarray(d["yaw_values"], float)
        pitch = np.asarray(d["pitch_values"], float)
        vss = np.asarray(d["vss_grid"], float)
        tomo_best = _tomo_best(yaw, pitch, vss)
        if float(tomo_best["vss"]) <= 1e-12:
            continue
        try:
            mesh_path = _mesh_path_for_stem(name)
        except FileNotFoundError:
            continue
        bbox_volume, face_count = _bbox_volume(mesh_path)

        centers = _uniform_centers(directions, order, yaw, pitch, vss)
        base_centers = centers[: args.base_top_k]
        base_result = _local_window_result(base_centers, yaw, pitch, vss,
                                           radius_degrees=args.window_degrees)
        base_seed = base_result["seed_best"]
        base_local = base_result["local_best"]
        gain = (float(base_seed["vss"]) / float(base_local["vss"])
                if base_seed and float(base_local["vss"]) > 1e-12 else float("inf"))
        boundary_hit = _cell_on_window_boundary(
            base_centers, yaw=float(base_local["yaw"]), pitch=float(base_local["pitch"]),
            radius_degrees=args.window_degrees, edge_margin_degrees=args.edge_margin_degrees)
        triggered, severe, reasons = _detector_flags(
            normalized_local_vss=float(base_local["vss"]) / bbox_volume,
            seed_to_local_gain=gain, boundary_hit=boundary_hit,
            high_support_fraction=args.high_support_fraction,
            low_gain=args.low_gain, high_gain=args.high_gain, boundary_gain=args.boundary_gain)

        common = dict(name=name, group=group, triggered=triggered, reasons=reasons,
                      tomo_best=tomo_best, bbox_volume=bbox_volume, face_count=face_count,
                      candidate_count=len(directions), full_grid_cells=int(vss.size),
                      window_degrees=args.window_degrees)
        rows.append(_stage_row(stage="base_top_k", centers=base_centers, result=base_result, **common))

        final_centers, final_result = base_centers, base_result
        if triggered:
            final_k = args.severe_escalate_top_k if severe else args.escalate_top_k
            final_centers = centers[:final_k]
            final_result = _local_window_result(final_centers, yaw, pitch, vss,
                                                radius_degrees=args.window_degrees)
        rows.append(_stage_row(stage="adaptive_final", centers=final_centers, result=final_result, **common))
        print(f"{name:<26}{group} trig={int(triggered)} severe={int(severe)} "
              f"base={rows[-2]['local_best_ratio']:.3f} final={rows[-1]['local_best_ratio']:.3f} "
              f"budget={100*rows[-1]['local_budget_fraction']:.2f}%", flush=True)

    # summaries: ALL + per group, per stage
    summary: list[dict[str, object]] = []
    by_stage: dict[str, list[dict[str, object]]] = defaultdict(list)
    for r in rows:
        by_stage[str(r["stage"])].append(r)
    for stage in ("base_top_k", "adaptive_final"):
        summary.append(_summarize(by_stage[stage], "ALL", stage))
        for g in sorted({str(r["group"]) for r in rows}):
            gsel = [r for r in by_stage[stage] if r["group"] == g]
            if gsel:
                summary.append(_summarize(gsel, g, stage))

    # per-mesh side-by-side vs stored SFTF AVE run
    sftf_final: dict[str, dict[str, float]] = {}
    if args.sftf_ave_csv.exists():
        with args.sftf_ave_csv.open(newline="", encoding="utf-8") as h:
            for row in csv.DictReader(h):
                if row["stage"] == "adaptive_final":
                    sftf_final[row["mesh"]] = {
                        "ratio": float(row["local_best_ratio"]),
                        "budget": float(row["local_budget_fraction"]),
                    }
    side_by_side = []
    for r in by_stage["adaptive_final"]:
        s = sftf_final.get(str(r["mesh"]))
        side_by_side.append({
            "mesh": r["mesh"], "group": r["group"],
            "sftf_ave_ratio": s["ratio"] if s else float("nan"),
            "sftf_ave_budget": s["budget"] if s else float("nan"),
            "uniform_ave_ratio": float(r["local_best_ratio"]),
            "uniform_ave_budget": float(r["local_budget_fraction"]),
            "uniform_triggered": bool(r["triggered"]),
        })

    out = PROJECT_ROOT / "Experimental" / "etc"
    (out / f"{args.output_stem}.json").write_text(json.dumps(
        {"config": vars(args) | {"grid_suffix": GRID_SUFFIX,
                                 "unique_axis_count": int(len(directions)),
                                 "sftf_ave_csv": str(args.sftf_ave_csv)},
         "summary": summary, "rows": rows, "side_by_side": side_by_side},
        indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    with (out / f"{args.output_stem}_summary.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(summary[0].keys()))
        w.writeheader(); w.writerows(summary)
    with (out / f"{args.output_stem}_records.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    with (out / f"{args.output_stem}_side_by_side.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(side_by_side[0].keys()))
        w.writeheader(); w.writerows(side_by_side)

    print("\n=== uniform-seed AVE control (group stage | mean max <=2.0 budget) ===")
    for s in summary:
        print(f"{s['group']:<4}{s['stage']:<15} mean={s['mean_local_ratio']:.3f} "
              f"max={s['max_local_ratio']:.3f} <=2.0={s['count_ratio_le_2_00']}/{s['mesh_count']} "
              f"budget={100*s['mean_local_budget_fraction']:.2f}% "
              f"trig={s['triggered_count']}/{s['mesh_count']}", flush=True)
    print(f"\nsaved: Experimental/etc/{args.output_stem}{{.json,_summary.csv,_records.csv,_side_by_side.csv}}")


if __name__ == "__main__":
    main()
