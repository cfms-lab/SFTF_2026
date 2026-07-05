from __future__ import annotations

import importlib.util
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import trimesh

from python_src.tse6_config import COOLWARM_COLORSCALE, make_tse6_config, mesh_label, print_time
from python_src.VisFacePair import VisFacePair


MESH_PATHS = [
    "./Experimental/etc/(7)Bunny_1k.obj",
    "./Experimental/etc/(3)manikin.ply",
]

FILAMENT_CRITICAL_ANGLE = 60.0
ANGLE_STEP = 10.0
ORIENTATION_SAMPLES_PER_PAIR = 16
MAX_PAIRS_PER_MESH = 250
PAIR_OVERSAMPLE_FACTOR = 4
CONTOUR_PAIR_LIMIT = 200
RANDOM_SEED = 20260619
RIDGE_LAMBDA = 1e-4
TARGET_COMPONENTS = ("v_ss", "v_nv")
OUTPUT_DIR = Path("comparison_outputs") / "tri_pair_shadow_regression"
MODEL_PATH = OUTPUT_DIR / "ridge_model_tomo_yaw_pitch_0_360_vss_vnv.npz"


def load_tri_pair_shadow_functions():
    module_path = Path(__file__).with_name("[function]tri_pair_shadow.py")
    spec = importlib.util.spec_from_file_location("tri_pair_shadow_functions", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"failed to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SHADOW = load_tri_pair_shadow_functions()


@dataclass
class MeshTrainingData:
    mesh_path: str
    label: str
    mesh: trimesh.Trimesh
    center: np.ndarray
    pair_faces: np.ndarray
    x: np.ndarray
    y: np.ndarray


@dataclass
class RidgeModel:
    mean: np.ndarray
    scale: np.ndarray
    weights: np.ndarray
    target_components: tuple[str, ...] = TARGET_COMPONENTS

    def predict(self, features: np.ndarray) -> np.ndarray:
        features = np.asarray(features, dtype=np.float64)
        was_1d = features.ndim == 1
        if was_1d:
            features = features[None, :]
        standardized = (features - self.mean) / self.scale
        design = np.column_stack((np.ones(len(standardized), dtype=np.float64), standardized))
        prediction = np.maximum(0.0, design @ self.weights)
        return prediction[0] if was_1d else prediction

    def predict_components(self, features: np.ndarray) -> dict[str, float]:
        values = np.asarray(self.predict(features), dtype=np.float64)
        return {component: float(values[idx]) for idx, component in enumerate(self.target_components)}


def save_ridge_model(model: RidgeModel, path: Path = MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        mean=model.mean,
        scale=model.scale,
        weights=model.weights,
        target_components=np.asarray(model.target_components),
    )
    print(f"wrote {path.resolve()}")


def load_ridge_model(path: Path = MODEL_PATH) -> RidgeModel:
    with np.load(path, allow_pickle=False) as data:
        target_components = (
            tuple(str(item) for item in np.asarray(data["target_components"]))
            if "target_components" in data.files
            else ("v_ss",)
        )
        return RidgeModel(
            mean=np.asarray(data["mean"], dtype=np.float64),
            scale=np.asarray(data["scale"], dtype=np.float64),
            weights=np.asarray(data["weights"], dtype=np.float64),
            target_components=target_components,
        )


def mesh_rotation_center(mesh: trimesh.Trimesh) -> np.ndarray:
    return np.asarray(mesh.vertices, dtype=np.float64).mean(axis=0)


def angle_grid(angle_step: float) -> tuple[np.ndarray, np.ndarray]:
    interval_count = int(360.0 / angle_step) + 1
    yaws = np.linspace(0.0, 360.0, num=interval_count, endpoint=True, dtype=np.float64)
    pitches = np.linspace(0.0, 360.0, num=interval_count, endpoint=True, dtype=np.float64)
    return yaws, pitches


def triangle_features(tri_a: np.ndarray, tri_b: np.ndarray, center: np.ndarray) -> np.ndarray:
    normal_a = SHADOW.triangle_normal(tri_a)
    normal_b = SHADOW.triangle_normal(tri_b)
    area_a = SHADOW.triangle_area(tri_a)
    area_b = SHADOW.triangle_area(tri_b)
    center_a = tri_a.mean(axis=0)
    center_b = tri_b.mean(axis=0)
    delta = center_b - center_a
    distance = max(float(np.linalg.norm(delta)), 1e-12)
    direction = delta / distance
    vertical = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    extent_a = float(np.max(np.linalg.norm(tri_a - center_a, axis=1)))
    extent_b = float(np.max(np.linalg.norm(tri_b - center_b, axis=1)))
    return np.array(
        [
            area_a,
            area_b,
            np.sqrt(max(area_a * area_b, 0.0)),
            extent_a,
            extent_b,
            distance,
            float(np.dot(normal_a, normal_b)),
            abs(float(np.dot(normal_a, vertical))),
            abs(float(np.dot(normal_b, vertical))),
            float(np.dot(direction, vertical)),
            abs(float(np.dot(direction, vertical))),
            float(np.dot(normal_a, direction)),
            float(np.dot(normal_b, direction)),
            float(np.linalg.norm(center_a - center)),
            float(np.linalg.norm(center_b - center)),
        ],
        dtype=np.float64,
    )


def angle_features(yaw_deg: float, pitch_deg: float) -> np.ndarray:
    yaw = np.deg2rad(float(yaw_deg))
    pitch = np.deg2rad(float(pitch_deg))
    return np.array(
        [
            np.sin(yaw),
            np.cos(yaw),
            np.sin(2.0 * yaw),
            np.cos(2.0 * yaw),
            np.sin(pitch),
            np.cos(pitch),
            np.sin(2.0 * pitch),
            np.cos(2.0 * pitch),
            np.sin(yaw) * np.sin(pitch),
            np.cos(yaw) * np.sin(pitch),
            np.sin(yaw) * np.cos(pitch),
            np.cos(yaw) * np.cos(pitch),
            np.sin(2.0 * yaw) * np.cos(pitch),
            np.cos(2.0 * yaw) * np.cos(pitch),
        ],
        dtype=np.float64,
    )


def regression_features(tri_a: np.ndarray, tri_b: np.ndarray, center: np.ndarray, yaw: float, pitch: float) -> np.ndarray:
    return np.concatenate((triangle_features(tri_a, tri_b, center), angle_features(yaw, pitch)))


def sample_pair_faces(pair_infos: np.ndarray, max_pairs: int, rng: np.random.Generator) -> np.ndarray:
    pair_infos = np.asarray(pair_infos, dtype=np.float64)
    if len(pair_infos) == 0:
        return np.empty((0, 2), dtype=np.int64)
    pair_faces = pair_infos[:, :2].astype(np.int64)
    if len(pair_faces) <= max_pairs:
        return pair_faces
    ids = rng.choice(len(pair_faces), size=max_pairs, replace=False)
    return pair_faces[np.sort(ids)]


def load_visible_pairs(mesh_path: str, rng: np.random.Generator) -> tuple[trimesh.Trimesh, np.ndarray, np.ndarray]:
    cfg = make_tse6_config(
        mesh_path=mesh_path,
        angle_step=ANGLE_STEP,
        critical_angle=FILAMENT_CRITICAL_ANGLE,
        deduplicate_orientations=True,
    )
    vis_face_pair = VisFacePair(cfg, cache_visible_pairs=True)
    vis_face_pair.run()
    pair_faces = sample_pair_faces(vis_face_pair.pair_infos, MAX_PAIRS_PER_MESH * PAIR_OVERSAMPLE_FACTOR, rng)
    return cfg.mesh, pair_faces, mesh_rotation_center(cfg.mesh)


def build_mesh_training_data(mesh_path: str, rng: np.random.Generator) -> MeshTrainingData:
    start = time.perf_counter()
    mesh, pair_faces, center = load_visible_pairs(mesh_path, rng)
    triangles = np.asarray(mesh.triangles, dtype=np.float64)
    x_rows: list[np.ndarray] = []
    y_values: list[np.ndarray] = []

    for pair_id, (face_i, face_j) in enumerate(pair_faces):
        tri_a = triangles[face_i]
        tri_b = triangles[face_j]
        yaws = rng.uniform(0.0, 360.0, size=ORIENTATION_SAMPLES_PER_PAIR)
        pitches = rng.uniform(0.0, 360.0, size=ORIENTATION_SAMPLES_PER_PAIR)
        for yaw, pitch in zip(yaws, pitches):
            x_rows.append(regression_features(tri_a, tri_b, center, float(yaw), float(pitch)))
            components = SHADOW.support_intersection_volume_components(
                float(yaw),
                float(pitch),
                tri_a=tri_a,
                tri_b=tri_b,
                center=center,
                critical_angle_deg=FILAMENT_CRITICAL_ANGLE,
            )
            y_values.append(np.asarray([components[name] for name in TARGET_COMPONENTS], dtype=np.float64))

        if (pair_id + 1) % 50 == 0 or pair_id + 1 == len(pair_faces):
            print(f"{mesh_label(mesh_path)} labels: {pair_id + 1}/{len(pair_faces)} pairs", flush=True)

    elapsed = time.perf_counter() - start
    y_array = np.asarray(y_values, dtype=np.float64)
    positive_rows = int(np.count_nonzero(np.any(y_array > 0.0, axis=1)))
    component_sums = ", ".join(
        f"{name} sum={float(np.sum(y_array[:, idx])):.6g}" for idx, name in enumerate(TARGET_COMPONENTS)
    )
    print(
        f"{mesh_label(mesh_path)} training rows: {len(y_values):,}, "
        f"visible pairs sampled: {len(pair_faces):,}, positive rows={positive_rows:,}, "
        f"{component_sums}, "
        f"elapsed={elapsed:.3f}s",
        flush=True,
    )
    return MeshTrainingData(
        mesh_path=mesh_path,
        label=mesh_label(mesh_path),
        mesh=mesh,
        center=center,
        pair_faces=pair_faces,
        x=np.asarray(x_rows, dtype=np.float64),
        y=y_array,
    )


def fit_ridge_regression(x: np.ndarray, y: np.ndarray, ridge_lambda: float = RIDGE_LAMBDA) -> RidgeModel:
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-12] = 1.0
    standardized = (x - mean) / scale
    design = np.column_stack((np.ones(len(standardized), dtype=np.float64), standardized))
    regularizer = ridge_lambda * np.eye(design.shape[1], dtype=np.float64)
    regularizer[0, 0] = 0.0
    weights = np.linalg.solve(design.T @ design + regularizer, design.T @ y)
    return RidgeModel(mean=mean, scale=scale, weights=weights, target_components=TARGET_COMPONENTS)


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, dict[str, float]]:
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    if y_true.ndim == 1:
        y_true = y_true[:, None]
    if y_pred.ndim == 1:
        y_pred = y_pred[:, None]
    metrics: dict[str, dict[str, float]] = {}
    for idx, component in enumerate(TARGET_COMPONENTS[: y_true.shape[1]]):
        error = y_pred[:, idx] - y_true[:, idx]
        ss_res = float(np.sum(error**2))
        ss_tot = float(np.sum((y_true[:, idx] - np.mean(y_true[:, idx])) ** 2))
        metrics[component] = {
            "mae": float(np.mean(np.abs(error))),
            "rmse": float(np.sqrt(np.mean(error**2))),
            "max_abs": float(np.max(np.abs(error))),
            "r2": 0.0 if ss_tot <= 1e-12 else float(1.0 - ss_res / ss_tot),
            "target_mean": float(np.mean(y_true[:, idx])),
            "target_max": float(np.max(y_true[:, idx])),
        }
    return metrics


