"""Reusable SFTF orientation routing and adaptive-verification policy.

The policy mirrors the fixed rules validated by the 2026-07-06 G5 audit:

* diagnose the calibrated (tuned-score) candidate pool with nearest-neighbour
  crowding and score coefficient of variation;
* route diffuse or unstable pools to a progressive uniform-axis safety net;
* otherwise retain a 25:75 tuned/uniform hybrid payload; and
* after a verifier has evaluated the local windows, choose the base, expanded,
  or severe AVE tier from the published detector signals.

This module deliberately contains no TOMO or slicer dependency.  Callers supply
the SFTF candidate pool and, for AVE, the verifier-derived scalar signals.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Sequence

import numpy as np


CandidateRow = Sequence[object]


@dataclass(frozen=True)
class RoutingPolicyConfig:
    """Fixed pre-verification routing parameters from the G5 audit."""

    top_k: int = 20
    nms_degrees: float = 3.0
    floor_factor: float = 1.5
    nn_fraction_min: float = 0.8
    score_cv_max: float = 2.0
    tuned_fraction: float = 0.25
    uniform_direction_count: int = 512


@dataclass(frozen=True)
class CandidatePoolSignals:
    """Diagnostics computed from the tuned-score candidate pool."""

    nn_fraction: float
    nn_mean_degrees: float
    score_cv: float
    top_k_used: int


@dataclass(frozen=True)
class OrientationPolicyResult:
    """Direction menu chosen by the pre-verification policy."""

    route: Literal["tuned_h25", "uniform"]
    directions: np.ndarray
    sources: tuple[str, ...]
    signals: CandidatePoolSignals
    config: RoutingPolicyConfig

    def metadata(self) -> dict[str, object]:
        return {
            "route": self.route,
            "sources": list(self.sources),
            "signals": asdict(self.signals),
            "config": asdict(self.config),
        }


@dataclass(frozen=True)
class AdaptiveVerificationConfig:
    """Fixed AVE detector and verification-budget tiers."""

    base_top_k: int = 10
    escalate_top_k: int = 50
    severe_top_k: int = 200
    high_support_fraction: float = 0.008
    low_gain: float = 1.5
    high_gain: float = 3.0


@dataclass(frozen=True)
class AdaptiveVerificationDecision:
    """AVE tier selected from verifier-derived diagnostics."""

    tier: Literal["base", "escalate", "severe"]
    top_k: int
    triggered: bool
    reasons: tuple[str, ...]


def _unit(direction: object) -> np.ndarray:
    vector = np.asarray(direction, dtype=np.float64)
    norm = float(np.linalg.norm(vector))
    if vector.shape != (3,) or not np.isfinite(norm) or norm <= 1e-12:
        raise ValueError("candidate directions must be finite non-zero 3-vectors")
    return vector / norm


def _candidate_score(row: CandidateRow) -> float:
    return float(row[0])


def _candidate_direction(row: CandidateRow) -> np.ndarray:
    return _unit(row[5])


def rank_tuned_candidate_pool(
    candidate_pool: Sequence[CandidateRow],
    *,
    limit: int,
    min_angle_degrees: float = 3.0,
) -> tuple[CandidateRow, ...]:
    """Rank by tuned score and apply axis-symmetric angular NMS."""

    limit = max(0, int(limit))
    if limit == 0:
        return ()
    min_dot = float(np.cos(np.deg2rad(float(min_angle_degrees))))
    ranked: list[CandidateRow] = []
    ranked_directions: list[np.ndarray] = []
    for row in sorted(candidate_pool, key=_candidate_score):
        direction = _candidate_direction(row)
        if any(abs(float(direction @ existing)) >= min_dot for existing in ranked_directions):
            continue
        ranked.append(row)
        ranked_directions.append(direction)
        if len(ranked) >= limit:
            break
    return tuple(ranked)


def candidate_pool_signals(
    candidate_pool: Sequence[CandidateRow],
    config: RoutingPolicyConfig | None = None,
) -> CandidatePoolSignals:
    """Compute the fixed crowding and score-spread routing signals."""

    config = RoutingPolicyConfig() if config is None else config
    top = rank_tuned_candidate_pool(
        candidate_pool,
        limit=config.top_k,
        min_angle_degrees=config.nms_degrees,
    )
    if len(top) < 2:
        return CandidatePoolSignals(
            nn_fraction=0.0,
            nn_mean_degrees=180.0,
            score_cv=float("inf"),
            top_k_used=len(top),
        )

    directions = np.asarray([_candidate_direction(row) for row in top], dtype=np.float64)
    dot = np.abs(directions @ directions.T)
    np.fill_diagonal(dot, -1.0)
    nn_angle = np.degrees(np.arccos(np.clip(dot.max(axis=1), -1.0, 1.0)))
    scores = np.asarray([_candidate_score(row) for row in top], dtype=np.float64)
    score_cv = float(np.std(scores) / max(abs(float(np.mean(scores))), 1e-12))
    return CandidatePoolSignals(
        nn_fraction=float(np.mean(nn_angle <= config.floor_factor * config.nms_degrees)),
        nn_mean_degrees=float(np.mean(nn_angle)),
        score_cv=score_cv,
        top_k_used=len(top),
    )


def fibonacci_directions(count: int = 512) -> np.ndarray:
    """Deterministic near-uniform unit directions on the sphere."""

    count = max(int(count), 1)
    indices = np.arange(count, dtype=np.float64)
    golden_angle = np.pi * (3.0 - np.sqrt(5.0))
    z = 1.0 - 2.0 * (indices + 0.5) / count
    radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    theta = indices * golden_angle
    return np.column_stack((radius * np.cos(theta), radius * np.sin(theta), z))


def progressive_uniform_axis_directions(count: int = 512) -> np.ndarray:
    """Return Fibonacci directions in farthest-first axis order."""

    directions = fibonacci_directions(count)
    order = [int(np.argmax(directions[:, 2]))]
    selected = np.zeros(len(directions), dtype=bool)
    selected[order[0]] = True
    nearest_similarity = np.abs(directions @ directions[order[0]])
    while len(order) < len(directions):
        scores = np.where(selected, np.inf, nearest_similarity)
        next_id = int(np.argmin(scores))
        order.append(next_id)
        selected[next_id] = True
        nearest_similarity = np.maximum(
            nearest_similarity,
            np.abs(directions @ directions[next_id]),
        )
    return directions[np.asarray(order, dtype=np.int64)]


def _append_separated(
    selected: list[np.ndarray],
    sources: list[str],
    candidates: Sequence[object],
    *,
    source: str,
    target_count: int,
    min_angle_degrees: float,
) -> None:
    min_dot = float(np.cos(np.deg2rad(float(min_angle_degrees))))
    for candidate in candidates:
        direction = _unit(candidate)
        if any(abs(float(direction @ existing)) >= min_dot for existing in selected):
            continue
        selected.append(direction)
        sources.append(source)
        if len(selected) >= target_count:
            return


def orientation_policy_from_pool(
    candidate_pool: Sequence[CandidateRow],
    *,
    limit: int = 5,
    config: RoutingPolicyConfig | None = None,
) -> OrientationPolicyResult:
    """Choose a routed tuned-h25 or uniform conditioning-direction menu.

    ``limit`` is a direction-menu size, not a TOMO cell budget.  The 25:75
    allocation is therefore rounded to whole directions, with at least one
    tuned direction retained when the pool passes the router.
    """

    config = RoutingPolicyConfig() if config is None else config
    limit = max(1, int(limit))
    signals = candidate_pool_signals(candidate_pool, config)
    tuned_route = (
        signals.nn_fraction >= config.nn_fraction_min
        and signals.score_cv <= config.score_cv_max
    )
    uniform = progressive_uniform_axis_directions(config.uniform_direction_count)
    selected: list[np.ndarray] = []
    sources: list[str] = []

    if tuned_route:
        tuned_rows = rank_tuned_candidate_pool(
            candidate_pool,
            limit=max(config.top_k, limit),
            min_angle_degrees=config.nms_degrees,
        )
        tuned_directions = [_candidate_direction(row) for row in tuned_rows]
        tuned_count = min(limit, max(1, int(round(limit * config.tuned_fraction))))
        _append_separated(
            selected,
            sources,
            tuned_directions,
            source="tuned",
            target_count=tuned_count,
            min_angle_degrees=config.nms_degrees,
        )
        _append_separated(
            selected,
            sources,
            uniform,
            source="uniform",
            target_count=limit,
            min_angle_degrees=config.nms_degrees,
        )
        route: Literal["tuned_h25", "uniform"] = "tuned_h25"
    else:
        _append_separated(
            selected,
            sources,
            uniform,
            source="uniform",
            target_count=limit,
            min_angle_degrees=config.nms_degrees,
        )
        route = "uniform"

    if len(selected) < limit:
        raise RuntimeError(f"policy produced only {len(selected)} of {limit} requested directions")
    return OrientationPolicyResult(
        route=route,
        directions=np.asarray(selected, dtype=np.float64),
        sources=tuple(sources),
        signals=signals,
        config=config,
    )


def adaptive_verification_decision(
    *,
    normalized_local_support: float,
    seed_to_local_gain: float,
    boundary_hit: bool,
    config: AdaptiveVerificationConfig | None = None,
) -> AdaptiveVerificationDecision:
    """Choose the fixed AVE verification tier from local-search diagnostics."""

    config = AdaptiveVerificationConfig() if config is None else config
    reasons: list[str] = []
    high_support = float(normalized_local_support) >= config.high_support_fraction
    stuck = float(seed_to_local_gain) <= config.low_gain
    big_jump = float(seed_to_local_gain) >= config.high_gain
    if high_support:
        reasons.append("high_normalized_support")
    if boundary_hit:
        reasons.append("boundary_local_minimum")
    if stuck:
        reasons.append("low_seed_to_local_gain")
    if big_jump:
        reasons.append("high_seed_to_local_gain")

    triggered = bool(high_support and (boundary_hit or stuck or big_jump))
    severe = bool(triggered and boundary_hit and stuck)
    if severe:
        reasons.append("boundary_plateau")
        return AdaptiveVerificationDecision("severe", config.severe_top_k, True, tuple(reasons))
    if triggered:
        return AdaptiveVerificationDecision("escalate", config.escalate_top_k, True, tuple(reasons))
    return AdaptiveVerificationDecision("base", config.base_top_k, False, tuple(reasons))
