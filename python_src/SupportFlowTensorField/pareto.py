from __future__ import annotations

import numpy as np


OBJECTIVE_NAMES = ("support_R_plus_B", "height", "overhang_area")


def _safe_unit(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float64)
    norm = float(np.linalg.norm(vector))
    return np.zeros(3, dtype=np.float64) if norm <= 1e-12 else vector / norm


def compute_objectives(
    direction: np.ndarray,
    vertices: np.ndarray,
    normals: np.ndarray,
    areas: np.ndarray,
    rayleigh_score: float,
    bed_score: float,
    diagonal: float,
) -> np.ndarray:
    """Return the Pareto cost vector for one candidate direction.

    All objectives are minimized:
    support_R_plus_B = R + B, height = build height / bbox diagonal,
    overhang_area = sum(max(0, -m_i dot n) A_i).
    """
    n = _safe_unit(direction)
    if np.linalg.norm(n) <= 1e-12:
        return np.full(3, float("inf"), dtype=np.float64)

    vertices = np.asarray(vertices, dtype=np.float64)
    normals = np.asarray(normals, dtype=np.float64)
    areas = np.asarray(areas, dtype=np.float64)
    safe_diagonal = max(float(diagonal), 1e-12)

    support = float(rayleigh_score) + float(bed_score)
    if vertices.size:
        projection = vertices @ n
        height = float((np.max(projection) - np.min(projection)) / safe_diagonal)
    else:
        height = 0.0

    if normals.size and areas.size:
        overhang = np.maximum(0.0, -(normals @ n))
        overhang_area = float(np.sum(overhang * areas))
    else:
        overhang_area = 0.0

    return np.asarray([support, height, overhang_area], dtype=np.float64)


def pareto_mask(costs: np.ndarray) -> np.ndarray:
    """Return a boolean mask for non-dominated rows.

    Each column is a minimization objective.  Row a dominates row b when
    a <= b for every objective and a < b for at least one objective.
    """
    costs = np.asarray(costs, dtype=np.float64)
    if costs.ndim != 2:
        raise ValueError("costs must be a 2D array")
    if costs.shape[0] == 0:
        return np.zeros(0, dtype=bool)

    finite_costs = np.where(np.isfinite(costs), costs, float("inf"))
    efficient = np.ones(finite_costs.shape[0], dtype=bool)
    for row_id in range(finite_costs.shape[0]):
        if not efficient[row_id]:
            continue
        dominates_row = (
            np.all(finite_costs <= finite_costs[row_id], axis=1)
            & np.any(finite_costs < finite_costs[row_id], axis=1)
        )
        dominates_row[row_id] = False
        if np.any(dominates_row):
            efficient[row_id] = False
    return efficient


def normalize_costs(costs: np.ndarray) -> np.ndarray:
    """Min-max normalize objective columns within the supplied rows."""
    costs = np.asarray(costs, dtype=np.float64)
    if costs.ndim != 2:
        raise ValueError("costs must be a 2D array")
    if costs.shape[0] == 0:
        return costs.copy()

    finite_costs = np.where(np.isfinite(costs), costs, float("inf"))
    finite_mask = np.isfinite(finite_costs)
    lower = np.zeros(finite_costs.shape[1], dtype=np.float64)
    upper = np.ones(finite_costs.shape[1], dtype=np.float64)
    for col in range(finite_costs.shape[1]):
        values = finite_costs[finite_mask[:, col], col]
        if values.size:
            lower[col] = float(np.min(values))
            upper[col] = float(np.max(values))
    span = np.where((upper - lower) > 1e-12, upper - lower, 1.0)
    normalized = (finite_costs - lower) / span
    return np.where(np.isfinite(normalized), normalized, 1.0)


def knee_point(front_costs: np.ndarray) -> int:
    """Pick the front row closest to the normalized utopia point."""
    front_costs = np.asarray(front_costs, dtype=np.float64)
    if front_costs.ndim != 2:
        raise ValueError("front_costs must be a 2D array")
    if front_costs.shape[0] == 0:
        raise ValueError("front_costs must contain at least one row")
    if front_costs.shape[0] == 1:
        return 0
    normalized = normalize_costs(front_costs)
    distances = np.linalg.norm(normalized, axis=1)
    return int(np.argmin(distances))


def weighted_pick(front_costs: np.ndarray, weights: np.ndarray) -> int:
    """Pick the normalized weighted-sum row within a Pareto front."""
    front_costs = np.asarray(front_costs, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if front_costs.ndim != 2:
        raise ValueError("front_costs must be a 2D array")
    if front_costs.shape[0] == 0:
        raise ValueError("front_costs must contain at least one row")
    if weights.shape != (front_costs.shape[1],):
        raise ValueError("weights must have one entry per objective")
    normalized = normalize_costs(front_costs)
    return int(np.argmin(normalized @ weights))
