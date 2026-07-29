from __future__ import annotations

import numpy as np
import trimesh

from SupportFlowTensorField.sftf_v2 import (
    SFTFV2Config,
    assemble_dimensionless_moments,
    deterministic_surface_samples,
    evaluate_sftf_v2,
)


def _two_plate_mesh(scale: float = 1.0) -> trimesh.Trimesh:
    lower = trimesh.creation.box(extents=np.array([2.0, 2.0, 0.2]) * scale)
    lower.apply_translation([0.0, 0.0, 0.1 * scale])
    upper = trimesh.creation.box(extents=np.array([1.0, 1.0, 0.2]) * scale)
    upper.apply_translation([0.0, 0.0, 1.1 * scale])
    return trimesh.util.concatenate((lower, upper))


def test_pair_rayleigh_and_ground_identity() -> None:
    n = np.array([0.0, 0.0, 1.0])
    source = np.array([[0.0, 0.0, -1.0], [0.0, 0.0, -1.0]])
    receiver = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 0.0]])
    tensor, rayleigh, bed, score, _skew = assemble_dimensionless_moments(
        n,
        source,
        receiver,
        overhang=np.ones(2),
        normalized_heights=np.array([0.25, 0.50]),
        hit_mask=np.array([True, False]),
        sample_denominator=2,
        distance_weight=1.0,
    )
    assert np.isclose(tensor[2, 2], -0.4)
    assert np.isclose(rayleigh, 0.4)
    assert np.isclose(bed, 0.75)
    assert np.isclose(score, 1.15)


def test_antisymmetric_tensor_cannot_change_rayleigh_scalar() -> None:
    n = np.array([0.2, -0.3, 0.9])
    n /= np.linalg.norm(n)
    skew = np.array([[0.0, 2.0, -1.0], [-2.0, 0.0, 0.5], [1.0, -0.5, 0.0]])
    assert np.isclose(float(n @ skew @ n), 0.0, atol=1.0e-15)


def test_surface_sample_is_fixed_and_area_normalized() -> None:
    mesh = _two_plate_mesh()
    first = deterministic_surface_samples(mesh, 512)
    second = deterministic_surface_samples(mesh, 512)
    assert np.array_equal(first.face_ids, second.face_ids)
    assert np.array_equal(first.points, second.points)
    assert np.isclose(first.diameter, np.linalg.norm(mesh.extents))


def test_full_score_is_invariant_to_uniform_scaling() -> None:
    config = SFTFV2Config(sample_count=1024, critical_angle_deg=60.0)
    direction = np.array([0.0, 0.0, 1.0])
    unit = evaluate_sftf_v2(_two_plate_mesh(1.0), direction, config=config)
    scaled = evaluate_sftf_v2(_two_plate_mesh(17.0), direction, config=config)
    assert unit.score > 0.0
    assert np.isclose(unit.score, scaled.score, rtol=1.0e-10, atol=1.0e-12)
    assert np.isclose(unit.rayleigh_score, scaled.rayleigh_score, rtol=1.0e-10)
    assert np.isclose(unit.bed_score, scaled.bed_score, rtol=1.0e-10)
