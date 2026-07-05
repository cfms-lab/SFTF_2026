"""Baseline 3 — normalized-cut / spectral clustering on the dual graph, label form.

Builds a sparse face-affinity matrix where adjacent faces are "close" across
convex/flat edges and "far" across concave creases (Katz-Tal / Shapira style
angular distance), so the spectral embedding tears the surface along concave
seams — giving smooth, natural part boundaries. Optionally blends in spatial
proximity of face centroids so clusters are also spatially compact (useful when
the goal is roughly equal printable chunks).

    affinity_ij = exp( -( eta * (1 - cos theta_ij) + beta * dist_ij/scale ) )
        eta = 1.0  on concave edges, eta = 0.1 on convex/flat edges

Then sklearn SpectralClustering(n_clusters=n_parts, affinity='precomputed').
This baseline does not optimise support directly — it represents the
"geometrically smoothest natural partition" end of the spectrum.

Note: cost grows with face count; decimate very large meshes (common.load_mesh
`decimate_to=...`). API mirrors the other baselines.

API:  partition(mesh, n_parts, printer_dims=None, eta_concave=1.0,
                 eta_convex=0.1, beta_spatial=0.0, random_state=0) -> labels
"""
from __future__ import annotations

import numpy as np
import trimesh
from scipy.sparse import csr_matrix
from sklearn.cluster import SpectralClustering

from common import DualGraph


def _affinity(mesh: trimesh.Trimesh, dual: DualGraph,
              eta_concave: float, eta_convex: float, beta_spatial: float) -> csr_matrix:
    n = len(mesh.faces)
    centers = np.asarray(mesh.triangles_center)
    scale = float(np.linalg.norm(mesh.extents)) + 1e-12

    fa, fb = dual.pairs[:, 0], dual.pairs[:, 1]
    sharp = np.clip(1 - np.cos(dual.angle), 0, 2)         # 0 flat .. 2 sharp
    eta = np.where(dual.convex, eta_convex, eta_concave)
    ang_dist = eta * sharp
    spatial = beta_spatial * np.linalg.norm(centers[fa] - centers[fb], axis=1) / scale
    w = np.exp(-(ang_dist + spatial))
    w = np.maximum(w, 1e-6)

    rows = np.concatenate([fa, fb])
    cols = np.concatenate([fb, fa])
    data = np.concatenate([w, w])
    A = csr_matrix((data, (rows, cols)), shape=(n, n))
    return A


def partition(mesh: trimesh.Trimesh, n_parts: int,
              printer_dims=None, eta_concave: float = 1.0, eta_convex: float = 0.1,
              beta_spatial: float = 0.0, random_state: int = 0) -> np.ndarray:
    dual = DualGraph.of(mesh)
    A = _affinity(mesh, dual, eta_concave, eta_convex, beta_spatial)
    sc = SpectralClustering(
        n_clusters=max(int(n_parts), 1),
        affinity="precomputed",
        assign_labels="discretize",
        random_state=random_state,
    )
    labels = sc.fit_predict(A)
    return np.asarray(labels, dtype=int)
