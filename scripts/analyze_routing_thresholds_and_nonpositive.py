"""Audit routing-threshold validation and nonpositive TOMO optima.

This script addresses two revision questions without rerunning TOMO itself:

1. Separate the historical post-hoc fixed router, calibration-only fitting,
   internal refitted cross-validation, and the retrospectively designated
   C6--C8 test split.  The fixed thresholds and C6--C8 data entered Git in the
   same commit, so the three meshes are not described here as chronologically
   held out.
2. Replay the same fixed router and AVE branches on every usable cached
   1-degree/60-degree grid, including records whose exhaustive TOMO optimum is
   nonpositive.  Ratios are not formed for those records; instead, the script
   reports surrogate excess, bounding-box-normalized excess, and within-grid
   range-normalized regret.

No TOMO grid is recomputed. Router signals and deployed selections come from a
completed fresh-candidate runtime replay; counterfactual branch controls use the
stored branch audits and cached TOMO grids.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Callable

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    SUPPORT_FLOW_COARSE_DIRECTION_COUNT,
    _spherical_sample_directions,
)
from scripts.experiment_ave_uniform_control import _uniform_centers  # noqa: E402
from scripts.experiment_budget_matched_local_baselines import (  # noqa: E402
    _farthest_axis_order,
    _unique_axis_directions,
)
from scripts.experiment_happy_method_g5_audit import (  # noqa: E402
    DEFAULT_BASE_TOP_K,
    DEFAULT_BOUNDARY_GAIN,
    DEFAULT_EDGE_MARGIN_DEGREES,
    DEFAULT_ESCALATE_TOP_K,
    DEFAULT_HIGH_GAIN,
    DEFAULT_HIGH_SUPPORT_FRACTION,
    DEFAULT_LOW_GAIN,
    DEFAULT_MIN_ANGLE_DEGREES,
    DEFAULT_SEVERE_ESCALATE_TOP_K,
    DEFAULT_WINDOW_DEGREES,
    G5_CACHE_DIR,
    G5_CANDIDATE_DIR,
    G5_CANDIDATE_SUFFIX,
    _cell_on_window_boundary,
    _detector_flags,
    _local_window_result,
    _mesh_path_for_stem,
    _record_group_from_name,
    _stage_row,
    analyze_condition,
)
from scripts.experiment_routing_rule_g5 import (  # noqa: E402
    DEFAULT_TOP_K,
    FIXED_T1,
    FIXED_T2,
    T1_GRID,
    T2_GRID,
    _fit_thresholds,
    _read_policy_ratios,
    _route,
    _routed_ratio,
)
from scripts.regenerate_sftf_vs_saved_tomo_summary import _tomo_best  # noqa: E402

ETC_DIR = PROJECT_ROOT / "Experimental" / "etc"
RATIOS_JSON = ETC_DIR / "sftf_budget_matched_g5_hybrid.json"
SFTF_AVE_CSV = ETC_DIR / "sftf_happy_method_g5_audit_1deg60.csv"
UNIFORM_AVE_CSV = ETC_DIR / "sftf_ave_uniform_control_1deg60_records.csv"
GRID_SUFFIX = "_tomo_int3_1deg_60deg.npz"
DEFAULT_FRESH_RUNTIME_JSON = ETC_DIR / "sftf_deployed_pipeline_runtime_g5_physical.json"
EXPECTED_RUNTIME_RECORD_COUNT = 41
EXPECTED_POSITIVE_COUNT = 26
EXPECTED_NONPOSITIVE_COUNT = 15

# These meshes were introduced as a test set in the manuscript, but the Git
# history shows that their data and the historical fixed thresholds were added
# together.  Accordingly, all outputs call this a retrospective test split.
RETROSPECTIVE_TEST_MESHES = {
    "Group_C6_nefertiti_100k",
    "Group_C7_liver_19k",
    "Group_C8_kidney_12k",
}
RECOVERED_RATIO_VALID_MESHES = {
    "Group_E2_45809",
    "Group_E4_46012",
}
ROUTER_AND_TEST_DATA_COMMIT = "a1a34f102f391ba8dde85f09055102d599b14114"
WILSON_Z_95 = 1.959963984540054


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_ready(item) for item in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Path):
        try:
            return str(value.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(value)
    return value


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(_json_ready(payload), indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )


def _wilson_interval(successes: int, total: int) -> dict[str, object]:
    if total <= 0:
        return {"successes": int(successes), "total": int(total), "estimate": None,
                "ci95_low": None, "ci95_high": None, "method": "Wilson score"}
    p = successes / total
    z2 = WILSON_Z_95**2
    denominator = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denominator
    radius = WILSON_Z_95 * math.sqrt(p * (1.0 - p) / total + z2 / (4.0 * total**2)) / denominator
    return {
        "successes": int(successes),
        "total": int(total),
        "estimate": float(p),
        "ci95_low": float(max(0.0, center - radius)),
        "ci95_high": float(min(1.0, center + radius)),
        "method": "Wilson score",
    }


def _bootstrap_mean_ci(values: list[float], *, resamples: int, seed: int) -> dict[str, object]:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return {"mean": None, "ci95_low": None, "ci95_high": None,
                "resamples": int(resamples), "method": "percentile mesh bootstrap"}
    rng = np.random.default_rng(seed)
    draws = rng.choice(arr, size=(resamples, arr.size), replace=True).mean(axis=1)
    low, high = np.percentile(draws, [2.5, 97.5])
    return {
        "mean": float(arr.mean()),
        "ci95_low": float(low),
        "ci95_high": float(high),
        "resamples": int(resamples),
        "method": "percentile mesh bootstrap",
    }


def _bootstrap_difference_ci(
    first: list[float],
    second: list[float],
    *,
    resamples: int,
    seed: int,
) -> dict[str, object]:
    a = np.asarray(first, dtype=np.float64)
    b = np.asarray(second, dtype=np.float64)
    if a.size == 0 or b.size == 0:
        return {"difference": None, "ci95_low": None, "ci95_high": None,
                "resamples": int(resamples), "method": "independent percentile mesh bootstrap"}
    rng = np.random.default_rng(seed)
    da = rng.choice(a, size=(resamples, a.size), replace=True).mean(axis=1)
    db = rng.choice(b, size=(resamples, b.size), replace=True).mean(axis=1)
    differences = da - db
    low, high = np.percentile(differences, [2.5, 97.5])
    return {
        "difference": float(a.mean() - b.mean()),
        "ci95_low": float(low),
        "ci95_high": float(high),
        "resamples": int(resamples),
        "method": "independent percentile mesh bootstrap",
    }


def _load_fresh_runtime(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("records", [])
    if payload.get("status") != "complete" or len(rows) != EXPECTED_RUNTIME_RECORD_COUNT:
        raise RuntimeError(
            f"fresh runtime must be complete with {EXPECTED_RUNTIME_RECORD_COUNT} rows: {path}"
        )
    if len({row["mesh"] for row in rows}) != EXPECTED_RUNTIME_RECORD_COUNT:
        raise RuntimeError("fresh runtime contains duplicate mesh keys")
    if not all(bool(row.get("fresh_candidates_used")) for row in rows):
        raise RuntimeError("fresh runtime contains a stored-candidate row")
    return {str(row["mesh"]): row for row in rows}


def _fresh_signals(row: dict[str, object]) -> dict[str, object]:
    return {
        "nn_frac": float(row["router_nn_frac"]),
        "nn_mean_deg": float(row["router_nn_mean_deg"]),
        "score_cv": float(row["router_score_cv"]),
        "top_k_used": int(DEFAULT_TOP_K),
    }


def _routing_records(fresh_runtime: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    per_mesh = _read_policy_ratios(RATIOS_JSON, top_k=DEFAULT_TOP_K)
    records: list[dict[str, object]] = []
    for mesh, info in sorted(per_mesh.items()):
        candidate_path = G5_CANDIDATE_DIR / f"{mesh}{G5_CANDIDATE_SUFFIX}"
        if not candidate_path.exists():
            continue
        if mesh not in fresh_runtime:
            raise RuntimeError(f"fresh runtime lacks ratio-valid mesh {mesh}")
        signals = _fresh_signals(fresh_runtime[mesh])
        record = {
            "mesh": mesh,
            "group": str(info["group"]),
            "sftf": float(info["sftf"]),
            "uniform": float(info["uniform"]),
            "hybrid25": float(info.get("hybrid25", info["sftf"])),
            **signals,
        }
        if mesh in RECOVERED_RATIO_VALID_MESHES:
            record["split"] = "recovered_mesh"
        elif mesh in RETROSPECTIVE_TEST_MESHES:
            record["split"] = "retrospective_test"
        else:
            record["split"] = "calibration"
        record["catastrophic_sftf_ratio_gt_2"] = bool(record["sftf"] > 2.0)
        if math.isclose(float(record["sftf"]), float(record["uniform"]), rel_tol=1e-12, abs_tol=1e-12):
            record["oracle"] = "tie"
        else:
            record["oracle"] = "SFTF" if record["sftf"] < record["uniform"] else "uniform"
        records.append(record)
    return records


def _threshold_objective(records: list[dict[str, object]], t1: float, t2: float) -> tuple[float, float, int]:
    ratios = [_routed_ratio(record, _route(record, t1, t2)) for record in records]
    sftf_count = sum(_route(record, t1, t2) == "SFTF" for record in records)
    return float(np.mean(ratios)), float(np.max(ratios)), int(sftf_count)


def _optimal_plateau(records: list[dict[str, object]]) -> list[dict[str, object]]:
    evaluated: list[tuple[tuple[float, float, int], float, float]] = []
    for t1 in T1_GRID:
        for t2 in T2_GRID:
            evaluated.append((_threshold_objective(records, float(t1), float(t2)), float(t1), float(t2)))
    best = min(item[0] for item in evaluated)
    plateau = []
    for objective, t1, t2 in evaluated:
        if (
            math.isclose(objective[0], best[0], rel_tol=1e-12, abs_tol=1e-12)
            and math.isclose(objective[1], best[1], rel_tol=1e-12, abs_tol=1e-12)
            and objective[2] == best[2]
        ):
            plateau.append({
                "nn_frac_min": t1,
                "score_cv_max": t2,
                "mean_ratio": objective[0],
                "max_ratio": objective[1],
                "sftf_route_count": objective[2],
            })
    return plateau


def _adaptive_branch_maps() -> dict[str, dict[str, dict[str, str]]]:
    sftf = {
        row["mesh"]: row for row in _read_csv(SFTF_AVE_CSV)
        if row["stage"] == "adaptive_final"
    }
    uniform = {
        row["mesh"]: row for row in _read_csv(UNIFORM_AVE_CSV)
        if row["stage"] == "adaptive_final"
    }
    return {"SFTF": sftf, "uniform": uniform}


def _branch_end_to_end_ratio(
    record: dict[str, object],
    route: str,
    branch_maps: dict[str, dict[str, dict[str, str]]],
) -> float:
    return float(branch_maps[route][str(record["mesh"])]["local_best_ratio"])


def _performance_summary(
    *,
    label: str,
    population: str,
    evaluation_kind: str,
    records: list[dict[str, object]],
    routes: list[str],
    ratios: list[float],
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> dict[str, object]:
    arr = np.asarray(ratios, dtype=np.float64)
    correct = 0
    catastrophes = 0
    detected = 0
    for record, route in zip(records, routes):
        oracle = str(record["oracle"])
        if oracle == "tie" or route == oracle:
            correct += 1
        if bool(record["catastrophic_sftf_ratio_gt_2"]):
            catastrophes += 1
            if route == "uniform":
                detected += 1
    ratio_le_2 = int(np.sum(arr <= 2.0))
    mean_ci = _bootstrap_mean_ci(ratios, resamples=bootstrap_resamples, seed=bootstrap_seed)
    return {
        "label": label,
        "population": population,
        "evaluation_kind": evaluation_kind,
        "record_count": int(arr.size),
        "mean_ratio": float(arr.mean()),
        "mean_ratio_ci95_low": mean_ci["ci95_low"],
        "mean_ratio_ci95_high": mean_ci["ci95_high"],
        "median_ratio": float(np.median(arr)),
        "max_ratio": float(arr.max()),
        "count_ratio_le_2": ratio_le_2,
        "ratio_le_2_wilson_ci95_low": _wilson_interval(ratio_le_2, len(records))["ci95_low"],
        "ratio_le_2_wilson_ci95_high": _wilson_interval(ratio_le_2, len(records))["ci95_high"],
        "sftf_route_count": int(sum(route == "SFTF" for route in routes)),
        "oracle_route_correct": int(correct),
        "oracle_route_accuracy": float(correct / len(records)),
        "oracle_route_wilson_ci95_low": _wilson_interval(correct, len(records))["ci95_low"],
        "oracle_route_wilson_ci95_high": _wilson_interval(correct, len(records))["ci95_high"],
        "catastrophic_sftf_count": int(catastrophes),
        "catastrophic_sftf_routed_to_uniform": int(detected),
        "catastrophe_detection_rate": float(detected / catastrophes) if catastrophes else None,
        "catastrophe_detection_wilson_ci95_low": _wilson_interval(detected, catastrophes)["ci95_low"],
        "catastrophe_detection_wilson_ci95_high": _wilson_interval(detected, catastrophes)["ci95_high"],
    }


def _refitted_cv_routes(
    records: list[dict[str, object]],
    *,
    scheme: str,
    key: Callable[[dict[str, object]], str],
) -> tuple[dict[str, str], list[dict[str, object]]]:
    outer_keys = sorted({key(record) for record in records})
    routes: dict[str, str] = {}
    folds: list[dict[str, object]] = []
    for outer_key in outer_keys:
        train = [record for record in records if key(record) != outer_key]
        test = [record for record in records if key(record) == outer_key]
        t1, t2 = _fit_thresholds(train)
        for record in test:
            route = _route(record, t1, t2)
            mesh = str(record["mesh"])
            routes[mesh] = route
            folds.append({
                "scheme": scheme,
                "outer_key": outer_key,
                "train_count": int(len(train)),
                "test_count": int(len(test)),
                "mesh": mesh,
                "group": str(record["group"]),
                "fitted_nn_frac_min": float(t1),
                "fitted_score_cv_max": float(t2),
                "route": route,
                "top20_ratio": _routed_ratio(record, route),
            })
    return routes, folds


def analyze_routing_thresholds(
    *,
    bootstrap_resamples: int,
    bootstrap_seed: int,
    fresh_runtime: dict[str, dict[str, object]],
    fresh_runtime_path: Path,
) -> dict[str, object]:
    records = _routing_records(fresh_runtime)
    calibration = [record for record in records if record["split"] == "calibration"]
    test = [record for record in records if record["split"] == "retrospective_test"]
    recovered = [record for record in records if record["split"] == "recovered_mesh"]
    if len(calibration) != 21 or len(test) != 3 or len(recovered) != 2 or len(records) != 26:
        raise RuntimeError(
            "expected 21 calibration + 3 retrospective test + 2 recovered ratio-valid records, got "
            f"{len(calibration)} + {len(test)} + {len(recovered)}"
        )

    calibration_fit = _fit_thresholds(calibration)
    all_fit = _fit_thresholds(records)
    calibration_plateau = _optimal_plateau(calibration)
    all_plateau = _optimal_plateau(records)
    historical = (float(FIXED_T1), float(FIXED_T2))

    cal_loo_routes, cal_loo_folds = _refitted_cv_routes(
        calibration, scheme="calibration_mesh_LOO_refit", key=lambda record: str(record["mesh"])
    )
    cal_logo_routes, cal_logo_folds = _refitted_cv_routes(
        calibration, scheme="calibration_group_holdout_refit", key=lambda record: str(record["group"])
    )
    all_loo_routes, all_loo_folds = _refitted_cv_routes(
        records, scheme="all26_mesh_LOO_refit_retrospective", key=lambda record: str(record["mesh"])
    )
    folds = cal_loo_folds + cal_logo_folds + all_loo_folds

    branch_maps = _adaptive_branch_maps()
    for fold in folds:
        record = next(item for item in records if item["mesh"] == fold["mesh"])
        fold["end_to_end_ave_ratio"] = _branch_end_to_end_ratio(record, str(fold["route"]), branch_maps)

    summary: list[dict[str, object]] = []
    summary_index = 0

    def append_summary(
        label: str,
        population: str,
        evaluation_kind: str,
        subset: list[dict[str, object]],
        route_map: dict[str, str],
        *,
        end_to_end: bool,
    ) -> None:
        nonlocal summary_index
        routes = [route_map[str(record["mesh"])] for record in subset]
        if end_to_end:
            ratios = [_branch_end_to_end_ratio(record, route, branch_maps) for record, route in zip(subset, routes)]
            scope = f"{evaluation_kind}:router_to_AVE"
        else:
            ratios = [_routed_ratio(record, route) for record, route in zip(subset, routes)]
            scope = f"{evaluation_kind}:top20_budget_matched"
        summary.append(_performance_summary(
            label=label,
            population=population,
            evaluation_kind=scope,
            records=subset,
            routes=routes,
            ratios=ratios,
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed + summary_index,
        ))
        summary_index += 1

    historical_routes = {str(record["mesh"]): _route(record, *historical) for record in records}
    calfit_routes = {str(record["mesh"]): _route(record, *calibration_fit) for record in records}
    allfit_routes = {str(record["mesh"]): _route(record, *all_fit) for record in records}

    for e2e in (False, True):
        append_summary("historical fixed 0.8/2.0", "calibration21", "in_sample_fixed", calibration,
                       historical_routes, end_to_end=e2e)
        append_summary("calibration-only canonical fit", "calibration21", "in_sample_fit", calibration,
                       calfit_routes, end_to_end=e2e)
        append_summary("calibration mesh-LOO threshold refit", "calibration21", "internal_mesh_LOO", calibration,
                       cal_loo_routes, end_to_end=e2e)
        append_summary("calibration group-holdout threshold refit", "calibration21", "internal_group_CV", calibration,
                       cal_logo_routes, end_to_end=e2e)
        append_summary("historical fixed 0.8/2.0", "retrospective_test3", "retrospective_test", test,
                       historical_routes, end_to_end=e2e)
        append_summary("calibration-only canonical fit", "retrospective_test3", "retrospective_test", test,
                       calfit_routes, end_to_end=e2e)
        append_summary("historical fixed 0.8/2.0", "recovered2", "retrospective_recovered", recovered,
                       historical_routes, end_to_end=e2e)
        append_summary("calibration-only canonical fit", "recovered2", "retrospective_recovered", recovered,
                       calfit_routes, end_to_end=e2e)
        append_summary("historical fixed 0.8/2.0", "all26", "retrospective_full_audit", records,
                       historical_routes, end_to_end=e2e)
        append_summary("all26 mesh-LOO threshold refit", "all26", "internal_mesh_LOO_not_external", records,
                       all_loo_routes, end_to_end=e2e)

    record_rows: list[dict[str, object]] = []
    for record in records:
        mesh = str(record["mesh"])
        historical_route = historical_routes[mesh]
        calfit_route = calfit_routes[mesh]
        allfit_route = allfit_routes[mesh]
        row = {
            "mesh": mesh,
            "group": record["group"],
            "split": record["split"],
            "sftf_top20_ratio": record["sftf"],
            "uniform_top20_ratio": record["uniform"],
            "oracle": record["oracle"],
            "catastrophic_sftf_ratio_gt_2": record["catastrophic_sftf_ratio_gt_2"],
            "nn_frac": record["nn_frac"],
            "score_cv": record["score_cv"],
            "historical_fixed_route": historical_route,
            "historical_fixed_top20_ratio": _routed_ratio(record, historical_route),
            "historical_fixed_end_to_end_ave_ratio": _branch_end_to_end_ratio(record, historical_route, branch_maps),
            "calibration_fit_route": calfit_route,
            "calibration_fit_top20_ratio": _routed_ratio(record, calfit_route),
            "calibration_fit_end_to_end_ave_ratio": _branch_end_to_end_ratio(record, calfit_route, branch_maps),
            "all26_insample_fit_route": allfit_route,
            "calibration_mesh_loo_route": cal_loo_routes.get(mesh),
            "calibration_group_cv_route": cal_logo_routes.get(mesh),
            "all26_mesh_loo_route": all_loo_routes[mesh],
        }
        record_rows.append(row)

    historical_on_calibration_plateau = any(
        math.isclose(float(row["nn_frac_min"]), historical[0])
        and math.isclose(float(row["score_cv_max"]), historical[1])
        for row in calibration_plateau
    )
    historical_decision_equivalent = all(
        historical_routes[str(record["mesh"])] == calfit_routes[str(record["mesh"])]
        for record in calibration
    )

    payload: dict[str, object] = {
        "provenance": {
            "historical_router_source": "scripts/experiment_routing_rule_g5.py",
            "ratio_source": str(RATIOS_JSON.relative_to(PROJECT_ROOT)),
            "sftf_ave_source": str(SFTF_AVE_CSV.relative_to(PROJECT_ROOT)),
            "uniform_ave_source": str(UNIFORM_AVE_CSV.relative_to(PROJECT_ROOT)),
            "fresh_router_and_selection_source": str(fresh_runtime_path.relative_to(PROJECT_ROOT)),
            "commit_adding_router_and_C6_C8_data": ROUTER_AND_TEST_DATA_COMMIT,
            "evidence_command": f"git show --name-status {ROUTER_AND_TEST_DATA_COMMIT}",
            "chronology_finding": (
                "The historical 0.8/2.0 router and C6-C8 candidate/grid data were added in the same commit. "
                "No repository evidence establishes that the thresholds were frozen before C6-C8 were observed."
            ),
            "validation_classification": (
                "post-hoc fixed threshold with a retrospectively designated 21/3 split; not a prospective or "
                "chronologically held-out test"
            ),
        },
        "config": {
            "historical_fixed_thresholds": {"nn_frac_min": historical[0], "score_cv_max": historical[1]},
            "calibration_only_canonical_fit": {
                "nn_frac_min": calibration_fit[0], "score_cv_max": calibration_fit[1]
            },
            "all26_insample_canonical_fit": {"nn_frac_min": all_fit[0], "score_cv_max": all_fit[1]},
            "threshold_grid": {"nn_frac_min": T1_GRID.tolist(), "score_cv_max": T2_GRID.tolist()},
            "objective": "lexicographic minimum of mean routed ratio, maximum routed ratio, then SFTF route count",
            "implicit_tie_break": (
                "The historical fitter has no pre-specified numeric-threshold tie-break after equal objective values; "
                "iteration order selects the first plateau point."
            ),
            "calibration_meshes": [str(record["mesh"]) for record in calibration],
            "retrospective_test_meshes": sorted(RETROSPECTIVE_TEST_MESHES),
            "recovered_ratio_valid_meshes_not_used_for_calibration": sorted(RECOVERED_RATIO_VALID_MESHES),
            "bootstrap_resamples": int(bootstrap_resamples),
            "bootstrap_seed": int(bootstrap_seed),
        },
        "threshold_plateau": {
            "calibration21": calibration_plateau,
            "all26": all_plateau,
            "historical_0_8_2_0_on_calibration_optimal_plateau": historical_on_calibration_plateau,
            "historical_and_canonical_calibration_routes_identical_on_calibration21": historical_decision_equivalent,
            "interpretation": (
                "0.8/2.0 is decision-equivalent to the canonical calibration-only fit on the 21 calibration records, "
                "but the code documents no prior tie-break selecting it from the plateau. It changes the C8 route "
                "relative to the canonical calibration fit and therefore remains post hoc unless external dated "
                "pre-registration evidence exists."
            ),
        },
        "summary": summary,
        "records": record_rows,
        "folds": folds,
        "claim_guidance": {
            "supported_wording": (
                "In a retrospectively designated 21/3 split, the historical fixed rule and the canonical "
                "calibration-only fit made identical decisions on the 21 calibration records. On C6-C8, the fixed "
                "rule routed both SFTF ratios above 2.0 to uniform, but the two-case sensitivity estimate has a wide "
                "Wilson interval. The two ratio-valid recovered E-group meshes were not used in the 21-record "
                "calibration and are reported as a separate retrospective audit; recovered E3 has a zero optimum."
            ),
            "unsupported_wording": (
                "Thresholds were frozen before C6-C8 onboarding; external held-out validation; all catastrophic "
                "cases are guaranteed to be detected."
            ),
            "nested_limit": (
                "The signal pair, threshold grid, and test designation were not protected by an outer prospective "
                "split. Mesh-LOO and group-holdout results are internal refitted CV, not nested external validation."
            ),
        },
    }

    _write_json(ETC_DIR / "sftf_routing_threshold_validation.json", payload)
    _write_csv(ETC_DIR / "sftf_routing_threshold_validation_records.csv", record_rows)
    _write_csv(ETC_DIR / "sftf_routing_threshold_validation_folds.csv", folds)
    _write_csv(ETC_DIR / "sftf_routing_threshold_validation_summary.csv", summary)
    return payload


def _uniform_ave_final_row(
    *,
    name: str,
    group: str,
    yaw: np.ndarray,
    pitch: np.ndarray,
    vss: np.ndarray,
    tomo_best: dict[str, float],
    bbox_volume: float,
    face_count: int,
    directions: np.ndarray,
    order: list[int],
) -> dict[str, object]:
    centers = _uniform_centers(directions, order, yaw, pitch, vss)
    base_centers = centers[:DEFAULT_BASE_TOP_K]
    base_result = _local_window_result(
        base_centers, yaw, pitch, vss, radius_degrees=DEFAULT_WINDOW_DEGREES
    )
    base_seed = base_result["seed_best"]
    base_local = base_result["local_best"]
    local_vss = float(base_local["vss"])
    gain = (
        float(base_seed["vss"]) / local_vss
        if base_seed and local_vss > 1e-12
        else float("inf")
    )
    boundary_hit = _cell_on_window_boundary(
        base_centers,
        yaw=float(base_local["yaw"]),
        pitch=float(base_local["pitch"]),
        radius_degrees=DEFAULT_WINDOW_DEGREES,
        edge_margin_degrees=DEFAULT_EDGE_MARGIN_DEGREES,
    )
    triggered, severe, reasons = _detector_flags(
        normalized_local_vss=local_vss / bbox_volume,
        seed_to_local_gain=gain,
        boundary_hit=boundary_hit,
        high_support_fraction=DEFAULT_HIGH_SUPPORT_FRACTION,
        low_gain=DEFAULT_LOW_GAIN,
        high_gain=DEFAULT_HIGH_GAIN,
        boundary_gain=DEFAULT_BOUNDARY_GAIN,
    )
    final_centers = base_centers
    final_result = base_result
    if triggered:
        final_k = DEFAULT_SEVERE_ESCALATE_TOP_K if severe else DEFAULT_ESCALATE_TOP_K
        final_centers = centers[:final_k]
        final_result = _local_window_result(
            final_centers, yaw, pitch, vss, radius_degrees=DEFAULT_WINDOW_DEGREES
        )
    return _stage_row(
        name=name,
        group=group,
        stage="adaptive_final",
        triggered=triggered,
        reasons=reasons,
        centers=final_centers,
        result=final_result,
        tomo_best=tomo_best,
        bbox_volume=bbox_volume,
        face_count=face_count,
        candidate_count=len(directions),
        full_grid_cells=int(vss.size),
        window_degrees=DEFAULT_WINDOW_DEGREES,
    )


def _surrogate_regret_metrics(
    *,
    selected_vss: float,
    optimum_vss: float,
    grid: np.ndarray,
    bbox_volume: float,
) -> dict[str, float]:
    finite = np.asarray(grid[np.isfinite(grid)], dtype=np.float64)
    if finite.size == 0:
        raise ValueError("grid has no finite values")
    grid_min = float(np.min(finite))
    grid_max = float(np.max(finite))
    grid_range = grid_max - grid_min
    raw_difference = float(selected_vss - optimum_vss)
    tolerance = 1e-10 * max(1.0, abs(selected_vss), abs(optimum_vss))
    excess = 0.0 if abs(raw_difference) <= tolerance else raw_difference
    if excess < 0.0:
        raise RuntimeError(f"selected vss {selected_vss} is below exhaustive optimum {optimum_vss}")
    # A conventional <= empirical CDF is misleading when many cells share the
    # exact zero optimum: an optimal selected cell can then have a large CDF.
    # The strict-better fraction is zero for every global optimum regardless of
    # plateau size, while the two tie fractions disclose the plateau itself.
    strict_better_fraction = float(np.mean(finite < selected_vss - tolerance))
    selected_tie_fraction = float(np.mean(np.abs(finite - selected_vss) <= tolerance))
    optimum_tolerance = 1e-10 * max(1.0, abs(optimum_vss))
    optimum_plateau_fraction = float(np.mean(np.abs(finite - optimum_vss) <= optimum_tolerance))
    return {
        "grid_min_vss": grid_min,
        "grid_max_vss": grid_max,
        "grid_range_vss": grid_range,
        "surrogate_excess_vss": excess,
        "absolute_surrogate_error_vss": abs(raw_difference),
        "bbox_normalized_surrogate_excess": excess / bbox_volume,
        "grid_range_normalized_regret": excess / grid_range if grid_range > 1e-12 else 0.0,
        "selected_grid_strictly_better_fraction": strict_better_fraction,
        "selected_value_tie_fraction": selected_tie_fraction,
        "global_optimum_plateau_fraction": optimum_plateau_fraction,
        "selected_is_global_optimum": bool(excess == 0.0),
        "nonnegative_clipped_excess_vss": max(selected_vss, 0.0) - max(optimum_vss, 0.0),
    }


def _metric_summary(
    records: list[dict[str, object]],
    *,
    metric: str,
    resamples: int,
    seed: int,
) -> dict[str, object]:
    values = [float(record[metric]) for record in records]
    ci = _bootstrap_mean_ci(values, resamples=resamples, seed=seed)
    return {
        "metric": metric,
        "record_count": int(len(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "max": float(np.max(values)),
        "mean_ci95_low": ci["ci95_low"],
        "mean_ci95_high": ci["ci95_high"],
    }


def analyze_nonpositive_optima(
    *,
    bootstrap_resamples: int,
    bootstrap_seed: int,
    fresh_runtime: dict[str, dict[str, object]],
    fresh_runtime_path: Path,
) -> dict[str, object]:
    branch_maps_raw = _adaptive_branch_maps()
    directions = _unique_axis_directions(
        _spherical_sample_directions(SUPPORT_FLOW_COARSE_DIRECTION_COUNT)
    )
    order = _farthest_axis_order(directions)

    usable_records: list[dict[str, object]] = []
    stale_or_unusable: list[dict[str, object]] = []
    for grid_path in sorted(G5_CACHE_DIR.glob(f"*{GRID_SUFFIX}")):
        name = grid_path.name[: -len(GRID_SUFFIX)]
        group = _record_group_from_name(name)
        candidate_path = G5_CANDIDATE_DIR / f"{name}{G5_CANDIDATE_SUFFIX}"
        data = np.load(grid_path, allow_pickle=False)
        yaw = np.asarray(data["yaw_values"], dtype=np.float64)
        pitch = np.asarray(data["pitch_values"], dtype=np.float64)
        vss = np.asarray(data["vss_grid"], dtype=np.float64)
        optimum = _tomo_best(yaw, pitch, vss)
        optimum_vss = float(optimum["vss"])

        if not candidate_path.exists():
            stale_or_unusable.append({
                "mesh": name, "group": group, "tomo_best_vss": optimum_vss,
                "reason": "missing_candidate_csv"
            })
            continue
        try:
            _mesh_path_for_stem(name)
        except FileNotFoundError:
            stale_or_unusable.append({
                "mesh": name, "group": group, "tomo_best_vss": optimum_vss,
                "reason": "missing_mesh_file"
            })
            continue

        if name not in fresh_runtime:
            raise RuntimeError(f"fresh runtime lacks usable mesh {name}")
        runtime_row = fresh_runtime[name]
        signals = _fresh_signals(runtime_row)
        route = _route(signals, FIXED_T1, FIXED_T2)
        if route.lower() != str(runtime_row["route"]).lower():
            raise RuntimeError(f"fresh runtime route mismatch for {name}: {route} vs {runtime_row['route']}")
        nonpositive = optimum_vss <= 1e-12

        if nonpositive:
            sftf_rows, detail = analyze_condition(
                grid_path,
                base_top_k=DEFAULT_BASE_TOP_K,
                escalate_top_k=DEFAULT_ESCALATE_TOP_K,
                severe_escalate_top_k=DEFAULT_SEVERE_ESCALATE_TOP_K,
                window_degrees=DEFAULT_WINDOW_DEGREES,
                min_angle_degrees=DEFAULT_MIN_ANGLE_DEGREES,
                high_support_fraction=DEFAULT_HIGH_SUPPORT_FRACTION,
                edge_margin_degrees=DEFAULT_EDGE_MARGIN_DEGREES,
                low_gain=DEFAULT_LOW_GAIN,
                high_gain=DEFAULT_HIGH_GAIN,
                boundary_gain=DEFAULT_BOUNDARY_GAIN,
                include_nonpositive_best=True,
            )
            if detail is None or not sftf_rows:
                stale_or_unusable.append({
                    "mesh": name, "group": group, "tomo_best_vss": optimum_vss,
                    "reason": "SFTF_replay_failed"
                })
                continue
            sftf_row = next(row for row in sftf_rows if row["stage"] == "adaptive_final")
            uniform_row = _uniform_ave_final_row(
                name=name,
                group=group,
                yaw=yaw,
                pitch=pitch,
                vss=vss,
                tomo_best=optimum,
                bbox_volume=float(detail["bbox_volume"]),
                face_count=int(detail["face_count"]),
                directions=directions,
                order=order,
            )
        else:
            if name not in branch_maps_raw["SFTF"] or name not in branch_maps_raw["uniform"]:
                stale_or_unusable.append({
                    "mesh": name, "group": group, "tomo_best_vss": optimum_vss,
                    "reason": "missing_positive_branch_replay"
                })
                continue
            sftf_row = branch_maps_raw["SFTF"][name]
            uniform_row = branch_maps_raw["uniform"][name]

        branches = {"SFTF": sftf_row, "uniform": uniform_row}
        selected = branches[route]
        bbox_volume = float(selected["bbox_volume"])
        branch_selected_vss = float(selected["local_best_vss"])
        selected_vss = float(runtime_row["final_support_tomo_vss"])
        if not math.isclose(selected_vss, branch_selected_vss, rel_tol=0.0, abs_tol=1e-9):
            raise RuntimeError(
                f"fresh selected value differs from stored branch control for {name}: "
                f"{selected_vss} vs {branch_selected_vss}"
            )
        sftf_vss = float(sftf_row["local_best_vss"])
        uniform_vss = float(uniform_row["local_best_vss"])
        metrics = _surrogate_regret_metrics(
            selected_vss=selected_vss,
            optimum_vss=optimum_vss,
            grid=vss,
            bbox_volume=bbox_volume,
        )
        sftf_metrics = _surrogate_regret_metrics(
            selected_vss=sftf_vss,
            optimum_vss=optimum_vss,
            grid=vss,
            bbox_volume=bbox_volume,
        )
        uniform_metrics = _surrogate_regret_metrics(
            selected_vss=uniform_vss,
            optimum_vss=optimum_vss,
            grid=vss,
            bbox_volume=bbox_volume,
        )
        usable_records.append({
            "mesh": name,
            "group": group,
            "split": (
                "recovered_mesh" if name in RECOVERED_RATIO_VALID_MESHES else
                "retrospective_test" if name in RETROSPECTIVE_TEST_MESHES else "calibration"
            ),
            "optimum_sign_class": "nonpositive" if nonpositive else "positive",
            "ratio_defined": not nonpositive,
            "tomo_best_yaw_deg": float(optimum["yaw"]),
            "tomo_best_pitch_deg": float(optimum["pitch"]),
            "tomo_best_vss": optimum_vss,
            "bbox_volume": bbox_volume,
            "nn_frac": float(signals["nn_frac"]),
            "score_cv": float(signals["score_cv"]),
            "fixed_route": route,
            "selected_source": runtime_row["initial_candidate_source"],
            "verification_count": int(runtime_row["final_candidate_center_count"]),
            "escalated": bool(runtime_row["escalated"]),
            "selected_yaw_deg": float(runtime_row["final_yaw_deg"]),
            "selected_pitch_deg": float(runtime_row["final_pitch_deg"]),
            "selected_vss": selected_vss,
            "ratio_to_exhaustive_optimum": selected_vss / optimum_vss if not nonpositive else None,
            "sftf_ave_vss": sftf_vss,
            "uniform_ave_vss": uniform_vss,
            "selected_branch_has_lower_surrogate_excess": bool(
                (route == "SFTF" and sftf_vss <= uniform_vss + 1e-10)
                or (route == "uniform" and uniform_vss <= sftf_vss + 1e-10)
            ),
            "sftf_grid_range_normalized_regret": sftf_metrics["grid_range_normalized_regret"],
            "uniform_grid_range_normalized_regret": uniform_metrics["grid_range_normalized_regret"],
            **metrics,
        })

    positive = [record for record in usable_records if record["optimum_sign_class"] == "positive"]
    nonpositive = [record for record in usable_records if record["optimum_sign_class"] == "nonpositive"]
    if len(positive) != EXPECTED_POSITIVE_COUNT or len(nonpositive) != EXPECTED_NONPOSITIVE_COUNT:
        raise RuntimeError(
            f"expected {EXPECTED_POSITIVE_COUNT} positive + {EXPECTED_NONPOSITIVE_COUNT} nonpositive usable "
            f"records, got {len(positive)} + {len(nonpositive)}"
        )

    metric_names = [
        "surrogate_excess_vss",
        "bbox_normalized_surrogate_excess",
        "grid_range_normalized_regret",
        "selected_grid_strictly_better_fraction",
        "nonnegative_clipped_excess_vss",
    ]
    metric_summary: list[dict[str, object]] = []
    metric_differences: list[dict[str, object]] = []
    for index, metric in enumerate(metric_names):
        for class_index, (label, subset) in enumerate((("positive", positive), ("nonpositive", nonpositive))):
            row = _metric_summary(
                subset,
                metric=metric,
                resamples=bootstrap_resamples,
                seed=bootstrap_seed + 100 + index * 2 + class_index,
            )
            row["optimum_sign_class"] = label
            metric_summary.append(row)
        difference = _bootstrap_difference_ci(
            [float(record[metric]) for record in nonpositive],
            [float(record[metric]) for record in positive],
            resamples=bootstrap_resamples,
            seed=bootstrap_seed + 200 + index,
        )
        difference["metric"] = metric
        difference["contrast"] = "nonpositive_mean_minus_positive_mean"
        metric_differences.append(difference)

    positive_counts = Counter(str(record["group"]) for record in positive)
    nonpositive_counts = Counter(str(record["group"]) for record in nonpositive)
    group_rows: list[dict[str, object]] = []
    for group in sorted(set(positive_counts) | set(nonpositive_counts)):
        n_pos = positive_counts[group]
        n_non = nonpositive_counts[group]
        total = n_pos + n_non
        group_rows.append({
            "group": group,
            "positive_optimum_count": n_pos,
            "nonpositive_optimum_count": n_non,
            "usable_count": total,
            "nonpositive_exclusion_fraction": n_non / total,
        })

    nonpositive_selected_lower = sum(bool(record["selected_branch_has_lower_surrogate_excess"]) for record in nonpositive)
    missed_lower_branch = [
        str(record["mesh"])
        for record in nonpositive
        if not bool(record["selected_branch_has_lower_surrogate_excess"])
    ]
    missed_zero_optimum_with_uniform_recovery = [
        str(record["mesh"])
        for record in nonpositive
        if not bool(record["selected_branch_has_lower_surrogate_excess"])
        and math.isclose(float(record["uniform_ave_vss"]), float(record["tomo_best_vss"]), abs_tol=1e-10)
    ]
    exact_optimum_by_class = {}
    for label, subset in (("positive", positive), ("nonpositive", nonpositive)):
        count = sum(bool(record["selected_is_global_optimum"]) for record in subset)
        exact_optimum_by_class[label] = _wilson_interval(count, len(subset))
    payload: dict[str, object] = {
        "config": {
            "fresh_router_and_selection_source": str(fresh_runtime_path.relative_to(PROJECT_ROOT)),
            "grid_suffix": GRID_SUFFIX,
            "historical_fixed_thresholds": {"nn_frac_min": FIXED_T1, "score_cv_max": FIXED_T2},
            "ave": {
                "base_top_k": DEFAULT_BASE_TOP_K,
                "escalate_top_k": DEFAULT_ESCALATE_TOP_K,
                "severe_escalate_top_k": DEFAULT_SEVERE_ESCALATE_TOP_K,
                "window_degrees": DEFAULT_WINDOW_DEGREES,
                "high_support_fraction": DEFAULT_HIGH_SUPPORT_FRACTION,
                "low_gain": DEFAULT_LOW_GAIN,
                "high_gain": DEFAULT_HIGH_GAIN,
            },
            "bootstrap_resamples": int(bootstrap_resamples),
            "bootstrap_seed": int(bootstrap_seed),
        },
        "population": {
            "stored_grid_count": int(len(usable_records) + len(stale_or_unusable)),
            "usable_mesh_and_candidate_count": int(len(usable_records)),
            "ratio_valid_positive_optimum_count": int(len(positive)),
            "ratio_undefined_nonpositive_optimum_count": int(len(nonpositive)),
            "zero_optimum_count": int(sum(float(record["tomo_best_vss"]) == 0.0 for record in nonpositive)),
            "negative_optimum_count": int(sum(float(record["tomo_best_vss"]) < 0.0 for record in nonpositive)),
            "stale_or_unusable_grid_count": int(len(stale_or_unusable)),
            "stale_or_unusable": stale_or_unusable,
            "group_counts": group_rows,
        },
        "metric_definitions": {
            "surrogate_excess_vss": "selected cached TOMO v_ss minus exhaustive cached-grid minimum",
            "bbox_normalized_surrogate_excess": "surrogate excess divided by axis-aligned mesh bounding-box volume",
            "grid_range_normalized_regret": "surrogate excess divided by max(v_ss)-min(v_ss) on the same cached grid",
            "selected_grid_strictly_better_fraction": (
                "fraction of finite cached-grid cells strictly below selected v_ss; zero means the selected value is globally optimal"
            ),
            "selected_value_tie_fraction": "fraction of finite cached-grid cells tied with the selected v_ss",
            "global_optimum_plateau_fraction": "fraction of finite cached-grid cells tied at the exhaustive optimum",
            "nonnegative_clipped_excess_vss": "max(selected,0)-max(optimum,0), reported only as a sensitivity analysis",
            "epsilon_ratio_decision": (
                "Not reported: for a zero or negative denominator, an epsilon-stabilized ratio changes sign or magnitude "
                "with the arbitrary epsilon scale and does not restore physical validity."
            ),
        },
        "metric_summary": metric_summary,
        "metric_differences": metric_differences,
        "selected_global_optimum_by_class": exact_optimum_by_class,
        "nonpositive_route_audit": {
            "record_count": int(len(nonpositive)),
            "sftf_route_count": int(sum(record["fixed_route"] == "SFTF" for record in nonpositive)),
            "uniform_route_count": int(sum(record["fixed_route"] == "uniform" for record in nonpositive)),
            "escalated_count": int(sum(bool(record["escalated"]) for record in nonpositive)),
            "selected_branch_has_lower_surrogate_excess_count": int(nonpositive_selected_lower),
            "selected_branch_has_lower_surrogate_excess_wilson": _wilson_interval(
                nonpositive_selected_lower, len(nonpositive)
            ),
            "fixed_route_missed_lower_regret_meshes": missed_lower_branch,
            "fixed_route_missed_zero_optimum_recovered_by_uniform": missed_zero_optimum_with_uniform_recovery,
            "selected_global_optimum_count": int(sum(bool(record["selected_is_global_optimum"]) for record in nonpositive)),
            "selected_global_optimum_wilson": _wilson_interval(
                sum(bool(record["selected_is_global_optimum"]) for record in nonpositive), len(nonpositive)
            ),
        },
        "exclusion_bias_assessment": {
            "finding": (
                "Ratio exclusion removes both exact recoveries and failures, but it specifically hides two fixed-router "
                "failures (A1 cube and A3 cylinder): the router selects SFTF and remains far above the zero optimum after "
                "AVE, whereas the uniform AVE branch reaches the zero optimum. Therefore the exclusion is favorable to "
                "the reported worst-case router result and cannot be described as benign."
            ),
            "distribution_limit": (
                "The nonpositive group also contains nine exact selected optima, and bootstrap intervals for the mean "
                "difference in bbox- and range-normalized regret include zero. The evidence supports a worst-case and "
                "composition-bias warning, not a precise population-average bias estimate."
            ),
            "physical_limit": (
                "All 15 nonpositive optima are exactly zero, not negative. The alternative metrics are numerical regret "
                "on the cached TOMO landscapes; do not merge them into positive-denominator ratio means."
            ),
        },
        "records": usable_records,
    }
    _write_json(ETC_DIR / "sftf_nonpositive_optimum_audit.json", payload)
    _write_csv(ETC_DIR / "sftf_nonpositive_optimum_audit_records.csv", usable_records)
    _write_csv(ETC_DIR / "sftf_nonpositive_optimum_audit_group_summary.csv", group_rows)
    metric_rows = []
    for row in metric_summary:
        metric_rows.append({"row_type": "class_summary", **row})
    for row in metric_differences:
        metric_rows.append({"row_type": "class_difference", **row})
    _write_csv(ETC_DIR / "sftf_nonpositive_optimum_audit_metric_summary.csv", metric_rows)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap-resamples", type=int, default=20_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260711)
    parser.add_argument(
        "--fresh-runtime-json",
        type=Path,
        default=DEFAULT_FRESH_RUNTIME_JSON,
        help="completed fresh-candidate runtime JSON used for router signals and deployed selections",
    )
    args = parser.parse_args()
    if args.bootstrap_resamples < 1_000:
        raise SystemExit("--bootstrap-resamples must be at least 1000")

    fresh_runtime_path = args.fresh_runtime_json.resolve()
    fresh_runtime = _load_fresh_runtime(fresh_runtime_path)
    routing = analyze_routing_thresholds(
        bootstrap_resamples=args.bootstrap_resamples,
        bootstrap_seed=args.bootstrap_seed,
        fresh_runtime=fresh_runtime,
        fresh_runtime_path=fresh_runtime_path,
    )
    nonpositive = analyze_nonpositive_optima(
        bootstrap_resamples=args.bootstrap_resamples,
        bootstrap_seed=args.bootstrap_seed,
        fresh_runtime=fresh_runtime,
        fresh_runtime_path=fresh_runtime_path,
    )

    print("=== routing-threshold validation ===")
    config = routing["config"]
    print(f"calibration/test: {len(config['calibration_meshes'])}/{len(config['retrospective_test_meshes'])}")
    print(f"historical fixed: {config['historical_fixed_thresholds']}")
    print(f"calibration canonical: {config['calibration_only_canonical_fit']}")
    for row in routing["summary"]:
        if row["evaluation_kind"].endswith("top20_budget_matched"):
            print(
                f"{row['label']:<44} {row['population']:<19} "
                f"mean={row['mean_ratio']:.3f} max={row['max_ratio']:.3f} "
                f"<=2={row['count_ratio_le_2']}/{row['record_count']}"
            )

    print("\n=== nonpositive-optimum audit ===")
    population = nonpositive["population"]
    print(
        f"stored={population['stored_grid_count']} usable={population['usable_mesh_and_candidate_count']} "
        f"positive={population['ratio_valid_positive_optimum_count']} "
        f"nonpositive={population['ratio_undefined_nonpositive_optimum_count']} "
        f"stale={population['stale_or_unusable_grid_count']}"
    )
    for row in nonpositive["metric_summary"]:
        if row["metric"] in {"grid_range_normalized_regret", "selected_grid_strictly_better_fraction"}:
            print(
                f"{row['metric']:<38} {row['optimum_sign_class']:<11} "
                f"mean={row['mean']:.5f} median={row['median']:.5f} max={row['max']:.5f}"
            )
    print("\nsaved: Experimental/etc/sftf_routing_threshold_validation{.json,_records.csv,_folds.csv,_summary.csv}")
    print("saved: Experimental/etc/sftf_nonpositive_optimum_audit{.json,_records.csv,_group_summary.csv,_metric_summary.csv}")


if __name__ == "__main__":
    main()
