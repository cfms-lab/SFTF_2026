"""ctypes bridge to the C++ SFTF candidate generator (sftf_cpp.dll).

This mirrors the pure-Python lean path
``evaluate_support_flow_candidate_pool`` -> ``support_flow_directions_from_candidate_pool``
(python_src/SupportFlowTensorField/support_flow_tensor_field.py) but runs the
compute in compiled C++ for a fair speed comparison against the TOMO_CPU DLL.
Python loads the mesh and passes vertex/face arrays; the DLL returns the optimal
and worst build orientations and the pure-compute time (mesh load excluded).

Windows x64 only. Build the DLL with::

    cmake -S cpp_src -B cpp_src/build_sftf -A x64
    cmake --build cpp_src/build_sftf --config Release --target sftf_cpp

which copies ``sftf_cpp.dll`` next to this module.
"""
from __future__ import annotations

import ctypes as ct
import warnings
from pathlib import Path

import numpy as np
import trimesh

from .mesh_orientation import orient_faces_outward

PACKAGE_ROOT = Path(__file__).resolve().parent
DLL_PATH = PACKAGE_ROOT / "sftf_cpp.dll"

# Matches the SFTF module defaults (support_flow_tensor_field.py).
COARSE_DIRECTION_COUNT = 512
CRITICAL_ANGLE = 60.0
USE_CRITICAL_ANGLE = False
FINAL_MIN_ANGLE_DEG = 3.0
TOP_K = 3
# Output stride per direction: [x, y, z, tuned_score, rayleigh, pair, bed, hit].
_STRIDE = 8

_dll: ct.CDLL | None = None


def _load_dll() -> ct.CDLL:
    global _dll
    if _dll is not None:
        return _dll
    if not DLL_PATH.exists():
        raise FileNotFoundError(
            f"sftf_cpp.dll not found at {DLL_PATH}. Build it with "
            "`cmake --build cpp_src/build_sftf --config Release --target sftf_cpp`."
        )
    dll = ct.WinDLL(str(DLL_PATH))
    fn = dll.sftf_compute_directions
    fn.argtypes = [
        ct.POINTER(ct.c_double), ct.c_int,   # vertices, n_vertices
        ct.POINTER(ct.c_int), ct.c_int,      # faces, n_faces
        ct.c_int, ct.c_double, ct.c_int,     # coarse_count, critical_angle_deg, use_critical_angle
        ct.c_int, ct.c_double, ct.c_int,     # top_k, min_angle_deg, n_threads
        ct.POINTER(ct.c_double), ct.POINTER(ct.c_double),  # out_optimal, out_worst
        ct.POINTER(ct.c_int), ct.POINTER(ct.c_int),        # out_optimal_count, out_worst_count
        ct.POINTER(ct.c_double),             # out_compute_ms
    ]
    fn.restype = ct.c_int
    _dll = dll
    return dll


def _load_mesh_arrays(mesh: str | Path | trimesh.Trimesh) -> tuple[np.ndarray, np.ndarray]:
    """Return (vertices float64 [N,3], faces int32 [M,3]) for a path or Trimesh.

    Loading mirrors ``support_flow_tensor_field.load_mesh`` (force a single mesh,
    concatenate any scene)."""
    if isinstance(mesh, trimesh.Trimesh):
        tm = mesh
    else:
        tm = trimesh.load_mesh(str(mesh), force="mesh")
        if isinstance(tm, trimesh.Scene):
            tm = tm.dump(concatenate=True)
    if not isinstance(tm, trimesh.Trimesh):
        raise TypeError(f"expected Trimesh, got {type(tm).__name__}")
    vertices = np.ascontiguousarray(tm.vertices, dtype=np.float64)
    faces = np.ascontiguousarray(tm.faces, dtype=np.int32)
    # An inside-out mesh (negative signed volume) flips the DLL's winding-derived
    # normals, so overhang detection inverts; rewind to consistent outward faces.
    if faces.size and float(tm.volume) < 0.0:
        warnings.warn(
            f"{mesh}: negative signed volume ({float(tm.volume):.6g}); "
            "mesh is inside-out -- rewinding faces to consistent outward orientation.",
            stacklevel=2,
        )
        faces = np.ascontiguousarray(orient_faces_outward(vertices, faces))
    return vertices, faces


def _rows_to_records(buffer: np.ndarray, count: int) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for i in range(count):
        row = buffer[i]
        records.append(
            {
                "rank": i + 1,
                "direction": [float(row[0]), float(row[1]), float(row[2])],
                "tuned_score": float(row[3]),
                "rayleigh_score": float(row[4]),
                "pair_score": float(row[5]),
                "bed_score": float(row[6]),
                "hit_count": int(round(float(row[7]))),
            }
        )
    return records


def compute_sftf_directions_cpp(
    mesh: str | Path | trimesh.Trimesh,
    *,
    coarse_count: int = COARSE_DIRECTION_COUNT,
    critical_angle: float = CRITICAL_ANGLE,
    use_critical_angle: bool = USE_CRITICAL_ANGLE,
    top_k: int = TOP_K,
    min_angle_deg: float = FINAL_MIN_ANGLE_DEG,
    n_threads: int = 0,
) -> dict[str, object]:
    """Run the C++ SFTF candidate generator and return optimal/worst directions.

    Returns ``{"optimal": [...], "worst": [...], "compute_ms": float,
    "face_count": int}`` where each direction entry is a dict with the unit
    ``direction`` and the ``tuned_score``/``rayleigh``/``pair``/``bed``/``hit``
    breakdown. ``compute_ms`` is the DLL's pure-compute time (mesh load excluded).
    """
    dll = _load_dll()
    vertices, faces = _load_mesh_arrays(mesh)
    top_k = int(max(top_k, 1))

    out_optimal = np.zeros(top_k * _STRIDE, dtype=np.float64)
    out_worst = np.zeros(top_k * _STRIDE, dtype=np.float64)
    n_opt = ct.c_int(0)
    n_wst = ct.c_int(0)
    compute_ms = ct.c_double(0.0)

    status = dll.sftf_compute_directions(
        vertices.ctypes.data_as(ct.POINTER(ct.c_double)), ct.c_int(len(vertices)),
        faces.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(len(faces)),
        ct.c_int(int(coarse_count)), ct.c_double(float(critical_angle)),
        ct.c_int(1 if use_critical_angle else 0),
        ct.c_int(top_k), ct.c_double(float(min_angle_deg)), ct.c_int(int(n_threads)),
        out_optimal.ctypes.data_as(ct.POINTER(ct.c_double)),
        out_worst.ctypes.data_as(ct.POINTER(ct.c_double)),
        ct.byref(n_opt), ct.byref(n_wst), ct.byref(compute_ms),
    )
    if status != 0:
        raise RuntimeError(f"sftf_compute_directions returned error code {status}")

    optimal = _rows_to_records(out_optimal.reshape(top_k, _STRIDE), int(n_opt.value))
    worst = _rows_to_records(out_worst.reshape(top_k, _STRIDE), int(n_wst.value))
    return {
        "optimal": optimal,
        "worst": worst,
        "compute_ms": float(compute_ms.value),
        "face_count": int(len(faces)),
    }
