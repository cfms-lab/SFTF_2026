from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import warnings
import webbrowser

import numpy as np
import trimesh

from .pareto import (
    compute_objectives as _compute_pareto_objectives,
    knee_point as _pareto_knee_point,
    pareto_mask as _pareto_mask,
    weighted_pick as _pareto_weighted_pick,
)


MESH_PATHS = [
    "./Experimental/etc/(1)Bunny_69k.ply",
    # "./Experimental/etc/(2)manikin.ply",
    # "./Experimental/etc/(3)dragon_100k_1.5x.ply",
    # "./Experimental/etc/(4)happy_50k_0.75x.ply",
    # "./Experimental/etc/(5)lucy_50k.ply",
    # "./Experimental/etc/FTree4x.stl",
    # "./Experimental/etc/Bunny_1k.ply",
]

EIGEN_VECTOR_DISPLAY_LENGTH = 0.005
EIGEN_VECTOR_DISPLAY_RADIUS = 0.0005
SUPPORT_CRITICAL_ANGLE_DEG = 60.0
SUPPORT_FLOW_COARSE_DIRECTION_COUNT = 512
SUPPORT_FLOW_REFINE_PARENT_COUNT = 12
SUPPORT_FLOW_REFINE_CONE_DEGREES = (2.0, 4.0, 6.0, 8.0)
SUPPORT_FLOW_REFINE_AZIMUTH_COUNT = 16
SUPPORT_FLOW_MIN_RAY_COUNT = 500
SUPPORT_FLOW_MAX_RAY_COUNT = 3000
SUPPORT_FLOW_FACE_FRACTION = 0.02
SUPPORT_FLOW_RAY_EPS_SCALE = 1e-6
SUPPORT_FLOW_HEIGHT_EPS_SCALE = 1e-5
SUPPORT_RECEIVER_NORMAL_THRESHOLD = 0.05
SUPPORT_FLOW_USE_FALLBACK_RAY_HITS = True
# When True, only faces whose downward tilt exceeds the support critical angle
# are treated as overhangs (matching TOMO_INT3's theta_c). A face needs support
# iff its angle from the build plate is below theta_c, i.e. (-m . n) > cos(theta_c).
# Default False preserves the original "any downward face" behaviour.
SUPPORT_OVERHANG_USE_CRITICAL_ANGLE = False
SUPPORT_SCORE_RAYLEIGH_WEIGHT = 1.0
SUPPORT_SCORE_PAIR_WEIGHT = 1.0
SUPPORT_SCORE_BED_WEIGHT = 1.0
# Nuclear-norm and sigma_1 terms are excluded from the objective J = R + P + B:
# the ablation showed they do not change candidate selection (J with and without
# them is identical). The singular values are still computed and exposed as
# auxiliary rank-tuning features only.
SUPPORT_SCORE_NUCLEAR_WEIGHT = 0.0
SUPPORT_SCORE_SIGMA1_WEIGHT = 0.0
SUPPORT_SCORE_FINAL_USE_RANK_TUNING = True
SUPPORT_SCORE_RANK_CURRENT_WEIGHT = 0.0
SUPPORT_SCORE_RANK_RAYLEIGH_WEIGHT = 0.731
SUPPORT_SCORE_RANK_PAIR_WEIGHT = -2.3897
SUPPORT_SCORE_RANK_BED_WEIGHT = 2.1447
SUPPORT_SCORE_RANK_HIT_WEIGHT = 2.3109
SUPPORT_SCORE_RANK_NUCLEAR_WEIGHT = -2.2922
SUPPORT_SCORE_RANK_SIGMA1_WEIGHT = 1.6363
SUPPORT_SCORE_USE_PARETO = False

# Backward-compatible names for older scripts.
SUPPORT_FLOW_DIRECTION_COUNT = SUPPORT_FLOW_COARSE_DIRECTION_COUNT
SUPPORT_FLOW_K_RAY = SUPPORT_FLOW_MIN_RAY_COUNT


@dataclass(frozen=True)
class ConcaveConfig:
    mesh: trimesh.Trimesh


@dataclass(frozen=True)
class SupportFlowDirection:
    rank: int
    label: str
    value: float
    direction: np.ndarray
    singular_values: np.ndarray | None = None
    tensor: np.ndarray | None = None
    rayleigh_score: float = 0.0
    pair_score: float = 0.0
    bed_score: float = 0.0
    hit_count: int = 0
    pareto_objectives: np.ndarray | None = None
    pareto_front_size: int | None = None
    pareto_knee: bool = False


@dataclass(frozen=True)
class SupportFlowAnalysis:
    normal_matrix: np.ndarray
    pca_matrix: np.ndarray
    support_directions: list[SupportFlowDirection]
    cavity_axes: list[SupportFlowDirection]
    flow_tensors: list[np.ndarray] | None = None
    support_candidate_results: list[tuple[float, float, float, float, int, np.ndarray, np.ndarray, np.ndarray]] | None = None


@dataclass(frozen=True)
class SupportFlowMeshData:
    normals: np.ndarray
    areas: np.ndarray
    centers: np.ndarray
    vertices: np.ndarray
    diagonal: float
    alpha: float
    ray_epsilon: float
    height_epsilon: float


EigenDirection = SupportFlowDirection
ConcaveEigenAnalysis = SupportFlowAnalysis


def print_time(label: str, elapsed: float) -> None:
    print(f"\033[92m{label}: {elapsed:.3f} s\033[0m", flush=True)


def mesh_label(mesh_path: str) -> str:
    return Path(mesh_path).stem


