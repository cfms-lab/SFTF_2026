"""Shared utilities for the SFTF partitioning comparison.

All baselines reduce to the SAME representation: a per-face integer label array
over the *original* mesh (length == len(mesh.faces)). Parts are recovered by
sub-meshing on those labels. This keeps every method comparable with one metric
set (metrics.py) and avoids fragile boolean geometry — the real fabrication would
perform the actual cut, but for *evaluating* support and seam quality, labelling
the original faces is faithful and robust.

Conventions
-----------
- build/up direction `d` is a unit vector; the part is printed "growing along d".
- A face needs support when it points steeply downward relative to d:
      n · d < -cos(overhang_threshold)          (default threshold 45 deg)
  i.e. the angle between the face normal and -d is below the threshold.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh


# --------------------------------------------------------------------------- #
# mesh loading
# --------------------------------------------------------------------------- #
def load_mesh(path: str, *, decimate_to: int | None = None) -> trimesh.Trimesh:
    """Load a mesh as a single watertight-ish Trimesh.

    `decimate_to` (target face count) is useful for the spectral baseline, whose
    cost grows with face count; pass e.g. 20000 for very large prints.
    """
    m = trimesh.load(path, force="mesh", process=True)
    if not isinstance(m, trimesh.Trimesh):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    m.remove_unreferenced_vertices()
    m.merge_vertices()
    if decimate_to and len(m.faces) > decimate_to:
        m = m.simplify_quadric_decimation(decimate_to)
    return m


# --------------------------------------------------------------------------- #
# build directions
# --------------------------------------------------------------------------- #
def fibonacci_directions(n: int = 64) -> np.ndarray:
    """`n` ~uniformly distributed unit vectors on the sphere (candidate build dirs)."""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5 ** 0.5) * i
    d = np.column_stack([np.cos(theta) * np.sin(phi),
                         np.sin(theta) * np.sin(phi),
                         np.cos(phi)])
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def axis_directions() -> np.ndarray:
    """The 6 axis-aligned build directions (a fast default candidate set)."""
    return np.array([[1, 0, 0], [-1, 0, 0],
                     [0, 1, 0], [0, -1, 0],
                     [0, 0, 1], [0, 0, -1]], dtype=float)


# --------------------------------------------------------------------------- #
# overhang / support geometry
# --------------------------------------------------------------------------- #
DEFAULT_OVERHANG_DEG = 45.0


def overhang_mask(face_normals: np.ndarray, d: np.ndarray,
                  threshold_deg: float = DEFAULT_OVERHANG_DEG) -> np.ndarray:
    """Boolean mask of faces that need support when printed along `d`."""
    d = d / np.linalg.norm(d)
    cos_t = np.cos(np.radians(threshold_deg))
    nd = face_normals @ d
    return nd < -cos_t            # steeply downward-facing


def support_volume_proxy(verts: np.ndarray, face_normals: np.ndarray,
                         areas: np.ndarray, centers: np.ndarray, d: np.ndarray,
                         threshold_deg: float = DEFAULT_OVERHANG_DEG) -> float:
    """A consistent, units-of-volume support estimate for one orientation `d`.

    For each overhang face we drop a vertical column to the part's lowest point:
        contribution = projected_area * drop_height
    with projected_area = area * |n . d| (area projected onto the build plate) and
    drop_height = (centroid . d) - min(vertex . d). Summed over overhang faces.
    Not a slicer-exact value, but monotone in "how much support" and identical for
    every method, which is what a fair comparison needs.
    """
    d = d / np.linalg.norm(d)
    mask = overhang_mask(face_normals, d, threshold_deg)
    if not mask.any():
        return 0.0
    base = float((verts @ d).min())
    drop = (centers[mask] @ d) - base
    drop = np.clip(drop, 0.0, None)
    proj_area = areas[mask] * np.abs(face_normals[mask] @ d)
    return float(np.sum(proj_area * drop))


@dataclass
class FaceGeom:
    """Cached per-face geometry for a sub-mesh (a part), to score orientations fast."""
    verts: np.ndarray
    normals: np.ndarray
    areas: np.ndarray
    centers: np.ndarray

    @classmethod
    def of(cls, mesh: trimesh.Trimesh) -> "FaceGeom":
        return cls(np.asarray(mesh.vertices), np.asarray(mesh.face_normals),
                   np.asarray(mesh.area_faces), np.asarray(mesh.triangles_center))

    def best_support(self, directions: np.ndarray,
                     threshold_deg: float = DEFAULT_OVERHANG_DEG) -> tuple[float, np.ndarray]:
        """Min support over candidate `directions` (each part is oriented freely)."""
        best, best_d = np.inf, directions[0]
        for d in directions:
            s = support_volume_proxy(self.verts, self.normals, self.areas,
                                     self.centers, d, threshold_deg)
            if s < best:
                best, best_d = s, d
        return best, best_d


# --------------------------------------------------------------------------- #
# dual graph (face adjacency) — shared by graph-cut and spectral baselines
# --------------------------------------------------------------------------- #
@dataclass
class DualGraph:
    pairs: np.ndarray          # (E,2) adjacent face indices
    edge_len: np.ndarray       # (E,) shared-edge length
    angle: np.ndarray          # (E,) dihedral angle (rad), 0 == flat
    convex: np.ndarray         # (E,) bool, True == convex/flat, False == concave

    @classmethod
    def of(cls, mesh: trimesh.Trimesh) -> "DualGraph":
        pairs = np.asarray(mesh.face_adjacency)
        ev = np.asarray(mesh.face_adjacency_edges)           # shared-edge vertex ids
        v = np.asarray(mesh.vertices)
        elen = np.linalg.norm(v[ev[:, 0]] - v[ev[:, 1]], axis=1)
        angle = np.asarray(mesh.face_adjacency_angles)
        convex = np.asarray(mesh.face_adjacency_convex)
        return cls(pairs, elen, angle, convex)


def submesh_by_label(mesh: trimesh.Trimesh, labels: np.ndarray, lab: int) -> trimesh.Trimesh:
    """The part (sub-mesh) made of all faces carrying `lab`."""
    idx = np.where(labels == lab)[0]
    return mesh.submesh([idx], append=True, repair=False)
