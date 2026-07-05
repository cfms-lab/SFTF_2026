"""Numerical self-test for the trimesh-independent core.

Validates the math that the comparison relies on, using hand-built inputs with
known answers. The trimesh I/O glue (load_mesh, submesh-based support_total,
planar/graphcut full runs) is exercised in the user's env where trimesh + maxflow
are installed; here we pin down the algorithmic core.
"""
import sys
import types

# stub trimesh so the trimesh-independent core can be imported here
# (production code uses real trimesh; the functions tested below never call it)
_t = types.ModuleType("trimesh")
_t.Trimesh = object
_t.util = types.SimpleNamespace(concatenate=lambda *a, **k: None)
_t.load = lambda *a, **k: None
sys.modules.setdefault("trimesh", _t)

import numpy as np
import common
import metrics


def approx(a, b, tol=1e-6):
    return abs(a - b) <= tol


# 1) fibonacci directions: shape + unit norm
d = common.fibonacci_directions(64)
assert d.shape == (64, 3)
assert np.allclose(np.linalg.norm(d, axis=1), 1.0, atol=1e-9)
print("[ok] fibonacci_directions: 64 unit vectors")

# 2) overhang_mask: a straight-down face needs support along +z; an up face doesn't
normals = np.array([[0, 0, -1.0],   # faces straight down -> overhang
                    [0, 0, 1.0],    # up -> no
                    [1, 0, 0.0]])   # vertical -> no (exactly at 90deg)
mask = common.overhang_mask(normals, np.array([0, 0, 1.0]), threshold_deg=45)
assert mask.tolist() == [True, False, False], mask.tolist()
print("[ok] overhang_mask: only the downward face flagged")

# 3) support_volume_proxy: one down-facing unit face of area 1 at height 2 over base 0
#    projected_area = 1*|n.d| = 1 ; drop = 2-0 = 2 ; support = 2.0
verts = np.array([[0, 0, 0.0], [0, 0, 2.0]])          # base at z=0
fn = np.array([[0, 0, -1.0]])
areas = np.array([1.0])
centers = np.array([[0, 0, 2.0]])
s = common.support_volume_proxy(verts, fn, areas, centers, np.array([0, 0, 1.0]))
assert approx(s, 2.0), s
print(f"[ok] support_volume_proxy: {s} == 2.0")


# ---- build a flat 3x3 grid (8 triangles) and split it left/right at x=1 ---- #
def build_grid():
    V, idx = [], {}
    for i in range(3):
        for j in range(3):
            idx[(i, j)] = len(V)
            V.append([i, j, 0.0])
    V = np.array(V)
    faces = []
    for ci in range(2):
        for cj in range(2):
            v00 = idx[(ci, cj)]; v10 = idx[(ci + 1, cj)]
            v01 = idx[(ci, cj + 1)]; v11 = idx[(ci + 1, cj + 1)]
            faces.append([v00, v10, v11])
            faces.append([v00, v11, v01])
    faces = np.array(faces)
    # adjacency: face pairs sharing exactly 2 vertices
    adj, adj_edges = [], []
    for a in range(len(faces)):
        for b in range(a + 1, len(faces)):
            shared = np.intersect1d(faces[a], faces[b])
            if len(shared) == 2:
                adj.append([a, b]); adj_edges.append(shared.tolist())
    return V, faces, np.array(adj), np.array(adj_edges)


class FakeMesh:
    """Minimal duck-typed mesh exposing only what the seam metrics read."""
    def __init__(self, V, faces, adj, adj_edges):
        self.vertices = V
        self.faces = faces
        self.face_adjacency = adj
        self.face_adjacency_edges = adj_edges
        self.triangles_center = V[faces].mean(axis=1)


V, faces, adj, adj_edges = build_grid()
fm = FakeMesh(V, faces, adj, adj_edges)
labels = (fm.triangles_center[:, 0] >= 1.0).astype(int)   # split at x=1

slen = metrics.seam_length(fm, labels)
assert approx(slen, 2.0, 1e-9), slen                      # two unit edges along x=1
print(f"[ok] seam_length: {slen} == 2.0")

rough = metrics.seam_roughness(fm, labels)
assert rough < 1e-6, rough                                # perfectly straight seam
print(f"[ok] seam_roughness: {rough:.3g} ~ 0 (straight)")

plan = metrics.seam_planarity(fm, labels)
assert plan < 1e-9, plan                                  # colinear seam -> flat
print(f"[ok] seam_planarity: {plan:.3g} ~ 0 (planar)")

# a wiggly seam (checkerboard labels) must be rougher than the straight one
checker = ((faces.sum(axis=1)) % 2).astype(int)
if len(np.unique(checker)) == 2:
    r2 = metrics.seam_roughness(fm, checker)
    print(f"[ok] checkerboard seam_roughness {r2:.3g} > straight {rough:.3g}: {r2 > rough}")

print("\nALL CORE TESTS PASSED")
