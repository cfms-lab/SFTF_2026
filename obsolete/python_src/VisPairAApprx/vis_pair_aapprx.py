import importlib.util
import sys
from pathlib import Path

import numpy as np
import trimesh


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_tri_pair_shadow_regression():
    module_path = PROJECT_ROOT / "[regression]tri_pair_shadow.py"
    spec = importlib.util.spec_from_file_location("tri_pair_shadow_regression", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"failed to load {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


REGRESSION = load_tri_pair_shadow_regression()


class VisPairAApprx:
    pair_feature_count = 15
    MODEL_PATH = REGRESSION.MODEL_PATH

    def __init__(self, model=None, regression_module=REGRESSION, chunk_size: int = 256):
        self.regression_module = regression_module
        self.model = self.ensure_model(regression_module) if model is None else model
        self.chunk_size = int(chunk_size)

    @staticmethod
    def ensure_model(regression_module=REGRESSION):
        model_path = regression_module.MODEL_PATH
        if model_path.exists():
            print(f"loading regression model: {model_path.resolve()}")
            return regression_module.load_ridge_model(model_path)

        print(f"regression model not found: {model_path.resolve()}")
        print("training regression model now; run [regression]tri_pair_shadow.py beforehand to reuse a saved model.")
        result = regression_module.run_regression()
        return result["model"]

    @staticmethod
    def vectorized_triangle_features(
        triangles: np.ndarray,
        pair_faces: np.ndarray,
        center: np.ndarray,
    ) -> np.ndarray:
        tri_a = triangles[pair_faces[:, 0]]
        tri_b = triangles[pair_faces[:, 1]]

        def normals_and_areas(tri: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
            cross_norm = np.linalg.norm(cross, axis=1)
            safe_norm = np.maximum(cross_norm, 1e-12)
            return cross / safe_norm[:, None], 0.5 * cross_norm

        normal_a, area_a = normals_and_areas(tri_a)
        normal_b, area_b = normals_and_areas(tri_b)
        center_a = tri_a.mean(axis=1)
        center_b = tri_b.mean(axis=1)
        delta = center_b - center_a
        distance = np.maximum(np.linalg.norm(delta, axis=1), 1e-12)
        direction = delta / distance[:, None]
        extent_a = np.max(np.linalg.norm(tri_a - center_a[:, None, :], axis=2), axis=1)
        extent_b = np.max(np.linalg.norm(tri_b - center_b[:, None, :], axis=2), axis=1)

        return np.column_stack(
            (
                area_a,
                area_b,
                np.sqrt(np.maximum(area_a * area_b, 0.0)),
                extent_a,
                extent_b,
                distance,
                np.einsum("ij,ij->i", normal_a, normal_b),
                np.abs(normal_a[:, 2]),
                np.abs(normal_b[:, 2]),
                direction[:, 2],
                np.abs(direction[:, 2]),
                np.einsum("ij,ij->i", normal_a, direction),
                np.einsum("ij,ij->i", normal_b, direction),
                np.linalg.norm(center_a - center, axis=1),
                np.linalg.norm(center_b - center, axis=1),
            )
        ).astype(np.float64, copy=False)

    @staticmethod
    def angle_feature_matrix(angles_yaw: np.ndarray, angles_pitch: np.ndarray) -> np.ndarray:
        yaw_grid, pitch_grid = np.meshgrid(angles_yaw, angles_pitch, indexing="xy")
        yaw = np.deg2rad(yaw_grid.ravel())
        pitch = np.deg2rad(pitch_grid.ravel())
        sin_yaw = np.sin(yaw)
        cos_yaw = np.cos(yaw)
        sin_2yaw = np.sin(2.0 * yaw)
        cos_2yaw = np.cos(2.0 * yaw)
        sin_pitch = np.sin(pitch)
        cos_pitch = np.cos(pitch)
        return np.column_stack(
            (
                sin_yaw,
                cos_yaw,
                sin_2yaw,
                cos_2yaw,
                sin_pitch,
                cos_pitch,
                np.sin(2.0 * pitch),
                np.cos(2.0 * pitch),
                sin_yaw * sin_pitch,
                cos_yaw * sin_pitch,
                sin_yaw * cos_pitch,
                cos_yaw * cos_pitch,
                sin_2yaw * cos_pitch,
                cos_2yaw * cos_pitch,
            )
        ).astype(np.float64, copy=False)

    def compute_v_ss_rg_grid(
        self,
        mesh: trimesh.Trimesh,
        pair_infos: np.ndarray,
        center: np.ndarray,
        angles_yaw: np.ndarray,
        angles_pitch: np.ndarray,
    ) -> np.ndarray:
        return self.compute_v_ss_v_nv_rg_grids(
            mesh,
            pair_infos,
            center,
            angles_yaw,
            angles_pitch,
        )["v_ss"]

    def compute_v_ss_v_nv_rg_grids(
        self,
        mesh: trimesh.Trimesh,
        pair_infos: np.ndarray,
        center: np.ndarray,
        angles_yaw: np.ndarray,
        angles_pitch: np.ndarray,
    ) -> dict[str, np.ndarray]:
        angles_yaw = np.asarray(angles_yaw, dtype=np.float64)
        angles_pitch = np.asarray(angles_pitch, dtype=np.float64)
        triangles = np.asarray(mesh.triangles, dtype=np.float64)
        pairs = np.asarray(pair_infos, dtype=np.float64)
        pair_faces = pairs[:, :2].astype(np.int64) if len(pairs) else np.empty((0, 2), dtype=np.int64)
        target_components = tuple(getattr(self.model, "target_components", ("v_ss",)))
        component_count = len(target_components)
        grids = {
            component: np.zeros((len(angles_pitch), len(angles_yaw)), dtype=np.float64)
            for component in target_components
        }
        if "v_ss" not in grids:
            grids["v_ss"] = np.zeros((len(angles_pitch), len(angles_yaw)), dtype=np.float64)
        if "v_nv" not in grids:
            grids["v_nv"] = np.zeros((len(angles_pitch), len(angles_yaw)), dtype=np.float64)

        if len(pair_faces) == 0:
            return grids

        pair_features = self.vectorized_triangle_features(triangles, pair_faces, center)
        angle_features = self.angle_feature_matrix(angles_yaw, angles_pitch)
        mean = np.asarray(self.model.mean, dtype=np.float64)
        scale = np.asarray(self.model.scale, dtype=np.float64)
        weights = np.asarray(self.model.weights, dtype=np.float64)
        if weights.ndim == 1:
            weights = weights[:, None]
            component_count = 1
            target_components = ("v_ss",)
            grids = {"v_ss": grids.get("v_ss", np.zeros((len(angles_pitch), len(angles_yaw)), dtype=np.float64))}
        n_pair_features = self.pair_feature_count

        pair_linear = ((pair_features - mean[:n_pair_features]) / scale[:n_pair_features]) @ weights[
            1 : n_pair_features + 1
        ]
        angle_linear = (
            (angle_features - mean[n_pair_features:]) / scale[n_pair_features:]
        ) @ weights[n_pair_features + 1 :]
        pair_base = weights[0] + pair_linear

        orientation_count = len(angles_pitch) * len(angles_yaw)
        flat_outputs = np.zeros((orientation_count, component_count), dtype=np.float64)
        for chunk_start in range(0, orientation_count, self.chunk_size):
            chunk_stop = min(chunk_start + self.chunk_size, orientation_count)
            flat_outputs[chunk_start:chunk_stop] = np.maximum(
                0.0,
                pair_base[None, :, :] + angle_linear[chunk_start:chunk_stop, None, :],
            ).sum(axis=1)
            print(f"predicting regression v_ss/v_nv grid: {chunk_stop}/{orientation_count}", flush=True)

        for component_id, component in enumerate(target_components):
            grids[component][:, :] = flat_outputs[:, component_id].reshape(len(angles_pitch), len(angles_yaw))
        return {key: np.asarray(value, dtype=np.float64) for key, value in grids.items()}

    def compute_v_nv_rg_grid(
        self,
        mesh: trimesh.Trimesh,
        pair_infos: np.ndarray,
        center: np.ndarray,
        angles_yaw: np.ndarray,
        angles_pitch: np.ndarray,
        critical_angle_deg: float,
    ) -> np.ndarray:
        _ = critical_angle_deg
        return self.compute_v_ss_v_nv_rg_grids(
            mesh,
            pair_infos,
            center,
            angles_yaw,
            angles_pitch,
        )["v_nv"]