def train_test_split(x: np.ndarray, y: np.ndarray, rng: np.random.Generator, test_ratio: float = 0.2):
    ids = np.arange(len(y))
    rng.shuffle(ids)
    test_count = max(1, int(round(len(ids) * test_ratio)))
    test_ids = ids[:test_count]
    train_ids = ids[test_count:]
    return x[train_ids], y[train_ids], x[test_ids], y[test_ids]


def make_parity_figure(y_true: np.ndarray, y_pred: np.ndarray, title: str) -> go.Figure:
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    if y_true.ndim == 1:
        y_true = y_true[:, None]
    if y_pred.ndim == 1:
        y_pred = y_pred[:, None]
    component_count = y_true.shape[1]
    fig = make_subplots(rows=1, cols=component_count, subplot_titles=TARGET_COMPONENTS[:component_count])
    for idx, component in enumerate(TARGET_COMPONENTS[:component_count], start=1):
        true_component = y_true[:, idx - 1]
        pred_component = y_pred[:, idx - 1]
        vmax = float(max(np.max(true_component), np.max(pred_component), 1e-12))
        fig.add_trace(
            go.Scattergl(
                x=true_component,
                y=pred_component,
                mode="markers",
                marker=dict(size=5, opacity=0.55),
                name=f"{component} samples",
                showlegend=False,
            ),
            row=1,
            col=idx,
        )
        fig.add_trace(
            go.Scatter(x=[0.0, vmax], y=[0.0, vmax], mode="lines", name=f"{component} ideal", showlegend=False),
            row=1,
            col=idx,
        )
        fig.update_xaxes(title_text=f"function {component}", row=1, col=idx)
        fig.update_yaxes(title_text=f"regression {component}", row=1, col=idx)
    fig.update_layout(title=title, width=520 * component_count, height=560)
    return fig


