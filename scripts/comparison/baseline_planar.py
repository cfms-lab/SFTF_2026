"""Baseline 1 — planar BSP partitioning (Chopper-style), label form.

Recursively splits the worst part with a single plane until the target part count
is reached (and/or every part fits the build volume). For each split we try a few
candidate plane normals (the part's 3 PCA axes + 3 world axes), offset at the
median of the centroid projections, and keep the plane minimising

    objective = support(part_A) + support(part_B) + w_seam * seam_length

Cuts are represented by *labelling* original faces with the half-space their
centroid falls in — no boolean geometry, so it never fails on dirty meshes. The
flat plane makes the seam maximally smooth (planarity ~ 0), which is exactly the
behaviour this baseline is meant to showcase.

API:  partition(mesh, n_parts, printer_dims=None, directions=None, w_seam=...) -> labels
"""
from __future__ import annotations

import numpy as np
import trimesh

from common import FaceGeom, axis_directions
import metrics as M


def _principal_normals(centers: np.ndarray) -> np.ndarray:
    c = centers - centers.mean(axis=0)
    if len(c) < 3:
        return np.eye(3)
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    return np.vstack([vt, np.eye(3)])           # PCA axes first, then world axes


def _longest_extent(mesh: trimesh.Trimesh, idx: np.ndarray) -> float:
    p = np.asarray(mesh.triangles_center)[idx]
    return float((p.max(axis=0) - p.min(axis=0)).max()) if len(p) else 0.0


def _split_cost(mesh, idx, side, directions, w_seam):
    """support(A)+support(B) + w_seam * (#boundary faces proxy) for one candidate."""
    ia, ib = idx[side], idx[~side]
    if len(ia) == 0 or len(ib) == 0:
        return np.inf
    sup = 0.0
    for sub in (ia, ib):
        part = mesh.submesh([sub], append=True, repair=False)
        s, _ = FaceGeom.of(part).best_support(directions)
        sup += s
    # cheap seam proxy: boundary faces are paid for by a smaller of the two sides
    seam_proxy = min(len(ia), len(ib))
    return sup + w_seam * seam_proxy


def partition(mesh: trimesh.Trimesh, n_parts: int,
              printer_dims=None, directions: np.ndarray | None = None,
              w_seam: float = 0.0) -> np.ndarray:
    if directions is None:
        directions = axis_directions()
    centers = np.asarray(mesh.triangles_center)
    labels = np.zeros(len(mesh.faces), dtype=int)
    next_label = 1

    def needs_split(idx) -> bool:
        if printer_dims is None:
            return False
        part = mesh.submesh([idx], append=True, repair=False)
        ext = np.sort(part.bounding_box_oriented.extents)
        return bool(np.any(ext > np.sort(np.asarray(printer_dims, float)) + 1e-9))

    while True:
        labs = np.unique(labels)
        # candidate parts to split: those too big, else the geometrically largest
        groups = {l: np.where(labels == l)[0] for l in labs}
        must = [l for l, idx in groups.items() if needs_split(idx)]
        if len(labs) >= n_parts and not must:
            break
        if must:
            target = max(must, key=lambda l: _longest_extent(mesh, groups[l]))
        else:
            if len(labs) >= n_parts:
                break
            target = max(groups, key=lambda l: _longest_extent(mesh, groups[l]))
        idx = groups[target]
        if len(idx) < 2:
            break

        c = centers[idx]
        best = (np.inf, None)
        for normal in _principal_normals(c):
            proj = c @ normal
            offset = np.median(proj)
            side = proj >= offset                # boolean over idx
            cost = _split_cost(mesh, idx, side, directions, w_seam)
            if cost < best[0]:
                best = (cost, side)
        if best[1] is None:
            break
        side = best[1]
        labels[idx[side]] = next_label
        next_label += 1
        if len(np.unique(labels)) >= n_parts and printer_dims is None:
            break
        if next_label > 4 * max(n_parts, 1) + 8:    # safety stop
            break
    return labels
