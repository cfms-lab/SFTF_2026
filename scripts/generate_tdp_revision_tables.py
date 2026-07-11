"""Generate the revision-only supplementary LaTeX tables from experiment JSON.

The manuscript includes these fragments with ``\\input``.  Generation fails if
the expected populations are incomplete, preventing hand-copied numbers from
drifting away from the executable results.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ETC = ROOT / "Experimental" / "etc"
OUT = ROOT / "draft" / "generated"


def _load(name: str) -> dict:
    return json.loads((ETC / name).read_text(encoding="utf-8"))


def _esc(value: object) -> str:
    text = str(value)
    for old, new in (("\\", r"\textbackslash{}"), ("_", r"\_"),
                     ("%", r"\%"), ("&", r"\&"), ("#", r"\#")):
        text = text.replace(old, new)
    return text


def _short_mesh(stem: str) -> str:
    return _esc(stem.removeprefix("Group_"))


def _num(value: object, digits: int = 3) -> str:
    if value is None:
        return "--"
    number = float(value)
    if not math.isfinite(number):
        return "--"
    if abs(number) >= 10000 or (0 < abs(number) < 0.001):
        return f"{number:.2e}"
    return f"{number:.{digits}f}"


def _write(name: str, text: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(text.rstrip() + "\n", encoding="utf-8")


def _pipeline_table(runtime: dict) -> str:
    rows = runtime["records"]
    if runtime.get("status") != "complete" or len(rows) != 41:
        raise RuntimeError(f"pipeline table requires 41 records, got {len(rows)}")
    if len({row["mesh"] for row in rows}) != 41:
        raise RuntimeError("pipeline table requires 41 unique mesh keys")
    physical = all(bool(row.get("physical_tomo_executed")) for row in rows)
    if not physical:
        raise RuntimeError("pipeline table requires completed physical TOMO timing")
    valid_count = sum(bool(row.get("ratio_valid")) for row in rows)
    if valid_count != 26 or len(rows) - valid_count != 15:
        raise RuntimeError(
            f"pipeline population drift: expected 26 positive/15 zero, got "
            f"{valid_count}/{len(rows) - valid_count}"
        )
    skipped = runtime.get("skipped", [])
    if skipped:
        raise RuntimeError(f"pipeline has unexpected skipped records: {skipped}")
    if not all(bool(row.get("fresh_candidates_used")) for row in rows):
        raise RuntimeError("pipeline table requires fresh candidate generation on every row")
    mismatches = {row["mesh"] for row in rows if not bool(row.get("fresh_candidates_match_stored"))}
    if mismatches != {"Group_B4_pipe_elbow", "Group_D10_37416"}:
        raise RuntimeError(f"unexpected fresh/stored candidate mismatch set: {sorted(mismatches)}")
    if not all(bool(row.get("fresh_route_matches_stored")) for row in rows):
        raise RuntimeError("fresh candidate regeneration changed at least one route")
    expected_rows = [row for row in rows if row.get("cache_replay_policy_result_matches_existing_24") is not None]
    if len(expected_rows) != 26 or not all(
        bool(row["cache_replay_policy_result_matches_existing_24"]) for row in expected_rows
    ):
        raise RuntimeError("fresh cached replay changed a route, tier, orientation, or final value")
    cell_mismatches = {
        row["mesh"] for row in expected_rows
        if not bool(row.get("cache_replay_cell_count_matches_existing_24"))
    }
    if cell_mismatches != {"Group_D10_37416"}:
        raise RuntimeError(f"unexpected historical cell-count mismatch set: {sorted(cell_mismatches)}")
    if any(not bool(row.get("physical_trigger_matches_cache")) for row in rows):
        raise RuntimeError("physical TOMO changed an AVE trigger relative to cached-grid replay")
    if any(not bool(row.get("physical_severity_matches_cache")) for row in rows):
        raise RuntimeError("physical TOMO changed an AVE severity tier relative to cached-grid replay")
    if any(not bool(row.get("physical_k_matches_cache")) for row in rows):
        raise RuntimeError("physical TOMO changed the final verification tier")
    if any(not bool(row.get("physical_orientation_matches_cache")) for row in rows):
        raise RuntimeError("physical TOMO changed a final orientation relative to cached-grid replay")
    if any(
        int(row["physical_total_unique_cell_count"])
        != int(row["corrected_total_unique_grid_cell_count"])
        for row in rows
    ):
        raise RuntimeError("physical and cached corrected-cell counts differ")
    lines = [
        r"\begin{landscape}",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.5pt}",
        r"\renewcommand{\arraystretch}{0.85}",
        r"\begin{longtable}{@{}lccccrrrrrrr@{}}",
        r"\caption{Per-mesh execution of the deployed main-text algorithm on all 41 usable records. "
        r"Seed is the initial candidate source (S: calibrated SFTF, U: farthest-point uniform); "
        r"$K$ is the final center count and Cells includes unique sign-resolution probes. Ratio is "
        r"reported only for the 26 positive optima; Exc. is absolute TOMO-proxy excess for the 15 "
        r"zero optima. Selection time sums measured mesh-input, fresh-candidate, rank, route, map, "
        r"cold-batch physical-TOMO, AVE, orchestration, and primary-checkpoint wall time using a "
        r"direct timer; evaluation-only reference-grid/stored-cache checks and the timing-metadata "
        r"rewrite are excluded. Fresh pools differ numerically from stored pools for B4 and D10, "
        r"but all routes and final selections agree; fresh results are reported. Generated by "
        r"\texttt{scripts/generate\_tdp\_revision\_tables.py}.}"
        r"\label{stab:deployed-pipeline}\\",
        r"\toprule",
        r"Mesh & G & Route & Seed & Esc. & $K$ & Cells & Final yaw/pitch & Final $V_{ss}$ & Ratio & Exc. & Sel. time (s)\\",
        r"\midrule",
        r"\endfirsthead",
        r"\multicolumn{12}{l}{\tablename\ \thetable\ (continued)}\\",
        r"\toprule",
        r"Mesh & G & Route & Seed & Esc. & $K$ & Cells & Final yaw/pitch & Final $V_{ss}$ & Ratio & Exc. & Sel. time (s)\\",
        r"\midrule",
        r"\endhead",
    ]
    for row in sorted(rows, key=lambda item: (item["group"], item["mesh"])):
        ratio_valid = bool(row["ratio_valid"])
        support = row["physical_final_support_tomo_vss"]
        ratio = row.get("physical_ratio_to_exhaustive_optimum") if ratio_valid else None
        excess = None if ratio_valid else row.get("physical_absolute_excess_support")
        seed = "S" if row["route"] == "sftf" else "U"
        orientation = f"{float(row['physical_final_yaw_deg']):.0f}/{float(row['physical_final_pitch_deg']):.0f}"
        lines.append(
            " & ".join([
                _short_mesh(row["mesh"]), _esc(row["group"]), _esc(row["route"]), seed,
                "Y" if row["physical_triggered"] else "N",
                str(int(row["physical_final_candidate_center_count"])),
                str(int(row["physical_total_unique_cell_count"])), orientation,
                _num(support, 2), _num(ratio, 3), _num(excess, 2),
                _num(row["physical_selection_plus_primary_checkpoint_wall_s"], 2),
            ]) + r"\\"
        )
    lines += [r"\bottomrule", r"\end{longtable}", r"\end{landscape}"]
    return "\n".join(lines)


def _threshold_table(payload: dict) -> str:
    wanted = [
        ("historical fixed 0.8/2.0", "calibration21", "in_sample_fixed"),
        ("calibration mesh-LOO threshold refit", "calibration21", "internal_mesh_LOO"),
        ("calibration group-holdout threshold refit", "calibration21", "internal_group_CV"),
        ("historical fixed 0.8/2.0", "retrospective_test3", "retrospective_test"),
        ("calibration-only canonical fit", "retrospective_test3", "retrospective_test"),
        ("historical fixed 0.8/2.0", "recovered2", "retrospective_recovered"),
        ("calibration-only canonical fit", "recovered2", "retrospective_recovered"),
        ("historical fixed 0.8/2.0", "all26", "retrospective_full_audit"),
        ("all26 mesh-LOO threshold refit", "all26", "internal_mesh_LOO_not_external"),
    ]
    by_key: dict[tuple[str, str, str, str], dict] = {}
    for row in payload["summary"]:
        evaluation, stage = row["evaluation_kind"].split(":", 1)
        by_key[(row["label"], row["population"], evaluation, stage)] = row
    for stage in ("top20_budget_matched", "router_to_AVE"):
        missing = [key for key in wanted if (*key, stage) not in by_key]
        if missing:
            raise RuntimeError(f"threshold summary rows are incomplete for {stage}: {missing}")
    lines = [
        r"\begin{table}[H]", r"\scriptsize", r"\centering",
        r"\caption{Routing-threshold validation with branch-specific AVE. Fixed-rule rows are "
        r"post hoc; mesh-LOO and group-holdout rows refit thresholds internally and are not "
        r"external validation. Panel A reports the routed top-20 budget-matched output before "
        r"AVE; Panel B reports the final routed-AVE output. Mean 95\% intervals use a percentile "
        r"mesh bootstrap; Wilson intervals for count outcomes are retained in the JSON. The "
        r"last column in both panels counts the same pre-AVE SFTF top-20 ratios above 2.0 "
        r"that were routed to uniform.}",
        r"\label{stab:threshold-validation}",
    ]
    rule_names = {
        "historical fixed 0.8/2.0": "Fixed 0.8/2.0",
        "calibration mesh-LOO threshold refit": "Mesh-LOO refit",
        "calibration group-holdout threshold refit": "Group-holdout refit",
        "calibration-only canonical fit": "Cal. first plateau point",
        "all26 mesh-LOO threshold refit": "All-26 mesh-LOO refit",
    }
    population_names = {
        "calibration21": "Cal. 21", "retrospective_test3": "Test 3",
        "recovered2": "Recovered 2", "all26": "All 26",
    }
    evaluation_names = {
        "in_sample_fixed": "in-sample",
        "internal_mesh_LOO": "internal LOO",
        "internal_group_CV": "internal group CV",
        "retrospective_test": "retrospective test",
        "retrospective_recovered": "recovered audit",
        "retrospective_full_audit": "retrospective audit",
        "internal_mesh_LOO_not_external": "internal all-26 LOO",
    }
    for panel, stage in (("A: routed top-20 output", "top20_budget_matched"),
                         ("B: final routed-AVE output", "router_to_AVE")):
        lines += [rf"\par\smallskip\textit{{Panel {panel}}}\par\smallskip",
                  r"\resizebox{\textwidth}{!}{%",
                  r"\begin{tabular}{lllrrrrr}", r"\toprule",
                  r"Rule & Population & Evaluation & Mean & Mean 95\% CI & Max & $\le2$ & Top-20 SFTF $>2$ to U\\",
                  r"\midrule"]
        selected = [by_key[(*key, stage)] for key in wanted]
        for row in selected:
            evaluation = row["evaluation_kind"].split(":")[0]
            lines.append(" & ".join([
                _esc(rule_names[row["label"]]), _esc(population_names[row["population"]]),
                _esc(evaluation_names[evaluation]),
                _num(row["mean_ratio"], 3),
                f"{_num(row['mean_ratio_ci95_low'],3)}--{_num(row['mean_ratio_ci95_high'],3)}",
                _num(row["max_ratio"], 3),
                f"{row['count_ratio_le_2']}/{row['record_count']}",
                f"{row['catastrophic_sftf_routed_to_uniform']}/{row['catastrophic_sftf_count']}",
            ]) + r"\\")
        lines += [r"\bottomrule", r"\end{tabular}%", r"}", r"\par\medskip"]
    lines += [r"\end{table}"]
    return "\n".join(lines)


def _nonpositive_tables(payload: dict) -> str:
    population = payload["population"]
    expected = {
        "stored_grid_count": 41,
        "stale_or_unusable_grid_count": 0,
        "usable_mesh_and_candidate_count": 41,
        "ratio_valid_positive_optimum_count": 26,
        "ratio_undefined_nonpositive_optimum_count": 15,
        "zero_optimum_count": 15,
        "negative_optimum_count": 0,
    }
    actual = {key: int(population[key]) for key in expected}
    if actual != expected:
        raise RuntimeError(f"nonpositive population changed: expected {expected}, got {actual}")
    groups = population["group_counts"]
    nonpos = {row["metric"]: row for row in payload["metric_summary"]
              if row["optimum_sign_class"] == "nonpositive"}
    positive = {row["metric"]: row for row in payload["metric_summary"]
                if row["optimum_sign_class"] == "positive"}
    lines = [
        r"\begin{table}[H]", r"\centering", r"\small",
        r"\caption{Population accounting for positive and zero exhaustive TOMO minima. "
        r"All 41 stored grids have current mesh and candidate files and are usable. "
        r"All 15 nonpositive cases are exactly zero; no negative minima occur.}",
        r"\label{stab:nonpositive-groups}", r"\begin{tabular}{lrrrr}", r"\toprule",
        r"Group & Positive & Zero & Usable & Zero fraction\\", r"\midrule",
    ]
    for row in groups:
        lines.append(f"{_esc(row['group'])} & {row['positive_optimum_count']} & "
                     f"{row['nonpositive_optimum_count']} & {row['usable_count']} & "
                     f"{100*float(row['nonpositive_exclusion_fraction']):.1f}\\%\\\\")
    lines += [r"\midrule",
              f"All & {actual['ratio_valid_positive_optimum_count']} & "
              f"{actual['zero_optimum_count']} & {actual['usable_mesh_and_candidate_count']} & "
              f"{100 * actual['zero_optimum_count'] / actual['usable_mesh_and_candidate_count']:.1f}\\%\\\\",
              r"\bottomrule",
              r"\end{tabular}", r"\end{table}", "",
              r"\begin{table}[H]", r"\centering", r"\small",
              r"\caption{Alternative regret metrics for records where ratios are or are not defined. "
              r"The scale-free regret difference is uncertain, but the zero-minimum class contains "
              r"the A1 and A3 worst cases hidden by ratio-only reporting.}",
              r"\label{stab:nonpositive-metrics}", r"\begin{tabular}{lrrrr}", r"\toprule",
              r"Metric & Class & Mean & Median & Max\\", r"\midrule"]
    for metric in ("grid_range_normalized_regret", "selected_grid_strictly_better_fraction"):
        metric_label = {
            "grid_range_normalized_regret": "Grid-range-normalized regret",
            "selected_grid_strictly_better_fraction": "Strictly-better grid fraction",
        }[metric]
        for label, source in (("positive", positive), ("zero", nonpos)):
            row = source[metric]
            lines.append(f"{metric_label} & {label} & {_num(row['mean'],5)} & "
                         f"{_num(row['median'],5)} & {_num(row['max'],5)}\\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", "",
              r"\begin{table}[H]", r"\centering", r"\scriptsize",
              r"\caption{Per-record results for the 15 zero-optimum grids. Ratios are undefined; "
              r"Exc. is absolute surrogate excess, BBox-exc. divides excess by bounding-box volume, "
              r"and range regret divides by the within-grid range.}",
              r"\label{stab:nonpositive-records}",
              r"\begin{tabular}{llcrrrrr}", r"\toprule",
              r"Mesh & G & Route & $K$ & Final $V_{ss}$ & Exc. & BBox-exc. & Range regret\\", r"\midrule"]
    detail = [row for row in payload["records"] if row["optimum_sign_class"] == "nonpositive"]
    if len(detail) != 15:
        raise RuntimeError(f"expected 15 zero-optimum detail rows, got {len(detail)}")
    for row in sorted(detail, key=lambda item: (item["group"], item["mesh"])):
        lines.append(" & ".join([
            _short_mesh(row["mesh"]), _esc(row["group"]), _esc(row["fixed_route"]),
            str(int(row["verification_count"])), _num(row["selected_vss"], 2),
            _num(row["surrogate_excess_vss"], 2),
            _num(row["bbox_normalized_surrogate_excess"], 5),
            _num(row["grid_range_normalized_regret"], 5),
        ]) + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


def _cura_table(payload: dict) -> str:
    rows = payload.get("mesh_summaries", [])
    if payload.get("status") != "complete" or len(rows) != 8:
        raise RuntimeError("Cura table requires the complete eight-mesh run")
    if payload.get("expected_slice_count") != 141 or payload.get("completed_slice_count") != 141:
        raise RuntimeError("Cura table requires 141/141 completed slices")
    if payload.get("summary", {}).get("failed_slice_count") != 0:
        raise RuntimeError("Cura table requires zero failed slices")
    lines = [
        r"\begin{table}[H]", r"\scriptsize", r"\centering",
        r"\caption{Multi-direction TOMO--Cura rank validation. Each mesh uses the same 16 "
        r"TOMO-independent Fibonacci directions; the deployed and TOMO-global directions are "
        r"additional regret anchors. Legacy CuraEngine~15.04.6 uses the DP103 PLA settings "
        r"specified in Methods; the JSON records every setting and executable/input hash. "
        r"Exact grid-cell de-duplication produced 141/141 successful slices. The $n$, rank "
        r"correlations, top-$k$ overlaps, and best match are fixed-panel quantities; top-$k$ "
        r"is set overlap. Regret compares Cura support at the "
        r"TOMO-global anchor with the best Cura value among all evaluated directions.}",
        r"\label{stab:cura-multidirection}", r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
        r"Mesh & $n$ & $\rho$ & $\tau_b$ & Top-3 & Top-5 & Best match & TOMO regret & Deployed regret\\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(" & ".join([
            _short_mesh(row["mesh"]), str(row["fixed_panel_count"]),
            _num(row["fixed_panel_spearman"], 3), _num(row["fixed_panel_kendall_tau_b"], 3),
            _num(row["fixed_panel_top3_agreement_fraction"], 2),
            _num(row["fixed_panel_top5_agreement_fraction"], 2),
            "Y" if row["fixed_panel_best_exact_agreement"] else "N",
            f"{float(row['tomo_global_cura_regret_percent']):.1f}\\%",
            f"{float(row['deployed_cura_regret_percent']):.1f}\\%",
        ]) + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


def _cura_pair_table(payload: dict) -> str:
    records = payload.get("records", [])
    meshes = payload.get("config", {}).get("selected_meshes", [])
    if (payload.get("status") != "complete" or len(meshes) != 8
            or payload.get("completed_slice_count") != 141):
        raise RuntimeError("Cura two-anchor table requires the complete run")
    lines = [
        r"\begin{table}[H]", r"\footnotesize", r"\centering",
        r"\caption{Two-anchor Cura cross-check extracted from the completed multi-direction run. "
        r"Each row compares the final deployed direction with the cached TOMO-global direction. "
        r"This pairwise check is not a global rank validation; Table~\ref{stab:cura-multidirection} "
        r"reports the common 16-direction panel.}", r"\label{stab:cura-crosscheck}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{llrrrr}", r"\toprule",
        r"Mesh & Branch & Pred. (TOMO) & Meas. (Cura) & \multicolumn{2}{c}{Support, mm$^3$ (deployed / TOMO-global)}\\",
        r"\midrule",
    ]
    for mesh in meshes:
        subset = [row for row in records if row["mesh"] == mesh and row.get("ok")]
        deployed = next(row for row in subset if "deployed_pipeline" in row["sources"])
        global_row = next(row for row in subset if "tomo_global_optimum" in row["sources"])
        tomo_ratio = float(deployed["tomo_vss"]) / float(global_row["tomo_vss"])
        cura_ratio = float(deployed["cura_support_volume_mm3"]) / float(global_row["cura_support_volume_mm3"])
        lines.append(" & ".join([
            _short_mesh(mesh), _esc(deployed["deployed_route"]), _num(tomo_ratio, 2),
            _num(cura_ratio, 2), _num(deployed["cura_support_volume_mm3"], 0),
            _num(global_row["cura_support_volume_mm3"], 0),
        ]) + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}%", r"}", r"\end{table}"]
    return "\n".join(lines)


def _runtime_table(payload: dict) -> str:
    rows = payload["records"]
    if (payload.get("status") != "complete" or len(rows) != 41
            or not all(row.get("physical_tomo_executed") for row in rows)
            or not all(row.get("fresh_candidates_used") for row in rows)):
        raise RuntimeError("runtime summary requires 41 physical records")
    sums = {
        "mesh": sum(float(row.get("mesh_load_or_metadata_wall_s") or 0) for row in rows),
        "candidate": sum(float(row.get("fresh_candidate_generation_wall_s") or 0) for row in rows),
        "ranking": sum(float(row["ranking_wall_s"]) for row in rows),
        "routing": sum(float(row["routing_wall_s"]) for row in rows),
        "mapping": sum(float(row["seed_axis_to_grid_mapping_wall_s"]) for row in rows),
        "tomo": sum(float(row["physical_tomo_total_wall_s"]) for row in rows),
        "decision": sum(float(row["physical_ave_decision_wall_s"]) for row in rows),
        "checkpoint": sum(float(row["checkpoint_output_io_wall_s"]) for row in rows),
        "e2e": sum(float(row["physical_selection_plus_primary_checkpoint_wall_s"]) for row in rows),
    }
    setup = float(payload.get("summary", {}).get("global_uniform_seed_setup_wall_s") or 0)
    if setup <= 0:
        raise RuntimeError("runtime summary is missing the measured one-time uniform-seed setup")
    sums["other"] = sums["e2e"] - sum(
        sums[key] for key in
        ("mesh", "candidate", "ranking", "routing", "mapping", "tomo", "decision", "checkpoint")
    ) + setup
    sums["e2e"] += setup
    lines = [
        r"\begin{table}[H]", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}",
        r"\caption{Measured selection-path runtime over all 41 usable meshes. Total combines direct "
        r"per-record timers with the one-time uniform-seed setup and includes mesh input, fresh candidates, "
        r"ranking, routing, mapping, cold-batch "
        r"physical local TOMO, AVE, orchestration (Other, including the one-time setup), and the "
        r"primary checkpoint output. "
        r"Each sign/base/escalation TOMO batch reconstructs the backend and reloads the mesh; this "
        r"is a reproducible cold-batch measurement, not optimized stateful-verifier latency. The "
        r"reference grid, stored-pool comparison, cache-delta check, and timing-metadata rewrite "
        r"are evaluation/reporting-only and excluded. "
        r"Candidate-generation speedups in Tables~S1 and S12 are therefore not complete-pipeline speedups.}",
        r"\label{stab:runtime-e2e}", r"\begin{tabular}{lrrrrrrrrrr}", r"\toprule",
        r"Meshes & Load & Candidates & Rank & Route & Map & TOMO & AVE & Other & Checkpoint & Total\\",
        r"\midrule",
        "41 & " + " & ".join(_num(sums[key], 2) for key in
        ("mesh", "candidate", "ranking", "routing", "mapping", "tomo", "decision", "other", "checkpoint", "e2e")) + r"\\",
        r"\bottomrule", r"\end{tabular}", r"\end{table}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-json", default="sftf_deployed_pipeline_runtime_g5_physical.json")
    parser.add_argument("--cura-json", default="sftf_cura_multidirection_validation.json")
    args = parser.parse_args()
    runtime = _load(args.runtime_json)
    threshold = _load("sftf_routing_threshold_validation.json")
    nonpositive = _load("sftf_nonpositive_optimum_audit.json")
    cura = _load(args.cura_json)
    _write("tdp_deployed_pipeline_table.tex", _pipeline_table(runtime))
    _write("tdp_threshold_table.tex", _threshold_table(threshold))
    _write("tdp_nonpositive_tables.tex", _nonpositive_tables(nonpositive))
    _write("tdp_cura_two_anchor_table.tex", _cura_pair_table(cura))
    _write("tdp_cura_multidirection_table.tex", _cura_table(cura))
    _write("tdp_runtime_table.tex", _runtime_table(runtime))
    print(f"generated 6 fragments in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