def pair_grid_values(
    mesh: trimesh.Trimesh,
    center: np.ndarray,
    pair_faces: np.ndarray,
    yaws: np.ndarray,
    pitches: np.ndarray,
    model: RidgeModel | None,
) -> tuple[np.ndarray, np.ndarray | None]:
    triangles = np.asarray(mesh.triangles, dtype=np.float64)
    component_count = len(TARGET_COMPONENTS)
    exact_grid = np.zeros((component_count, len(pitches), len(yaws)), dtype=np.float64)
    pred_grid = None if model is None else np.zeros_like(exact_grid)

    for pitch_id, pitch in enumerate(pitches):
        for yaw_id, yaw in enumerate(yaws):
            exact_total = np.zeros(component_count, dtype=np.float64)
            pred_features = []
            for face_i, face_j in pair_faces:
                tri_a = triangles[face_i]
                tri_b = triangles[face_j]
                components = SHADOW.support_intersection_volume_components(
                    float(yaw),
                    float(pitch),
                    tri_a=tri_a,
                    tri_b=tri_b,
                    center=center,
                    critical_angle_deg=FILAMENT_CRITICAL_ANGLE,
                )
                exact_total += np.asarray([components[name] for name in TARGET_COMPONENTS], dtype=np.float64)
                if model is not None:
                    pred_features.append(regression_features(tri_a, tri_b, center, float(yaw), float(pitch)))
            exact_grid[:, pitch_id, yaw_id] = exact_total
            if model is not None and pred_features:
                pred_grid[:, pitch_id, yaw_id] = np.sum(
                    model.predict(np.asarray(pred_features, dtype=np.float64)),
                    axis=0,
                )

    return exact_grid, pred_grid


