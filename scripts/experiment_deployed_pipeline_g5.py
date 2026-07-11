"""Replay the declared deployed pipeline on every ratio-valid G5 record.

The router and the two AVE seed policies were historically evaluated in
separate scripts.  This program joins them by mesh using the *fixed* routing
rule and selects only the AVE result of the branch actually chosen by that
rule.  It deliberately does not report the unselected branch as pipeline
performance.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ETC = ROOT / "Experimental" / "etc"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as h:
        return list(csv.DictReader(h))


def main() -> None:
    started = time.perf_counter()
    routing = {r["mesh"]: r for r in read_rows(ETC / "sftf_routing_rule_g5_records.csv")}
    sftf = {r["mesh"]: r for r in read_rows(ETC / "sftf_happy_method_g5_audit_1deg60.csv")
            if r["stage"] == "adaptive_final"}
    uniform = {r["mesh"]: r for r in read_rows(ETC / "sftf_ave_uniform_control_1deg60_records.csv")
               if r["stage"] == "adaptive_final"}
    records: list[dict[str, object]] = []
    for mesh, route in routing.items():
        branch = str(route["fixed_route"]).lower()
        source = sftf if branch == "sftf" else uniform
        selected = source[mesh]
        records.append({
            "mesh": mesh, "group": route["group"], "route": branch,
            "initial_candidate_source": "calibrated SFTF top-20" if branch == "sftf" else "farthest-point uniform axes",
            "verification_count": int(selected["candidate_center_count"]),
            "escalated": selected["triggered"].lower() == "true",
            "final_yaw_deg": float(selected["local_best_yaw"]),
            "final_pitch_deg": float(selected["local_best_pitch"]),
            "final_support_tomo_vss": float(selected["local_best_vss"]),
            "ratio_to_exhaustive_optimum": float(selected["local_best_ratio"]),
            "verified_grid_cells": int(selected["local_cell_count"]),
            "grid_budget_fraction": float(selected["local_budget_fraction"]),
        })
    elapsed = time.perf_counter() - started
    # Cached-grid replay time is reported separately and is not physical TOMO
    # evaluation time; the source experiments contain no per-mesh wall clock.
    each = elapsed / len(records)
    for r in records:
        r["cached_replay_wall_clock_s"] = each
    ratios = [float(r["ratio_to_exhaustive_optimum"]) for r in records]
    summary = {
        "record_count": len(records), "mean_ratio": sum(ratios) / len(ratios),
        "max_ratio": max(ratios), "count_ratio_le_2": sum(x <= 2 for x in ratios),
        "mean_grid_budget_fraction": sum(float(r["grid_budget_fraction"]) for r in records) / len(records),
        "cached_replay_wall_clock_s": elapsed,
        "runtime_scope": "CSV/cache replay only; excludes candidate generation and TOMO grid generation",
    }
    stem = ETC / "sftf_deployed_pipeline_g5"
    stem.with_suffix(".json").write_text(json.dumps({"summary": summary, "records": records}, indent=2), encoding="utf-8")
    with Path(str(stem) + "_records.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(records[0])); w.writeheader(); w.writerows(records)
    print(json.dumps(summary, indent=2))
    for r in records:
        print(f"{r['mesh']:<30} {r['route']:<7} n={r['verification_count']:>3} "
              f"esc={int(r['escalated'])} ratio={r['ratio_to_exhaustive_optimum']:.3f}")


if __name__ == "__main__":
    main()