def load_mesh(mesh_path: str) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(mesh_path, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(f"expected Trimesh from {mesh_path}, got {type(mesh).__name__}")
    return _repair_inverted_orientation(mesh, mesh_path)


def _repair_inverted_orientation(mesh: trimesh.Trimesh, mesh_path: str) -> trimesh.Trimesh:
    """Repair an inside-out mesh (negative signed volume).

    An inverted mesh silently flips overhang detection (``-(normals @ n)``), so
    a convex solid reports face-to-face support everywhere. The repair rewinds
    each edge-connected component to a consistent outward orientation (handles
    mixed-winding files, e.g. pipe_elbow). Rebuilding the Trimesh from the
    repaired faces also discards file-stored facet normals, which trimesh would
    otherwise keep cached even after the winding is corrected.
    """
    if mesh.faces.size == 0 or float(mesh.volume) >= 0.0:
        return mesh
    warnings.warn(
        f"{mesh_path}: negative signed volume ({float(mesh.volume):.6g}); "
        "mesh is inside-out -- rewinding faces to consistent outward orientation.",
        stacklevel=3,
    )
    faces = np.asarray(mesh.faces, dtype=np.int64)
    try:
        from cpp_src.Tomo_GPU2026.mesh_orientation import orient_faces_outward
        faces = orient_faces_outward(mesh.vertices, faces)
    except ImportError:  # cpp_src not importable -> global flip is still better
        faces = faces[:, ::-1]
    return trimesh.Trimesh(
        vertices=np.asarray(mesh.vertices, dtype=np.float64),
        faces=faces,
        process=False,
    )


def mesh_vertices_faces_at_origin(mesh: trimesh.Trimesh) -> tuple[np.ndarray, np.ndarray]:
    clean_mesh = mesh.copy()
    clean_mesh.remove_unreferenced_vertices()
    vertices = np.asarray(clean_mesh.vertices, dtype=np.float64)
    vertices = vertices - vertices.min(axis=0)
    faces = np.asarray(clean_mesh.faces, dtype=np.int32)
    return vertices, faces


def _safe_unit(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    return np.zeros(3, dtype=np.float64) if norm <= 1e-12 else vector / norm


def _rotation_align_vector_to_z(vector: np.ndarray) -> np.ndarray:
    source = _safe_unit(vector)
    target = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    if np.linalg.norm(source) <= 1e-12:
        return np.eye(3, dtype=np.float64)

    cross = np.cross(source, target)
    sin_angle = float(np.linalg.norm(cross))
    cos_angle = float(np.clip(np.dot(source, target), -1.0, 1.0))
    if sin_angle <= 1e-12:
        if cos_angle > 0.0:
            return np.eye(3, dtype=np.float64)
        return np.diag([1.0, -1.0, -1.0]).astype(np.float64)

    axis = cross / sin_angle
    kx, ky, kz = axis
    skew = np.array(
        [
            [0.0, -kz, ky],
            [kz, 0.0, -kx],
            [-ky, kx, 0.0],
        ],
        dtype=np.float64,
    )
    return np.eye(3, dtype=np.float64) + skew * sin_angle + (skew @ skew) * (1.0 - cos_angle)


def _rotated_vertices_for_build_direction(vertices: np.ndarray, direction: np.ndarray) -> np.ndarray:
    rotation = _rotation_align_vector_to_z(direction)
    rotated = np.asarray(vertices, dtype=np.float64) @ rotation.T
    rotated -= rotated.min(axis=0)
    return rotated


def _sorted_eigen_directions(
    matrix: np.ndarray,
    *,
    labels: tuple[str, str, str],
    ascending: bool,
) -> list[SupportFlowDirection]:
    eigenvalues, eigenvectors = np.linalg.eigh(np.asarray(matrix, dtype=np.float64))
    order = np.argsort(eigenvalues)
    if not ascending:
        order = order[::-1]

    directions = []
    for rank, eigen_id in enumerate(order, start=1):
        direction = _safe_unit(eigenvectors[:, eigen_id])
        dominant_axis = int(np.argmax(np.abs(direction)))
        if direction[dominant_axis] < 0.0:
            direction = -direction
        directions.append(
            EigenDirection(
                rank=rank,
                label=labels[rank - 1],
                value=float(eigenvalues[eigen_id]),
                direction=direction,
            )
        )
    return directions


def _triangle_surface_data(mesh: trimesh.Trimesh) -> SupportFlowMeshData:
    normals = np.asarray(mesh.face_normals, dtype=np.float64)
    areas = np.asarray(mesh.area_faces, dtype=np.float64)
    centers = np.asarray(mesh.triangles_center, dtype=np.float64)
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    if normals.size == 0 or areas.size == 0 or centers.size == 0:
        diagonal = max(float(np.linalg.norm(np.ptp(vertices, axis=0))) if vertices.size else 0.0, 1e-12)
        return SupportFlowMeshData(
            normals=np.empty((0, 3), dtype=np.float64),
            areas=np.empty(0, dtype=np.float64),
            centers=np.empty((0, 3), dtype=np.float64),
            vertices=vertices,
            diagonal=diagonal,
            alpha=1.0 / diagonal,
            ray_epsilon=diagonal * SUPPORT_FLOW_RAY_EPS_SCALE,
            height_epsilon=diagonal * SUPPORT_FLOW_HEIGHT_EPS_SCALE,
        )

    valid = (
        np.isfinite(areas)
        & (areas > 0.0)
        & np.all(np.isfinite(normals), axis=1)
        & np.all(np.isfinite(centers), axis=1)
    )
    clean_normals = np.where(valid[:, None], normals, 0.0)
    clean_areas = np.where(valid, areas, 0.0)
    clean_centers = np.where(valid[:, None], centers, 0.0)
    diagonal = max(float(np.linalg.norm(np.ptp(vertices, axis=0))) if vertices.size else 0.0, 1e-12)
    return SupportFlowMeshData(
        normals=clean_normals,
        areas=clean_areas,
        centers=clean_centers,
        vertices=vertices,
        diagonal=diagonal,
        alpha=1.0 / diagonal,
        ray_epsilon=diagonal * SUPPORT_FLOW_RAY_EPS_SCALE,
        height_epsilon=diagonal * SUPPORT_FLOW_HEIGHT_EPS_SCALE,
    )


def _area_weighted_center_covariance(meshes: list[trimesh.Trimesh]) -> np.ndarray:
    centers = []
    weights = []
    for mesh in meshes:
        face_centers = np.asarray(mesh.triangles_center, dtype=np.float64)
        areas = np.asarray(mesh.area_faces, dtype=np.float64)
        if face_centers.size == 0 or areas.size == 0:
            continue
        valid = np.isfinite(areas) & (areas > 0.0) & np.all(np.isfinite(face_centers), axis=1)
        if np.any(valid):
            centers.append(face_centers[valid])
            weights.append(areas[valid])

    if not centers:
        return np.zeros((3, 3), dtype=np.float64)

    all_centers = np.vstack(centers)
    all_weights = np.concatenate(weights)
    total_weight = float(np.sum(all_weights))
    if total_weight <= 1e-12:
        return np.zeros((3, 3), dtype=np.float64)

    centroid = np.average(all_centers, axis=0, weights=all_weights)
    centered = all_centers - centroid
    return np.einsum("i,ij,ik->jk", all_weights, centered, centered) / total_weight


def _spherical_sample_directions(count: int) -> np.ndarray:
    count = max(int(count), 1)
    indices = np.arange(count, dtype=np.float64)
    golden_angle = np.pi * (3.0 - np.sqrt(5.0))
    z = 1.0 - 2.0 * (indices + 0.5) / count
    radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    theta = indices * golden_angle
    return np.column_stack((radius * np.cos(theta), radius * np.sin(theta), z))


def _orthonormal_basis(direction: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = _safe_unit(direction)
    seed = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    if abs(float(np.dot(seed, n))) > 0.85:
        seed = np.array([0.0, 1.0, 0.0], dtype=np.float64)
    u = _safe_unit(np.cross(n, seed))
    v = _safe_unit(np.cross(n, u))
    return u, v


def _cone_sample_directions(
    center_direction: np.ndarray,
    *,
    cone_degrees: tuple[float, ...] = SUPPORT_FLOW_REFINE_CONE_DEGREES,
    azimuth_count: int = SUPPORT_FLOW_REFINE_AZIMUTH_COUNT,
) -> np.ndarray:
    n = _safe_unit(center_direction)
    if np.linalg.norm(n) <= 1e-12:
        return np.empty((0, 3), dtype=np.float64)
    u, v = _orthonormal_basis(n)
    directions = [n]
    azimuths = np.linspace(0.0, 2.0 * np.pi, max(int(azimuth_count), 1), endpoint=False)
    for degree in cone_degrees:
        angle = np.deg2rad(float(degree))
        for azimuth in azimuths:
            tangent = np.cos(azimuth) * u + np.sin(azimuth) * v
            directions.append(_safe_unit(np.cos(angle) * n + np.sin(angle) * tangent))
    return np.asarray(directions, dtype=np.float64)


def _adaptive_k_ray(face_count: int) -> int:
    by_fraction = int(np.ceil(max(int(face_count), 1) * SUPPORT_FLOW_FACE_FRACTION))
    return int(np.clip(by_fraction, SUPPORT_FLOW_MIN_RAY_COUNT, SUPPORT_FLOW_MAX_RAY_COUNT))


def _unique_directions(directions: list[np.ndarray], *, dot_tolerance: float = 1.0 - 1e-10) -> list[np.ndarray]:
    unique: list[np.ndarray] = []
    unique_matrix = np.empty((0, 3), dtype=np.float64)
    for direction in directions:
        unit = _safe_unit(direction)
        if np.linalg.norm(unit) <= 1e-12:
            continue
        if unique_matrix.size and np.any(np.abs(unique_matrix @ unit) >= dot_tolerance):
            continue
        unique.append(unit)
        unique_matrix = np.vstack([unique_matrix, unit])
    return unique


def _sample_ray_face_ids(areas: np.ndarray, overhang: np.ndarray, k_ray: int) -> np.ndarray:
    weights = np.asarray(areas, dtype=np.float64) * np.asarray(overhang, dtype=np.float64)
    valid_ids = np.flatnonzero(weights > 0.0)
    k_ray = int(max(k_ray, 1))
    if valid_ids.size <= k_ray:
        return valid_ids

    valid_weights = weights[valid_ids]
    total_weight = float(np.sum(valid_weights))
    if total_weight <= 1e-12:
        return np.empty(0, dtype=np.int64)

    cumulative = np.cumsum(valid_weights)
    targets = (np.arange(k_ray, dtype=np.float64) + 0.5) * total_weight / k_ray
    sampled = valid_ids[np.searchsorted(cumulative, targets, side="left")]
    sampled = np.unique(sampled)
    if sampled.size >= k_ray:
        return sampled[:k_ray]

    missing = k_ray - sampled.size
    keep_remainder = np.ones(valid_ids.size, dtype=bool)
    keep_remainder[np.searchsorted(valid_ids, sampled)] = False
    remainder = valid_ids[keep_remainder]
    if remainder.size == 0:
        return sampled
    remainder_weights = weights[remainder]
    if missing < remainder.size:
        candidate_ids = np.argpartition(remainder_weights, -missing)[-missing:]
    else:
        candidate_ids = np.arange(remainder.size)
    order = candidate_ids[np.argsort(remainder_weights[candidate_ids])[::-1]]
    return np.concatenate([sampled, remainder[order]])


def _valid_ray_hit_mask(
    ray_ids: np.ndarray,
    triangle_ids: np.ndarray,
    distances: np.ndarray,
    source_face_ids: np.ndarray,
    normals: np.ndarray,
    centers: np.ndarray,
    build_direction: np.ndarray,
    height_epsilon: float,
) -> np.ndarray:
    if triangle_ids.size == 0:
        return np.zeros(0, dtype=bool)

    source_ids = source_face_ids[ray_ids]
    heights = (centers[source_ids] - centers[triangle_ids]) @ build_direction
    receiver_alignment = normals[triangle_ids] @ build_direction
    return (
        (triangle_ids != source_ids)
        & (distances > max(1e-10, height_epsilon))
        & (heights > height_epsilon)
        & (receiver_alignment > SUPPORT_RECEIVER_NORMAL_THRESHOLD)
    )


def _first_valid_ray_hits(
    mesh: trimesh.Trimesh,
    origins: np.ndarray,
    ray_directions: np.ndarray,
    source_face_ids: np.ndarray,
    normals: np.ndarray,
    centers: np.ndarray,
    build_direction: np.ndarray,
    height_epsilon: float,
) -> dict[int, int]:
    hit_map: dict[int, int] = {}
    if len(origins) == 0:
        return hit_map

    try:
        triangle_ids, ray_ids, locations = mesh.ray.intersects_id(
            origins,
            ray_directions,
            return_locations=True,
            multiple_hits=False,
        )
    except Exception:
        return hit_map

    triangle_ids = np.asarray(triangle_ids, dtype=np.int64)
    ray_ids = np.asarray(ray_ids, dtype=np.int64)
    locations = np.asarray(locations, dtype=np.float64)
    if triangle_ids.size == 0:
        return hit_map

    distances = np.einsum("ij,ij->i", locations - origins[ray_ids], ray_directions[ray_ids])
    valid_hit = _valid_ray_hit_mask(
        ray_ids,
        triangle_ids,
        distances,
        source_face_ids,
        normals,
        centers,
        build_direction,
        height_epsilon,
    )
    if np.any(valid_hit):
        hit_map.update(
            (int(ray_id), int(triangle_id))
            for ray_id, triangle_id in zip(ray_ids[valid_hit], triangle_ids[valid_hit])
        )

    first_hit_rays = np.unique(ray_ids)
    if hit_map:
        accepted_ray_ids = np.fromiter(hit_map.keys(), dtype=np.int64, count=len(hit_map))
        fallback_mask = np.ones(first_hit_rays.size, dtype=bool)
        fallback_mask[np.searchsorted(first_hit_rays, accepted_ray_ids)] = False
        fallback_ray_ids = first_hit_rays[fallback_mask]
    else:
        fallback_ray_ids = first_hit_rays
    if fallback_ray_ids.size == 0:
        return hit_map
    if not SUPPORT_FLOW_USE_FALLBACK_RAY_HITS:
        return hit_map

    try:
        fallback_triangle_ids, fallback_local_ray_ids, fallback_locations = mesh.ray.intersects_id(
            origins[fallback_ray_ids],
            ray_directions[fallback_ray_ids],
            return_locations=True,
            multiple_hits=True,
        )
    except Exception:
        return hit_map

    fallback_triangle_ids = np.asarray(fallback_triangle_ids, dtype=np.int64)
    fallback_local_ray_ids = np.asarray(fallback_local_ray_ids, dtype=np.int64)
    fallback_locations = np.asarray(fallback_locations, dtype=np.float64)
    if fallback_triangle_ids.size == 0:
        return hit_map

    fallback_origins = origins[fallback_ray_ids][fallback_local_ray_ids]
    fallback_directions = ray_directions[fallback_ray_ids][fallback_local_ray_ids]
    fallback_distances = np.einsum(
        "ij,ij->i",
        fallback_locations - fallback_origins,
        fallback_directions,
    )
    fallback_valid = _valid_ray_hit_mask(
        fallback_local_ray_ids,
        fallback_triangle_ids,
        fallback_distances,
        source_face_ids[fallback_ray_ids],
        normals,
        centers,
        build_direction,
        height_epsilon,
    )
    if not np.any(fallback_valid):
        return hit_map

    valid_ids = np.flatnonzero(fallback_valid)
    order = valid_ids[np.argsort(fallback_distances[valid_ids], kind="stable")]
    _unique_local_ray_ids, first_order_ids = np.unique(fallback_local_ray_ids[order], return_index=True)
    selected_ids = order[first_order_ids]
    hit_map.update(
        (int(fallback_ray_ids[int(local_ray_id)]), int(triangle_id))
        for local_ray_id, triangle_id in zip(fallback_local_ray_ids[selected_ids], fallback_triangle_ids[selected_ids])
    )
    return hit_map


def _support_flow_tensor_for_direction(
    mesh: trimesh.Trimesh,
    direction: np.ndarray,
    *,
    k_ray: int | None = None,
    surface_data: SupportFlowMeshData | None = None,
) -> tuple[np.ndarray, np.ndarray, float, float, float, float, int]:
    n = _safe_unit(direction)
    if np.linalg.norm(n) <= 1e-12:
        return np.zeros((3, 3), dtype=np.float64), np.zeros(3, dtype=np.float64), float("inf"), 0.0, 0.0, 0.0, 0

    data = _triangle_surface_data(mesh) if surface_data is None else surface_data
    normals = data.normals
    areas = data.areas
    centers = data.centers
    vertices = data.vertices
    if normals.size == 0 or vertices.size == 0:
        return np.zeros((3, 3), dtype=np.float64), np.zeros(3, dtype=np.float64), float("inf"), 0.0, 0.0, 0.0, 0

    k_ray = _adaptive_k_ray(len(areas)) if k_ray is None else int(k_ray)
    overhang = np.maximum(0.0, -(normals @ n))
    if SUPPORT_OVERHANG_USE_CRITICAL_ANGLE:
        critical_cosine = float(np.cos(np.deg2rad(SUPPORT_CRITICAL_ANGLE_DEG)))
        overhang = np.where(overhang > critical_cosine, overhang, 0.0)
    source_face_ids = _sample_ray_face_ids(areas, overhang, k_ray)
    if source_face_ids.size == 0:
        return np.zeros((3, 3), dtype=np.float64), np.zeros(3, dtype=np.float64), 0.0, 0.0, 0.0, 0.0, 0

    origins = centers[source_face_ids] - data.ray_epsilon * n
    ray_directions = np.tile(-n, (len(source_face_ids), 1))
    hit_map = _first_valid_ray_hits(
        mesh,
        origins,
        ray_directions,
        source_face_ids,
        normals,
        centers,
        n,
        data.height_epsilon,
    )

    flow = np.zeros((3, 3), dtype=np.float64)
    pair_score = 0.0
    if hit_map:
        hit_ray_ids = np.fromiter(hit_map.keys(), dtype=np.int64, count=len(hit_map))
        target_face_ids = np.fromiter(hit_map.values(), dtype=np.int64, count=len(hit_map))
        hit_source_face_ids = source_face_ids[hit_ray_ids]
        h_ij = (centers[hit_source_face_ids] - centers[target_face_ids]) @ n
        valid_pair = h_ij > data.height_epsilon
        if np.any(valid_pair):
            source_ids = hit_source_face_ids[valid_pair]
            target_ids = target_face_ids[valid_pair]
            heights = h_ij[valid_pair]
            # P(n): the height attenuation 1/(1+a*h) in the pair weight cancels with the
            # (1+a*h) factor it is multiplied back by, so the pair score is just the
            # area-weighted overhang of the valid hits.
            pair_base = overhang[source_ids] * areas[source_ids] * areas[target_ids]
            pair_score = float(np.sum(pair_base))
            # F(n) keeps the height attenuation so distant face-face flow contributes less.
            pair_weights = pair_base / (1.0 + data.alpha * heights)
            flow = np.einsum(
                "i,ij,ik->jk",
                pair_weights,
                normals[source_ids],
                normals[target_ids],
            )
    else:
        hit_ray_ids = np.empty(0, dtype=np.int64)

    support_floor = float(np.min(vertices @ n))
    bed_source_mask = np.ones(len(source_face_ids), dtype=bool)
    bed_source_mask[hit_ray_ids] = False
    bed_source_ids = source_face_ids[bed_source_mask]
    bed_score = 0.0
    if bed_source_ids.size:
        bed_heights = centers[bed_source_ids] @ n - support_floor
        valid_bed = bed_heights > data.height_epsilon
        if np.any(valid_bed):
            source_ids = bed_source_ids[valid_bed]
            heights = bed_heights[valid_bed]
            bed_score = float(
                np.sum(
                    overhang[source_ids]
                    * areas[source_ids]
                    * (1.0 + data.alpha * heights)
                )
            )

    symmetric_flow = 0.5 * (flow + flow.T)
    raw_rayleigh = float(n @ symmetric_flow @ n)
    rayleigh_score = max(0.0, -raw_rayleigh)
    singular_values = np.linalg.svd(flow, compute_uv=False)
    nuclear_score = float(np.sum(singular_values))
    sigma1_score = float(singular_values[0]) if singular_values.size else 0.0
    score = (
        SUPPORT_SCORE_RAYLEIGH_WEIGHT * rayleigh_score
        + SUPPORT_SCORE_PAIR_WEIGHT * pair_score
        + SUPPORT_SCORE_BED_WEIGHT * bed_score
        + SUPPORT_SCORE_NUCLEAR_WEIGHT * nuclear_score
        + SUPPORT_SCORE_SIGMA1_WEIGHT * sigma1_score
    )
    return flow, singular_values, score, rayleigh_score, pair_score, bed_score, len(hit_map)


def _evaluate_support_flow_candidate(
    mesh: trimesh.Trimesh,
    direction: np.ndarray,
    surface_data: SupportFlowMeshData,
    *,
    k_ray: int | None = None,
) -> tuple[float, float, float, float, int, np.ndarray, np.ndarray, np.ndarray] | None:
    (
        flow,
        singular_values,
        score,
        rayleigh_score,
        pair_score,
        bed_score,
        hit_count,
    ) = _support_flow_tensor_for_direction(mesh, direction, k_ray=k_ray, surface_data=surface_data)
    if not np.isfinite(score):
        return None
    return (
        float(score),
        float(rayleigh_score),
        float(pair_score),
        float(bed_score),
        int(hit_count),
        _safe_unit(direction),
        np.asarray(flow, dtype=np.float64),
        np.asarray(singular_values, dtype=np.float64),
    )


def _rank_support_flow_results(
    results: list[tuple[float, float, float, float, int, np.ndarray, np.ndarray, np.ndarray]],
    *,
    limit: int = 3,
    min_angle_degrees: float = 4.0,
) -> list[tuple[float, float, float, float, int, np.ndarray, np.ndarray, np.ndarray]]:
    ranked = []
    min_dot = float(np.cos(np.deg2rad(min_angle_degrees)))
    for result in sorted(results, key=lambda item: item[0]):
        direction = result[5]
        if any(abs(float(np.dot(direction, existing[5]))) >= min_dot for existing in ranked):
            continue
        ranked.append(result)
        if len(ranked) >= limit:
            break
    return ranked


def _pareto_objective_rows(
    results: list[tuple[float, float, float, float, int, np.ndarray, np.ndarray, np.ndarray]],
    surface_data: SupportFlowMeshData,
) -> np.ndarray:
    return np.asarray(
        [
            _compute_pareto_objectives(
                result[5],
                surface_data.vertices,
                surface_data.normals,
                surface_data.areas,
                result[1],
                result[3],
                surface_data.diagonal,
            )
            for result in results
        ],
        dtype=np.float64,
    )


def _rank_support_flow_results_pareto(
    results: list[tuple[float, float, float, float, int, np.ndarray, np.ndarray, np.ndarray]],
    surface_data: SupportFlowMeshData,
    *,
    limit: int = 3,
    min_angle_degrees: float = 4.0,
    weights: np.ndarray | None = None,
) -> tuple[
    list[tuple[float, float, float, float, int, np.ndarray, np.ndarray, np.ndarray]],
    dict[int, dict[str, object]],
]:
    if not results:
        return [], {}

    costs = _pareto_objective_rows(results, surface_data)
    front_ids = np.flatnonzero(_pareto_mask(costs))
    if front_ids.size == 0:
        return _rank_support_flow_results(results, limit=limit, min_angle_degrees=min_angle_degrees), {}

    front_costs = costs[front_ids]
    if weights is None:
        knee_local_id = _pareto_knee_point(front_costs)
    else:
        knee_local_id = _pareto_weighted_pick(front_costs, weights)
    knee_result_id = int(front_ids[knee_local_id])

    # Pareto is a filter, not a replacement scalar objective.  We order front
    # candidates by the primary support cost R+B only to choose basin
    # representatives before TOMO/slicer verification.
    order = front_ids[np.argsort(front_costs[:, 0], kind="stable")]
    ranked_ids: list[int] = []
    min_dot = float(np.cos(np.deg2rad(min_angle_degrees)))
    for result_id in order:
        direction = np.asarray(results[int(result_id)][5], dtype=np.float64)
        if any(float(np.dot(direction, results[existing_id][5])) >= min_dot for existing_id in ranked_ids):
            continue
        ranked_ids.append(int(result_id))
        if len(ranked_ids) >= limit:
            break

    metadata = {
        id(results[int(result_id)]): {
            "objectives": costs[int(result_id)].copy(),
            "front_size": int(front_ids.size),
            "knee": int(result_id) == knee_result_id,
        }
        for result_id in front_ids
    }
    return [results[result_id] for result_id in ranked_ids], metadata


def _rank_normalized_feature(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.size <= 1:
        return np.zeros_like(values, dtype=np.float64)
    order = np.argsort(values, kind="stable")
    ranks = np.empty_like(values, dtype=np.float64)
    ranks[order] = np.linspace(0.0, 1.0, len(values), dtype=np.float64)
    return ranks


def _tune_final_support_flow_scores(
    results: list[tuple[float, float, float, float, int, np.ndarray, np.ndarray, np.ndarray]],
) -> list[tuple[float, float, float, float, int, np.ndarray, np.ndarray, np.ndarray]]:
    if not SUPPORT_SCORE_FINAL_USE_RANK_TUNING or len(results) <= 1:
        return results

    feature_rows = []
    for score, rayleigh_score, pair_score, bed_score, hit_count, _direction, _flow, singular_values in results:
        singular_values = np.asarray(singular_values, dtype=np.float64)
        feature_rows.append(
            (
                float(score),
                float(rayleigh_score),
                float(pair_score),
                float(bed_score),
                float(hit_count),
                float(np.sum(singular_values)),
                float(singular_values[0]) if singular_values.size else 0.0,
            )
        )

    features = np.asarray(feature_rows, dtype=np.float64)
    rank_features = np.column_stack(
        [_rank_normalized_feature(features[:, feature_id]) for feature_id in range(features.shape[1])]
    )
    weights = np.asarray(
        [
            SUPPORT_SCORE_RANK_CURRENT_WEIGHT,
            SUPPORT_SCORE_RANK_RAYLEIGH_WEIGHT,
            SUPPORT_SCORE_RANK_PAIR_WEIGHT,
            SUPPORT_SCORE_RANK_BED_WEIGHT,
            SUPPORT_SCORE_RANK_HIT_WEIGHT,
            SUPPORT_SCORE_RANK_NUCLEAR_WEIGHT,
            SUPPORT_SCORE_RANK_SIGMA1_WEIGHT,
        ],
        dtype=np.float64,
    )
    tuned_scores = rank_features @ weights
    return [
        (float(tuned_scores[result_id]),) + tuple(result[1:])
        for result_id, result in enumerate(results)
    ]


def evaluate_support_flow_candidate_pool(
    mesh: trimesh.Trimesh,
    *,
    k_ray: int | None = None,
) -> list[tuple[float, float, float, float, int, np.ndarray, np.ndarray, np.ndarray]]:
    results = []
    surface_data = _triangle_surface_data(mesh)
    coarse_directions = _spherical_sample_directions(SUPPORT_FLOW_COARSE_DIRECTION_COUNT)
    for direction in coarse_directions:
        result = _evaluate_support_flow_candidate(mesh, direction, surface_data, k_ray=k_ray)
        if result is not None:
            results.append(result)

    parent_results = _rank_support_flow_results(
        results,
        limit=SUPPORT_FLOW_REFINE_PARENT_COUNT,
        min_angle_degrees=8.0,
    )
    refine_directions = _unique_directions(
        [
            direction
            for parent in parent_results
            for direction in _cone_sample_directions(parent[5])
        ]
    )
    for direction in refine_directions:
        result = _evaluate_support_flow_candidate(mesh, direction, surface_data, k_ray=k_ray)
        if result is not None:
            results.append(result)

    return _tune_final_support_flow_scores(results)


def support_flow_directions_from_candidate_pool(
    results: list[tuple[float, float, float, float, int, np.ndarray, np.ndarray, np.ndarray]],
    *,
    limit: int = 3,
    min_angle_degrees: float = 3.0,
    use_pareto: bool | None = None,
    mesh: trimesh.Trimesh | None = None,
    surface_data: SupportFlowMeshData | None = None,
    pareto_weights: np.ndarray | None = None,
) -> list[SupportFlowDirection]:
    use_pareto = SUPPORT_SCORE_USE_PARETO if use_pareto is None else bool(use_pareto)
    pareto_metadata: dict[int, dict[str, object]] = {}
    if use_pareto:
        if surface_data is None:
            if mesh is None:
                raise ValueError("mesh or surface_data is required when use_pareto=True")
            surface_data = _triangle_surface_data(mesh)
        results, pareto_metadata = _rank_support_flow_results_pareto(
            results,
            surface_data,
            limit=limit,
            min_angle_degrees=min_angle_degrees,
            weights=pareto_weights,
        )
    else:
        results = _rank_support_flow_results(results, limit=limit, min_angle_degrees=min_angle_degrees)

    directions = []
    for rank, (
        score,
        rayleigh_score,
        pair_score,
        bed_score,
        hit_count,
        direction,
        flow,
        singular_values,
    ) in enumerate(results, start=1):
        pareto_entry = pareto_metadata.get(id(results[rank - 1]))
        pareto_objectives = (
            np.asarray(pareto_entry["objectives"], dtype=np.float64)
            if pareto_entry is not None
            else None
        )
        if pareto_objectives is None:
            label = (
                f"support flow score {rank} hits={hit_count} "
                f"ray={rayleigh_score:.4g} pair={pair_score:.4g} bed={bed_score:.4g}"
            )
            value = float(score)
        else:
            label = (
                f"pareto support flow {rank} hits={hit_count} "
                f"R+B={pareto_objectives[0]:.4g} height={pareto_objectives[1]:.4g} "
                f"overhang={pareto_objectives[2]:.4g}"
            )
            value = float(pareto_objectives[0])
        directions.append(
            SupportFlowDirection(
                rank=rank,
                label=label,
                value=value,
                direction=direction,
                singular_values=np.asarray(singular_values, dtype=np.float64),
                tensor=np.asarray(flow, dtype=np.float64),
                rayleigh_score=float(rayleigh_score),
                pair_score=float(pair_score),
                bed_score=float(bed_score),
                hit_count=int(hit_count),
                pareto_objectives=pareto_objectives,
                pareto_front_size=(
                    int(pareto_entry["front_size"]) if pareto_entry is not None else None
                ),
                pareto_knee=bool(pareto_entry["knee"]) if pareto_entry is not None else False,
            )
        )
    return directions


def evaluate_support_flow_directions(
    mesh: trimesh.Trimesh,
    *,
    use_pareto: bool | None = None,
) -> list[SupportFlowDirection]:
    return support_flow_directions_from_candidate_pool(
        evaluate_support_flow_candidate_pool(mesh),
        mesh=mesh,
        use_pareto=use_pareto,
    )


def analyze_support_flow_directions(
    meshes: list[trimesh.Trimesh],
    input_mesh: trimesh.Trimesh | None = None,
) -> SupportFlowAnalysis:
    input_mesh = meshes[0] if input_mesh is None and meshes else input_mesh
    pca_matrix = _area_weighted_center_covariance(meshes)
    support_candidate_results = evaluate_support_flow_candidate_pool(input_mesh) if input_mesh is not None else []
    support_directions = support_flow_directions_from_candidate_pool(support_candidate_results) if input_mesh is not None else []
    normal_matrix = (
        np.mean([item.tensor for item in support_directions if item.tensor is not None], axis=0)
        if support_directions
        else np.zeros((3, 3), dtype=np.float64)
    )
    return SupportFlowAnalysis(
        normal_matrix=normal_matrix,
        pca_matrix=pca_matrix,
        support_directions=support_directions,
        cavity_axes=_sorted_eigen_directions(
            pca_matrix,
            labels=("cavity major axis", "cavity middle axis", "cavity minor axis"),
            ascending=False,
        ),
        flow_tensors=[item.tensor for item in support_directions if item.tensor is not None],
        support_candidate_results=support_candidate_results,
    )


def analyze_concave_eigen_directions(
    meshes: list[trimesh.Trimesh],
    input_mesh: trimesh.Trimesh | None = None,
) -> ConcaveEigenAnalysis:
    return analyze_support_flow_directions(meshes, input_mesh=input_mesh)


def print_concave_eigen_analysis(label: str, analysis: ConcaveEigenAnalysis) -> None:
    print(f"{label} spherical sampled support flow directions:")
    for item in analysis.support_directions:
        x, y, z = item.direction
        sv = (
            ", ".join(f"{float(value):.4g}" for value in item.singular_values)
            if item.singular_values is not None
            else ""
        )
        print(
            f"  {item.rank}. {item.label}: score={item.value:.6g}, "
            f"direction=({x:.4f}, {y:.4f}, {z:.4f}), sv=[{sv}]"
        )

    print(f"{label} concave cavity PCA axes:")
    for item in analysis.cavity_axes:
        x, y, z = item.direction
        print(
            f"  {item.rank}. {item.label}: variance={item.value:.6g}, "
            f"axis=({x:.4f}, {y:.4f}, {z:.4f})"
        )


class SupportFlowTensorField:
    def __init__(
        self,
        input_mesh: trimesh.Trimesh,
        convex_hull: trimesh.Trimesh,
        *,
        boolean_engine: str | None = None,
        check_volume: bool = False,
    ) -> None:
        self.input_mesh = self._clean_mesh(input_mesh)
        self.convex_hull = self._clean_mesh(convex_hull)
        self.boolean_engine = boolean_engine
        self.check_volume = bool(check_volume)
        self.concaveMeshes = self._build_concave_meshes()
        self.eigen_analysis = analyze_support_flow_directions(
            self.concaveMeshes,
            input_mesh=self.input_mesh,
        )

    @staticmethod
    def _clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        clean_mesh = mesh.copy()
        clean_mesh.update_faces(clean_mesh.nondegenerate_faces())
        clean_mesh.remove_unreferenced_vertices()
        clean_mesh.fix_normals()
        return clean_mesh

    def _build_concave_meshes(self) -> list[trimesh.Trimesh]:
        try:
            concave_volume = trimesh.boolean.difference(
                [self.convex_hull, self.input_mesh],
                engine=self.boolean_engine,
                check_volume=self.check_volume,
            )
        except Exception as exc:
            raise RuntimeError(
                "Failed to build concaveMeshes with trimesh boolean difference. "
                "Install a boolean backend such as manifold3d, or pass another "
                "trimesh-compatible engine."
            ) from exc

        if concave_volume is None:
            return []
        if isinstance(concave_volume, trimesh.Scene):
            concave_volume = concave_volume.dump(concatenate=True)

        concave_volume = self._clean_mesh(concave_volume)
        return [
            self._clean_mesh(component)
            for component in concave_volume.split(only_watertight=False)
            if len(component.faces) > 0
        ]

    def render_polyscope(
        self,
        renderer,
        *,
        offset: np.ndarray | None = None,
        name_prefix: str = "",
        enabled: bool = True,
    ) -> None:
        offset = np.zeros(3, dtype=np.float64) if offset is None else np.asarray(offset, dtype=np.float64)
        label_prefix = f"{name_prefix} " if name_prefix else ""
        group = (
            renderer.create_group(f"{label_prefix}concaveMeshes")
            if hasattr(renderer, "create_group")
            else None
        )

        for mesh_id, concave_mesh in enumerate(self.concaveMeshes):
            vertices = np.asarray(concave_mesh.vertices, dtype=np.float64) + offset
            faces = np.asarray(concave_mesh.faces, dtype=np.int32)
            ps_mesh = renderer.register_surface_mesh(
                f"{label_prefix}concaveMesh {mesh_id}",
                vertices,
                faces,
                smooth_shade=False,
                color=(0.12, 0.72, 0.46),
                transparency=0.50,
            )
            ps_mesh.set_enabled(enabled)
            if group is not None:
                ps_mesh.add_to_group(group)

    def render_eigen_directions(
        self,
        renderer,
        *,
        offset: np.ndarray | None = None,
        name_prefix: str = "",
        enabled: bool = True,
    ) -> None:
        offset = np.zeros(3, dtype=np.float64) if offset is None else np.asarray(offset, dtype=np.float64)
        label_prefix = f"{name_prefix} " if name_prefix else ""
        if self.concaveMeshes:
            vertices = np.vstack([np.asarray(mesh.vertices, dtype=np.float64) for mesh in self.concaveMeshes])
        else:
            vertices = np.asarray(self.input_mesh.vertices, dtype=np.float64)
        if vertices.size == 0:
            return
        center = 0.5 * (vertices.min(axis=0) + vertices.max(axis=0)) + offset
        group = (
            renderer.create_group(f"{label_prefix}support flow directions")
            if hasattr(renderer, "create_group")
            else None
        )

        render_specs = [
            ("support", self.eigen_analysis.support_directions, (0.08, 0.30, 0.95)),
            ("cavity", self.eigen_analysis.cavity_axes, (0.95, 0.55, 0.08)),
        ]
        for spec_name, directions, color in render_specs:
            points = []
            vectors = []
            values = []
            for item in directions:
                points.append(center)
                vectors.append(item.direction * EIGEN_VECTOR_DISPLAY_LENGTH)
                values.append(item.value)
            if not points:
                continue

            point_cloud = renderer.register_point_cloud(
                f"{label_prefix}{spec_name} directions",
                np.asarray(points, dtype=np.float64),
                radius=EIGEN_VECTOR_DISPLAY_RADIUS,
                color=color,
            )
            point_cloud.set_enabled(enabled)
            if group is not None:
                point_cloud.add_to_group(group)
            point_cloud.add_vector_quantity(
                f"{spec_name} direction",
                np.asarray(vectors, dtype=np.float64),
                enabled=True,
                color=color,
            )
            point_cloud.add_scalar_quantity(
                f"{spec_name} flow score" if spec_name == "support" else f"{spec_name} eigenvalue",
                np.asarray(values, dtype=np.float64),
                enabled=False,
            )


SupportFlowEvaluator = SupportFlowTensorField


def render_eigen_oriented_meshes(
    renderer,
    result: dict[str, object],
    *,
    cell_origin: np.ndarray,
    item_step: np.ndarray,
) -> None:
    mesh = result["cfg"].mesh
    vertices, faces = mesh_vertices_faces_at_origin(mesh)
    support_directions = result["support_flow_tensor_field"].eigen_analysis.support_directions
    label = str(result["label"])
    group = (
        renderer.create_group(f"{label} support flow oriented meshes")
        if hasattr(renderer, "create_group")
        else None
    )

    for direction_id, direction in enumerate(support_directions, start=1):
        rotated_vertices = _rotated_vertices_for_build_direction(vertices, direction.direction)
        offset = cell_origin + np.array([direction_id * item_step[0], 0.0, 0.0], dtype=np.float64)
        score = float(direction_id)
        ps_mesh = renderer.register_surface_mesh(
            f"{label} v_ss score {direction_id} flow={direction.value:.6g}",
            np.ascontiguousarray(rotated_vertices + offset, dtype=np.float64),
            np.asarray(faces, dtype=np.int32),
            smooth_shade=False,
            color=(0.18, 0.38, 0.88),
            transparency=0.42,
        )
        if group is not None:
            ps_mesh.add_to_group(group)
        ps_mesh.add_scalar_quantity(
            "v_ss score",
            np.full(len(rotated_vertices), score, dtype=np.float64),
            enabled=True,
        )
        ps_mesh.add_scalar_quantity(
            "support flow score",
            np.full(len(rotated_vertices), direction.value, dtype=np.float64),
            enabled=False,
        )


def render_input_mesh_reference(
    renderer,
    result: dict[str, object],
    *,
    offset: np.ndarray,
) -> None:
    mesh = result["cfg"].mesh
    label = str(result["label"])
    ps_mesh = renderer.register_surface_mesh(
        f"{label} input mesh",
        np.asarray(mesh.vertices, dtype=np.float64) + offset,
        np.asarray(mesh.faces, dtype=np.int32),
        smooth_shade=False,
        color=(0.72, 0.74, 0.78),
        transparency=0.34,
    )
    if hasattr(renderer, "create_group"):
        ps_mesh.add_to_group(renderer.create_group(f"{label} input"))


def run_sftf_mesh(renderer, mesh_path: str) -> dict[str, object]:
    cfg = ConcaveConfig(mesh=load_mesh(mesh_path))
    print(f"\n=== {mesh_path} ===", flush=True)

    support_flow_tensor_field = SupportFlowTensorField(cfg.mesh, cfg.mesh.convex_hull)
    print(f"concaveMeshes: {len(support_flow_tensor_field.concaveMeshes)}")
    print_concave_eigen_analysis(mesh_label(mesh_path), support_flow_tensor_field.eigen_analysis)

    return {
        "mesh_path": mesh_path,
        "label": mesh_label(mesh_path),
        "cfg": cfg,
        "support_flow_tensor_field": support_flow_tensor_field,
    }


def render_sftf_results(renderer, results: list[dict[str, object]]) -> None:
    extents = []
    for result in results:
        vertices, _faces = mesh_vertices_faces_at_origin(result["cfg"].mesh)
        extents.append(vertices.max(axis=0) - vertices.min(axis=0))

    max_extent = np.maximum(np.max(np.asarray(extents, dtype=np.float64), axis=0), 1e-6)
    item_gap = 0.25 * float(max_extent.max())
    item_step = max_extent + item_gap
    row_step = item_step[1] + item_gap

    for result_id, result in enumerate(results):
        cell_origin = np.array([0.0, -result_id * row_step, 0.0], dtype=np.float64)
        mesh_min = result["cfg"].mesh.vertices.min(axis=0)
        display_offset = cell_origin - mesh_min

        render_input_mesh_reference(
            renderer,
            result,
            offset=display_offset,
        )
        result["support_flow_tensor_field"].render_polyscope(
            renderer,
            offset=display_offset,
            name_prefix=str(result["label"]),
        )
        result["support_flow_tensor_field"].render_eigen_directions(
            renderer,
            offset=display_offset,
            name_prefix=str(result["label"]),
        )
        render_eigen_oriented_meshes(
            renderer,
            result,
            cell_origin=cell_origin,
            item_step=item_step,
        )


def show_tomo_sftf_plotly_comparison(
    results: list[dict[str, object]],
    *,
    project_root: Path | None = None,
    tomo_root: Path | None = None,
    output_html: Path | None = None,
) -> None:
    project_root = Path(__file__).resolve().parents[2] if project_root is None else Path(project_root)
    tomo_root = project_root / "cpp_src" / "Tomo_GPU2026" if tomo_root is None else Path(tomo_root)
    output_html = (
        project_root / "Experimental" / "etc" / "tomo_int3_sftf_active_mesh_comparison.html"
        if output_html is None
        else Path(output_html)
    )

    from scripts.plot_sftf_tomo_int3_contours import build_figure_for_results

    figure = build_figure_for_results(
        results,
        project_root=project_root,
        tomo_root=tomo_root,
    )
    output_html.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(output_html, include_plotlyjs="cdn")
    webbrowser.open(output_html.resolve().as_uri())
