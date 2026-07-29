"""Dimensionless, surface-measure Support Flow Tensor Field (SFTF v2).

This module is intentionally separate from ``support_flow_tensor_field.py``.
The legacy implementation remains frozen so that the submitted-paper results
can be reproduced.  SFTF v2 removes the legacy source-area times receiver-area
term, uses one fixed deterministic surface sample for every direction, and
normalizes ray heights by the mesh bounding-box diagonal.

The scalar score is lower-is-better and has two terms::

    F_pair(n) = E_A[ I_hit O/(1 + lambda h/D) m_s outer m_r ]
    R(n)      = max(0, -n.T sym(F_pair) n)
    B(n)      = E_A[ I_bed O (1 + lambda h_bed/D) ]
    S(n)      = R(n) + B(n)

``E_A`` denotes expectation under normalized surface-area measure.  Therefore
the score is dimensionless and invariant to uniform mesh scaling.  The
antisymmetric part of ``F_pair`` is reported only as an uncertainty diagnostic;
it cannot change the Rayleigh scalar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import trimesh


@dataclass(frozen=True)
class SFTFV2Config:
    """Numerical settings that must be frozen before external evaluation."""

    sample_count: int = 4096
    critical_angle_deg: float = 60.0
    distance_weight: float = 1.0
    receiver_normal_min: float = 1.0e-8
    ray_epsilon_scale: float = 1.0e-7
    apply_critical_gate: bool = True


@dataclass(frozen=True)
class SurfaceMeasureSamples:
    """A deterministic area-uniform sample reused for all build directions."""

    points: np.ndarray
    normals: np.ndarray
    face_ids: np.ndarray
    diameter: float


@dataclass(frozen=True)
class SFTFV2Evaluation:
    """Dimensionless SFTF v2 diagnostics for one build direction."""

    direction: np.ndarray
    score: float
    rayleigh_score: float
    bed_score: float
    tensor: np.ndarray
    skew_ratio: float
    hit_fraction: float
    active_surface_fraction: float
    sample_count: int


def _unit(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float64)
    norm = float(np.linalg.norm(value))
    if not np.isfinite(norm) or norm <= 1.0e-15:
        raise ValueError("build direction must be a finite nonzero vector")
    return value / norm


def _radical_inverse(indices: np.ndarray, base: int) -> np.ndarray:
    """Vectorized radical inverse used for deterministic triangle coordinates."""

    remaining = np.asarray(indices, dtype=np.int64).copy()
    result = np.zeros(remaining.shape, dtype=np.float64)
    factor = 1.0 / float(base)
    while np.any(remaining > 0):
        result += factor * (remaining % base)
        remaining //= base
        factor /= float(base)
    return result


def deterministic_surface_samples(
    mesh: trimesh.Trimesh,
    sample_count: int,
) -> SurfaceMeasureSamples:
    """Sample the mesh under normalized area measure without random state.

    Face IDs are selected by midpoint quadrature on cumulative triangle area.
    Base-2/base-3 radical-inverse coordinates place the sample inside each
    selected triangle.  Reusing this object across directions prevents the
    direction-dependent sampling distribution used by the legacy scorer.
    """

    count = int(sample_count)
    if count <= 0:
        raise ValueError("sample_count must be positive")
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        raise ValueError("mesh must be a nonempty trimesh.Trimesh")

    triangles = np.asarray(mesh.triangles, dtype=np.float64)
    areas = np.asarray(mesh.area_faces, dtype=np.float64)
    valid = np.isfinite(areas) & (areas > 0.0)
    if not np.any(valid):
        raise ValueError("mesh has no finite positive-area triangles")

    valid_ids = np.flatnonzero(valid)
    valid_areas = areas[valid_ids]
    total_area = float(np.sum(valid_areas))
    cumulative = np.cumsum(valid_areas)
    targets = (np.arange(count, dtype=np.float64) + 0.5) * total_area / count
    face_ids = valid_ids[np.searchsorted(cumulative, targets, side="left")]

    sequence_ids = np.arange(1, count + 1, dtype=np.int64)
    u = _radical_inverse(sequence_ids, 2)
    v = _radical_inverse(sequence_ids, 3)
    root_u = np.sqrt(u)
    barycentric = np.column_stack(
        (1.0 - root_u, root_u * (1.0 - v), root_u * v)
    )
    points = np.einsum("ij,ijk->ik", barycentric, triangles[face_ids])
    normals = np.asarray(mesh.face_normals, dtype=np.float64)[face_ids]

    extents = np.asarray(mesh.bounds[1] - mesh.bounds[0], dtype=np.float64)
    diameter = float(np.linalg.norm(extents))
    if not np.isfinite(diameter) or diameter <= 1.0e-15:
        raise ValueError("mesh bounding-box diagonal must be positive")

    return SurfaceMeasureSamples(
        points=points,
        normals=normals,
        face_ids=np.asarray(face_ids, dtype=np.int64),
        diameter=diameter,
    )


def _first_receiver_hits(
    mesh: trimesh.Trimesh,
    points: np.ndarray,
    source_face_ids: np.ndarray,
    direction: np.ndarray,
    *,
    diameter: float,
    receiver_normal_min: float,
    ray_epsilon_scale: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the first valid receiver face and source-to-hit height per ray."""

    ray_count = len(points)
    receiver_ids = np.full(ray_count, -1, dtype=np.int64)
    heights = np.full(ray_count, np.nan, dtype=np.float64)
    if ray_count == 0:
        return receiver_ids, heights

    epsilon = max(float(diameter) * float(ray_epsilon_scale), 1.0e-12)
    origins = np.asarray(points, dtype=np.float64) - epsilon * direction
    ray_directions = np.tile(-direction, (ray_count, 1))

    try:
        triangle_ids, ray_ids, locations = mesh.ray.intersects_id(
            origins,
            ray_directions,
            return_locations=True,
            multiple_hits=True,
        )
    except Exception:
        return receiver_ids, heights

    triangle_ids = np.asarray(triangle_ids, dtype=np.int64)
    ray_ids = np.asarray(ray_ids, dtype=np.int64)
    locations = np.asarray(locations, dtype=np.float64)
    if triangle_ids.size == 0:
        return receiver_ids, heights

    source_points = np.asarray(points, dtype=np.float64)[ray_ids]
    source_to_hit = np.einsum("ij,j->i", source_points - locations, direction)
    receiver_alignment = (
        np.asarray(mesh.face_normals, dtype=np.float64)[triangle_ids] @ direction
    )
    valid = (
        (triangle_ids != np.asarray(source_face_ids, dtype=np.int64)[ray_ids])
        & np.isfinite(source_to_hit)
        & (source_to_hit > epsilon)
        & (receiver_alignment > float(receiver_normal_min))
    )
    if not np.any(valid):
        return receiver_ids, heights

    valid_ids = np.flatnonzero(valid)
    order = valid_ids[
        np.lexsort((source_to_hit[valid_ids], ray_ids[valid_ids]))
    ]
    ordered_rays = ray_ids[order]
    _unique_rays, first_positions = np.unique(ordered_rays, return_index=True)
    selected = order[first_positions]
    receiver_ids[ray_ids[selected]] = triangle_ids[selected]
    heights[ray_ids[selected]] = source_to_hit[selected]
    return receiver_ids, heights


