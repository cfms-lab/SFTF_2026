"""Tests for the inside-out mesh repair used by all three mesh-loading paths.

Five of the g5test validation meshes (A2 sphere, B4 pipe_elbow, D10 37416,
E8 64445, E9 64446) ship with inverted winding/normals, which silently flips
overhang detection. These tests cover the repair on synthetic equivalents of
each failure mode.
"""
from __future__ import annotations

import sys
import unittest
import warnings
from pathlib import Path

import numpy as np
import trimesh

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cpp_src.Tomo_GPU2026.mesh_orientation import (
    orient_faces_outward,
    signed_volume,
)
from python_src.SupportFlowTensorField.support_flow_tensor_field import load_mesh


def _icosphere(inverted: bool = False) -> trimesh.Trimesh:
    mesh = trimesh.creation.icosphere(subdivisions=2, radius=10.0)
    if inverted:
        mesh = trimesh.Trimesh(
            vertices=mesh.vertices.copy(), faces=mesh.faces[:, ::-1], process=False
        )
    return mesh


class OrientFacesOutwardTests(unittest.TestCase):
    def test_correct_mesh_is_unchanged(self) -> None:
        mesh = _icosphere()
        fixed = orient_faces_outward(mesh.vertices, mesh.faces)
        np.testing.assert_array_equal(fixed, mesh.faces)

    def test_fully_inverted_consistent_mesh_is_flipped(self) -> None:
        mesh = _icosphere(inverted=True)
        self.assertLess(signed_volume(mesh.vertices, mesh.faces), 0.0)
        fixed = orient_faces_outward(mesh.vertices, mesh.faces)
        self.assertGreater(signed_volume(mesh.vertices, fixed), 0.0)
        repaired = trimesh.Trimesh(vertices=mesh.vertices.copy(), faces=fixed, process=False)
        self.assertTrue(repaired.is_winding_consistent)

    def test_mixed_winding_is_made_consistent_and_outward(self) -> None:
        # B4 pipe_elbow failure mode: mostly inverted with a minority of
        # correctly wound faces on the same closed surface.
        mesh = _icosphere(inverted=True)
        faces = mesh.faces.copy()
        faces[::10] = faces[::10, ::-1]  # re-flip every 10th face
        fixed = orient_faces_outward(mesh.vertices, faces)
        repaired = trimesh.Trimesh(vertices=mesh.vertices.copy(), faces=fixed, process=False)
        self.assertTrue(repaired.is_winding_consistent)
        self.assertAlmostEqual(float(repaired.volume), float(_icosphere().volume), places=6)

    def test_multibody_components_are_oriented_individually(self) -> None:
        # D10 failure mode: many closed sub-bodies, each inverted.
        a = _icosphere(inverted=True)
        b = _icosphere(inverted=True)
        vertices = np.vstack([a.vertices, b.vertices + [30.0, 0.0, 0.0]])
        faces = np.vstack([a.faces, b.faces + len(a.vertices)])
        fixed = orient_faces_outward(vertices, faces)
        expected = 2.0 * float(_icosphere().volume)
        self.assertAlmostEqual(signed_volume(vertices, fixed), expected, places=6)

    def test_open_patches_get_a_single_group_flip(self) -> None:
        # E8/E9 failure mode: a consistent but inverted surface broken into
        # open patches (no manifold adjacency across the cut); mutual
        # orientation must be preserved by one group flip, not per-patch signs.
        mesh = _icosphere(inverted=True)
        z = mesh.triangles_center[:, 2]
        top = mesh.faces[z >= 0.0]
        bottom = mesh.faces[z < 0.0]
        # duplicate vertices for the bottom patch so the two halves share no edges
        offset = len(mesh.vertices)
        vertices = np.vstack([mesh.vertices, mesh.vertices])
        faces = np.vstack([top, bottom + offset])
        self.assertLess(signed_volume(vertices, faces), 0.0)
        fixed = orient_faces_outward(vertices, faces)
        self.assertAlmostEqual(
            signed_volume(vertices, fixed), abs(signed_volume(vertices, faces)), places=6
        )


class LoadMeshGuardTests(unittest.TestCase):
    def test_load_mesh_repairs_inverted_file(self) -> None:
        mesh = _icosphere(inverted=True)
        path = Path(self.enterContext(_tempdir())) / "inverted_sphere.stl"
        mesh.export(path)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            loaded = load_mesh(str(path))
        self.assertGreater(float(loaded.volume), 0.0)
        # normals must be recomputed from the repaired winding, not taken from
        # the file's stored (inverted) facet normals
        outward = np.einsum(
            "ij,ij->i", loaded.face_normals, loaded.triangles_center - loaded.centroid
        )
        self.assertTrue(bool(np.all(outward > 0.0)))

    def test_load_mesh_leaves_hollow_solid_alone(self) -> None:
        # a hollow box (inner shell deliberately wound inward) has positive
        # total volume and must NOT be "repaired"
        outer = trimesh.creation.box(extents=(4.0, 4.0, 4.0))
        inner = trimesh.creation.box(extents=(2.0, 2.0, 2.0))
        inner = trimesh.Trimesh(
            vertices=inner.vertices.copy(), faces=inner.faces[:, ::-1], process=False
        )
        hollow = trimesh.util.concatenate([outer, inner])
        path = Path(self.enterContext(_tempdir())) / "hollow_box.stl"
        hollow.export(path)
        loaded = load_mesh(str(path))
        self.assertAlmostEqual(float(loaded.volume), 64.0 - 8.0, places=6)


def _tempdir():
    import tempfile

    return tempfile.TemporaryDirectory()


if __name__ == "__main__":
    unittest.main()
