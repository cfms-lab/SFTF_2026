from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import trimesh

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField.pareto import (  # noqa: E402
    compute_objectives,
    knee_point,
    pareto_mask,
    weighted_pick,
)
from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    evaluate_support_flow_candidate_pool,
    support_flow_directions_from_candidate_pool,
)


class ParetoUtilityTests(unittest.TestCase):
    def test_toy_dominance(self) -> None:
        costs = np.asarray(
            [
                [100.0, 50.0],
                [120.0, 30.0],
                [130.0, 60.0],
            ],
            dtype=np.float64,
        )
        np.testing.assert_array_equal(pareto_mask(costs), np.array([True, True, False]))

    def test_all_tradeoff_points_are_non_dominated(self) -> None:
        costs = np.asarray(
            [
                [1.0, 5.0],
                [2.0, 4.0],
                [3.0, 3.0],
                [4.0, 2.0],
                [5.0, 1.0],
            ],
            dtype=np.float64,
        )
        self.assertTrue(bool(np.all(pareto_mask(costs))))

    def test_single_point_mask_and_knee(self) -> None:
        costs = np.asarray([[2.0, 3.0, 4.0]], dtype=np.float64)
        np.testing.assert_array_equal(pareto_mask(costs), np.array([True]))
        self.assertEqual(knee_point(costs), 0)

    def test_knee_point_prefers_normalized_utopia_distance(self) -> None:
        costs = np.asarray(
            [
                [0.0, 1.0],
                [0.45, 0.45],
                [1.0, 0.0],
            ],
            dtype=np.float64,
        )
        self.assertEqual(knee_point(costs), 1)

    def test_weighted_pick_uses_normalized_front_costs(self) -> None:
        costs = np.asarray(
            [
                [0.0, 1.0],
                [0.4, 0.4],
                [1.0, 0.0],
            ],
            dtype=np.float64,
        )
        self.assertEqual(weighted_pick(costs, np.array([0.1, 0.9])), 2)

    def test_compute_objectives_minimization_components(self) -> None:
        vertices = np.asarray(
            [
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 2.0],
            ],
            dtype=np.float64,
        )
        normals = np.asarray([[0.0, 0.0, -1.0], [0.0, 0.0, 1.0]], dtype=np.float64)
        areas = np.asarray([3.0, 5.0], dtype=np.float64)
        objectives = compute_objectives(
            np.array([0.0, 0.0, 1.0]),
            vertices,
            normals,
            areas,
            rayleigh_score=2.0,
            bed_score=7.0,
            diagonal=2.0,
        )
        np.testing.assert_allclose(objectives, [9.0, 1.0, 3.0], atol=1e-12)


class SftfParetoIntegrationTests(unittest.TestCase):
    def test_use_pareto_false_preserves_default_top_directions(self) -> None:
        mesh = trimesh.creation.box(extents=(2.0, 1.0, 1.0))
        pool = evaluate_support_flow_candidate_pool(mesh)
        default_rows = support_flow_directions_from_candidate_pool(pool, limit=3)
        explicit_rows = support_flow_directions_from_candidate_pool(pool, limit=3, use_pareto=False)

        self.assertEqual(len(default_rows), len(explicit_rows))
        for default, explicit in zip(default_rows, explicit_rows):
            np.testing.assert_allclose(default.direction, explicit.direction, atol=1e-12)
            self.assertAlmostEqual(default.value, explicit.value, places=12)
            self.assertIsNone(explicit.pareto_objectives)

    def test_pareto_path_returns_front_candidates_with_objectives(self) -> None:
        mesh = trimesh.creation.box(extents=(2.0, 1.0, 1.0))
        pool = evaluate_support_flow_candidate_pool(mesh)
        rows = support_flow_directions_from_candidate_pool(
            pool,
            limit=3,
            min_angle_degrees=3.0,
            use_pareto=True,
            mesh=mesh,
        )

        self.assertGreater(len(rows), 0)
        self.assertLessEqual(len(rows), 3)
        self.assertTrue(all(row.pareto_objectives is not None for row in rows))
        self.assertTrue(all(row.pareto_front_size is not None for row in rows))
        self.assertGreaterEqual(sum(1 for row in rows if row.pareto_knee), 0)

    def test_pareto_requires_mesh_context(self) -> None:
        mesh = trimesh.creation.box(extents=(2.0, 1.0, 1.0))
        pool = evaluate_support_flow_candidate_pool(mesh)
        with self.assertRaises(ValueError):
            support_flow_directions_from_candidate_pool(pool, use_pareto=True)


if __name__ == "__main__":
    unittest.main()
