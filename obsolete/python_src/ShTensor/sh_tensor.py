"""
Shadow tensor pipeline utilities.

This package is the class-based home for the workflow that used to live in
``tse6_shadow_tensor.py``.  The module-level functions are kept so existing
scripts can still import the smaller building blocks directly.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
import os
from typing import Mapping, Sequence
import time

import numpy as np
import trimesh

from ..tse6_config import (
    TSE6Config,
    draw_tri_struc,
    get_center,
    get_tris_on_plane,
    get_tri_list_normal,
    triangle_areas,
    yaw_pitch_matrix,
)

try:
    from scipy.spatial import ConvexHull
except Exception:  # pragma: no cover
    ConvexHull = None


MESH_PATH = "Experimental/etc/(7)Bunny_1k.obj"


def log_time(label, start_time):
    print(f"{label}: {time.perf_counter() - start_time:.3f}s")


def _require_scipy() -> None:
    if ConvexHull is None:
        raise ImportError("scipy is required for convex hull computation: pip install scipy")


@dataclass
class ShTensorConfig:
    mesh_path: str = MESH_PATH
    mesh: trimesh.Trimesh | None = None
    angles_yaw: Sequence[float] = field(default_factory=lambda: (0.0,))
    angles_pitch: Sequence[float] = field(default_factory=lambda: (0.0,))
    orientation_pairs: np.ndarray | None = None
    orientation_inverse: np.ndarray | None = None
    critical_angle: float = float(np.deg2rad(60.0))
    make_arrow_data: bool = False
    build_triangle_structures: bool = False
    store_bottom_projected_triangles: bool = False
    tensor_chunk_size: int = 4096
    shadow_chunk_size: int = 512
    store_raw_by_plane: bool = False
    renderer: object | None = None


@dataclass
class ShadowTensorResult:
    triangles: np.ndarray
    triangle_centers: np.ndarray
    triangle_normals: np.ndarray
    triangle_areas: np.ndarray
    hull_info: dict[str, np.ndarray]
    convex_hull_planes: list[dict[str, np.ndarray]]
    orientation_vectors: np.ndarray
    bottom_planes: list[dict[str, np.ndarray]]
    bottom_projected_triangles: list[np.ndarray] | None
    triangle_structures: list[dict[str, np.ndarray]] | None
    graphics_arrow_data: list[dict[str, np.ndarray]] | None
    volumes: dict[str, np.ndarray | None]


class ShTensor:
    def __init__(self, config: ShTensorConfig | dict | None = None, **overrides):
        if config is None:
            config = ShTensorConfig()
        elif isinstance(config, TSE6Config):
            config = ShTensorConfig(
                mesh=config.mesh,
                angles_yaw=config.angles_yaw,
                angles_pitch=config.angles_pitch,
                orientation_pairs=config.orientation_pairs,
                orientation_inverse=config.orientation_inverse,
                critical_angle=float(np.deg2rad(config.critical_angle)),
                renderer=config.renderer,
            )
        elif isinstance(config, dict):
            config = dict(config)
            config = ShTensorConfig(**config)

        for key, value in overrides.items():
            if not hasattr(config, key):
                raise AttributeError(f"Unknown ShTensorConfig field: {key}")
            setattr(config, key, value)

        self.config = config
        self.renderer = config.renderer
        self.mesh = None
        self.result = None

    @staticmethod
    def coordinate_bounds(points: np.ndarray, scale: float = 1.02) -> np.ndarray:
        """Equivalent to CoordinateBounds[..., Scaled[...]] for point arrays."""
        points = np.asarray(points, dtype=float)
        lo = points.min(axis=0)
        hi = points.max(axis=0)
        center = 0.5 * (lo + hi)
        half = 0.5 * (hi - lo) * scale
        return np.column_stack((center - half, center + half))

    @staticmethod
    def convex_hull_triangles(tris: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Return convex hull vertices, triangular faces, and face triangles.

        Mathematica equivalent:
        H = ConvexHullMesh[Flatten[T,1]];
        H_vtx = MeshCoordinates[H];
        H_face = Flatten @ MeshCells[H,2][[All,1,1;;3]];
        H_tri = Partition[Part[H_vtx,H_face],3];
        """
        _require_scipy()
        points = np.asarray(tris, dtype=float).reshape(-1, 3)
        hull = ConvexHull(points)
        hull_vertices = points
        hull_faces = hull.simplices.astype(int)
        hull_tris = hull_vertices[hull_faces]
        return hull_vertices, hull_faces, hull_tris

    @classmethod
    def build_convex_hull_planes(cls, tris: np.ndarray) -> tuple[list[dict[str, np.ndarray]], dict[str, np.ndarray]]:
        """Cell 0 equivalent: build convex-hull planes from the mesh triangles."""
        hull_vertices, hull_faces, hull_tris = cls.convex_hull_triangles(tris)
        hull_normals = get_tri_list_normal(hull_tris)
        planes = [
            {"origin": tri[0].copy(), "normal": normal.copy()}
            for tri, normal in zip(hull_tris, hull_normals)
        ]
        info = {
            "hull_vertices": hull_vertices,
            "hull_faces": hull_faces,
            "hull_triangles": hull_tris,
            "hull_normals": hull_normals,
            "view_range": cls.coordinate_bounds(hull_vertices, 1.02),
        }
        return planes, info

    @staticmethod
    def orientation_vectors(angles_yaw: Sequence[float], angles_pitch: Sequence[float]) -> np.ndarray:
        """
        Bottom-plane normals from the same yaw/pitch matrix used by FboVtc.

        Inputs are degrees. FboVtc rotates vertices by R; this returns R.T @ +Z
        so shadow volumes are computed in the original mesh space with the same
        printer-bed direction.
        """
        return np.asarray(
            [
                yaw_pitch_matrix(float(yaw), float(pitch)).T @ np.array([0.0, 0.0, 1.0])
                for pitch in np.asarray(angles_pitch, dtype=float)
                for yaw in np.asarray(angles_yaw, dtype=float)
            ],
            dtype=np.float64,
        )

    @staticmethod
    def orientation_vectors_for_pairs(angle_pairs: np.ndarray) -> np.ndarray:
        angle_pairs = np.asarray(angle_pairs, dtype=float)
        return np.asarray(
            [
                yaw_pitch_matrix(float(yaw), float(pitch)).T @ np.array([0.0, 0.0, 1.0])
                for yaw, pitch in angle_pairs.reshape(-1, 2)
            ],
            dtype=np.float64,
        )

    @staticmethod
    def build_bottom_planes(
        mesh_center: np.ndarray,
        hull_vertices: np.ndarray,
        ort_vectors: np.ndarray,
    ) -> list[dict[str, np.ndarray]]:
        """
        Cell 1 equivalent: for each orientation vector, choose the convex-hull vertex
        farthest in the ground direction as the origin of the bottom plane.
        """
        mesh_center = np.asarray(mesh_center, dtype=float)
        hull_vertices = np.asarray(hull_vertices, dtype=float)
        ort_vectors = np.asarray(ort_vectors, dtype=float)
        normal_lengths = np.linalg.norm(ort_vectors, axis=1)
        normal_lengths = np.where(normal_lengths > 0.0, normal_lengths, 1.0)
        unit_vectors = ort_vectors / normal_lengths[:, None]

        centered_hull = hull_vertices - mesh_center
        support_ids = np.empty(len(unit_vectors), dtype=np.int64)
        chunk_size = 4096
        for start in range(0, len(unit_vectors), chunk_size):
            end = min(start + chunk_size, len(unit_vectors))
            support_ids[start:end] = np.argmax(centered_hull @ unit_vectors[start:end].T, axis=0)

        planes = [
            {"origin": hull_vertices[point_id].copy(), "normal": up.copy()}
            for point_id, up in zip(support_ids, ort_vectors)
        ]
        return planes

    @staticmethod
    def tensor_sizes_for_triangles(
        centers: np.ndarray,
        normals: np.ndarray,
        critical_angle: float,
        bottom_planes: Sequence[Mapping[str, np.ndarray]],
        chunk_size: int = 4096,
    ) -> np.ndarray:
        centers = np.asarray(centers, dtype=float)
        normals = np.asarray(normals, dtype=float)
        plane_origins = np.asarray([plane["origin"] for plane in bottom_planes], dtype=float)
        plane_normals = np.asarray([plane["normal"] for plane in bottom_planes], dtype=float)
        normal_lengths = np.linalg.norm(plane_normals, axis=1)
        normal_lengths = np.where(normal_lengths > 0.0, normal_lengths, 1.0)
        unit_normals = plane_normals / normal_lengths[:, None]
        origin_offsets = np.einsum("ij,ij->i", plane_origins, unit_normals)

        tensor_sizes = np.empty((len(centers), len(bottom_planes)), dtype=float)
        cos_critical = np.cos(critical_angle)
        chunk_size = max(int(chunk_size), 1)

        for start in range(0, len(centers), chunk_size):
            end = min(start + chunk_size, len(centers))
            center_chunk = centers[start:end]
            normal_chunk = normals[start:end]

            dist2bp = center_chunk @ unit_normals.T - origin_offsets
            dots = normal_chunk @ unit_normals.T

            non_overhangs = (dots < 0.01) & (dots > -cos_critical)
            dist2bp[non_overhangs] = 0.0
            tensor_sizes[start:end] = np.where(dots < 0.0, -dist2bp, dist2bp)

        return tensor_sizes

    @staticmethod
    def build_triangle_structures(
        tris: np.ndarray,
        critical_angle: float,
        bottom_planes: Sequence[Mapping[str, np.ndarray]],
        ort_vectors: np.ndarray | None = None,
        tensor_chunk_size: int = 4096,
    ) -> tuple[list[dict[str, np.ndarray]], list[dict[str, np.ndarray]] | None]:
        """
        Cell 2 equivalent: build per-triangle associations and tensor sizes.

        Returns (TS, gTS_data). gTS_data is the arrow-geometry replacement for the
        original graphics if `ort_vectors` is provided; otherwise None.
        """
        tris = np.asarray(tris, dtype=float)
        centers = tris.mean(axis=1)
        normals = get_tri_list_normal(tris)
        areas = triangle_areas(tris)
        tensor_sizes = ShTensor.tensor_sizes_for_triangles(
            centers,
            normals,
            critical_angle,
            bottom_planes,
            chunk_size=tensor_chunk_size,
        )

        ts_list: list[dict[str, np.ndarray]] = []
        gts = [] if ort_vectors is not None else None
        for center, normal, area, tri, tensor_size in zip(centers, normals, areas, tris, tensor_sizes):
            ts = {
                "center": center,
                "normal": normal,
                "area": np.asarray(area),
                # Keep original notebook typo as an alias, plus a corrected key.
                "verticezs": tri,
                "vertices": tri,
            }
            ts["tensorsize"] = tensor_size
            ts_list.append(ts)
            if gts is not None:
                gts.append(draw_tri_struc(ts, np.asarray(ort_vectors, dtype=float)))
        return ts_list, gts

    @staticmethod
    def compute_triangle_to_btplane_volumes(
        tris: np.ndarray,
        tri_normals: np.ndarray,
        bottom_planes: Sequence[Mapping[str, np.ndarray]],
        critical_angle: float,
        n_yaw: int,
        n_pitch: int,
        tri_centers: np.ndarray | None = None,
        tri_areas: np.ndarray | None = None,
        chunk_size: int = 512,
        store_raw_by_plane: bool = False,
    ) -> dict[str, np.ndarray | None]:
        """
        Cell 3 equivalent: compute V_al_bt, V_be_bt, V_nv_bt, V_ss_bt
        and reshape to yaw/pitch grids.
        """
        expected = n_yaw * n_pitch
        if len(bottom_planes) != expected:
            raise ValueError(f"n_yaw * n_pitch = {expected}, but there are {len(bottom_planes)} bottom planes")

        tris = np.asarray(tris, dtype=float)
        tri_normals = np.asarray(tri_normals, dtype=float)
        tri_centers = tris.mean(axis=1) if tri_centers is None else np.asarray(tri_centers, dtype=float)
        tri_areas = triangle_areas(tris) if tri_areas is None else np.asarray(tri_areas, dtype=float)

        plane_origins = np.asarray([plane["origin"] for plane in bottom_planes], dtype=float)
        plane_normals = np.asarray([plane["normal"] for plane in bottom_planes], dtype=float)
        normal_lengths = np.linalg.norm(plane_normals, axis=1)
        normal_lengths = np.where(normal_lengths > 0.0, normal_lengths, 1.0)
        unit_normals = plane_normals / normal_lengths[:, None]
        origin_offsets = np.einsum("ij,ij->i", plane_origins, unit_normals)

        plane_count = len(bottom_planes)
        tri_count = len(tris)
        v_al = np.zeros(plane_count, dtype=float)
        v_be = np.zeros(plane_count, dtype=float)
        v_nv = np.zeros(plane_count, dtype=float)
        raw_by_plane = np.empty((plane_count, 3, tri_count), dtype=float) if store_raw_by_plane else None

        sin_critical = np.sin(critical_angle)
        cos_critical = np.cos(critical_angle)
        chunk_size = max(int(chunk_size), 1)

        for start in range(0, plane_count, chunk_size):
            end = min(start + chunk_size, plane_count)
            normal_chunk = unit_normals[start:end]
            offset_chunk = origin_offsets[start:end]

            dots = tri_normals @ normal_chunk.T
            center_dist = tri_centers @ normal_chunk.T - offset_chunk
            volumes = tri_areas[:, None] * np.abs(dots) * np.abs(center_dist)

            al_mask = dots < 0.001
            be_mask = ~al_mask
            al_values = np.where(al_mask, volumes, 0.0)
            be_values = np.where(be_mask, volumes, 0.0)

            be_nv_mask = be_mask & (dots > cos_critical)
            be_nv_values = np.where(be_nv_mask, volumes, 0.0)
            nv_values =  be_nv_values

            v_al[start:end] = al_values.sum(axis=0)
            v_be[start:end] = be_values.sum(axis=0)
            v_nv[start:end] = nv_values.sum(axis=0)

            if raw_by_plane is not None:
                raw_by_plane[start:end, 0, :] = al_values.T
                raw_by_plane[start:end, 1, :] = be_values.T
                raw_by_plane[start:end, 2, :] = nv_values.T

        return {
            "V_al_bt": v_al.reshape(n_pitch, n_yaw),
            "V_be_bt": v_be.reshape(n_pitch, n_yaw),
            "V_nv_bt": v_nv.reshape(n_pitch, n_yaw),
            "V_ss_bt": np.zeros_like(v_al).reshape(n_pitch, n_yaw),
            "V_o_bt": (v_al - v_be).reshape(n_pitch, n_yaw),
            "vtotal": np.array([v_al.sum(), v_be.sum(), v_nv.sum()], dtype=float),
            "raw_by_plane": raw_by_plane,
        }

    @staticmethod
    def compute_vispair_volumes(
        tris: np.ndarray,
        tri_normals: np.ndarray,
        bottom_planes: Sequence[Mapping[str, np.ndarray]],
        critical_angle: float,
        n_yaw: int,
        n_pitch: int,
        visible_face_pairs: Sequence[Sequence[int]] | np.ndarray | None = None,
        tri_centers: np.ndarray | None = None,
        tri_areas: np.ndarray | None = None,
        chunk_size: int = 512,
        store_raw_by_plane: bool = False,
    ) -> dict[str, np.ndarray | None]:
        """
        Compute vis-pair V_ss_vpair and V_nv_vpair contributions.
        """
        expected = n_yaw * n_pitch
        if len(bottom_planes) != expected:
            raise ValueError(f"n_yaw * n_pitch = {expected}, but there are {len(bottom_planes)} bottom planes")

        tris = np.asarray(tris, dtype=float)
        tri_normals = np.asarray(tri_normals, dtype=float)
        tri_centers = tris.mean(axis=1) if tri_centers is None else np.asarray(tri_centers, dtype=float)
        if tri_areas is not None:
            np.asarray(tri_areas, dtype=float)

        plane_count = len(bottom_planes)
        tri_count = len(tris)

        if visible_face_pairs is None:
            visible_pairs = np.empty((0, 2), dtype=np.int64)
        else:
            visible_pairs = np.asarray(visible_face_pairs, dtype=np.int64).reshape(-1, 2)
            if np.any(visible_pairs < 0) or np.any(visible_pairs >= tri_count):
                raise IndexError("visPairs contains a face index outside the mesh face range.")

        if visible_pairs.size:
            pair_vectors = tri_centers[visible_pairs[:, 1]] - tri_centers[visible_pairs[:, 0]]
            pair_lengths = np.linalg.norm(pair_vectors, axis=1)
            valid_pairs = pair_lengths > 1e-15
            visible_pairs = visible_pairs[valid_pairs]
        pair_volumes = ShTensor.getVisPairVolume(
            visible_pairs,
            tris,
            bottom_planes,
            critical_angle,
            tri_normals=tri_normals,
            chunk_size=chunk_size,
            store_raw_by_plane=store_raw_by_plane,
        )
        v_ss_vpair = pair_volumes["v_ss_vpair"]
        v_nv_vpair = pair_volumes["v_nv_vpair"]
        raw_by_plane = pair_volumes["raw_by_plane"]

        v_nv_vpair_grid = v_nv_vpair.reshape(n_pitch, n_yaw)
        v_ss_grid = v_ss_vpair.reshape(n_pitch, n_yaw)
        return {
            "V_nv_vpair": v_nv_vpair_grid,
            "V_ss_vpair": v_ss_grid,
            "vtotal": np.array([0.0, 0.0, v_nv_vpair.sum()], dtype=float),
            "raw_by_plane": raw_by_plane,
        }

    @staticmethod
    def compute_vispair_volumes_approx(
        tris: np.ndarray,
        tri_normals: np.ndarray,
        bottom_planes: Sequence[Mapping[str, np.ndarray]],
        critical_angle: float,
        *,
        n_yaw: int,
        n_pitch: int,
        visible_face_pairs: Sequence[Sequence[int]] | np.ndarray | None = None,
        tri_centers: np.ndarray | None = None,
        tri_areas: np.ndarray | None = None,
        chunk_size: int = 512,
        store_raw_by_plane: bool = False,
    ) -> dict[str, np.ndarray | None]:
        """
        Fast polynomial approximation of vis-pair volume contributions.

        This keeps the same input/output contract as compute_vispair_volumes(),
        but replaces the exact polyhedron/prism intersection with a vectorized
        projected-area estimator:

            volume ~= abs((center_B - center_A) . n)
                      * area(triangle projected along n)
                      * quadratic skew correction

        It is intended for trend exploration of V_ss, not as a geometric ground
        truth. Use compute_vispair_volumes() when exact intersection volumes are
        required.
        """
        expected = n_yaw * n_pitch
        if len(bottom_planes) != expected:
            raise ValueError(f"n_yaw * n_pitch = {expected}, but there are {len(bottom_planes)} bottom planes")

        tris = np.asarray(tris, dtype=float)
        tri_normals = np.asarray(tri_normals, dtype=float)
        tri_centers = tris.mean(axis=1) if tri_centers is None else np.asarray(tri_centers, dtype=float)
        if tri_areas is None:
            tri_areas = triangle_areas(tris)
        else:
            tri_areas = np.asarray(tri_areas, dtype=float)

        plane_count = len(bottom_planes)
        tri_count = len(tris)

        if visible_face_pairs is None:
            visible_pairs = np.empty((0, 2), dtype=np.int64)
        else:
            visible_pairs = np.asarray(visible_face_pairs, dtype=np.int64).reshape(-1, 2)
            if np.any(visible_pairs < 0) or np.any(visible_pairs >= tri_count):
                raise IndexError("visPairs contains a face index outside the mesh face range.")

        if visible_pairs.size:
            pair_vectors = tri_centers[visible_pairs[:, 1]] - tri_centers[visible_pairs[:, 0]]
            pair_lengths = np.linalg.norm(pair_vectors, axis=1)
            visible_pairs = visible_pairs[pair_lengths > 1e-15]

        pair_volumes = ShTensor.getVisPairVolumeApprox(
            visible_pairs,
            tris,
            bottom_planes,
            critical_angle,
            tri_normals=tri_normals,
            tri_centers=tri_centers,
            tri_areas=tri_areas,
            chunk_size=chunk_size,
            store_raw_by_plane=store_raw_by_plane,
        )
        v_ss_vpair = pair_volumes["v_ss_vpair"]
        v_nv_vpair = pair_volumes["v_nv_vpair"]
        raw_by_plane = pair_volumes["raw_by_plane"]

        return {
            "V_nv_vpair": v_nv_vpair.reshape(n_pitch, n_yaw),
            "V_ss_vpair": v_ss_vpair.reshape(n_pitch, n_yaw),
            "vtotal": np.array([0.0, 0.0, v_nv_vpair.sum()], dtype=float),
            "raw_by_plane": raw_by_plane,
        }

    @staticmethod
    def getVisPairVolumeApprox(
        visible_face_pairs: Sequence[Sequence[int]] | np.ndarray,
        tris: np.ndarray,
        bottom_planes: Sequence[Mapping[str, np.ndarray]],
        critical_angle: float,
        tri_normals: np.ndarray | None = None,
        tri_centers: np.ndarray | None = None,
        tri_areas: np.ndarray | None = None,
        chunk_size: int = 512,
        store_raw_by_plane: bool = False,
    ) -> dict[str, np.ndarray | None]:
        """
        Return approximate per-bottom-plane vis-pair volumes.

        The estimator uses low-order polynomial terms of dot products between
        the bottom-plane normal, the triangle normals, and the pair direction.
        It avoids ConvexHull/halfspace intersection entirely, so its runtime is
        dominated by dense NumPy matrix operations.
        """
        tris = np.asarray(tris, dtype=float)
        visible_pairs = np.asarray(visible_face_pairs, dtype=np.int64).reshape(-1, 2)
        if np.any(visible_pairs < 0) or np.any(visible_pairs >= len(tris)):
            raise IndexError("visible_face_pairs contains a face index outside the mesh face range.")

        plane_count = len(bottom_planes)
        original_pair_count = len(visible_pairs)
        v_ss_vpair = np.zeros(plane_count, dtype=float)
        v_nv_vpair = np.zeros(plane_count, dtype=float)
        raw_by_plane = np.empty((plane_count, original_pair_count), dtype=float) if store_raw_by_plane else None
        if original_pair_count == 0 or plane_count == 0:
            return {"v_ss_vpair": v_ss_vpair, "v_nv_vpair": v_nv_vpair, "raw_by_plane": raw_by_plane}

        tri_centers = tris.mean(axis=1) if tri_centers is None else np.asarray(tri_centers, dtype=float)
        tri_areas = triangle_areas(tris) if tri_areas is None else np.asarray(tri_areas, dtype=float)
        if tri_normals is None:
            all_normals = get_tri_list_normal(tris)
        else:
            all_normals = np.asarray(tri_normals, dtype=float).copy()
            zero_mask = np.linalg.norm(all_normals, axis=1) <= 1e-12
            if np.any(zero_mask):
                all_normals[zero_mask] = get_tri_list_normal(tris[zero_mask])
        all_normals = ShTensor._normalize_vectors(all_normals)

        tri_a_ids = visible_pairs[:, 0]
        tri_b_ids = visible_pairs[:, 1]
        pair_vectors = tri_centers[tri_b_ids] - tri_centers[tri_a_ids]
        pair_lengths = np.linalg.norm(pair_vectors, axis=1)
        valid_pairs = pair_lengths > 1e-15
        if not np.all(valid_pairs):
            visible_pairs = visible_pairs[valid_pairs]
            tri_a_ids = visible_pairs[:, 0]
            tri_b_ids = visible_pairs[:, 1]
            pair_vectors = pair_vectors[valid_pairs]
            pair_lengths = pair_lengths[valid_pairs]
            if raw_by_plane is not None:
                raw_by_plane[:, ~valid_pairs] = 0.0

        if len(visible_pairs) == 0:
            return {"v_ss_vpair": v_ss_vpair, "v_nv_vpair": v_nv_vpair, "raw_by_plane": raw_by_plane}

        pair_dirs = pair_vectors / pair_lengths[:, None]
        tri_a_normals = all_normals[tri_a_ids]
        tri_b_normals = all_normals[tri_b_ids]
        tri_a_areas = tri_areas[tri_a_ids]
        tri_b_areas = tri_areas[tri_b_ids]
        normal_similarity = np.clip(np.abs(np.sum(tri_a_normals * tri_b_normals, axis=1)), 0.0, 1.0)

        plane_normals = np.asarray([plane["normal"] for plane in bottom_planes], dtype=float)
        unit_normals = ShTensor._normalize_vectors(plane_normals)
        cos_critical = float(np.cos(critical_angle))
        chunk_size = max(int(chunk_size), 1)

        raw_valid = None
        if raw_by_plane is not None:
            raw_valid = np.zeros((plane_count, len(visible_pairs)), dtype=float)

        for start in range(0, plane_count, chunk_size):
            end = min(start + chunk_size, plane_count)
            normals = unit_normals[start:end]

            depth = np.abs(normals @ pair_vectors.T)
            pair_alignment = np.abs(normals @ pair_dirs.T)
            a_dot_abs = np.abs(normals @ tri_a_normals.T)
            b_dot_abs = np.abs(normals @ tri_b_normals.T)

            skew_penalty = (1.0 - normal_similarity)[None, :] * (1.0 - pair_alignment**2)
            quadratic_correction = np.clip(1.0 - 0.25 * skew_penalty, 0.75, 1.0)

            vol_a = depth * (tri_a_areas[None, :] * a_dot_abs) * quadratic_correction
            vol_b = depth * (tri_b_areas[None, :] * b_dot_abs) * quadratic_correction

            tri_a_support = (normals @ tri_a_normals.T) >= cos_critical
            tri_b_support = (normals @ tri_b_normals.T) >= cos_critical
            v_ss_vpair[start:end] = np.sum(vol_a * tri_a_support + vol_b * tri_b_support, axis=1)
            v_nv_vpair[start:end] = np.sum(vol_a * ~tri_a_support + vol_b * ~tri_b_support, axis=1)
            if raw_valid is not None:
                raw_valid[start:end, :] = vol_a + vol_b

        if raw_by_plane is not None and raw_valid is not None:
            raw_by_plane[:, valid_pairs] = raw_valid

        return {"v_ss_vpair": v_ss_vpair, "v_nv_vpair": v_nv_vpair, "raw_by_plane": raw_by_plane}

    @staticmethod
    def getVisPairVolume(
        visible_face_pairs: Sequence[Sequence[int]] | np.ndarray,
        tris: np.ndarray,
        bottom_planes: Sequence[Mapping[str, np.ndarray]],
        critical_angle: float,
        tri_normals: np.ndarray | None = None,
        chunk_size: int = 512,
        store_raw_by_plane: bool = False,
    ) -> dict[str, np.ndarray | None]:
        """
        Return per-bottom-plane vis-pair volumes.

        For each visible pair, form polyAB from the two triangles. For each
        bottom-plane normal, intersect polyAB with the infinite triangular
        prism swept from tri_A along +/-normal, then repeat for tri_B. The
        critical angle only classifies each intersection volume into
        V_ss_vpair or V_nv_vpair.
        """
        tris = np.asarray(tris, dtype=float)
        visible_pairs = np.asarray(visible_face_pairs, dtype=np.int64).reshape(-1, 2)
        if np.any(visible_pairs < 0) or np.any(visible_pairs >= len(tris)):
            raise IndexError("visible_face_pairs contains a face index outside the mesh face range.")
        plane_count = len(bottom_planes)
        original_pair_count = len(visible_pairs)
        v_ss_vpair = np.zeros(plane_count, dtype=float)
        v_nv_vpair = np.zeros(plane_count, dtype=float)
        raw_by_plane = np.empty((plane_count, original_pair_count), dtype=float) if store_raw_by_plane else None

        if original_pair_count == 0 or plane_count == 0:
            return {"v_ss_vpair": v_ss_vpair, "v_nv_vpair": v_nv_vpair, "raw_by_plane": raw_by_plane}

        tri_a = tris[visible_pairs[:, 0]]
        tri_b = tris[visible_pairs[:, 1]]
        if tri_normals is None:
            tri_a_normals = get_tri_list_normal(tri_a)
            tri_b_normals = get_tri_list_normal(tri_b)
        else:
            all_normals = np.asarray(tri_normals, dtype=float)
            tri_a_normals = all_normals[visible_pairs[:, 0]]
            tri_b_normals = all_normals[visible_pairs[:, 1]]
        zero_a_mask = np.linalg.norm(tri_a_normals, axis=1) <= 1e-12
        if np.any(zero_a_mask):
            tri_a_normals[zero_a_mask] = get_tri_list_normal(tri_a[zero_a_mask])
        zero_b_mask = np.linalg.norm(tri_b_normals, axis=1) <= 1e-12
        if np.any(zero_b_mask):
            tri_b_normals[zero_b_mask] = get_tri_list_normal(tri_b[zero_b_mask])
        pair_data = []
        for pair_tri_a, pair_tri_b, normal_a, normal_b in zip(tri_a, tri_b, tri_a_normals, tri_b_normals):
            poly_halfspaces = ShTensor._poly_pair_halfspaces(pair_tri_a, pair_tri_b)
            if poly_halfspaces is None:
                pair_data.append(None)
                continue
            poly_points = np.vstack((pair_tri_a, pair_tri_b))
            pair_data.append(
                (
                    poly_halfspaces,
                    poly_points,
                    np.asarray(pair_tri_a, dtype=float),
                    np.asarray(pair_tri_b, dtype=float),
                    np.asarray(normal_a, dtype=float),
                    np.asarray(normal_b, dtype=float),
                )
            )

        plane_normals = np.asarray([plane["normal"] for plane in bottom_planes], dtype=float)
        normal_lengths = np.linalg.norm(plane_normals, axis=1)
        normal_lengths = np.where(normal_lengths > 0.0, normal_lengths, 1.0)
        unit_normals = plane_normals / normal_lengths[:, None]
        cached_normals, normal_inverse = ShTensor._unique_canonical_normals(unit_normals)

        cos_critical = float(np.cos(critical_angle))
        parallel_chunk_size = max(1, min(max(int(chunk_size), 1), 32))
        tasks = [
            (
                start,
                min(start + parallel_chunk_size, len(cached_normals)),
                cached_normals[start : min(start + parallel_chunk_size, len(cached_normals))],
                pair_data,
            )
            for start in range(0, len(cached_normals), parallel_chunk_size)
        ]

        worker_count = min(len(tasks), max((os.cpu_count() or 1) - 1, 1))
        use_parallel = worker_count > 1 and len(cached_normals) * original_pair_count >= 256
        vol_a_cache = np.zeros((len(cached_normals), original_pair_count), dtype=float)
        vol_b_cache = np.zeros((len(cached_normals), original_pair_count), dtype=float)
        if use_parallel:
            with ProcessPoolExecutor(max_workers=worker_count) as executor:
                results = executor.map(ShTensor._compute_vispair_volume_chunk, tasks)
                for start, end, vol_a_chunk, vol_b_chunk in results:
                    vol_a_cache[start:end, :] = vol_a_chunk
                    vol_b_cache[start:end, :] = vol_b_chunk
        else:
            for task in tasks:
                start, end, vol_a_chunk, vol_b_chunk = ShTensor._compute_vispair_volume_chunk(task)
                vol_a_cache[start:end, :] = vol_a_chunk
                vol_b_cache[start:end, :] = vol_b_chunk

        for plane_id, normal in enumerate(unit_normals):
            cache_id = normal_inverse[plane_id]
            vol_a = vol_a_cache[cache_id]
            vol_b = vol_b_cache[cache_id]
            tri_a_support = (tri_a_normals @ normal) >= cos_critical
            tri_b_support = (tri_b_normals @ normal) >= cos_critical
            v_ss_vpair[plane_id] = vol_a[tri_a_support].sum() + vol_b[tri_b_support].sum()
            v_nv_vpair[plane_id] = vol_a[~tri_a_support].sum() + vol_b[~tri_b_support].sum()
            if raw_by_plane is not None:
                raw_by_plane[plane_id, :] = vol_a + vol_b

        return {"v_ss_vpair": v_ss_vpair, "v_nv_vpair": v_nv_vpair, "raw_by_plane": raw_by_plane}

    @staticmethod
    def _normalize_vectors(vectors: np.ndarray) -> np.ndarray:
        vectors = np.asarray(vectors, dtype=float)
        lengths = np.linalg.norm(vectors, axis=1)
        safe_lengths = np.where(lengths > 1e-12, lengths, 1.0)
        normalized = vectors / safe_lengths[:, None]
        normalized[lengths <= 1e-12] = 0.0
        return normalized

    @staticmethod
    def _unique_canonical_normals(normals: np.ndarray, tol: float = 1e-10) -> tuple[np.ndarray, np.ndarray]:
        normals = np.asarray(normals, dtype=float)
        unique_normals = []
        key_to_id = {}
        inverse = np.empty(len(normals), dtype=np.int64)

        for normal_id, normal in enumerate(normals):
            canonical = ShTensor._canonical_direction(normal)
            key = tuple(np.round(canonical / tol).astype(np.int64))
            unique_id = key_to_id.get(key)
            if unique_id is None:
                unique_id = len(unique_normals)
                key_to_id[key] = unique_id
                unique_normals.append(canonical)
            inverse[normal_id] = unique_id

        return np.asarray(unique_normals, dtype=float), inverse

    @staticmethod
    def _canonical_direction(direction: np.ndarray) -> np.ndarray:
        canonical = np.asarray(direction, dtype=float).copy()
        length = np.linalg.norm(canonical)
        if length <= 1e-12:
            return canonical
        canonical = canonical / length
        pivot = int(np.argmax(np.abs(canonical)))
        if canonical[pivot] < 0.0:
            canonical = -canonical
        return canonical

    @staticmethod
    def _compute_vispair_volume_chunk(args):
        start, end, normal_chunk, pair_data = args
        pair_count = len(pair_data)
        vol_a_chunk = np.zeros((end - start, pair_count), dtype=float)
        vol_b_chunk = np.zeros((end - start, pair_count), dtype=float)

        for local_plane_id, normal in enumerate(normal_chunk):
            for pair_id, item in enumerate(pair_data):
                if item is None:
                    continue
                poly_halfspaces, poly_points, pair_tri_a, pair_tri_b, _normal_a, _normal_b = item
                vol_a_chunk[local_plane_id, pair_id] = ShTensor.triangle_sweep_poly_intersection_volume_from_halfspaces(
                    poly_halfspaces,
                    pair_tri_a,
                    normal,
                    poly_points=poly_points,
                )
                vol_b_chunk[local_plane_id, pair_id] = ShTensor.triangle_sweep_poly_intersection_volume_from_halfspaces(
                    poly_halfspaces,
                    pair_tri_b,
                    normal,
                    poly_points=poly_points,
                )

        return start, end, vol_a_chunk, vol_b_chunk

    @staticmethod
    def _triangle_sweep_halfspaces(tri: np.ndarray, direction: np.ndarray) -> np.ndarray:
        tri = np.asarray(tri, dtype=float)
        direction = ShTensor._canonical_direction(direction)
        direction_length = np.linalg.norm(direction)
        if direction_length <= 1e-12:
            return np.empty((0, 4), dtype=float)

        centroid = tri.mean(axis=0)
        halfspaces = []
        for vertex_id in range(3):
            p0 = tri[vertex_id]
            p1 = tri[(vertex_id + 1) % 3]
            edge = p1 - p0
            normal = np.cross(edge, direction)
            normal_length = np.linalg.norm(normal)
            if normal_length <= 1e-12:
                continue
            normal = normal / normal_length
            offset = -float(normal @ p0)
            if float(normal @ centroid + offset) > 0.0:
                normal = -normal
                offset = -offset
            halfspaces.append(np.append(normal, offset))
        return np.asarray(halfspaces, dtype=float)

    @staticmethod
    def _halfspace_intersection_volume(halfspaces: np.ndarray, tol: float = 1e-9) -> float:
        halfspaces = np.asarray(halfspaces, dtype=float)
        if len(halfspaces) < 4:
            return 0.0

        coeffs = halfspaces[:, :3]
        offsets = halfspaces[:, 3]
        count = len(halfspaces)
        combos = []
        for i in range(count - 2):
            for j in range(i + 1, count - 1):
                for k in range(j + 1, count):
                    combos.append((i, j, k))
        if not combos:
            return 0.0
        combo_ids = np.asarray(combos, dtype=np.int64)
        matrices = coeffs[combo_ids]
        rhs = -offsets[combo_ids]
        determinants = np.linalg.det(matrices)
        valid_matrices = np.abs(determinants) > 1e-12
        if not np.any(valid_matrices):
            return 0.0
        try:
            candidates = np.linalg.solve(matrices[valid_matrices], rhs[valid_matrices])
        except np.linalg.LinAlgError:
            return 0.0
        inside = np.all(candidates @ coeffs.T + offsets[None, :] <= tol, axis=1)
        if not np.any(inside):
            return 0.0
        points = np.unique(np.round(candidates[inside], decimals=10), axis=0)
        if len(points) < 4:
            return 0.0
        _require_scipy()
        try:
            return float(ConvexHull(points).volume)
        except Exception:
            return 0.0

    @staticmethod
    def _poly_pair_halfspaces(poly_tri_a: np.ndarray, poly_tri_b: np.ndarray) -> np.ndarray | None:
        poly_points = np.vstack((np.asarray(poly_tri_a, dtype=float), np.asarray(poly_tri_b, dtype=float)))
        if len(np.unique(np.round(poly_points, decimals=12), axis=0)) < 4:
            return None
        _require_scipy()
        try:
            return np.asarray(ConvexHull(poly_points).equations, dtype=float)
        except Exception:
            return None

    @staticmethod
    def triangle_sweep_poly_intersection_volume_from_halfspaces(
        poly_halfspaces: np.ndarray,
        sweep_tri: np.ndarray,
        direction: np.ndarray,
        poly_points: np.ndarray | None = None,
    ) -> float:
        prism_halfspaces = ShTensor._triangle_sweep_halfspaces(sweep_tri, direction)
        if len(prism_halfspaces) < 3:
            return 0.0
        if poly_points is not None:
            values = np.asarray(poly_points, dtype=float) @ prism_halfspaces[:, :3].T + prism_halfspaces[:, 3]
            if np.any(np.all(values > 1e-9, axis=0)):
                return 0.0
        return ShTensor._halfspace_intersection_volume(np.vstack((poly_halfspaces, prism_halfspaces)))

    @staticmethod
    def triangle_sweep_poly_intersection_volume(
        poly_tri_a: np.ndarray,
        poly_tri_b: np.ndarray,
        sweep_tri: np.ndarray,
        direction: np.ndarray,
    ) -> float:
        poly_halfspaces = ShTensor._poly_pair_halfspaces(poly_tri_a, poly_tri_b)
        if poly_halfspaces is None:
            return 0.0
        return ShTensor.triangle_sweep_poly_intersection_volume_from_halfspaces(
            poly_halfspaces,
            sweep_tri,
            direction,
        )

    @staticmethod
    def triangular_prismatoid_volume(tri_a: np.ndarray, tri_b: np.ndarray) -> float:
        points = np.vstack((np.asarray(tri_a, dtype=float), np.asarray(tri_b, dtype=float)))
        if len(np.unique(np.round(points, decimals=12), axis=0)) < 4:
            return 0.0
        _require_scipy()
        try:
            return float(ConvexHull(points).volume)
        except Exception:
            return 0.0

    @staticmethod
    def load_trimesh_triangles(path: str) -> tuple[trimesh.Trimesh, np.ndarray]:
        mesh = trimesh.load_mesh(path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        mesh = mesh.copy()
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        return mesh, np.asarray(mesh.triangles, dtype=float)

    @staticmethod
    def triangles_from_mesh(mesh: trimesh.Trimesh) -> tuple[trimesh.Trimesh, np.ndarray]:
        mesh = mesh.copy()
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        return mesh, np.asarray(mesh.triangles, dtype=float)

    @staticmethod
    def visible_face_pairs_from_pairs(vis_pairs: Sequence[Sequence[int]] | np.ndarray | None) -> np.ndarray | None:
        if vis_pairs is None:
            return None

        face_pairs = np.asarray(vis_pairs, dtype=np.int64).reshape(-1, 2)
        if face_pairs.size == 0:
            return np.empty((0, 2), dtype=np.int64)
        return face_pairs

    def compute(
        self,
        tris: np.ndarray,
        mesh_center: np.ndarray | None = None,
        angles_yaw: Sequence[float] | None = None,
        angles_pitch: Sequence[float] | None = None,
        critical_angle: float | None = None,
        make_arrow_data: bool | None = None,
        build_triangle_structures: bool | None = None,
        store_bottom_projected_triangles: bool | None = None,
        store_raw_by_plane: bool | None = None,
        vis_pairs: Sequence[Sequence[int]] | np.ndarray | None = None,
    ) -> ShadowTensorResult:
        """
        End-to-end Python replacement for the Mathematica notebook workflow.

        Parameters
        ----------
        tris:
            Triangle vertices with shape (n_triangles, 3, 3).
        mesh_center:
            Equivalent to ScriptCapitalM_c. If omitted, the centroid of all mesh
            vertices is used.
        angles_yaw, angles_pitch:
            Degree angles used to generate Rotation.from_euler('xyz', [yaw, pitch, 0]).
        critical_angle:
            Radian critical angle. Mathematica used `60 Degree`.
        """
        cfg = self.config
        use_unique_orientations = (
            angles_yaw is None
            and angles_pitch is None
            and cfg.orientation_pairs is not None
            and cfg.orientation_inverse is not None
        )
        angles_yaw = cfg.angles_yaw if angles_yaw is None else angles_yaw
        angles_pitch = cfg.angles_pitch if angles_pitch is None else angles_pitch
        critical_angle = cfg.critical_angle if critical_angle is None else critical_angle
        make_arrow_data = cfg.make_arrow_data if make_arrow_data is None else make_arrow_data
        build_triangle_structures = (
            cfg.build_triangle_structures
            if build_triangle_structures is None
            else build_triangle_structures
        )
        store_bottom_projected_triangles = (
            cfg.store_bottom_projected_triangles
            if store_bottom_projected_triangles is None
            else store_bottom_projected_triangles
        )
        store_raw_by_plane = cfg.store_raw_by_plane if store_raw_by_plane is None else store_raw_by_plane
        build_triangle_structures = bool(build_triangle_structures or make_arrow_data)
        visible_face_pairs = self.visible_face_pairs_from_pairs(vis_pairs)

        tris = np.asarray(tris, dtype=float)
        tri_centers = tris.mean(axis=1)
        tri_normals = get_tri_list_normal(tris)
        tri_areas = triangle_areas(tris)

        if mesh_center is None:
            mesh_center = get_center(tris.reshape(-1, 3))
        else:
            mesh_center = np.asarray(mesh_center, dtype=float)

        convex_hull_planes, hull_info = self.build_convex_hull_planes(tris)
        if use_unique_orientations:
            ort_vectors = self.orientation_vectors_for_pairs(cfg.orientation_pairs)
            n_yaw, n_pitch = len(cfg.orientation_pairs), 1
        else:
            ort_vectors = self.orientation_vectors(angles_yaw, angles_pitch)
            n_yaw, n_pitch = len(angles_yaw), len(angles_pitch)
        bottom_planes = self.build_bottom_planes(mesh_center, hull_info["hull_vertices"], ort_vectors)
        bottom_projected_triangles = (
            [get_tris_on_plane(tris, plane) for plane in bottom_planes]
            if store_bottom_projected_triangles
            else None
        )

        if build_triangle_structures:
            triangle_structures, arrow_data = self.build_triangle_structures(
                tris,
                critical_angle,
                bottom_planes,
                ort_vectors if make_arrow_data else None,
                tensor_chunk_size=cfg.tensor_chunk_size,
            )
        else:
            triangle_structures = None
            arrow_data = None

        volumes = self.compute_triangle_to_btplane_volumes(
            tris,
            tri_normals,
            bottom_planes,
            critical_angle,
            n_yaw=n_yaw,
            n_pitch=n_pitch,
            tri_centers=tri_centers,
            tri_areas=tri_areas,
            chunk_size=cfg.shadow_chunk_size,
            store_raw_by_plane=bool(store_raw_by_plane),
        )
        # Use the fast estimator by default for project runs. The exact
        # intersection-based compute_vispair_volumes() remains available for
        # calibration and validation.
        vispair_volumes = self.compute_vispair_volumes_approx(
            tris,
            tri_normals,
            bottom_planes,
            critical_angle,
            n_yaw=n_yaw,
            n_pitch=n_pitch,
            visible_face_pairs=visible_face_pairs,
            tri_centers=tri_centers,
            tri_areas=tri_areas,
            chunk_size=cfg.shadow_chunk_size,
            store_raw_by_plane=False,
        )
        v_al_bt = np.asarray(volumes["V_al_bt"])
        v_be_bt = np.asarray(volumes["V_be_bt"])
        v_nv_bt = np.asarray(volumes["V_nv_bt"])

        v_nv_vpair = np.asarray(vispair_volumes["V_nv_vpair"])
        v_ss_vpair = np.asarray(vispair_volumes["V_ss_vpair"])

        volumes["V_nv_vpair"] = v_nv_vpair
        volumes["V_ss_vpair"] = v_ss_vpair

        # Backward-compatible aggregate keys. compute_v_ss recomputes these
        # explicitly from the *_bt and *_vpair components.
        volumes["V_al"] = v_al_bt
        volumes["V_be"] = v_be_bt
        volumes["V_nv"] = v_nv_bt# + v_nv_vpair
        volumes["V_ss"] = np.asarray(volumes["V_ss_bt"])# + v_ss_vpair

        volumes["V_o"] = volumes["V_al"] - volumes["V_be"]
        volumes["vtotal"] = np.asarray(volumes["vtotal"]) + np.asarray(vispair_volumes["vtotal"])
        if use_unique_orientations:
            inverse = np.asarray(cfg.orientation_inverse, dtype=np.int64)
            for key in (
                "V_al_bt",
                "V_be_bt",
                "V_nv_bt",
                "V_o_bt",
                "V_ss_bt",
                "V_nv_vpair",
                "V_ss_vpair",
                "V_al",
                "V_be",
                "V_nv",
                "V_o"
            ):
                volumes[key] = np.asarray(volumes[key]).reshape(-1)[inverse]

        return ShadowTensorResult(
            triangles=tris,
            triangle_centers=tri_centers,
            triangle_normals=tri_normals,
            triangle_areas=tri_areas,
            hull_info=hull_info,
            convex_hull_planes=convex_hull_planes,
            orientation_vectors=ort_vectors,
            bottom_planes=bottom_planes,
            bottom_projected_triangles=bottom_projected_triangles,
            triangle_structures=triangle_structures,
            graphics_arrow_data=arrow_data,
            volumes=volumes,
        )

    def run(
        self,
        vis_pairs: Sequence[Sequence[int]] | np.ndarray | None = None,
        mesh_path: str | None = None,
    ) -> ShadowTensorResult:
        
        t0 = time.perf_counter()

        if mesh_path is None and self.config.mesh is not None:
            mesh, triangles = self.triangles_from_mesh(self.config.mesh)
        else:
            mesh_path = self.config.mesh_path if mesh_path is None else mesh_path
            mesh, triangles = self.load_trimesh_triangles(mesh_path)
        result = self.compute(
            triangles,
            mesh_center=np.asarray(mesh.centroid, dtype=float),
            angles_yaw=self.config.angles_yaw,
            angles_pitch=self.config.angles_pitch,
            vis_pairs=vis_pairs,
        )

        print(f"mesh: {mesh_path if mesh_path is not None or self.config.mesh is None else '<TSE6Config.mesh>'}")
        print(f"faces: {len(mesh.faces)}")
        print(f"vertices: {len(mesh.vertices)}")

        print("V_al_bt:\n", result.volumes["V_al_bt"])
        print("V_be_bt:\n", result.volumes["V_be_bt"])
        print("V_nv_bt:\n", result.volumes["V_nv_bt"])

        print("V_nv_vpair:\n", result.volumes["V_nv_vpair"])
        print("V_ss_vpair:\n", result.volumes["V_ss_vpair"])
        
        print("V_al:\n", result.volumes["V_al"])
        print("V_be:\n", result.volumes["V_be"])
        print("V_nv:\n", result.volumes["V_nv"])
        self.mesh = mesh
        self.result = result

        log_time(f"shTensor calc. time= ", t0)

        return result

    def render(
        self,
        mesh: trimesh.Trimesh | None = None,
        result: ShadowTensorResult | None = None,
    ) -> None:
        if self.renderer is None:
            return
        mesh = self.mesh if mesh is None else mesh
        result = self.result if result is None else result
        if mesh is None or result is None:
            return

        ps_mesh = self.renderer.register_surface_mesh(
            "ShTensor mesh",
            np.asarray(mesh.vertices, dtype=np.float64),
            np.asarray(mesh.faces, dtype=np.int32),
            smooth_shade=False,
            color=(0.38, 0.78, 0.42),
            transparency=0.18,
        )
        ps_mesh.set_enabled(False)

        hull_vertices = np.asarray(result.hull_info["hull_vertices"], dtype=np.float64)
        hull_faces = np.asarray(result.hull_info["hull_faces"], dtype=np.int32)
        ps_hull = self.renderer.register_surface_mesh(
            "ShTensor convex hull",
            hull_vertices,
            hull_faces,
            smooth_shade=False,
            color=(0.25, 0.80, 0.55),
            transparency=0.35,
        )
        ps_hull.set_enabled(False)

        origins = np.asarray([plane["origin"] for plane in result.bottom_planes], dtype=np.float64)
        normals = np.asarray([plane["normal"] for plane in result.bottom_planes], dtype=np.float64)
        scale = max(float(np.max(mesh.bounding_box.extents)) * 0.12, 1e-6)
        plane_cloud = self.renderer.register_point_cloud(
            "ShTensor bottom plane origins",
            origins,
            radius=0.004,
            color=(0.1, 0.85, 0.25),
        )
        plane_cloud.add_vector_quantity(
            "bottom plane normal",
            normals * scale,
            enabled=True,
            color=(0.1, 0.85, 0.25),
        )
