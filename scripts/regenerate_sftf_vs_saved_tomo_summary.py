"""Regenerate support_flow_tensor_field_vs_saved_tomo_int3_summary.{csv,json}.

This reuses the *saved* TOMO ``*_tomo_int3_vss_grid_1deg_60deg.npz`` grids
(it does NOT recompute TOMO and needs no GPU DLL) and only re-evaluates the
Support Flow Tensor Field candidates for the current code configuration. Run it
after changing any SFTF parameter (e.g. SUPPORT_FLOW_USE_FALLBACK_RAY_HITS) to
refresh the paper Table numbers.

Mesh files live in the shared corpus ``../sftf_Mesh_Data/g5test`` as
``Group_C{N}_{stem}.ply`` (the grids are named ``({N}){stem}_...``); the
resolver below maps grid -> mesh and also falls back to the legacy locations.

The SFTF build direction ``n`` is mapped onto the saved yaw/pitch grid by the
same convention TOMO uses: the grid point whose rotation R(yaw, pitch, 0) best
aligns ``n`` with +z. ``n`` and ``-n`` are both evaluated; the smaller v_ss is
the signed result.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    SUPPORT_FLOW_USE_FALLBACK_RAY_HITS,
    evaluate_support_flow_candidate_pool,
    load_mesh,
    support_flow_directions_from_candidate_pool,
)
from scripts._mesh_paths import G5_RAW_MESH, MESH_DATA  # noqa: E402

MESH_DIR = PROJECT_ROOT / "Experimental" / "etc"
GRID_SUFFIX = "_tomo_int3_vss_grid_1deg_60deg.npz"

# Saved grids are named "({N}){stem}_tomo_int3_..."; the meshes were moved to the
# shared corpus ../sftf_Mesh_Data/g5test as "Group_C{N}_{stem}.ply".
SHARED_MESH_ROOT = MESH_DATA
G5_MESH_DIR = G5_RAW_MESH
_MESH_EXTS = (".ply", ".obj", ".stl")


def _resolve_mesh_path(stem: str) -> Path:
    """Locate the mesh for a grid stem like ``(1)Bunny_69k``.

    Tries the canonical g5test name ``Group_C{N}_{rest}`` first, then the shared
    corpus and the legacy Experimental/etc location, across .ply/.obj/.stl.
    """
    candidates: list[Path] = []
    m = re.match(r"^\((\d+)\)(.+)$", stem)
    if m:
        g5_name = f"Group_C{m.group(1)}_{m.group(2)}"
        candidates += [G5_MESH_DIR / f"{g5_name}{ext}" for ext in _MESH_EXTS]
    candidates += [SHARED_MESH_ROOT / f"{stem}{ext}" for ext in _MESH_EXTS]
    candidates += [MESH_DIR / f"{stem}{ext}" for ext in _MESH_EXTS]  # legacy
    for cand in candidates:
        if cand.exists():
            return cand
    raise FileNotFoundError(
        f"mesh for grid stem {stem!r} not found (looked in {G5_MESH_DIR}, "
        f"{SHARED_MESH_ROOT}, {MESH_DIR})"
    )


def _alignment_grid(direction: np.ndarray, yaw_deg: np.ndarray, pitch_deg: np.ndarray) -> np.ndarray:
    """z-component of R(yaw, pitch, 0) @ direction over the full yaw/pitch grid.

    Mirrors tomo_shell_io.getRotationMatrix row 2 with roll = 0, so the result is
    identical to the original validation without importing the GPU module.
    """
    dx, dy, dz = (float(direction[0]), float(direction[1]), float(direction[2]))
    yaw = np.deg2rad(np.asarray(yaw_deg, dtype=np.float64))
    pitch = np.deg2rad(np.asarray(pitch_deg, dtype=np.float64))
    cos_p = np.cos(pitch)[:, None]
    sin_p = np.sin(pitch)[:, None]
    cos_y = np.cos(yaw)[None, :]
    sin_y = np.sin(yaw)[None, :]
    return -sin_p * dx + cos_p * sin_y * dy + cos_p * cos_y * dz


def _nearest_grid_orientation(
    direction: np.ndarray,
    yaw_deg: np.ndarray,
    pitch_deg: np.ndarray,
    vss_grid: np.ndarray,
) -> dict[str, float]:
    unit = np.asarray(direction, dtype=np.float64)
    unit = unit / max(float(np.linalg.norm(unit)), 1e-12)
    alignment = _alignment_grid(unit, yaw_deg, pitch_deg)
    pitch_id, yaw_id = np.unravel_index(int(np.argmax(alignment)), alignment.shape)
    return {
        "yaw": float(yaw_deg[yaw_id]),
        "pitch": float(pitch_deg[pitch_id]),
        "alignment": float(alignment[pitch_id, yaw_id]),
        "vss": float(vss_grid[pitch_id, yaw_id]),
    }


def _signed_orientation(
    direction: np.ndarray,
    yaw_deg: np.ndarray,
    pitch_deg: np.ndarray,
    vss_grid: np.ndarray,
) -> tuple[dict[str, float], dict[str, float]]:
    positive = _nearest_grid_orientation(direction, yaw_deg, pitch_deg, vss_grid)
    negative = _nearest_grid_orientation(-np.asarray(direction, dtype=np.float64), yaw_deg, pitch_deg, vss_grid)
    signed = positive if positive["vss"] <= negative["vss"] else negative
    return positive, signed


def _tomo_best(yaw_deg: np.ndarray, pitch_deg: np.ndarray, vss_grid: np.ndarray) -> dict[str, float]:
    flat_id = int(np.nanargmin(vss_grid.reshape(-1)))
    pitch_id, yaw_id = np.unravel_index(flat_id, vss_grid.shape)
    return {
        "yaw": float(yaw_deg[yaw_id]),
        "pitch": float(pitch_deg[pitch_id]),
        "vss": float(vss_grid[pitch_id, yaw_id]),
    }


def _ratio(value: float, reference: float) -> float:
    return value / reference if abs(reference) > 1e-12 else float("inf")


def regenerate_row(grid_path: Path) -> dict[str, object]:
    stem = grid_path.name[: -len(GRID_SUFFIX)]
    mesh_path = _resolve_mesh_path(stem)

    data = np.load(grid_path, allow_pickle=True)
    yaw_deg = np.asarray(data["yaw_values"], dtype=np.float64)
    pitch_deg = np.asarray(data["pitch_values"], dtype=np.float64)
    vss_grid = np.asarray(data["vss_grid"], dtype=np.float64)
    tomo_best = _tomo_best(yaw_deg, pitch_deg, vss_grid)

    start = time.perf_counter()
    mesh = load_mesh(str(mesh_path))
    pool = evaluate_support_flow_candidate_pool(mesh)
    directions = support_flow_directions_from_candidate_pool(pool)
    elapsed = time.perf_counter() - start

    mapped = []
    for rank, item in enumerate(directions, start=1):
        positive, signed = _signed_orientation(item.direction, yaw_deg, pitch_deg, vss_grid)
        mapped.append({"rank": rank, "item": item, "positive": positive, "signed": signed})

    score1 = mapped[0]
    best3 = min(mapped, key=lambda entry: entry["positive"]["vss"])
    best3_signed = min(mapped, key=lambda entry: entry["signed"]["vss"])

    sftf_rows = [
        {
            "rank": entry["rank"],
            "tuned_score": float(entry["item"].value),
            "hit_count": int(entry["item"].hit_count),
            "direction": np.asarray(entry["item"].direction, dtype=np.float64).tolist(),
            "yaw": entry["positive"]["yaw"],
            "pitch": entry["positive"]["pitch"],
            "alignment": entry["positive"]["alignment"],
            "vss": entry["positive"]["vss"],
            "signed_yaw": entry["signed"]["yaw"],
            "signed_pitch": entry["signed"]["pitch"],
            "signed_alignment": entry["signed"]["alignment"],
            "signed_vss": entry["signed"]["vss"],
        }
        for entry in mapped
    ]

    return {
        "mesh": f"{stem}.ply",
        "npz": str(grid_path.relative_to(PROJECT_ROOT)),
        "face_count": int(len(mesh.faces)),
        "tomo_best_yaw": tomo_best["yaw"],
        "tomo_best_pitch": tomo_best["pitch"],
        "tomo_best_vss": tomo_best["vss"],
        "sftf_score1_yaw": score1["positive"]["yaw"],
        "sftf_score1_pitch": score1["positive"]["pitch"],
        "sftf_score1_vss": score1["positive"]["vss"],
        "sftf_score1_ratio": _ratio(score1["positive"]["vss"], tomo_best["vss"]),
        "sftf_score1_signed_yaw": score1["signed"]["yaw"],
        "sftf_score1_signed_pitch": score1["signed"]["pitch"],
        "sftf_score1_signed_vss": score1["signed"]["vss"],
        "sftf_score1_signed_ratio": _ratio(score1["signed"]["vss"], tomo_best["vss"]),
        "sftf_best3_rank": best3["rank"],
        "sftf_best3_yaw": best3["positive"]["yaw"],
        "sftf_best3_pitch": best3["positive"]["pitch"],
        "sftf_best3_vss": best3["positive"]["vss"],
        "sftf_best3_ratio": _ratio(best3["positive"]["vss"], tomo_best["vss"]),
        "sftf_best3_signed_rank": best3_signed["rank"],
        "sftf_best3_signed_yaw": best3_signed["signed"]["yaw"],
        "sftf_best3_signed_pitch": best3_signed["signed"]["pitch"],
        "sftf_best3_signed_vss": best3_signed["signed"]["vss"],
        "sftf_best3_signed_ratio": _ratio(best3_signed["signed"]["vss"], tomo_best["vss"]),
        "elapsed_sec": elapsed,
        "sftf_rows": sftf_rows,
    }


def main() -> None:
    grid_paths = sorted(MESH_DIR.glob(f"*{GRID_SUFFIX}"))
    if not grid_paths:
        raise FileNotFoundError(f"no saved TOMO grids found in {MESH_DIR}")

    print(f"SUPPORT_FLOW_USE_FALLBACK_RAY_HITS = {SUPPORT_FLOW_USE_FALLBACK_RAY_HITS}", flush=True)
    rows = []
    for grid_id, grid_path in enumerate(grid_paths, start=1):
        print(f"[{grid_id}/{len(grid_paths)}] {grid_path.name}", flush=True)
        row = regenerate_row(grid_path)
        rows.append(row)
        print(
            f"  faces={row['face_count']} tomo_best={row['tomo_best_vss']:.6g} "
            f"score1_signed_ratio={row['sftf_score1_signed_ratio']:.4g} "
            f"best3_signed_ratio={row['sftf_best3_signed_ratio']:.4g} "
            f"({row['elapsed_sec']:.2f}s)",
            flush=True,
        )

    csv_path = MESH_DIR / "support_flow_tensor_field_vs_saved_tomo_int3_summary.csv"
    json_path = MESH_DIR / "support_flow_tensor_field_vs_saved_tomo_int3_summary.json"
    csv_fieldnames = [key for key in rows[0].keys() if key != "sftf_rows"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsaved: {csv_path.name}, {json_path.name}", flush=True)


if __name__ == "__main__":
    main()
