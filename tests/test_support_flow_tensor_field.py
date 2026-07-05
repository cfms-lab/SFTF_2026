"""Tests for the active Support Flow Tensor Field pipeline.

These replace the retired ShTensor / tse6_config tests (those modules now live
under ``obsolete/``). They exercise the current SFTF module only.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import trimesh

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField.support_flow_tensor_field import (
    SUPPORT_FLOW_COARSE_DIRECTION_COUNT,
    _rank_normalized_feature,
    _rotation_align_vector_to_z,
    _spherical_sample_directions,
    _unique_directions,
    evaluate_support_flow_candidate_pool,
    support_flow_directions_from_candidate_pool,
)
from cpp_src.Tomo_GPU2026.tomo_sftf import DLL_PATH, compute_sftf_directions_cpp


class SphericalSamplingTests(unittest.TestCase):
    def test_directions_are_unit_norm_and_correct_count(self) -> None:
        directions = _spherical_sample_directions(SUPPORT_FLOW_COARSE_DIRECTION_COUNT)
        self.assertEqual(directions.shape, (SUPPORT_FLOW_COARSE_DIRECTION_COUNT, 3))
        norms = np.linalg.norm(directions, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-9)

    def test_unique_directions_collapses_antipodal_duplicates(self) -> None:
        z = np.array([0.0, 0.0, 1.0])
        unique = _unique_directions([z, -z, np.array([1.0, 0.0, 0.0])])
        self.assertEqual(len(unique), 2)


class RankNormalizationTests(unittest.TestCase):
    def test_rank_is_in_unit_interval_and_monotone(self) -> None:
        values = np.array([5.0, 1.0, 3.0, 9.0])
        ranks = _rank_normalized_feature(values)
        self.assertAlmostEqual(float(ranks.min()), 0.0)
        self.assertAlmostEqual(float(ranks.max()), 1.0)
        # smallest value -> rank 0, largest value -> rank 1
        self.assertAlmostEqual(float(ranks[np.argmin(values)]), 0.0)
        self.assertAlmostEqual(float(ranks[np.argmax(values)]), 1.0)

    def test_single_value_returns_zero(self) -> None:
        np.testing.assert_array_equal(_rank_normalized_feature(np.array([7.0])), np.array([0.0]))


class RotationAlignmentTests(unittest.TestCase):
    def test_direction_is_rotated_onto_z(self) -> None:
        direction = np.array([0.3, -0.7, 0.5])
        direction = direction / np.linalg.norm(direction)
        rotation = _rotation_align_vector_to_z(direction)
        rotated = rotation @ direction
        np.testing.assert_allclose(rotated, [0.0, 0.0, 1.0], atol=1e-9)

    def test_rotation_is_orthonormal(self) -> None:
        rotation = _rotation_align_vector_to_z(np.array([1.0, 2.0, 3.0]))
        np.testing.assert_allclose(rotation @ rotation.T, np.eye(3), atol=1e-9)
        self.assertAlmostEqual(float(np.linalg.det(rotation)), 1.0, places=9)


class CandidatePoolTests(unittest.TestCase):
    def test_pool_scores_finite_and_directions_unit(self) -> None:
        mesh = trimesh.creation.box(extents=(2.0, 1.0, 1.0))
        pool = evaluate_support_flow_candidate_pool(mesh)
        self.assertGreater(len(pool), 0)
        for result in pool:
            score = result[0]
            direction = np.asarray(result[5], dtype=np.float64)
            self.assertTrue(np.isfinite(score))
            self.assertAlmostEqual(float(np.linalg.norm(direction)), 1.0, places=6)

    def test_top_directions_are_angularly_separated(self) -> None:
        mesh = trimesh.creation.box(extents=(2.0, 1.0, 1.0))
        pool = evaluate_support_flow_candidate_pool(mesh)
        directions = support_flow_directions_from_candidate_pool(pool, limit=3, min_angle_degrees=3.0)
        self.assertLessEqual(len(directions), 3)
        min_dot = float(np.cos(np.deg2rad(3.0)))
        for i in range(len(directions)):
            for j in range(i + 1, len(directions)):
                dot = abs(float(np.dot(directions[i].direction, directions[j].direction)))
                self.assertLess(dot, min_dot)


@unittest.skipUnless(sys.platform == "win32" and DLL_PATH.exists(), "sftf_cpp.dll is available on Windows only")
class SftfCppParityTests(unittest.TestCase):
    def assert_cpp_matches_python(
        self,
        mesh: trimesh.Trimesh,
        *,
        top_k: int = 3,
        direction_atol: float = 1e-12,
        score_atol: float = 1e-10,
        component_atol: float = 1e-9,
    ) -> None:
        py_pool = evaluate_support_flow_candidate_pool(mesh)
        py_rows = support_flow_directions_from_candidate_pool(
            py_pool,
            limit=top_k,
            min_angle_degrees=3.0,
        )
        cpp_rows = compute_sftf_directions_cpp(
            mesh,
            top_k=top_k,
            min_angle_deg=3.0,
            n_threads=1,
        )["optimal"]

        self.assertEqual(len(py_rows), top_k)
        self.assertEqual(len(cpp_rows), top_k)

        for py_row, cpp_row in zip(py_rows, cpp_rows):
            py_dir = np.asarray(py_row.direction, dtype=np.float64)
            cpp_dir = np.asarray(cpp_row["direction"], dtype=np.float64)
            self.assertLessEqual(1.0 - abs(float(py_dir @ cpp_dir)), direction_atol)
            self.assertAlmostEqual(float(py_row.value), float(cpp_row["tuned_score"]), delta=score_atol)
            self.assertAlmostEqual(
                float(py_row.rayleigh_score),
                float(cpp_row["rayleigh_score"]),
                delta=component_atol,
            )
            self.assertAlmostEqual(
                float(py_row.pair_score),
                float(cpp_row["pair_score"]),
                delta=component_atol,
            )
            self.assertAlmostEqual(
                float(py_row.bed_score),
                float(cpp_row["bed_score"]),
                delta=component_atol,
            )
            self.assertEqual(int(py_row.hit_count), int(cpp_row["hit_count"]))

    def test_cpp_matches_python_for_bed_only_box(self) -> None:
        mesh = trimesh.creation.box(extents=(2.0, 1.0, 1.0))
        self.assert_cpp_matches_python(mesh)

    def test_cpp_matches_python_for_torus_with_ray_hits(self) -> None:
        if not hasattr(trimesh.creation, "torus"):
            self.skipTest("trimesh.creation.torus is unavailable")
        mesh = trimesh.creation.torus(
            major_radius=1.0,
            minor_radius=0.25,
            major_sections=32,
            minor_sections=12,
        )
        self.assert_cpp_matches_python(mesh)


if __name__ == "__main__":
    unittest.main()
