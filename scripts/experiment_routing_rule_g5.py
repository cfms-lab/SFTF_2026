"""Pre-verification routing rule: candidate-pool signals -> SFTF or uniform.

Follow-up to the hybrid budget-policy gate (GATE_2026-07-06): fixed-split
hybrids lose to uniform-only, but SFTF wins on the organic C meshes while
uniform wins on the large mechanical D/E parts. This experiment asks whether
that per-mesh winner is predictable *before* spending any verification budget,
using only signals computable from the SFTF candidate pool itself:

  * nn_frac  -- fraction of the deployed top-K (after 3 degree NMS) whose
    nearest-neighbour axis angle is within 1.5x the NMS floor. High crowding
    means the candidates agree on a few narrow basins (organic-like signal);
    a spread-out pool means the ranking is diffuse (mechanical-like no-signal).
  * score_cv -- coefficient of variation of the top-K tuned scores. Extreme
    spread flags unstable rankings even when the pool is crowded (E2/E9).

Routing rule: send the mesh to SFTF top-K local verification iff
nn_frac >= T1 and score_cv <= T2; otherwise fall back to uniform-axis windows
at the same budget. Evaluated retrospectively on the ratio-valid records from
the budget-matched hybrid run, three ways:

  1. fixed rule (T1=0.8, T2=2.0) fitted in-sample (reported for reference);
  2. leave-one-out: thresholds re-fitted on the other N-1 meshes by grid
     search minimising mean routed ratio, then applied to the held-out mesh --
     the honest generalisation estimate;
  3. oracle per-mesh winner (upper bound).

Uses the per-mesh SFTF/uniform ratios already computed by
experiment_budget_matched_g5.py (run with --output-stem sftf_budget_matched_g5_hybrid),
so no grid recomputation is needed.
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

from scripts.experiment_happy_method_g5_audit import (  # noqa: E402
    _read_candidate_csv,
    _rank_candidates,
)

CAND_DIR = PROJECT_ROOT / "Experimental" / "G5Test" / "SFTF_result"
DEFAULT_RATIOS_JSON = PROJECT_ROOT / "Experimental" / "etc" / "sftf_budget_matched_g5_hybrid.json"

DEFAULT_TOP_K = 20
DEFAULT_NMS_DEG = 3.0
DEFAULT_FLOOR_FACTOR = 1.5
FIXED_T1 = 0.8   # nn_frac >= T1
FIXED_T2 = 2.0   # score_cv <= T2
T1_GRID = np.round(np.arange(0.50, 1.00, 0.05), 2)
T2_GRID = np.round(np.arange(0.5, 3.5, 0.25), 2)


def _pool_signals(cand_path: Path, *, top_k: int, nms_deg: float, floor_factor: float) -> dict[str, float]:
    cands = _read_candidate_csv(cand_path)
    top = _rank_candidates(cands, limit=top_k, min_angle_degrees=nms_deg)
    dirs = np.asarray([c["direction"] for c in top], dtype=np.float64)
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    dot = np.abs(dirs @ dirs.T)  # axis-symmetric: n and -n equivalent
    np.fill_diagonal(dot, -1.0)
    nn_ang = np.degrees(np.arccos(np.clip(dot.max(axis=1), -1.0, 1.0)))
    scores = np.asarray([float(c["score"]) for c in top], dtype=np.float64)
    return {
        "nn_frac": float(np.mean(nn_ang <= floor_factor * nms_deg)),
        "nn_mean_deg": float(np.mean(nn_ang)),
        "score_cv": float(np.std(scores) / max(abs(float(np.mean(scores))), 1e-12)),
        "top_k_used": int(len(top)),
    }


def _read_policy_ratios(ratios_json: Path, *, top_k: int) -> dict[str, dict[str, object]]:
    data = json.loads(ratios_json.read_text(encoding="utf-8"))
    sftf_policy = f"SFTF top-{top_k} local"
    per_mesh: dict[str, dict[str, object]] = {}
    for row in data["aggregate_rows"]:
        m = per_mesh.setdefault(str(row["mesh"]), {"group": row.get("group", "?")})
        if row["policy"] == sftf_policy:
            m["sftf"] = float(row["local_best_ratio"])
        elif row["policy"] == "Uniform matched local":
            m["uniform"] = float(row["local_best_ratio"])
        elif row["policy"] == "Hybrid 25:75 SFTF:uniform":
            m["hybrid25"] = float(row["local_best_ratio"])
    return {m: v for m, v in per_mesh.items() if "sftf" in v and "uniform" in v}


def _route(record: dict[str, object], t1: float, t2: float) -> str:
    ok = record["nn_frac"] >= t1 and record["score_cv"] <= t2
    return "SFTF" if ok else "uniform"


def _routed_ratio(record: dict[str, object], choice: str) -> float:
    return float(record["sftf"] if choice == "SFTF" else record["uniform"])


def _fit_thresholds(records: list[dict[str, object]]) -> tuple[float, float]:
    """Grid-search (T1, T2) minimising mean routed ratio; ties -> lower max, then
    fewer SFTF routes (conservative fallback)."""
    best = None
    for t1 in T1_GRID:
        for t2 in T2_GRID:
            ratios = [_routed_ratio(r, _route(r, t1, t2)) for r in records]
            n_sftf = sum(1 for r in records if _route(r, t1, t2) == "SFTF")
            key = (float(np.mean(ratios)), float(np.max(ratios)), n_sftf)
            if best is None or key < best[0]:
                best = (key, (float(t1), float(t2)))
    assert best is not None
    return best[1]


def _summarize(name: str, ratios: list[float]) -> dict[str, object]:
    arr = np.asarray(ratios, dtype=np.float64)
    return {
        "policy": name,
        "mesh_count": int(arr.size),
        "mean_ratio": float(arr.mean()),
        "median_ratio": float(np.median(arr)),
        "max_ratio": float(arr.max()),
        "count_ratio_le_2_00": int(np.sum(arr <= 2.0)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ratios-json", type=Path, default=DEFAULT_RATIOS_JSON)
    ap.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    ap.add_argument("--nms-degrees", type=float, default=DEFAULT_NMS_DEG)
    ap.add_argument("--floor-factor", type=float, default=DEFAULT_FLOOR_FACTOR)
    ap.add_argument("--output-stem", default="sftf_routing_rule_g5")
    args = ap.parse_args()

    per_mesh = _read_policy_ratios(args.ratios_json, top_k=args.top_k)
    records: list[dict[str, object]] = []
    for mesh, info in sorted(per_mesh.items()):
        cand_path = CAND_DIR / f"{mesh}_candidates.csv"
        if not cand_path.exists():
            print(f"skip {mesh}: no candidate CSV", flush=True)
            continue
        sig = _pool_signals(cand_path, top_k=args.top_k, nms_deg=args.nms_degrees,
                            floor_factor=args.floor_factor)
        records.append({"mesh": mesh, "group": info["group"],
                        "sftf": float(info["sftf"]), "uniform": float(info["uniform"]),
                        "hybrid25": float(info.get("hybrid25", info["sftf"])), **sig})

    # --- per-mesh routing: fixed rule, LOO rule, oracle ---
    for i, rec in enumerate(records):
        rec["oracle"] = "SFTF" if rec["sftf"] < rec["uniform"] else "uniform"
        rec["fixed_route"] = _route(rec, FIXED_T1, FIXED_T2)
        train = records[:i] + records[i + 1:]
        t1, t2 = _fit_thresholds(train)
        rec["loo_t1"], rec["loo_t2"] = t1, t2
        rec["loo_route"] = _route(rec, t1, t2)
        rec["fixed_ratio"] = _routed_ratio(rec, rec["fixed_route"])
        rec["loo_ratio"] = _routed_ratio(rec, rec["loo_route"])
        rec["oracle_ratio"] = _routed_ratio(rec, rec["oracle"])
        # soft variant: routed-to-SFTF meshes use the hybrid 25:75 payload, so a
        # misroute keeps 75% of the budget on the uniform safety net
        rec["fixed_h25_ratio"] = float(rec["hybrid25"]) if rec["fixed_route"] == "SFTF" else float(rec["uniform"])
        rec["loo_h25_ratio"] = float(rec["hybrid25"]) if rec["loo_route"] == "SFTF" else float(rec["uniform"])

    fixed_t = _fit_thresholds(records)

    summary = [
        _summarize(f"SFTF top-{args.top_k} only", [r["sftf"] for r in records]),
        _summarize("Uniform only", [r["uniform"] for r in records]),
        _summarize(f"Routed fixed (nn_frac>={FIXED_T1}, cv<={FIXED_T2})",
                   [r["fixed_ratio"] for r in records]),
        _summarize("Routed LOO (thresholds refit per fold)", [r["loo_ratio"] for r in records]),
        _summarize("Routed fixed -> hybrid 25:75 branch", [r["fixed_h25_ratio"] for r in records]),
        _summarize("Routed LOO -> hybrid 25:75 branch", [r["loo_h25_ratio"] for r in records]),
        _summarize("Oracle per-mesh winner", [r["oracle_ratio"] for r in records]),
    ]

    # misclassification vs oracle (ties count as correct either way)
    def _misroutes(key: str) -> list[str]:
        out = []
        for r in records:
            if r[key] != r["oracle"] and not np.isclose(r["sftf"], r["uniform"]):
                out.append(f"{r['mesh']}({r['group']}:{r[key]} vs {r['oracle']})")
        return out

    out_dir = PROJECT_ROOT / "Experimental" / "etc"
    payload = {
        "config": {
            "top_k": int(args.top_k), "nms_degrees": float(args.nms_degrees),
            "floor_factor": float(args.floor_factor),
            "fixed_thresholds": {"nn_frac_min": FIXED_T1, "score_cv_max": FIXED_T2},
            "insample_best_thresholds": {"nn_frac_min": fixed_t[0], "score_cv_max": fixed_t[1]},
            "t1_grid": T1_GRID.tolist(), "t2_grid": T2_GRID.tolist(),
            "ratios_json": str(args.ratios_json.relative_to(PROJECT_ROOT)),
        },
        "summary": summary,
        "records": records,
        "misroutes_fixed": _misroutes("fixed_route"),
        "misroutes_loo": _misroutes("loo_route"),
    }
    (out_dir / f"{args.output_stem}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    with (out_dir / f"{args.output_stem}_records.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(records[0].keys()))
        w.writeheader(); w.writerows(records)
    with (out_dir / f"{args.output_stem}_summary.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(summary[0].keys()))
        w.writeheader(); w.writerows(summary)

    print(f"{'mesh':<26}{'grp':<4}{'SFTF':>8}{'unif':>8} | {'nn_frac':>8}{'cv':>8} "
          f"{'fixed':>8}{'loo':>8}{'oracle':>8}")
    for r in records:
        print(f"{r['mesh']:<26}{r['group']:<4}{r['sftf']:>8.3f}{r['uniform']:>8.3f} | "
              f"{r['nn_frac']:>8.2f}{r['score_cv']:>8.2f} "
              f"{r['fixed_route']:>8}{r['loo_route']:>8}{r['oracle']:>8}")
    print("\n=== routing summary ===")
    for s in summary:
        print(f"{s['policy']:<44} mean={s['mean_ratio']:.3f} median={s['median_ratio']:.3f} "
              f"max={s['max_ratio']:.3f} <=2.0={s['count_ratio_le_2_00']}/{s['mesh_count']}")
    print(f"\nin-sample best thresholds: nn_frac>={fixed_t[0]}, cv<={fixed_t[1]}")
    print(f"misroutes (fixed): {payload['misroutes_fixed'] or 'none'}")
    print(f"misroutes (LOO):   {payload['misroutes_loo'] or 'none'}")
    print(f"\nsaved: Experimental/etc/{args.output_stem}{{.json,_records.csv,_summary.csv}}")


if __name__ == "__main__":
    main()
