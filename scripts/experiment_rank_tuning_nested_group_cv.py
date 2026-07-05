"""Nested CV and group CV for reduced SFTF rank-tuning feature sets.

The older calibration used all seven rank-normalized features
``[J, R, P, B, H, S, sigma1]``.  This experiment compares that full model
against smaller, more defensible feature sets such as ``R+B`` and ``R+P+B``.

The script reads precomputed SFTF candidate CSV files and saved TOMO_CPU grids,
so it does not need to recompute SFTF candidates or run the TOMO DLL.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField.support_flow_tensor_field import _rank_normalized_feature  # noqa: E402
from scripts.analyze_sftf_feature_correlations import _best_of_k_ratio  # noqa: E402
from scripts.regenerate_sftf_vs_saved_tomo_summary import (  # noqa: E402
    GRID_SUFFIX,
    MESH_DIR,
    _signed_orientation,
    _tomo_best,
)

FEATURE_LABELS = ["J", "R", "P", "B", "H", "S", "s1"]
FEATURE_TO_COL = {label: index for index, label in enumerate(FEATURE_LABELS)}
MODEL_SPECS = {
    "B": ["B"],
    "R+B": ["R", "B"],
    "R+P+B": ["R", "P", "B"],
    "full7": FEATURE_LABELS,
}
DEFAULT_ALPHA_GRID = (0.01, 0.1, 1.0, 10.0, 100.0)
G5_CACHE_DIR = PROJECT_ROOT / "Experimental" / "G5Test" / "tomo_cpu_cache"
G5_CANDIDATE_DIR = PROJECT_ROOT / "Experimental" / "G5Test" / "SFTF_result"
G5_GRID_SUFFIX = "_tomo_cpu_3deg_60deg.npz"
G5_CANDIDATE_SUFFIX = "_candidates.csv"


def _ratio(value: float, reference: float) -> float:
    return value / reference if reference > 1e-12 else float("inf")


def _record_group_from_name(name: str) -> str:
    parts = name.split("_")
    return parts[1][0].upper() if len(parts) > 1 and parts[1] else "?"


def _read_candidate_csv(path: Path) -> dict[str, np.ndarray]:
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    if not rows:
        raise ValueError(f"empty candidate CSV: {path}")

    def col(name: str) -> np.ndarray:
        return np.asarray([float(row[name]) for row in rows], dtype=np.float64)

    directions = np.column_stack([col("dir_x"), col("dir_y"), col("dir_z")])
    sigma1, sigma2, sigma3 = col("sigma1"), col("sigma2"), col("sigma3")
    return {
        "directions": directions,
        "R": col("rayleigh"),
        "P": col("pair"),
        "B": col("bed"),
        "H": col("hit"),
        "S": sigma1 + sigma2 + sigma3,
        "s1": sigma1,
    }


def _make_record(
    *,
    name: str,
    group: str,
    grid_path: Path,
    candidate_path: Path,
    source: str,
    skip_nonpositive_best: bool,
) -> dict[str, object] | None:
    grid_data = np.load(grid_path, allow_pickle=True)
    yaw_values = np.asarray(grid_data["yaw_values"], dtype=np.float64)
    pitch_values = np.asarray(grid_data["pitch_values"], dtype=np.float64)
    vss_grid = np.asarray(grid_data["vss_grid"], dtype=np.float64)
    tomo_best = _tomo_best(yaw_values, pitch_values, vss_grid)
    tomo_best_vss = float(tomo_best["vss"])
    if skip_nonpositive_best and tomo_best_vss <= 1e-12:
        return None

    candidate = _read_candidate_csv(candidate_path)
    directions = np.asarray(candidate["directions"], dtype=np.float64)
    raw = np.column_stack(
        [
            candidate["R"] + candidate["P"] + candidate["B"],
            candidate["R"],
            candidate["P"],
            candidate["B"],
            candidate["H"],
            candidate["S"],
            candidate["s1"],
        ]
    )
    rank_features = np.column_stack([_rank_normalized_feature(raw[:, index]) for index in range(raw.shape[1])])
    signed_vss = np.asarray(
        [_signed_orientation(direction, yaw_values, pitch_values, vss_grid)[1]["vss"] for direction in directions],
        dtype=np.float64,
    )
    return {
        "name": name,
        "group": group,
        "source": source,
        "grid_path": str(grid_path.relative_to(PROJECT_ROOT)),
        "candidate_path": str(candidate_path.relative_to(PROJECT_ROOT)),
        "rank_features": rank_features,
        "raw_features": raw,
        "directions": directions,
        "signed_vss": signed_vss,
        "target": _rank_normalized_feature(signed_vss),
        "tomo_best_yaw": float(tomo_best["yaw"]),
        "tomo_best_pitch": float(tomo_best["pitch"]),
        "tomo_best_vss": tomo_best_vss,
        "oracle_ratio": _ratio(float(np.nanmin(signed_vss)), tomo_best_vss),
        "untuned_J_ratio": _best_of_k_ratio(raw[:, FEATURE_TO_COL["J"]], directions, signed_vss, tomo_best_vss),
    }


def load_stanford_records(*, include_happy: bool) -> tuple[list[dict[str, object]], list[str]]:
    records: list[dict[str, object]] = []
    skipped: list[str] = []
    for grid_path in sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}")):
        stem = grid_path.name[: -len(GRID_SUFFIX)]
        if not include_happy and "happy" in stem.lower():
            skipped.append(f"{stem}: excluded happy")
            continue
        if not stem.startswith("(") or ")" not in stem:
            skipped.append(f"{stem}: cannot map to Group_C candidate CSV")
            continue
        mesh_id, plain = stem[1:].split(")", 1)
        candidate_path = G5_CANDIDATE_DIR / f"Group_C{mesh_id}_{plain}{G5_CANDIDATE_SUFFIX}"
        if not candidate_path.exists():
            skipped.append(f"{stem}: missing {candidate_path.name}")
            continue
        record = _make_record(
            name=stem,
            group=f"C{mesh_id}",
            grid_path=grid_path,
            candidate_path=candidate_path,
            source="stanford_1deg",
            skip_nonpositive_best=True,
        )
        if record is None:
            skipped.append(f"{stem}: nonpositive TOMO best")
            continue
        records.append(record)
    return records, skipped


def _source_label_for_g5_suffix(grid_suffix: str) -> str:
    if grid_suffix == G5_GRID_SUFFIX:
        return "g5_3deg"
    token = grid_suffix
    if token.startswith("_tomo_cpu_"):
        token = token[len("_tomo_cpu_") :]
    if token.endswith(".npz"):
        token = token[: -len(".npz")]
    return f"g5_{token}"


def load_g5_records(
    *,
    skip_nonpositive_best: bool,
    grid_suffix: str = G5_GRID_SUFFIX,
) -> tuple[list[dict[str, object]], list[str]]:
    records: list[dict[str, object]] = []
    skipped: list[str] = []
    source_label = _source_label_for_g5_suffix(grid_suffix)
    for grid_path in sorted(G5_CACHE_DIR.glob(f"*{grid_suffix}")):
        stem = grid_path.name[: -len(grid_suffix)]
        candidate_path = G5_CANDIDATE_DIR / f"{stem}{G5_CANDIDATE_SUFFIX}"
        if not candidate_path.exists():
            skipped.append(f"{stem}: missing candidate CSV")
            continue
        record = _make_record(
            name=stem,
            group=_record_group_from_name(stem),
            grid_path=grid_path,
            candidate_path=candidate_path,
            source=source_label,
            skip_nonpositive_best=skip_nonpositive_best,
        )
        if record is None:
            skipped.append(f"{stem}: nonpositive TOMO best")
            continue
        records.append(record)
    return records, skipped


def _cols_for_model(model: str) -> list[int]:
    return [FEATURE_TO_COL[label] for label in MODEL_SPECS[model]]


def _ridge_fit(records: list[dict[str, object]], *, model: str, alpha: float) -> np.ndarray:
    cols = _cols_for_model(model)
    x = np.vstack([np.asarray(record["rank_features"], dtype=np.float64)[:, cols] for record in records])
    y = np.concatenate([np.asarray(record["target"], dtype=np.float64) for record in records])
    gram = x.T @ x + float(alpha) * np.eye(len(cols))
    sub = np.linalg.solve(gram, x.T @ y)
    weights = np.zeros(len(FEATURE_LABELS), dtype=np.float64)
    weights[cols] = sub
    return weights


def _ratio_for_weights(record: dict[str, object], weights: np.ndarray) -> float:
    scores = np.asarray(record["rank_features"], dtype=np.float64) @ weights
    return _best_of_k_ratio(
        scores,
        np.asarray(record["directions"], dtype=np.float64),
        np.asarray(record["signed_vss"], dtype=np.float64),
        float(record["tomo_best_vss"]),
    )


def _raw_ratio(record: dict[str, object], labels: list[str]) -> float:
    raw = np.asarray(record["raw_features"], dtype=np.float64)
    scores = np.sum(raw[:, [_cols_for_label(label) for label in labels]], axis=1)
    return _best_of_k_ratio(
        scores,
        np.asarray(record["directions"], dtype=np.float64),
        np.asarray(record["signed_vss"], dtype=np.float64),
        float(record["tomo_best_vss"]),
    )


def _cols_for_label(label: str) -> int:
    return FEATURE_TO_COL[label]


def _make_folds(records: list[dict[str, object]], mode: str) -> list[dict[str, object]]:
    if mode == "mesh":
        keys = [str(record["name"]) for record in records]
    elif mode == "group":
        keys = sorted({str(record["group"]) for record in records})
    else:
        raise ValueError(f"unsupported CV mode: {mode}")

    folds = []
    for key in keys:
        if mode == "mesh":
            test = [record for record in records if str(record["name"]) == key]
            train = [record for record in records if str(record["name"]) != key]
        else:
            test = [record for record in records if str(record["group"]) == key]
            train = [record for record in records if str(record["group"]) != key]
        if train and test:
            folds.append({"key": key, "train": train, "test": test})
    return folds


def _inner_cv_score(
    train_records: list[dict[str, object]],
    *,
    inner_mode: str,
    model: str,
    alpha: float,
) -> float:
    folds = _make_folds(train_records, inner_mode)
    if not folds:
        weights = _ridge_fit(train_records, model=model, alpha=alpha)
        return float(np.mean([_ratio_for_weights(record, weights) for record in train_records]))

    ratios = []
    for fold in folds:
        weights = _ridge_fit(fold["train"], model=model, alpha=alpha)
        ratios.extend(_ratio_for_weights(record, weights) for record in fold["test"])
    return float(np.mean(ratios)) if ratios else float("inf")


def _select_alpha(
    train_records: list[dict[str, object]],
    *,
    inner_mode: str,
    model: str,
    alpha_grid: list[float],
) -> tuple[float, float]:
    scores = [
        (_inner_cv_score(train_records, inner_mode=inner_mode, model=model, alpha=alpha), alpha)
        for alpha in alpha_grid
    ]
    score, alpha = min(scores, key=lambda item: (item[0], item[1]))
    return alpha, score


def run_nested_cv(
    records: list[dict[str, object]],
    *,
    outer_mode: str,
    inner_mode: str,
    alpha_grid: list[float],
) -> dict[str, object]:
    folds = _make_folds(records, outer_mode)
    model_names = list(MODEL_SPECS)
    per_record: list[dict[str, object]] = []
    per_fold: list[dict[str, object]] = []

    for fold in folds:
        selected: dict[str, dict[str, float]] = {}
        for model in model_names:
            alpha, inner_score = _select_alpha(
                fold["train"],
                inner_mode=inner_mode,
                model=model,
                alpha_grid=alpha_grid,
            )
            selected[model] = {"alpha": alpha, "inner_score": inner_score}

        best_model = min(
            model_names,
            key=lambda name: (
                selected[name]["inner_score"],
                len(MODEL_SPECS[name]),
                selected[name]["alpha"],
                name,
            ),
        )
        fold_result: dict[str, object] = {
            "outer_key": fold["key"],
            "test_count": len(fold["test"]),
            "selected_model": best_model,
            "selected_alpha": selected[best_model]["alpha"],
            "selected_inner_score": selected[best_model]["inner_score"],
            "model_selection": selected,
        }
        per_fold.append(fold_result)

        weights_by_model = {
            model: _ridge_fit(fold["train"], model=model, alpha=selected[model]["alpha"])
            for model in model_names
        }
        selected_weights = weights_by_model[best_model]
        for record in fold["test"]:
            row = {
                "source": record["source"],
                "outer_key": fold["key"],
                "name": record["name"],
                "group": record["group"],
                "oracle": float(record["oracle_ratio"]),
                "untuned_J": float(record["untuned_J_ratio"]),
                "raw_R+B": _raw_ratio(record, ["R", "B"]),
                "raw_R+P+B": _raw_ratio(record, ["R", "P", "B"]),
                "selected_model": best_model,
                "selected_alpha": selected[best_model]["alpha"],
                "selected": _ratio_for_weights(record, selected_weights),
            }
            for model in model_names:
                row[f"{model}_nested"] = _ratio_for_weights(record, weights_by_model[model])
                row[f"{model}_alpha"] = selected[model]["alpha"]
                row[f"{model}_inner_score"] = selected[model]["inner_score"]
            per_record.append(row)

    metric_names = [
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
    means = {
        metric: float(np.mean([float(row[metric]) for row in per_record]))
        for metric in metric_names
        if per_record
    }
    return {
        "outer_mode": outer_mode,
        "inner_mode": inner_mode,
        "alpha_grid": alpha_grid,
        "means": means,
        "per_fold": per_fold,
        "per_record": per_record,
    }


def _parse_alpha_grid(value: str) -> list[float]:
    alphas = [float(item.strip()) for item in value.split(",") if item.strip()]
    if not alphas or any(alpha <= 0.0 or not math.isfinite(alpha) for alpha in alphas):
        raise argparse.ArgumentTypeError("alpha grid must contain positive finite floats")
    return sorted(set(alphas))


def _write_outputs(result: dict[str, object], output_stem: str) -> tuple[Path, Path]:
    json_path = MESH_DIR / f"{output_stem}.json"
    csv_path = MESH_DIR / f"{output_stem}.csv"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    rows = list(result["cv"]["per_record"])
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return csv_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["stanford", "g5"], default="stanford")
    parser.add_argument("--outer", choices=["mesh", "group"], default=None)
    parser.add_argument("--inner", choices=["mesh", "group"], default=None)
    parser.add_argument("--include-happy", action="store_true", help="Only applies to the Stanford 1 degree dataset.")
    parser.add_argument(
        "--include-nonpositive-best",
        action="store_true",
        help="Keep G5 records with TOMO best <= 0; ratios will be inf.",
    )
    parser.add_argument(
        "--g5-grid-suffix",
        default=G5_GRID_SUFFIX,
        help="Only applies to the G5 dataset.",
    )
    parser.add_argument("--alpha-grid", type=_parse_alpha_grid, default=list(DEFAULT_ALPHA_GRID))
    parser.add_argument("--output-stem", default=None)
    args = parser.parse_args()

    if args.dataset == "stanford":
        records, skipped = load_stanford_records(include_happy=args.include_happy)
        outer_mode = args.outer or "mesh"
        inner_mode = args.inner or "mesh"
        default_stem = "sftf_rank_tuning_nested_cv_stanford"
        if args.include_happy:
            default_stem += "_with_happy"
    else:
        records, skipped = load_g5_records(
            skip_nonpositive_best=not args.include_nonpositive_best,
            grid_suffix=args.g5_grid_suffix,
        )
        outer_mode = args.outer or "group"
        inner_mode = args.inner or "group"
        default_stem = "sftf_rank_tuning_group_cv_g5"

    if len(records) < 3:
        raise SystemExit(f"need at least 3 usable records, got {len(records)}")

    print(
        f"dataset={args.dataset} records={len(records)} outer={outer_mode} inner={inner_mode} "
        f"alphas={args.alpha_grid}",
        flush=True,
    )
    if skipped:
        print(f"skipped={len(skipped)}", flush=True)
    cv = run_nested_cv(records, outer_mode=outer_mode, inner_mode=inner_mode, alpha_grid=args.alpha_grid)
    print("=== mean best-of-3 ratio ===")
    for key, value in cv["means"].items():
        print(f"{key:<14} {value:.3f}")

    result = {
        "config": {
            "dataset": args.dataset,
            "outer_mode": outer_mode,
            "inner_mode": inner_mode,
            "alpha_grid": args.alpha_grid,
            "include_happy": args.include_happy,
            "include_nonpositive_best": args.include_nonpositive_best,
            "g5_grid_suffix": args.g5_grid_suffix,
            "feature_labels": FEATURE_LABELS,
            "model_specs": MODEL_SPECS,
        },
        "records": [
            {
                "name": record["name"],
                "group": record["group"],
                "source": record["source"],
                "grid_path": record["grid_path"],
                "candidate_path": record["candidate_path"],
                "tomo_best_vss": record["tomo_best_vss"],
                "oracle_ratio": record["oracle_ratio"],
                "untuned_J_ratio": record["untuned_J_ratio"],
            }
            for record in records
        ],
        "skipped": skipped,
        "cv": cv,
    }
    output_stem = args.output_stem or default_stem
    csv_path, json_path = _write_outputs(result, output_stem)
    print(f"\nsaved: {csv_path.relative_to(PROJECT_ROOT)}, {json_path.relative_to(PROJECT_ROOT)}", flush=True)


if __name__ == "__main__":
    main()