def assemble_dimensionless_moments(
    build_direction: np.ndarray,
    source_normals: np.ndarray,
    receiver_normals: np.ndarray,
    overhang: np.ndarray,
    normalized_heights: np.ndarray,
    hit_mask: np.ndarray,
    *,
    sample_denominator: int,
    distance_weight: float = 1.0,
) -> tuple[np.ndarray, float, float, float, float]:
    """Assemble ``F_pair``, ``R``, ``B``, ``S``, and the skew diagnostic.

    Inputs may contain only active overhang samples, but ``sample_denominator``
    must be the size of the original area-uniform surface sample.  This keeps
    the expectation normalized by total surface area instead of by overhang
    area, which is required for comparable scores across directions.
    """

    n = _unit(build_direction)
    source = np.asarray(source_normals, dtype=np.float64)
    receiver = np.asarray(receiver_normals, dtype=np.float64)
    overhang_values = np.asarray(overhang, dtype=np.float64)
    heights = np.asarray(normalized_heights, dtype=np.float64)
    hits = np.asarray(hit_mask, dtype=bool)
    count = len(overhang_values)
    if source.shape != (count, 3) or receiver.shape != (count, 3):
        raise ValueError("source_normals and receiver_normals must have shape (N, 3)")
    if heights.shape != (count,) or hits.shape != (count,):
        raise ValueError("overhang, normalized_heights, and hit_mask must have length N")
    denominator = int(sample_denominator)
    if denominator <= 0:
        raise ValueError("sample_denominator must be positive")
    if np.any(~np.isfinite(overhang_values)) or np.any(overhang_values < 0.0):
        raise ValueError("overhang values must be finite and nonnegative")
    if np.any(~np.isfinite(heights)) or np.any(heights < 0.0):
        raise ValueError("normalized heights must be finite and nonnegative")

    tensor = np.zeros((3, 3), dtype=np.float64)
    if np.any(hits):
        pair_weights = overhang_values[hits] / (
            1.0 + float(distance_weight) * heights[hits]
        )
        tensor = np.einsum(
            "i,ij,ik->jk",
            pair_weights / denominator,
            source[hits],
            receiver[hits],
        )

    symmetric = 0.5 * (tensor + tensor.T)
    skew = 0.5 * (tensor - tensor.T)
    rayleigh = max(0.0, -float(n @ symmetric @ n))
    bed_mask = ~hits
    bed = float(
        np.sum(
            overhang_values[bed_mask]
            * (1.0 + float(distance_weight) * heights[bed_mask])
        )
        / denominator
    )
    score = rayleigh + bed
    skew_ratio = float(
        np.linalg.norm(skew, ord="fro")
        / max(np.linalg.norm(symmetric, ord="fro"), 1.0e-15)
    )
    return tensor, rayleigh, bed, score, skew_ratio


