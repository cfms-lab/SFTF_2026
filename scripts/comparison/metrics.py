"""Common evaluation metrics for a partition (mesh + per-face labels).

Every baseline AND SFTF is scored with exactly these functions so the numbers are
comparable. Two families of metric matter for split-printing of large objects:

  * support   — how much support material the parts need (lower is better). Each
                part is allowed its own best build orientation (parts print
                separately), evaluated over a candidate direction set.
  * seam       — how "clean" the cut interfaces are (lower is better):
                  - seam_length     : total length of the cut boundary on the mesh
                  - seam_roughness  : mean turning angle (deg) along the seam — how
                                      wiggly the boundary is; flat planar cuts ~0
                  - seam_planarity  : RMS distance of seam vertices to their best-fit
                                      plane, normalised by seam extent — how close
                                      the seam is to a single flat plane
  * fit        — do all parts fit the printer build volume?
"""
from __future__ import annotations

import numpy as np
import trimesh

from common import DEFAULT_OVERHANG_DEG, FaceGeom, axis_directions, submesh_by_label


# --------------------------------------------------------------------------- #
# support
# --------------------------------------------------------------------------- #
def support_total(mesh: trimesh.Trimesh, labels: np.ndarray,
                  directions: np.ndarray | None = None,
                  threshold_deg: float = DEFAULT_OVERHANG_DEG) -> tuple[float, list[float]]:
    """Sum of each part's min-over-orientation support proxy. Returns (total, per_part)."""
    if directions is None:
        directions = axis_directions()
    per = []
    for lab in np.unique(labels):
        part = submesh_by_label(mesh, labels, lab)
        if len(part.faces) == 0:
            continue
        s, _ = FaceGeom.of(part).best_support(directions, threshold_deg)
        per.append(s)
    return float(np.sum(per)), per


# --------------------------------------------------------------------------- #
# seam geometry
# --------------------------------------------------------------------------- #
def _seam_edges(mesh: trimesh.Trimesh, labels: np.ndarray) -> np.ndarray:
    """Vertex-id pairs (E,2) of mesh edges that lie between two different parts."""
    pairs = np.asarray(mesh.face_adjacency)             # (A,2) face ids
    ev = np.asarray(mesh.face_adjacency_edges)          # (A,2) shared-edge vertex ids
    cut = labels[pairs[:, 0]] != labels[pairs[:, 1]]
    return ev[cut]


def seam_length(mesh: trimesh.Trimesh, labels: np.ndarray) -> float:
    ev = _seam_edges(mesh, labels)
    if len(ev) == 0:
        return 0.0
    v = np.asarray(mesh.vertices)
    return float(np.linalg.norm(v[ev[:, 0]] - v[ev[:, 1]], axis=1).sum())


def seam_roughness(mesh: trimesh.Trimesh, labels: np.ndarray) -> float:
    """Mean turning angle (degrees) between seam segments meeting at a vertex.

    0 == perfectly straight/flat boundary; larger == more jagged. Chains the seam
    segments through shared endpoints and averages the angle between consecutive
    segment directions.
    """
    ev = _seam_edges(mesh, labels)
    if len(ev) < 2:
        return 0.0
    v = np.asarray(mesh.vertices)
    # group segments by endpoint vertex
    from collections import defaultdict
    incident: dict[int, list[np.ndarray]] = defaultdict(list)
    for a, b in ev:
        da = v[b] - v[a]
        n = np.linalg.norm(da)
        if n < 1e-12:
            continue
        da = da / n
        incident[int(a)].append(-da)   # direction leaving vertex a backwards
        incident[int(b)].append(da)    # direction arriving at b
    angles = []
    for _, dirs in incident.items():
        if len(dirs) < 2:
            continue
        for i in range(len(dirs)):
            for j in range(i + 1, len(dirs)):
                c = float(np.clip(np.dot(dirs[i], dirs[j]), -1, 1))
                # turning angle = deviation from straight (180 deg between in/out dirs)
                angles.append(180.0 - np.degrees(np.arccos(c)))
    return float(np.mean(np.abs(angles))) if angles else 0.0


def seam_planarity(mesh: trimesh.Trimesh, labels: np.ndarray) -> float:
    """RMS distance of seam vertices to their best-fit plane / seam extent.

    ~0 for a single flat planar cut; grows for curved/branching seams. If there
    are multiple seam loops this measures global flatness (a conservative proxy).
    """
    ev = _seam_edges(mesh, labels)
    if len(ev) == 0:
        return 0.0
    v = np.asarray(mesh.vertices)
    pts = np.unique(v[np.unique(ev)], axis=0)
    if len(pts) < 3:
        return 0.0
    c = pts.mean(axis=0)
    u, s, vt = np.linalg.svd(pts - c, full_matrices=False)
    normal = vt[-1]
    dist = (pts - c) @ normal
    extent = float(np.linalg.norm(pts.max(axis=0) - pts.min(axis=0))) or 1.0
    return float(np.sqrt(np.mean(dist ** 2)) / extent)


# --------------------------------------------------------------------------- #
# fit in build volume
# --------------------------------------------------------------------------- #
def fits_in_volume(mesh: trimesh.Trimesh, labels: np.ndarray,
                   printer_dims: np.ndarray | None) -> tuple[int, int]:
    """Returns (n_parts_fitting, n_parts). Uses each part's oriented bbox."""
    if printer_dims is None:
        labs = np.unique(labels)
        return len(labs), len(labs)
    dims = np.sort(np.asarray(printer_dims, dtype=float))
    ok = 0
    labs = np.unique(labels)
    for lab in labs:
        part = submesh_by_label(mesh, labels, lab)
        if len(part.faces) == 0:
            ok += 1
            continue
        ext = np.sort(part.bounding_box_oriented.extents)
        if np.all(ext <= dims + 1e-9):
            ok += 1
    return ok, len(labs)


# --------------------------------------------------------------------------- #
# one-call evaluation
# --------------------------------------------------------------------------- #
def evaluate(mesh: trimesh.Trimesh, labels: np.ndarray, *,
             directions: np.ndarray | None = None,
             printer_dims: np.ndarray | None = None,
             threshold_deg: float = DEFAULT_OVERHANG_DEG) -> dict:
    """Full metric dict for one partition. Lower is better for every numeric field
    except n_parts / parts_fit (reported for context)."""
    labels = np.asarray(labels)
    sup_total, sup_per = support_total(mesh, labels, directions, threshold_deg)
    fit, n = fits_in_volume(mesh, labels, printer_dims)
    return {
        "n_parts": int(len(np.unique(labels))),
        "support_proxy": sup_total,
        "support_per_part_max": float(max(sup_per)) if sup_per else 0.0,
        "seam_length": seam_length(mesh, labels),
        "seam_roughness_deg": seam_roughness(mesh, labels),
        "seam_planarity": seam_planarity(mesh, labels),
        "parts_fit": fit,
        "parts_total": n,
    }