def make_contour_comparison_figure(
    label: str,
    yaws: np.ndarray,
    pitches: np.ndarray,
    exact_grid: np.ndarray,
    pred_grid: np.ndarray,
) -> go.Figure:
    component_count = exact_grid.shape[0]
    subplot_titles = []
    for component in TARGET_COMPONENTS[:component_count]:
        subplot_titles.extend((f"Function {component}", f"Regression {component}"))
    fig = make_subplots(rows=component_count, cols=2, subplot_titles=subplot_titles)
    for row, component in enumerate(TARGET_COMPONENTS[:component_count], start=1):
        for col, grid, name in (
            (1, exact_grid[row - 1], "function"),
            (2, pred_grid[row - 1], "regression"),
        ):
            fig.add_trace(
                go.Contour(
                    x=yaws,
                    y=pitches,
                    z=grid,
                    colorscale=COOLWARM_COLORSCALE,
                    contours=dict(showlabels=True),
                    colorbar=dict(title=f"merged {component}") if col == 2 else None,
                    showscale=col == 2,
                    hovertemplate=(
                        f"{name} {component}<br>yaw=%{{x:.1f}}<br>pitch=%{{y:.1f}}"
                        f"<br>{component}=%{{z:.6g}}<extra></extra>"
                    ),
                ),
                row=row,
                col=col,
            )
            x_anchor = "x" if row == 1 and col == 1 else f"x{(row - 1) * 2 + col}"
            fig.update_xaxes(title_text="Yaw angle (deg)", row=row, col=col)
            fig.update_yaxes(title_text="Pitch angle (deg)", scaleanchor=x_anchor, scaleratio=1.0, row=row, col=col)
    fig.update_layout(title=f"{label}: visible-pair v_ss/v_nv regression comparison", width=1120, height=500 * component_count)
    return fig