def evaluate_sftf_v2(
    mesh: trimesh.Trimesh,
    direction: np.ndarray,
    *,
    config: SFTFV2Config | None = None,
    samples: SurfaceMeasureSamples | None = None,
) -> SFTFV2Evaluation:
    """Evaluate the dimensionless SFTF v2 score for one direction."""

    settings = SFTFV2Config() if config is None else config
    n = _unit(direction)
    surface = (
        deterministic_surface_samples(mesh, settings.sample_count)
        if samples is None
        else samples
    )
    total_samples = len(surface.points)
    if total_samples <= 0:
        raise ValueError("surface sample must not be empty")

    overhang_all = np.maximum(0.0, -(surface.normals @ n))
    active = overhang_all > 0.0
    if settings.apply_critical_gate:
        threshold = float(np.cos(np.deg2rad(settings.critical_angle_deg)))
        active &= overhang_all >= threshold
    active_ids = np.flatnonzero(active)
    if active_ids.size == 0:
        return SFTFV2Evaluation(
            direction=n,
            score=0.0,
            rayleigh_score=0.0,
            bed_score=0.0,
            tensor=np.zeros((3, 3), dtype=np.float64),
            skew_ratio=0.0,
            hit_fraction=0.0,
            active_surface_fraction=0.0,
            sample_count=total_samples,
        )

    active_points = surface.points[active_ids]
    active_faces = surface.face_ids[active_ids]
    receiver_ids, pair_heights = _first_receiver_hits(
        mesh,
        active_points,
        active_faces,
        n,
        diameter=surface.diameter,
        receiver_normal_min=settings.receiver_normal_min,
        ray_epsilon_scale=settings.ray_epsilon_scale,
    )
    hit_mask = receiver_ids >= 0

    receiver_normals = np.zeros((active_ids.size, 3), dtype=np.float64)
    normalized_heights = np.zeros(active_ids.size, dtype=np.float64)
    if np.any(hit_mask):
        receiver_normals[hit_mask] = np.asarray(
            mesh.face_normals, dtype=np.float64
        )[receiver_ids[hit_mask]]
        normalized_heights[hit_mask] = (
            pair_heights[hit_mask] / surface.diameter
        )

    bed_mask = ~hit_mask
    if np.any(bed_mask):
        support_floor = float(np.min(np.asarray(mesh.vertices, dtype=np.float64) @ n))
        bed_heights = active_points[bed_mask] @ n - support_floor
        normalized_heights[bed_mask] = np.maximum(0.0, bed_heights / surface.diameter)

    tensor, rayleigh, bed, score, skew_ratio = assemble_dimensionless_moments(
        n,
        surface.normals[active_ids],
        receiver_normals,
        overhang_all[active_ids],
        normalized_heights,
        hit_mask,
        sample_denominator=total_samples,
        distance_weight=settings.distance_weight,
    )
    return SFTFV2Evaluation(
        direction=n,
        score=score,
        rayleigh_score=rayleigh,
        bed_score=bed,
        tensor=tensor,
        skew_ratio=skew_ratio,
        hit_fraction=float(np.mean(hit_mask)),
        active_surface_fraction=float(active_ids.size / total_samples),
        sample_count=total_samples,
    )


def rank_sftf_v2_directions(
    mesh: trimesh.Trimesh,
    directions: Iterable[np.ndarray],
    *,
    config: SFTFV2Config | None = None,
) -> list[SFTFV2Evaluation]:
    """Evaluate and return directions sorted from lowest to highest score."""

    settings = SFTFV2Config() if config is None else config
    samples = deterministic_surface_samples(mesh, settings.sample_count)
    evaluations = [
        evaluate_sftf_v2(mesh, direction, config=settings, samples=samples)
        for direction in directions
    ]
    return sorted(evaluations, key=lambda item: (item.score, *item.direction.tolist()))
