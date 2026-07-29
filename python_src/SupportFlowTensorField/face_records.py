"""Public per-face support-flow extraction API.

This module is the supported boundary for downstream partitioners.  It keeps
the ray-casting implementation private to ``support_flow_tensor_field`` while
exposing stable, face-indexed arrays needed by SFTF-derived applications.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh

from .support_flow_tensor_field import (
    SUPPORT_CRITICAL_ANGLE_DEG,
    SUPPORT_OVERHANG_USE_CRITICAL_ANGLE,
    _first_valid_ray_hits,
    _safe_unit,
    _triangle_surface_data,
)


@dataclass(frozen=True)
class SupportFlowFaceRecords:
    direction: np.ndarray
    vertices: np.ndarray
    centers: np.ndarray
    normals: np.ndarray
    areas: np.ndarray
    height_epsilon: float
    overhang: np.ndarray
    source_face_ids: np.ndarray
    target_face: np.ndarray


def normalize_direction(direction: object) -> np.ndarray:
    """Return a finite unit 3-vector using the core SFTF convention."""

    return _safe_unit(np.asarray(direction, dtype=np.float64))


def extract_support_flow_face_records(
    mesh: trimesh.Trimesh,
    direction: object,
    *,
    use_critical_angle: bool | None = None,
    critical_angle_degrees: float = SUPPORT_CRITICAL_ANGLE_DEG,
) -> SupportFlowFaceRecords:
    """Extract full-resolution per-face overhang and receiver records.

    Every overhang face is traced; unlike candidate scoring, this public
    application API does not subsample source faces.
    """

    data = _triangle_surface_data(mesh)
    n = normalize_direction(direction)
    face_count = len(data.normals)
    overhang = (
        np.maximum(0.0, -(data.normals @ n))
        if face_count
        else np.zeros(0, dtype=np.float64)
    )
    gate = SUPPORT_OVERHANG_USE_CRITICAL_ANGLE if use_critical_angle is None else bool(use_critical_angle)
    if gate and face_count:
        critical_cosine = float(np.cos(np.deg2rad(float(critical_angle_degrees))))
        overhang = np.where(overhang > critical_cosine, overhang, 0.0)

    source_face_ids = np.flatnonzero(overhang > 0.0).astype(np.int64)
    target_face = np.full(face_count, -1, dtype=np.int64)
    if source_face_ids.size:
        origins = data.centers[source_face_ids] - n * data.ray_epsilon
        ray_directions = np.tile(-n, (len(source_face_ids), 1))
        hit_map = _first_valid_ray_hits(
            mesh,
            origins,
            ray_directions,
            source_face_ids,
            data.normals,
            data.centers,
            n,
            data.height_epsilon,
        )
        for local_id, target_id in hit_map.items():
            target_face[int(source_face_ids[int(local_id)])] = int(target_id)

    return SupportFlowFaceRecords(
        direction=n,
        vertices=data.vertices,
        centers=data.centers,
        normals=data.normals,
        areas=data.areas,
        height_epsilon=float(data.height_epsilon),
        overhang=overhang,
        source_face_ids=source_face_ids,
        target_face=target_face,
    )