def run_regression(mesh_paths: Sequence[str] = MESH_PATHS) -> dict[str, object]:
    rng = np.random.default_rng(RANDOM_SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    mesh_data = [build_mesh_training_data(mesh_path, rng) for mesh_path in mesh_paths]
    nonempty_mesh_data = [item for item in mesh_data if len(item.y)]
    if not nonempty_mesh_data:
        raise RuntimeError("No training rows were generated. The selected meshes had no sampled visible face pairs.")
    x = np.vstack([item.x for item in nonempty_mesh_data])
    y = np.vstack([item.y for item in nonempty_mesh_data])
    train_x, train_y, test_x, test_y = train_test_split(x, y, rng)
    model = fit_ridge_regression(train_x, train_y)
    save_ridge_model(model)
    test_pred = model.predict(test_x)
    metrics = regression_metrics(test_y, test_pred)

    print("regression metrics:")
    for component, component_metrics in metrics.items():
        print(f"  {component}:")
        for key, value in component_metrics.items():
            print(f"    {key}: {value:.6g}")

    parity = make_parity_figure(test_y, test_pred, "tri-pair shadow v_ss/v_nv regression parity")
    parity_path = OUTPUT_DIR / "regression_parity.html"
    parity.write_html(parity_path)
    print(f"wrote {parity_path.resolve()}")

    yaws, pitches = angle_grid(ANGLE_STEP)
    contour_outputs = []
    for item in mesh_data:
        pair_faces = item.pair_faces[:CONTOUR_PAIR_LIMIT]
        exact_grid, pred_grid = pair_grid_values(item.mesh, item.center, pair_faces, yaws, pitches, model)
        fig = make_contour_comparison_figure(item.label, yaws, pitches, exact_grid, pred_grid)
        output_path = OUTPUT_DIR / f"{item.label}_contour_comparison.html"
        fig.write_html(output_path)
        print(f"wrote {output_path.resolve()}")
        contour_outputs.append(output_path)

    return {
        "model": model,
        "metrics": metrics,
        "mesh_data": mesh_data,
        "parity_path": parity_path,
        "contour_outputs": contour_outputs,
    }


def main() -> None:
    start = time.perf_counter()
    run_regression()
    print_time("[regression]tri_pair_shadow.py total time", time.perf_counter() - start)


if __name__ == "__main__":
    main()
