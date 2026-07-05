"""Expand the SFTF rank-tuning learning/validation set.

The earlier rank-tuning checks used only the five Stanford-like Group C meshes
or the positive subset of the G5 critical-angle-60 cache.  This script audits
the cached five-group TOMO_CPU sweeps, builds a manifest of usable conditions,
and runs nested CV on a larger set of mesh/critical-angle records.

By default it uses the 3 degree TOMO_CPU grids at critical angles
0, 30, 45, and 60 degrees.  Splits are group-held-out by default, so all
conditions for a shape family stay together and the expanded set does not leak
the same family into train and validation.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.experiment_rank_tuning_nested_group_cv import (  # noqa: E402
    DEFAULT_ALPHA_GRID,
    G5_CANDIDATE_DIR,
    G5_CANDIDATE_SUFFIX,
    G5_CACHE_DIR,
    MODEL_SPECS,
    _make_record,
    _parse_alpha_grid,
    run_nested_cv,
)
from scripts.regenerate_sftf_vs_saved_tomo_summary import MESH_DIR, _tomo_best  # noqa: E402

GRID_RE = re.compile(r"^(?P<stem>.+)_tomo_cpu_(?P<angle_step>[^_]+)_(?P<critical_angle>[^_]+)\.npz$")
DEFAULT_ANGLE_STEPS = ("3deg",)
DEFAULT_CRITICAL_ANGLES = ("0deg", "30deg", "45deg", "60deg")


def _parse_token_list(value: str) -> list[str]:
    tokens = [item.strip() for item in value.split(",") if item.strip()]
    if not tokens:
        raise argparse.ArgumentTypeError("expected a comma-separated non-empty list")
    return sorted(set(tokens), key=tokens.index)


def _family_from_stem(stem: str) -> str:
    parts = stem.split("_")
    return parts[1][0].upper() if len(parts) > 1 and parts[1] else "?"


def _group_id_from_stem(stem: str) -> str:
    parts = stem.split("_")
    return parts[1] if len(parts) > 1 and parts[1] else "?"


def _grid_info(path: Path) -> dict[str, str] | None:
    match = GRID_RE.match(path.name)
    if match is None:
        return None
    return {
        "stem": match.group("stem"),
        "angle_step": match.group("angle_step"),
        "critical_angle": match.group("critical_angle"),
    }


def _candidate_count(path: Path) -> int | None:
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _row in csv.DictReader(handle))


def _tomo_best_vss(path: Path) -> float:
    data = np.load(path, allow_pickle=True)
    best = _tomo_best(
        np.asarray(data["yaw_values"], dtype=np.float64),
        np.asarray(data["pitch_values"], dtype=np.float64),
        np.asarray(data["vss_grid"], dtype=np.float64),
    )
    return float(best["vss"])


def build_manifest(
    *,
    angle_steps: list[str],
    critical_angles: list[str],
    include_nonpositive_best: bool,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    wanted_steps = set(angle_steps)
    wanted_angles = set(critical_angles)

    for grid_path in sorted(G5_CACHE_DIR.glob("*_tomo_cpu_*.npz")):
        info = _grid_info(grid_path)
        if info is None:
            continue
        if info["angle_step"] not in wanted_steps or info["critical_angle"] not in wanted_angles:
            continue

        stem = info["stem"]
        candidate_path = G5_CANDIDATE_DIR / f"{stem}{G5_CANDIDATE_SUFFIX}"
        has_candidate = candidate_path.exists()
        candidate_count = _candidate_count(candidate_path)
        tomo_best_vss = _tomo_best_vss(grid_path)

        if not has_candidate:
            usable = False
            reason = "missing_candidate_csv"
        elif not include_nonpositive_best and tomo_best_vss <= 1e-12:
            usable = False
            reason = "nonpositive_tomo_best"
        elif not math.isfinite(tomo_best_vss):
            usable = False
            reason = "nonfinite_tomo_best"
        else:
            usable = True
            reason = "usable"

        rows.append(
            {
                "stem": stem,
                "family": _family_from_stem(stem),
                "group_id": _group_id_from_stem(stem),
                "angle_step": info["angle_step"],
                "critical_angle": info["critical_angle"],
                "grid_path": str(grid_path.relative_to(PROJECT_ROOT)),
                "candidate_path": str(candidate_path.relative_to(PROJECT_ROOT)) if has_candidate else "",
                "has_candidate": bool(has_candidate),
                "candidate_count": candidate_count if candidate_count is not None else "",
                "tomo_best_vss": tomo_best_vss,
                "usable": bool(usable),
                "skip_reason": reason,
            }
        )
    return rows


def _split_group_for_record(row: dict[str, object], split: str) -> str:
    if split == "family":
        return str(row["family"])
    if split == "mesh":
        return str(row["stem"])
    raise ValueError(f"unsupported split: {split}")


def load_expanded_records(
    manifest_rows: list[dict[str, object]],
    *,
    split: str,
    include_nonpositive_best: bool,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for row in manifest_rows:
        if not bool(row["usable"]):
            continue
        stem = str(row["stem"])
        grid_path = PROJECT_ROOT / str(row["grid_path"])
        candidate_path = PROJECT_ROOT / str(row["candidate_path"])
        condition = f"{row['angle_step']}_{row['critical_angle']}"
        record = _make_record(
            name=f"{stem}_{condition}",
            group=_split_group_for_record(row, split),
            grid_path=grid_path,
            candidate_path=candidate_path,
            source=f"g5_{condition}",
            skip_nonpositive_best=not include_nonpositive_best,
        )
        if record is None:
            continue
        record["mesh_stem"] = stem
        record["family"] = row["family"]
        record["group_id"] = row["group_id"]
        record["angle_step"] = row["angle_step"]
        record["critical_angle"] = row["critical_angle"]
        record["split_group"] = record["group"]
        records.append(record)
    return records


def _manifest_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    total = len(rows)
    usable = [row for row in rows if bool(row["usable"])]
    by_condition: dict[str, Counter[str]] = defaultdict(Counter)
    by_family: dict[str, Counter[str]] = defaultdict(Counter)
    skip_reasons = Counter(str(row["skip_reason"]) for row in rows)

    for row in rows:
        condition = f"{row['angle_step']}_{row['critical_angle']}"
        by_condition[condition]["total"] += 1
        by_condition[condition]["usable"] += int(bool(row["usable"]))
        by_family[str(row["family"])]["total"] += 1
        by_family[str(row["family"])]["usable"] += int(bool(row["usable"]))

    return {
        "total_conditions": total,
        "usable_conditions": len(usable),
        "unique_usable_meshes": len({str(row["stem"]) for row in usable}),
        "unique_usable_families": sorted({str(row["family"]) for row in usable}),
        "skip_reasons": dict(skip_reasons),
        "by_condition": {key: dict(value) for key, value in sorted(by_condition.items())},
        "by_family": {key: dict(value) for key, value in sorted(by_family.items())},
    }


def _record_summary(records: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for record in records:
        rows.append(
            {
                "name": record["name"],
                "mesh_stem": record["mesh_stem"],
                "family": record["family"],
                "group_id": record["group_id"],
                "split_group": record["split_group"],
                "source": record["source"],
                "angle_step": record["angle_step"],
                "critical_angle": record["critical_angle"],
                "grid_path": record["grid_path"],
                "candidate_path": record["candidate_path"],
                "tomo_best_vss": float(record["tomo_best_vss"]),
                "oracle_ratio": float(record["oracle_ratio"]),
                "untuned_J_ratio": float(record["untuned_J_ratio"]),
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_cv_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CV CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _metric_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    metrics = [
        "oracle",
        "untuned_J",
        "raw_R+B",
        "raw_R+P+B",
        "B_nested",
        "R+B_nested",
        "R+P+B_nested",
        "full7_nested",
        "selected",
    ]
    summary: list[dict[str, object]] = []
    for metric in metrics:
        values = np.asarray([float(row[metric]) for row in rows], dtype=np.float64)
        summary.append(
            {
                "metric": metric,
                "count": int(values.size),
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "p80": float(np.percentile(values, 80)),
                "p90": float(np.percentile(values, 90)),
                "max": float(np.max(values)),
                "count_le_1_25": int(np.sum(values <= 1.25)),
                "count_le_1_50": int(np.sum(values <= 1.50)),
                "count_le_2_00": int(np.sum(values <= 2.00)),
            }
        )
    return summary


def _outlier_rows(rows: list[dict[str, object]], *, threshold: float = 10.0) -> list[dict[str, object]]:
    outliers = []
    for row in rows:
        selected = float(row["selected"])
        if selected <= threshold:
            continue
        outliers.append(
            {
                "name": row["name"],
                "source": row["source"],
                "outer_key": row["outer_key"],
                "oracle": float(row["oracle"]),
                "raw_R+B": float(row["raw_R+B"]),
                "B_nested": float(row["B_nested"]),
                "selected": selected,
                "selected_model": row["selected_model"],
            }
        )
    return sorted(outliers, key=lambda row: float(row["selected"]), reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--angle-steps", type=_parse_token_list, default=list(DEFAULT_ANGLE_STEPS))
    parser.add_argument("--critical-angles", type=_parse_token_list, default=list(DEFAULT_CRITICAL_ANGLES))
    parser.add_argument("--split", choices=["family", "mesh"], default="family")
    parser.add_argument("--outer", choices=["group"], default="group")
    parser.add_argument("--inner", choices=["group"], default="group")
    parser.add_argument("--include-nonpositive-best", action="store_true")
    parser.add_argument("--alpha-grid", type=_parse_alpha_grid, default=list(DEFAULT_ALPHA_GRID))
    parser.add_argument("--output-stem", default="sftf_rank_tuning_expanded_g5_multiangle")
    args = parser.parse_args()

    manifest_rows = build_manifest(
        angle_steps=args.angle_steps,
        critical_angles=args.critical_angles,
        include_nonpositive_best=args.include_nonpositive_best,
    )
    if not manifest_rows:
        raise SystemExit("no cached TOMO_CPU conditions matched the requested filters")

    records = load_expanded_records(
        manifest_rows,
        split=args.split,
        include_nonpositive_best=args.include_nonpositive_best,
    )
    if len(records) < 3:
        raise SystemExit(f"need at least 3 usable records, got {len(records)}")

    manifest_summary = _manifest_summary(manifest_rows)
    print(
        f"expanded set: usable={len(records)}/{len(manifest_rows)} "
        f"meshes={manifest_summary['unique_usable_meshes']} "
        f"families={','.join(manifest_summary['unique_usable_families'])} "
        f"split={args.split}",
        flush=True,
    )
    for condition, counts in manifest_summary["by_condition"].items():
        print(f"  {condition}: usable {counts.get('usable', 0)}/{counts.get('total', 0)}", flush=True)

    cv = run_nested_cv(records, outer_mode=args.outer, inner_mode=args.inner, alpha_grid=args.alpha_grid)
    print("\n=== expanded mean best-of-3 ratio ===")
    for key, value in cv["means"].items():
        print(f"{key:<14} {value:.3f}", flush=True)

    manifest_path = MESH_DIR / f"{args.output_stem}_manifest.csv"
    records_path = MESH_DIR / f"{args.output_stem}_records.csv"
    summary_path = MESH_DIR / f"{args.output_stem}_{args.split}_cv_summary.csv"
    csv_path = MESH_DIR / f"{args.output_stem}_{args.split}_cv.csv"
    json_path = MESH_DIR / f"{args.output_stem}_{args.split}_cv.json"
    cv_rows = list(cv["per_record"])
    metric_summary = _metric_summary(cv_rows)
    outliers = _outlier_rows(cv_rows)

    _write_csv(manifest_path, manifest_rows)
    _write_csv(records_path, _record_summary(records))
    _write_csv(summary_path, metric_summary)
    _write_cv_csv(csv_path, cv_rows)
    json_path.write_text(
        json.dumps(
            {
                "config": {
                    "angle_steps": args.angle_steps,
                    "critical_angles": args.critical_angles,
                    "split": args.split,
                    "outer_mode": args.outer,
                    "inner_mode": args.inner,
                    "alpha_grid": args.alpha_grid,
                    "include_nonpositive_best": args.include_nonpositive_best,
                    "model_specs": MODEL_SPECS,
                },
                "manifest_summary": manifest_summary,
                "metric_summary": metric_summary,
                "selected_outliers_gt_10": outliers,
                "records": _record_summary(records),
                "cv": cv,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        "\nsaved: "
        + ", ".join(
            str(path.relative_to(PROJECT_ROOT))
            for path in (manifest_path, records_path, summary_path, csv_path, json_path)
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
