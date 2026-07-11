"""Budget-matched local-window controls (SFTF vs uniform-axis vs random) over
the full corrected G5 ratio-valid set, not just the 5 stored organic meshes.

Motivation: on the int16-corrected v_ss, the uniform-axis control matches SFTF
on the 5 organic C meshes. This extends the same control to the large group-E
parts (and A/B/D) to test whether SFTF's window placement helps where it is
supposed to -- high-face-count real parts with narrow optima.

Per ratio-valid mesh (positive TOMO best at 1deg/60deg):
  * SFTF top-K: rank the stored SFTF candidates (same NMS as the audit), take
    the union of +/-window cells of the top-K, record its cell count (the
    per-mesh budget cap) and its best-in-window ratio;
  * Uniform matched: farthest-point axis order over the coarse Fibonacci
    directions, greedily add windows up to the cap;
  * Random matched (median): random seed orders, median over trials at the cap.
Reuses the vetted helpers from experiment_budget_matched_local_baselines.
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
    _evaluate_window_order,
    _farthest_axis_order,
    _precompute_windows,
    _random_mesh_medians,
    _stable_mesh_seed,
    _summarize_policy_rows,
    _unique_axis_directions,
)
from scripts.experiment_happy_method_g5_audit import (  # noqa: E402
    _read_candidate_csv,
    _record_group_from_name,
    _ranked_centers,
    _local_window_result,
)
from scripts.experiment_rtilde_ranking_g5 import _with_score  # noqa: E402
from scripts.regenerate_sftf_vs_saved_tomo_summary import _tomo_best  # noqa: E402
from scripts._mesh_paths import G5_RAW_MESH  # noqa: E402

G5_ROOT = PROJECT_ROOT / "Experimental" / "G5Test"
CACHE_DIR = G5_ROOT / "tomo_int3_cache"
CAND_DIR = G5_ROOT / "SFTF_result"
MESH_DIR = G5_RAW_MESH
GRID_SUFFIX = "_tomo_int3_1deg_60deg.npz"
CAND_SUFFIX = "_candidates.csv"


def _mesh_exists(stem: str) -> bool:
    return any(MESH_DIR.glob(stem + ".*"))


def _fill_windows(
    visited: np.ndarray,
    order,
    windows: list[np.ndarray],
    vss_flat: np.ndarray,
    *,
    cap_cells: int,
    best_vss: float,
) -> float:
    """Greedily add windows (union of new cells) up to cap_cells, tracking best.

    Mirrors the budget accounting in ``_evaluate_window_order``: skip a window
    that would exceed the cap, stop once the cap is reached. ``visited`` is
    mutated in place so the caller can chain phases under one shared budget.
    """
    for center_id in order:
        window = windows[int(center_id)]
        if window.size == 0:
            continue
        new_cells = window[~visited[window]]
        if new_cells.size == 0:
            continue
        if int(np.count_nonzero(visited)) + int(new_cells.size) > int(cap_cells):
            continue
        visited[new_cells] = True
        local_best = float(np.nanmin(vss_flat[new_cells]))
        if local_best < best_vss:
            best_vss = local_best
        if int(np.count_nonzero(visited)) >= int(cap_cells):
            break
    return best_vss


def _evaluate_hybrid(
    *,
    policy: str,
    mesh: str,
    group: str,
    sftf_order,
    sftf_windows: list[np.ndarray],
    uni_order,
    uni_windows: list[np.ndarray],
    vss_flat: np.ndarray,
    tomo_best_vss: float,
    full_grid_cells: int,
    budget_cap_cells: int,
    sftf_fraction: float,
) -> dict:
    """Split the shared budget: SFTF windows fill ``sftf_fraction`` of the cap,
    uniform-axis windows fill the remainder. Union of cells, best-in-window ratio."""
    visited = np.zeros(int(full_grid_cells), dtype=bool)
    sftf_cap = int(round(int(budget_cap_cells) * float(sftf_fraction)))
    best = _fill_windows(visited, sftf_order, sftf_windows, vss_flat,
                         cap_cells=sftf_cap, best_vss=float("inf"))
    best = _fill_windows(visited, uni_order, uni_windows, vss_flat,
                         cap_cells=int(budget_cap_cells), best_vss=best)
    used = int(np.count_nonzero(visited))
    return {
        "policy": policy, "mesh": mesh, "group": group, "trial": 0,
        "local_cell_count": used, "budget_cap_cells": int(budget_cap_cells),
        "local_budget_fraction": used / max(1, int(full_grid_cells)),
        "tomo_best_vss": float(tomo_best_vss),
        "local_best_ratio": float(best) / float(tomo_best_vss),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top-k", type=int, default=20)
    ap.add_argument("--window-degrees", type=float, default=10.0)
    ap.add_argument("--min-angle-degrees", type=float, default=3.0)
    ap.add_argument("--random-trials", type=int, default=500)
    ap.add_argument("--random-seed", type=int, default=20260625)
    ap.add_argument("--hybrid-fractions", default="0.25,0.5,0.75",
                    help="SFTF budget shares for hybrid SFTF+uniform policies")
    ap.add_argument("--output-stem", default="sftf_budget_matched_g5")
    args = ap.parse_args()

    hybrid_fractions = [float(x) for x in str(args.hybrid_fractions).split(",") if x.strip()]

    def _hybrid_policy(frac: float) -> str:
        s = int(round(frac * 100))
        return f"Hybrid {s}:{100 - s} SFTF:uniform"

    def _rt_hybrid_policy(frac: float) -> str:
        s = int(round(frac * 100))
        return f"Hybrid {s}:{100 - s} Rtilde:uniform"

    directions = _unique_axis_directions(_spherical_sample_directions(SUPPORT_FLOW_COARSE_DIRECTION_COUNT))
    uniform_order = _farthest_axis_order(directions)

    detail: list[dict] = []
    agg: list[dict] = []
    for grid in sorted(CACHE_DIR.glob(f"*{GRID_SUFFIX}")):
        stem = grid.name[: -len(GRID_SUFFIX)]
        cand = CAND_DIR / f"{stem}{CAND_SUFFIX}"
        if not cand.exists() or not _mesh_exists(stem):
            continue
        d = np.load(grid, allow_pickle=False)
        yaw = np.asarray(d["yaw_values"], float)
        pitch = np.asarray(d["pitch_values"], float)
        vss = np.asarray(d["vss_grid"], float)
        tb = _tomo_best(yaw, pitch, vss)
        if float(tb["vss"]) <= 1e-12:
            continue
        grp = _record_group_from_name(stem)
        vss_flat = vss.reshape(-1)
        full = int(vss.size)

        # --- SFTF top-K ---
        cands = _read_candidate_csv(cand)
        centers = _ranked_centers(cands, yaw, pitch, vss, limit=args.top_k,
                                  min_angle_degrees=args.min_angle_degrees)
        res = _local_window_result(centers, yaw, pitch, vss, radius_degrees=args.window_degrees)
        cap = int(res["cell_count"])
        sftf_ratio = float(res["local_best"]["vss"]) / float(tb["vss"])
        sftf_row = {"policy": f"SFTF top-{args.top_k} local", "mesh": stem, "group": grp,
                    "trial": 0, "local_cell_count": cap, "budget_cap_cells": cap,
                    "local_budget_fraction": cap / max(1, full),
                    "tomo_best_vss": float(tb["vss"]), "local_best_ratio": sftf_ratio}
        agg.append(sftf_row)
        detail.append(sftf_row)

        # --- uniform + random at the same cap ---
        ucenters = _centers_from_directions(directions, yaw, pitch, vss)
        windows = _precompute_windows(ucenters, yaw, pitch,
                                      radius_degrees=args.window_degrees, yaw_count=len(yaw))
        urow = _evaluate_window_order(policy="Uniform matched local", mesh=stem, trial=0,
                                      order=uniform_order, centers=ucenters, windows=windows,
                                      vss_flat=vss_flat, yaw_values=yaw, pitch_values=pitch,
                                      tomo_best_vss=float(tb["vss"]), full_grid_cells=full,
                                      budget_cap_cells=cap)
        urow["group"] = grp
        detail.append(urow)

        rng = np.random.default_rng(int(args.random_seed) + _stable_mesh_seed(stem))
        base = np.arange(len(directions), dtype=np.int64)
        rrows = []
        for t in range(int(args.random_trials)):
            order = base.copy()
            rng.shuffle(order)
            rr = _evaluate_window_order(policy="Random matched local", mesh=stem, trial=t,
                                        order=order.tolist(), centers=ucenters, windows=windows,
                                        vss_flat=vss_flat, yaw_values=yaw, pitch_values=pitch,
                                        tomo_best_vss=float(tb["vss"]), full_grid_cells=full,
                                        budget_cap_cells=cap)
            rr["group"] = grp
            rrows.append(rr)
        detail.extend(rrows)
        rmed = _random_mesh_medians(rrows)
        for r in rmed:
            r["group"] = grp
        agg.append(urow)
        agg.extend(rmed)

        # --- hybrid (SFTF top-K/f union uniform) at the same cap ---
        sftf_windows = _precompute_windows(centers, yaw, pitch,
                                           radius_degrees=args.window_degrees, yaw_count=len(yaw))
        sftf_order = list(range(len(centers)))
        hyb_ratios = {}
        for frac in hybrid_fractions:
            hrow = _evaluate_hybrid(
                policy=_hybrid_policy(frac), mesh=stem, group=grp,
                sftf_order=sftf_order, sftf_windows=sftf_windows,
                uni_order=uniform_order, uni_windows=windows,
                vss_flat=vss_flat, tomo_best_vss=float(tb["vss"]),
                full_grid_cells=full, budget_cap_cells=cap, sftf_fraction=frac)
            detail.append(hrow)
            agg.append(hrow)
            hyb_ratios[frac] = hrow["local_best_ratio"]

        # --- hybrid with R-tilde-ranked SFTF share (same cap, same uniform windows) ---
        rt_centers = _ranked_centers(_with_score(cands, "rtilde"), yaw, pitch, vss,
                                     limit=args.top_k, min_angle_degrees=args.min_angle_degrees)
        rt_windows = _precompute_windows(rt_centers, yaw, pitch,
                                         radius_degrees=args.window_degrees, yaw_count=len(yaw))
        rt_order = list(range(len(rt_centers)))
        rt_ratios = {}
        for frac in hybrid_fractions:
            hrow = _evaluate_hybrid(
                policy=_rt_hybrid_policy(frac), mesh=stem, group=grp,
                sftf_order=rt_order, sftf_windows=rt_windows,
                uni_order=uniform_order, uni_windows=windows,
                vss_flat=vss_flat, tomo_best_vss=float(tb["vss"]),
                full_grid_cells=full, budget_cap_cells=cap, sftf_fraction=frac)
            detail.append(hrow)
            agg.append(hrow)
            rt_ratios[frac] = hrow["local_best_ratio"]

        hyb_str = " ".join(f"h{int(f*100)}={hyb_ratios[f]:.3f}" for f in hybrid_fractions)
        rt_str = " ".join(f"rt{int(f*100)}={rt_ratios[f]:.3f}" for f in hybrid_fractions)
        print(f"{stem:<22}{grp} cap={cap:<5} SFTF={sftf_ratio:.3f} "
              f"uniform={urow['local_best_ratio']:.3f} "
              f"rand_med={rmed[0]['local_best_ratio']:.3f} {hyb_str} {rt_str}", flush=True)

    # summaries: ALL and per-group, for each policy
    out = PROJECT_ROOT / "Experimental" / "etc"
    def summarize(rows, tag):
        by_pol = defaultdict(list)
        for r in rows:
            by_pol[r["policy"]].append(r)
        res = []
        policy_order = [f"SFTF top-{args.top_k} local", "Uniform matched local",
                        "Random matched local (median)"]
        policy_order += [_hybrid_policy(f) for f in hybrid_fractions]
        policy_order += [_rt_hybrid_policy(f) for f in hybrid_fractions]
        for pol in policy_order:
            if by_pol.get(pol):
                s = _summarize_policy_rows(pol, by_pol[pol]); s["scope"] = tag
                res.append(s)
        return res

    summary = summarize(agg, "ALL")
    for g in sorted({r["group"] for r in agg}):
        summary += summarize([r for r in agg if r["group"] == g], g)

    (out / f"{args.output_stem}.json").write_text(json.dumps(
        {"summary": summary, "aggregate_rows": agg}, indent=2, ensure_ascii=False), encoding="utf-8")
    with (out / f"{args.output_stem}_summary.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)

    print("\n=== budget-matched G5 summary (scope: policy | mean max <=2.0) ===")
    for s in summary:
        print(f"{s['scope']:<4} {s['policy']:<28} mean={s['mean_local_ratio']:.3f} "
              f"max={s['max_local_ratio']:.3f} <=2.0={s['count_ratio_le_2_00']}/{s['mesh_count']} "
              f"bud={100*s['mean_local_budget_fraction']:.2f}%", flush=True)


if __name__ == "__main__":
    main()
