"""Baseline 2 — graph-cut (MRF) partitioning via PyMaxflow, label form.

Recursive binary min-cut. For each part we build a graph over its faces:

  * pairwise (smoothness) term on each dual edge — the price of cutting there.
    Cheap at concave creases (where part boundaries naturally belong), expensive
    across convex/flat regions, scaled by shared-edge length. This makes the cut
    snap to concave seams => smoother, more natural boundaries.
        penalty_ij = edge_len * [ k_convex*(1+sharp)  if convex/flat
                                  k_concave*(1-sharp)  if concave ]
  * data (terminal) term — a soft spatial bias along the part's longest PCA axis
    (source = low end, sink = high end) plus an optional support bias that nudges
    heavy-overhang faces to separate. The spatial bias gives the binary cut a
    direction to roughly bisect; the smoothness term decides exactly where.

Recurse on the larger child until the target part count is reached / parts fit.
Requires PyMaxflow:  uv add pymaxflow      (import name: ``maxflow``)

API:  partition(mesh, n_parts, printer_dims=None, directions=None,
                 lambda_smooth=..., k_concave=..., k_convex=...) -> labels
"""
from __future__ import annotations

import numpy as np
import trimesh

from common import DualGraph, axis_directions

try:
    import maxflow  # PyMaxflow
    HAVE_MAXFLOW = True
except Exception:  # pragma: no cover
    HAVE_MAXFLOW = False


def _binary_cut(mesh, idx, dual, lambda_smooth, k_concave, k_convex):
    """Min-cut one face group `idx` into two; returns boolean mask over idx."""
    local = {int(f): i for i, f in enumerate(idx)}
    centers = np.asarray(mesh.triangles_center)[idx]

    # data term: soft spatial bias along the longest PCA axis
    c = centers - centers.mean(axis=0)
    if len(c) >= 3:
        _, _, vt = np.linalg.svd(c, full_matrices=False)
        axis = vt[0]
    else:
        axis = np.array([1.0, 0, 0])
    t = c @ axis
    t = (t - t.min()) / (np.ptp(t) + 1e-12)        # in [0,1]
    src_cap = t                                    # prefers SOURCE when t small
    snk_cap = 1.0 - t

    g = maxflow.Graph[float]()
    nodes = g.add_nodes(len(idx))
    for i in range(len(idx)):
        g.add_tedge(nodes[i], float(src_cap[i]), float(snk_cap[i]))

    # pairwise term only on edges internal to this group
    mask_internal = np.isin(dual.pairs[:, 0], idx) & np.isin(dual.pairs[:, 1], idx)
    for (fa, fb), elen, ang, convex in zip(
        dual.pairs[mask_internal], dual.edge_len[mask_internal],
        dual.angle[mask_internal], dual.convex[mask_internal]
    ):
        sharp = float(np.clip(1 - np.cos(ang), 0, 2))
        if convex:
            pen = k_convex * (1.0 + sharp)
        else:
            pen = k_concave * max(1.0 - sharp, 0.05)   # sharp concave => cheap cut
        w = lambda_smooth * float(elen) * pen
        g.add_edge(nodes[local[int(fa)]], nodes[local[int(fb)]], w, w)

    g.maxflow()
    seg = np.array([g.get_segment(nodes[i]) for i in range(len(idx))], dtype=bool)
    return seg            # True == SINK side


def partition(mesh: trimesh.Trimesh, n_parts: int,
              printer_dims=None, directions: np.ndarray | None = None,
              lambda_smooth: float = 1.0, k_concave: float = 0.2,
              k_convex: float = 1.0) -> np.ndarray:
    if not HAVE_MAXFLOW:
        raise ImportError(
            "PyMaxflow not installed. Run `uv add pymaxflow` (import name 'maxflow')."
        )
    if directions is None:
        directions = axis_directions()
    dual = DualGraph.of(mesh)
    labels = np.zeros(len(mesh.faces), dtype=int)
    next_label = 1

    def longest(idx):
        p = np.asarray(mesh.triangles_center)[idx]
        return float((p.max(0) - p.min(0)).max()) if len(p) else 0.0

    def needs_split(idx):
        if printer_dims is None:
            return False
        part = mesh.submesh([idx], append=True, repair=False)
        ext = np.sort(part.bounding_box_oriented.extents)
        return bool(np.any(ext > np.sort(np.asarray(printer_dims, float)) + 1e-9))

    guard = 0
    while True:
        labs = np.unique(labels)
        groups = {l: np.where(labels == l)[0] for l in labs}
        must = [l for l, idx in groups.items() if needs_split(idx)]
        if len(labs) >= n_parts and not must:
            break
        target = (max(must, key=lambda l: longest(groups[l])) if must
                  else max(groups, key=lambda l: longest(groups[l])))
        idx = groups[target]
        if len(idx) < 2:
            break
        seg = _binary_cut(mesh, idx, dual, lambda_smooth, k_concave, k_convex)
        if seg.all() or (~seg).all():
            # degenerate cut (everything one side) — force a spatial median split
            centers = np.asarray(mesh.triangles_center)[idx]
            axis = centers.std(0).argmax()
            seg = centers[:, axis] >= np.median(centers[:, axis])
            if seg.all() or (~seg).all():
                break
        labels[idx[seg]] = next_label
        next_label += 1
        guard += 1
        if guard > 4 * max(n_parts, 1) + 8:
            break
    return labels
