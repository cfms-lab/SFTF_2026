from __future__ import annotations

import numpy as np
import trimesh

from python_src.SupportFlowTensorField import (
    AdaptiveVerificationConfig,
    RoutingPolicyConfig,
    adaptive_verification_decision,
    candidate_pool_signals,
    extract_support_flow_face_records,
    orientation_policy_from_pool,
    progressive_uniform_axis_directions,
)


def _row(score: float, direction: tuple[float, float, float]):
    return (score, 0.0, 0.0, 0.0, 0, np.asarray(direction, dtype=np.float64), np.eye(3), np.ones(3))


def test_uniform_axis_order_is_deterministic_and_separated() -> None:
    a = progressive_uniform_axis_directions(32)
    b = progressive_uniform_axis_directions(32)
    np.testing.assert_allclose(a, b)
    np.testing.assert_allclose(np.linalg.norm(a, axis=1), 1.0)
    assert int(np.argmax(a[:, 2])) == 0


def test_diffuse_pool_routes_to_uniform() -> None:
    pool = [
        _row(1.0, (1, 0, 0)),
        _row(1.1, (0, 1, 0)),
        _row(0.9, (0, 0, 1)),
        _row(1.2, (1, 1, 1)),
    ]
    config = RoutingPolicyConfig(top_k=4, nn_fraction_min=0.8)
    result = orientation_policy_from_pool(pool, limit=4, config=config)
    assert result.route == "uniform"
    assert result.sources == ("uniform",) * 4


def test_crowded_stable_pool_uses_tuned_h25() -> None:
    angles = np.deg2rad([0.0, 3.2, 6.4, 9.6])
    pool = [_row(1.0 + 0.01 * i, (np.sin(a), 0.0, np.cos(a))) for i, a in enumerate(angles)]
    config = RoutingPolicyConfig(
        top_k=4,
        nms_degrees=3.0,
        floor_factor=1.5,
        nn_fraction_min=0.75,
        score_cv_max=2.0,
    )
    signals = candidate_pool_signals(pool, config)
    assert signals.nn_fraction >= 0.75
    result = orientation_policy_from_pool(pool, limit=4, config=config)
    assert result.route == "tuned_h25"
    assert result.sources.count("tuned") == 1
    assert result.sources.count("uniform") == 3


def test_adaptive_verification_tiers() -> None:
    config = AdaptiveVerificationConfig()
    base = adaptive_verification_decision(
        normalized_local_support=0.001,
        seed_to_local_gain=2.0,
        boundary_hit=False,
        config=config,
    )
    assert (base.tier, base.top_k, base.triggered) == ("base", 10, False)
    escalated = adaptive_verification_decision(
        normalized_local_support=0.02,
        seed_to_local_gain=4.0,
        boundary_hit=False,
        config=config,
    )
    assert (escalated.tier, escalated.top_k, escalated.triggered) == ("escalate", 50, True)
    severe = adaptive_verification_decision(
        normalized_local_support=0.02,
        seed_to_local_gain=1.0,
        boundary_hit=True,
        config=config,
    )
    assert (severe.tier, severe.top_k, severe.triggered) == ("severe", 200, True)


def test_public_face_records_cover_every_overhang_source() -> None:
    mesh = trimesh.creation.box()
    records = extract_support_flow_face_records(mesh, (0.0, 0.0, 1.0))
    np.testing.assert_array_equal(records.source_face_ids, np.flatnonzero(records.overhang > 0.0))
    assert records.target_face.shape == (len(mesh.faces),)
    assert records.centers.shape == (len(mesh.faces), 3)
