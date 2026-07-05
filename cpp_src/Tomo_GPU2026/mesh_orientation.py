"""Pure-numpy repair of inside-out triangle meshes.

An inside-out mesh (negative total signed volume) silently flips every
winding-derived normal, so overhang detection in both the SFTF modules and the
TOMO DLL bridge inverts (a convex solid then reports face-to-face support over
its whole surface). ``orient_faces_outward`` repairs this without trimesh's
``networkx``-backed ``repair.fix_normals``:

  1. make the winding consistent inside every edge-connected face component
     (two faces sharing an edge must traverse it in opposite directions), then
  2. orient each component outward by the sign of its signed volume.

Non-manifold edges (shared by more than two faces) are left as constraints we
cannot decide and simply skipped; open (non-watertight) components use their
signed-volume sign as a best effort.
"""
from __future__ import annotations

import numpy as np


def signed_volume(vertices: np.ndarray, faces: np.ndarray) -> float:
    """Total signed volume of a triangle soup (divergence theorem; outward
    winding gives a positive value)."""
    if len(faces) == 0:
        return 0.0
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces, dtype=np.int64)
    v0, v1, v2 = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum() / 6.0)


def _face_adjacency_parity(faces: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Manifold-edge face pairs, the parity of each pair, and open-face flags.

    Parity 0: the two faces traverse the shared edge in opposite directions
    (consistent). Parity 1: same direction (one of the two must be flipped).
    ``open_faces[i]`` is True when face ``i`` has at least one non-manifold or
    boundary edge (an edge not shared by exactly two faces).
    """
    f = np.asarray(faces, dtype=np.int64)
    n_faces = len(f)
    # directed edges (3 per face) with owning face id
    edges = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]], axis=0)
    face_ids = np.tile(np.arange(n_faces, dtype=np.int64), 3)
    forward = edges[:, 0] < edges[:, 1]
    keys = np.where(forward[:, None], edges, edges[:, ::-1])
    order = np.lexsort((keys[:, 1], keys[:, 0]))
    keys_sorted = keys[order]
    same_as_prev = np.all(keys_sorted[1:] == keys_sorted[:-1], axis=1)
    # runs of identical undirected edges; manifold edges have run length 2
    run_starts = np.flatnonzero(np.concatenate(([True], ~same_as_prev)))
    run_lengths = np.diff(np.concatenate((run_starts, [len(keys_sorted)])))
    pair_starts = run_starts[run_lengths == 2]
    a_ids = order[pair_starts]
    b_ids = order[pair_starts + 1]
    pairs = np.column_stack((face_ids[a_ids], face_ids[b_ids]))
    # same 'forward' flag on both directed edges means same traversal direction
    parity = (forward[a_ids] == forward[b_ids]).astype(np.int8)
    keep = pairs[:, 0] != pairs[:, 1]

    open_faces = np.zeros(n_faces, dtype=bool)
    non_manifold_starts = run_starts[run_lengths != 2]
    if non_manifold_starts.size:
        bad_edge_ids = np.concatenate([
            order[s:s + l] for s, l in zip(non_manifold_starts, run_lengths[run_lengths != 2])
        ])
        open_faces[face_ids[bad_edge_ids]] = True
    # degenerate pairs (both directed edges from the same face) also leave the
    # face untrusted
    if np.any(~keep):
        open_faces[pairs[~keep, 0]] = True
    return pairs[keep], parity[keep], open_faces


def orient_faces_outward(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Return ``faces`` rewound so each edge-connected component is internally
    consistent and outward (positive signed volume). ``vertices`` is unchanged.
    """
    f = np.asarray(faces, dtype=np.int64)
    n_faces = len(f)
    if n_faces == 0:
        return np.asarray(faces).copy()

    pairs, parity, open_faces = _face_adjacency_parity(f)
    # CSR-style adjacency over undirected pairs
    src = np.concatenate((pairs[:, 0], pairs[:, 1]))
    dst = np.concatenate((pairs[:, 1], pairs[:, 0]))
    par = np.concatenate((parity, parity))
    order = np.argsort(src, kind="stable")
    src, dst, par = src[order], dst[order], par[order]
    starts = np.searchsorted(src, np.arange(n_faces + 1))

    flip = np.zeros(n_faces, dtype=np.int8)
    component = np.full(n_faces, -1, dtype=np.int64)
    n_components = 0
    for seed in range(n_faces):
        if component[seed] != -1:
            continue
        component[seed] = n_components
        stack = [seed]
        while stack:
            face = stack.pop()
            for k in range(starts[face], starts[face + 1]):
                neighbor = dst[k]
                want = flip[face] ^ par[k]
                if component[neighbor] == -1:
                    component[neighbor] = n_components
                    flip[neighbor] = want
                    stack.append(neighbor)
                # else: keep the first assignment (odd cycles are unrepairable
                # non-orientable spots; first-come parity is a best effort)
        n_components += 1

    consistent = np.where(flip[:, None].astype(bool), f[:, ::-1], f)

    v = np.asarray(vertices, dtype=np.float64)
    v0, v1, v2 = v[consistent[:, 0]], v[consistent[:, 1]], v[consistent[:, 2]]
    face_volumes = np.einsum("ij,ij->i", v0, np.cross(v1, v2)) / 6.0
    component_volumes = np.bincount(component, weights=face_volumes, minlength=n_components)

    # A component is CLOSED when none of its faces touch a boundary/non-manifold
    # edge; only then is its signed volume a trustworthy orientation test.
    component_open = np.zeros(n_components, dtype=bool)
    np.logical_or.at(component_open, component, open_faces)

    invert = np.zeros(n_faces, dtype=bool)
    closed_mask = ~component_open[component]
    invert[closed_mask] = component_volumes[component[closed_mask]] < 0.0

    # OPEN components (patches of a larger surface split by boundary or
    # non-manifold edges) keep their mutual orientation and are flipped as one
    # group by the sign of their combined volume: a fully inverted but
    # consistent file (e.g. E8/E9) then gets exactly one global flip.
    open_mask = ~closed_mask
    if np.any(open_mask) and float(face_volumes[open_mask].sum()) < 0.0:
        invert[open_mask] = True

    out = np.where(invert[:, None], consistent[:, ::-1], consistent)
    return out.astype(np.asarray(faces).dtype, copy=False)
