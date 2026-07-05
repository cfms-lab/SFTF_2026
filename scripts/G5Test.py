"""G5Test.py

Batch Support Flow Tensor Field (SFTF) verification over the five-group SCI
validation meshes ``Experimental/G5Test/RawMesh/Group_*_*.*`` (groups
A/B/C/D/E).

This is the batch counterpart of ``TSE6_SFTF.py``: instead of opening Polyscope
for one mesh at a time, it runs the SFTF candidate evaluation for every Group
mesh and writes, per mesh:

  * a Plotly HTML of the candidate orientation cost landscape
    (all sampled build directions, coloured by tuned score, top-3 marked),
  * a per-mesh JSON with the top-3 directions and a summary,
  * a per-mesh CSV of the full candidate pool.

It also writes a combined ``five_group_verification_summary.{csv,json}`` across
all meshes, plus ``_5G_CA<critical>deg_4Method_table.html`` -- a single standalone
page tabulating every mesh's result at a glance (with links to each per-mesh
landscape HTML). Input meshes and all outputs live in
``Experimental/G5Test/``.

The SFTF directions are computed from the input mesh alone (the same candidate
pool ``TSE6_SFTF.py`` reports), so no convex-hull boolean or GPU is required and
arbitrary Thingi10K meshes are handled robustly.

Usage:
    python scripts/five_group_verification.py             # groups enabled in RUN_GROUPS
    python scripts/five_group_verification.py A B          # only groups A and B (overrides flags)
    python scripts/five_group_verification.py E            # only the slow group E

To exclude slow groups without passing CLI args, flip their RUN_GROUPS flag to
False near the top of this file (e.g. set "C" and "D" to False to skip the large
Thingi10K meshes).

Group-by-group friendly:
  * Each backend's sweep is cached: TOMO_CPU under
    ``G5Test/tomo_cpu_cache/`` and TOMO_CUDA under
    ``G5Test/tomo_cuda_cache/``; a present cache is reused, so
    re-running a group skips the slow sweep (handy for the large group D).
  * Stage flags ``RUN_SFTF`` / ``RUN_TOMO_CPU`` / ``RUN_TOMO_CUDA`` /
    ``RUN_SFTF_CPP`` near the top enable the computations independently; a
    disabled stage keeps its previously stored per-mesh result, so selective runs
    accumulate into one table (e.g. run SFTF + TOMO_CPU now, add TOMO_CUDA
    later). ``RUN_SFTF_CPP`` runs the C++ SFTF DLL (sftf_cpp.dll) and records the
    optimal/worst orientations plus its pure-compute time, for a fair speed
    comparison against the TOMO_CPU/CUDA DLLs.
  * ``_5G_CA<critical>deg_4Method_table.html`` always lists the full A/B/C/D/E roster (every
    Group mesh file on disk), with grouped columns for Python SFTF, TOMO_CPU,
    TOMO_CUDA, and SFTF_C++. Cells for meshes/stages not yet computed are left
    blank, and each run fills in the blanks for the stages it processed.
"""
from __future__ import annotations

import csv
import html
import json
import sys
import time
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from python_src.SupportFlowTensorField.support_flow_tensor_field import (  # noqa: E402
    SUPPORT_FLOW_COARSE_DIRECTION_COUNT,
    evaluate_support_flow_candidate_pool,
    load_mesh,
    support_flow_directions_from_candidate_pool,
)
from cpp_src.Tomo_GPU2026.tomo_cpu import (  # noqa: E402
    ANGLE_STEP,
    CRITICAL_ANGLE,
    compute_tomo_cuda_vss_grid,
    compute_tomo_cpu_vss_grid,
    tomo_best_row,
)
from cpp_src.Tomo_GPU2026.tomo_sftf import compute_sftf_directions_cpp  # noqa: E402
from scripts.plot_sftf_tomo_cpu_contours import (  # noqa: E402
    largest_basin_rows,
    smallest_basin_rows,
)
from scripts._mesh_paths import G5_RAW_MESH

# --------------------------------------------------------------------------
# Group selection: flip a group to ``False`` to exclude it from the batch and
# speed the run up (groups C and D are the large Thingi10K meshes). A group's
# meshes are processed only when its flag is True. Command-line group arguments
# (e.g. ``python five_group_verification.py A B``) override these flags.
# --------------------------------------------------------------------------
RUN_GROUPS: dict[str, bool] = {
    "A": False,   # primitives (cube, sphere, cylinder, cone, torus)
    "B": False,   # simple parts (u_bracket, hook, c_clamp, pipe_elbow, hollow_box)
    "C": True,    # organic benchmark meshes (Bunny, manikin, dragon, happy, lucy)
    "D": False,   # Thingi10K set 1
    "E": False,   # Thingi10K set 2
}

# --------------------------------------------------------------------------
# Stage selection: each computation stage runs only when its flag is True, so
# SFTF, TOMO_CPU (CPU) and TOMO_CUDA (GPU) can be enabled independently (e.g.
# SFTF + TOMO_CPU today, TOMO_CUDA later). A disabled stage keeps whatever
# result is already stored in the per-mesh JSON, so selective runs accumulate
# into one table. The TOMO_CPU / TOMO_CUDA grid sweeps are each cached as an
# .npz (see the *_cache dirs below); when a cache is present the slow DLL sweep
# is skipped and only the contour HTML is rebuilt.
#
# TOMO_CUDA defaults to False, so its table columns stay blank until enabled.
# --------------------------------------------------------------------------
RUN_SFTF: bool = False        # SFTF candidate pool + landscape HTML (Python)
RUN_TOMO_CPU: bool = True    # TOMO_CPU (CPU) DLL sweep + contour HTML
RUN_TOMO_CUDA: bool = True  # TOMO_CUDA (GPU) DLL sweep + contour HTML
RUN_SFTF_CPP: bool = False    # SFTF candidate generator via sftf_cpp.dll (C++); records optimal/worst + compute_ms
RUN_ONLY_MISSING: bool = True  # Skip an enabled stage when its time, best row, and artifact are already stored.


# --------------------------------------------------------------------------
# Environment-variable overrides (non-destructive: absent vars keep the defaults
# above). A batch driver that sweeps several critical angles sets these per
# subprocess instead of editing this file. Flags: FGV_SFTF / FGV_CPU /
# FGV_CUDA / FGV_SFTFCPP / FGV_ONLY_MISSING accept 1/0/true/false; FGV_GROUPS is
# a comma list like "A,B,C,D,E" (overrides the RUN_GROUPS dict, still overridden
# in turn by any CLI group arguments).
# --------------------------------------------------------------------------
def _env_bool(name: str, default: bool) -> bool:
    raw = __import__("os").environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


RUN_SFTF = _env_bool("FGV_SFTF", RUN_SFTF)
RUN_TOMO_CPU = _env_bool("FGV_CPU", RUN_TOMO_CPU)
RUN_TOMO_CUDA = _env_bool("FGV_CUDA", RUN_TOMO_CUDA)
RUN_SFTF_CPP = _env_bool("FGV_SFTFCPP", RUN_SFTF_CPP)
RUN_ONLY_MISSING = _env_bool("FGV_ONLY_MISSING", RUN_ONLY_MISSING)

_env_groups = __import__("os").environ.get("FGV_GROUPS")
if _env_groups:
    _wanted = {g.strip().upper() for g in _env_groups.split(",") if g.strip()}
    RUN_GROUPS = {g: (g in _wanted) for g in RUN_GROUPS}

OUT_DIR = PROJECT_ROOT / "Experimental" / "G5Test"
MESH_DIR = G5_RAW_MESH
SFTF_RESULT_DIR = OUT_DIR / "SFTF_result"
# Cached TOMO_CPU / TOMO_CUDA grid sweeps live here; when a cache is present
# the slow DLL sweep is skipped. The cache key embeds the sweep parameters so
# changing the angle-step or critical-angle does not silently reuse a stale grid.
TOMO_CPU_CACHE_DIR = OUT_DIR / "tomo_cpu_cache"
TOMO_CUDA_CACHE_DIR = OUT_DIR / "tomo_cuda_cache"
MESH_GLOB = "Group_*_*.*"
# Non-mesh siblings that can match the glob are skipped.
MESH_EXTENSIONS = {".stl", ".obj", ".ply", ".off", ".3mf", ".glb"}


def angle_file_tag(angle_deg: float) -> str:
    """Filesystem-friendly critical-angle tag, e.g. 45 -> CA45deg."""
    text = f"{float(angle_deg):g}".replace("-", "m").replace(".", "p")
    return f"CA{text}deg"


def four_method_table_path() -> Path:
    return OUT_DIR / f"_5G_{angle_file_tag(CRITICAL_ANGLE)}_4Method_table.html"


def output_link(path: Path) -> str:
    return path.relative_to(OUT_DIR).as_posix()


def parse_group_id(stem: str) -> tuple[str, str]:
    """'Group_C10_37416' -> ('C', 'C10')."""
    parts = stem.split("_")
    gid = parts[1] if len(parts) > 1 else ""
    group = gid[:1] if gid else ""
    return group, gid


def mesh_sort_key(mesh_path: Path) -> tuple[str, int, str]:
    """Natural order: group letter, then numeric group-id index (C2 before C10)."""
    group, gid = parse_group_id(mesh_path.stem)
    num = gid[1:]
    return (group.upper(), int(num) if num.isdigit() else 0, mesh_path.stem)


def blank_record(mesh_path: Path) -> dict[str, object]:
    """A not-yet-computed roster entry: identity filled in, all results blank."""
    group, gid = parse_group_id(mesh_path.stem)
    return {
        "group": group, "group_id": gid, "mesh": mesh_path.name,
        "angle_step_deg": float(ANGLE_STEP), "critical_angle_deg": float(CRITICAL_ANGLE),
        "face_count": None, "coarse_direction_count": None, "candidate_pool_size": None,
        "score_min": None, "score_median": None, "score_max": None,
        "top_directions": [], "html": None, "candidates_csv": None,
        "elapsed_sec": None,
        "tomo_cpu_dll_sec": None, "tomo_cpu_cached": None,
        "tomo_cpu_html": None, "tomo_cpu_best": None, "tomo_cpu_error": None,
        "tomo_cuda_dll_sec": None, "tomo_cuda_cached": None,
        "tomo_cuda_html": None, "tomo_cuda_best": None, "tomo_cuda_error": None,
        "sftf_cpp_ms": None, "sftf_cpp_optimal": None,
        "sftf_cpp_worst": None, "sftf_cpp_error": None,
    }


def load_per_mesh_record(stem: str) -> dict[str, object] | None:
    """Load a previously written per-mesh result JSON, or None if absent/unreadable."""
    path = SFTF_RESULT_DIR / f"{stem}.json"
    if not path.exists():
        path = OUT_DIR / f"{stem}.json"
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    for key in ("html", "candidates_csv"):
        value = record.get(key)
        if isinstance(value, str) and value and "/" not in value and "\\" not in value:
            candidate = SFTF_RESULT_DIR / value
            if candidate.exists():
                record[key] = output_link(candidate)
    return record


def dedupe_roster_records(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Drop group-D meshes whose trailing number also appears in group E.

    The mesh folder contains a stray ``Group_D10_65942.stl`` that is byte-identical
    to ``Group_E10_65942.stl`` (a mislabeled duplicate; the canonical D10 is 37416).
    Without this the roster has 36 entries while the manuscript and Figure 6 use the
    canonical 35. Same rule as ``scripts/render_figure6_grouped.dedupe_records``.
    """
    def number(name: object) -> str:
        return Path(str(name)).stem.split("_")[-1]

    e_numbers = {number(r["mesh"]) for r in rows if str(r.get("group", "")).upper() == "E"}
    cleaned: list[dict[str, object]] = []
    for r in rows:
        if str(r.get("group", "")).upper() == "D" and number(r["mesh"]) in e_numbers:
            print(f"  roster: dropping mislabeled duplicate {r['mesh']} (already in group E)")
            continue
        cleaned.append(r)
    return cleaned


def collect_roster_records() -> list[dict[str, object]]:
    """Full A/B/C/D/E roster (every mesh file on disk) in natural group order, each
    paired with its per-mesh result JSON when present, or a blank stub otherwise.
    This is what lets group-by-group runs accumulate into one table.
    Mislabeled cross-group duplicates are dropped so the roster is the canonical 35."""
    roster = sorted(
        (p for p in MESH_DIR.glob(MESH_GLOB)
         if p.is_file() and p.suffix.lower() in MESH_EXTENSIONS),
        key=mesh_sort_key,
    )
    rows: list[dict[str, object]] = []
    for p in roster:
        rec = load_per_mesh_record(p.stem)
        rows.append(rec if rec is not None else blank_record(p))
    return dedupe_roster_records(rows)


def direction_to_spherical(direction: np.ndarray) -> tuple[float, float]:
    """Unit direction -> (azimuth deg in [-180,180], polar deg from +z in [0,180])."""
    x, y, z = (float(direction[0]), float(direction[1]), float(direction[2]))
    azimuth = float(np.degrees(np.arctan2(y, x)))
    polar = float(np.degrees(np.arccos(np.clip(z, -1.0, 1.0))))
    return azimuth, polar


def build_landscape_figure(
    label: str,
    pool: list[tuple],
    top_directions: list,
) -> go.Figure:
    scores = np.asarray([row[0] for row in pool], dtype=np.float64)
    az = np.empty(len(pool), dtype=np.float64)
    pol = np.empty(len(pool), dtype=np.float64)
    rayleigh = np.asarray([row[1] for row in pool], dtype=np.float64)
    pair = np.asarray([row[2] for row in pool], dtype=np.float64)
    bed = np.asarray([row[3] for row in pool], dtype=np.float64)
    hit = np.asarray([row[4] for row in pool], dtype=np.float64)
    for i, row in enumerate(pool):
        az[i], pol[i] = direction_to_spherical(row[5])

    customdata = np.column_stack([rayleigh, pair, bed, hit])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=az,
            y=pol,
            mode="markers",
            name="candidates",
            marker=dict(
                size=7,
                color=scores,
                colorscale="RdBu_r",
                colorbar=dict(title="tuned score<br>(lower=better)"),
                showscale=True,
                line=dict(width=0),
            ),
            customdata=customdata,
            hovertemplate=(
                "az=%{x:.1f}, polar=%{y:.1f}<br>"
                "score=%{marker.color:.4g}<br>"
                "R=%{customdata[0]:.4g}, P=%{customdata[1]:.4g}, "
                "B=%{customdata[2]:.4g}, hit=%{customdata[3]:.0f}<extra></extra>"
            ),
        )
    )

    if top_directions:
        t_az, t_pol, t_text = [], [], []
        for item in top_directions:
            a, p = direction_to_spherical(item.direction)
            t_az.append(a)
            t_pol.append(p)
            t_text.append(str(item.rank))
        fig.add_trace(
            go.Scatter(
                x=t_az,
                y=t_pol,
                mode="markers+text",
                name="top-3",
                text=t_text,
                textposition="top center",
                marker=dict(symbol="star", size=16, color="#1664d8", line=dict(color="#ffffff", width=1)),
                hovertemplate="top-%{text}<br>az=%{x:.1f}, polar=%{y:.1f}<extra></extra>",
            )
        )

    fig.update_layout(
        title=f"{label}: SFTF candidate orientation cost landscape",
        xaxis_title="azimuth (deg)",
        yaxis_title="polar angle from +z (deg)",
        width=940,
        height=720,
    )
    fig.update_xaxes(range=[-180, 180], dtick=45)
    fig.update_yaxes(range=[180, 0], dtick=30)  # 0 (top, +z build dir) at top
    return fig


def build_tomo_contour_figure(
    label: str,
    yaw_values: np.ndarray,
    pitch_values: np.ndarray,
    vss_grid: np.ndarray,
    method: str = "TOMO_CPU",
) -> go.Figure:
    """TOMO (CPU/CUDA) v_ss contour over the yaw/pitch grid, with the optimal
    and worst support-volume basins marked. ``method`` only labels the title."""
    optimal = smallest_basin_rows(vss_grid, yaw_values, pitch_values, count=3)
    worst = largest_basin_rows(vss_grid, yaw_values, pitch_values, count=3)

    fig = go.Figure()
    fig.add_trace(
        go.Contour(
            x=yaw_values,
            y=pitch_values,
            z=vss_grid,
            colorscale="RdBu_r",
            contours=dict(showlabels=True),
            colorbar=dict(title="v_ss<br>(lower=better)"),
            hovertemplate=(
                "yaw=%{x:.1f}<br>pitch=%{y:.1f}<br>v_ss=%{z:.6g}<extra></extra>"
            ),
        )
    )
    for rows, name, symbol, color, prefix, pos in (
        (optimal, "optimal", "star", "#1664d8", "o", "top center"),
        (worst, "worst", "x", "#d93f21", "w", "bottom center"),
    ):
        if not rows:
            continue
        fig.add_trace(
            go.Scatter(
                x=[r["yaw"] for r in rows],
                y=[r["pitch"] for r in rows],
                mode="markers+text",
                name=name,
                text=[f"{prefix}{r['rank']}" for r in rows],
                textposition=pos,
                marker=dict(symbol=symbol, size=13, color=color, line=dict(color="#ffffff", width=1)),
                customdata=[[r["vss"]] for r in rows],
                hovertemplate=(
                    f"{name} %{{text}}<br>yaw=%{{x:.1f}}<br>pitch=%{{y:.1f}}"
                    "<br>v_ss=%{customdata[0]:.6g}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=f"{label}: {method} v_ss contour ({ANGLE_STEP:g}deg / {CRITICAL_ANGLE:.0f}deg)",
        xaxis_title="yaw (deg)",
        yaxis_title="pitch (deg)",
        width=940,
        height=720,
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def _load_or_run_tomo(
    mesh_path: Path,
    stem: str,
    *,
    compute_fn,
    cache_dir: Path,
    method_tag: str,
) -> tuple[dict[str, object], float | None, bool]:
    """Return ``(tomo_grid, dll_sec, cached)`` for any TOMO backend.

    If a cached grid exists for this mesh and these sweep parameters it is loaded
    and the DLL sweep is skipped (``cached=True``); otherwise ``compute_fn`` runs
    the sweep and its grid is written to the cache. ``dll_sec`` is the original
    compute wall-clock time, restored from the cache when available. The cache
    key embeds ``method_tag`` ("tomo_cpu"/"tomo_cuda") plus the sweep parameters,
    so CPU and CUDA never collide and a parameter change never reuses a stale
    grid."""
    cache_path = cache_dir / f"{stem}_{method_tag}_{ANGLE_STEP:g}deg_{CRITICAL_ANGLE:g}deg.npz"
    if cache_path.exists():
        try:
            data = np.load(cache_path, allow_pickle=False)
            tomo = {
                "yaw_values": np.asarray(data["yaw_values"], dtype=np.float64),
                "pitch_values": np.asarray(data["pitch_values"], dtype=np.float64),
                "vss_grid": np.asarray(data["vss_grid"], dtype=np.float64),
            }
            dll_sec = float(data["dll_sec"]) if "dll_sec" in data.files else None
            return tomo, dll_sec, True
        except Exception as exc:  # corrupt/old cache -> recompute
            print(f"  {method_tag} cache unreadable ({exc}); recomputing", flush=True)

    start = time.perf_counter()
    tomo = compute_fn(mesh_path, critical_angle=CRITICAL_ANGLE, angle_step=ANGLE_STEP)
    dll_sec = time.perf_counter() - start
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        cache_path,
        yaw_values=np.asarray(tomo["yaw_values"], dtype=np.float64),
        pitch_values=np.asarray(tomo["pitch_values"], dtype=np.float64),
        vss_grid=np.asarray(tomo["vss_grid"], dtype=np.float64),
        dll_sec=np.float64(dll_sec),
    )
    return tomo, dll_sec, False


def load_or_run_tomo_cpu(
    mesh_path: Path, stem: str
) -> tuple[dict[str, object], float | None, bool]:
    """Cached TOMO_CPU (CPU) grid sweep; see ``_load_or_run_tomo``."""
    return _load_or_run_tomo(
        mesh_path, stem,
        compute_fn=compute_tomo_cpu_vss_grid,
        cache_dir=TOMO_CPU_CACHE_DIR,
        method_tag="tomo_cpu",
    )


def load_or_run_tomo_cuda(
    mesh_path: Path, stem: str
) -> tuple[dict[str, object], float | None, bool]:
    """Cached TOMO_CUDA (GPU) grid sweep; see ``_load_or_run_tomo``."""
    return _load_or_run_tomo(
        mesh_path, stem,
        compute_fn=compute_tomo_cuda_vss_grid,
        cache_dir=TOMO_CUDA_CACHE_DIR,
        method_tag="tomo_cuda",
    )


def save_candidate_pool_csv(path: Path, pool: list[tuple]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["tuned_score", "rayleigh", "pair", "bed", "hit", "dir_x", "dir_y", "dir_z", "sigma1", "sigma2", "sigma3"])
        for row in pool:
            sv = np.asarray(row[7], dtype=np.float64)
            sv3 = list(sv[:3]) + [0.0] * (3 - min(len(sv), 3))
            d = np.asarray(row[5], dtype=np.float64)
            writer.writerow([row[0], row[1], row[2], row[3], row[4], d[0], d[1], d[2], sv3[0], sv3[1], sv3[2]])


def direction_record(item) -> dict[str, object]:
    return {
        "rank": int(item.rank),
        "label": str(item.label),
        "tuned_score": float(item.value),
        "direction": np.asarray(item.direction, dtype=np.float64).tolist(),
        "rayleigh_score": float(item.rayleigh_score),
        "pair_score": float(item.pair_score),
        "bed_score": float(item.bed_score),
        "hit_count": int(item.hit_count),
        "singular_values": (
            np.asarray(item.singular_values, dtype=np.float64).tolist()
            if item.singular_values is not None
            else []
        ),
    }


def _run_tomo_stage(
    mesh_path: Path,
    stem: str,
    record: dict[str, object],
    *,
    loader,
    method: str,
    html_suffix: str,
    sec_key: str,
    cached_key: str,
    html_key: str,
    best_key: str,
    error_key: str,
) -> None:
    """Run one TOMO backend (cached), build its v_ss contour HTML, and write the
    timing/cached/best/contour fields into ``record`` in place. A backend failure
    is recorded in ``error_key`` but never aborts the mesh (SFTF output and the
    other backend's result are preserved)."""
    if (
        RUN_ONLY_MISSING
        and record.get(sec_key) is not None
        and record.get(best_key) is not None
        and record.get(html_key)
    ):
        return
    record[error_key] = None
    try:
        tomo, dll_sec, cached = loader(mesh_path, stem)
        yaw_values = np.asarray(tomo["yaw_values"], dtype=np.float64)
        pitch_values = np.asarray(tomo["pitch_values"], dtype=np.float64)
        vss_grid = np.asarray(tomo["vss_grid"], dtype=np.float64)
        fig = build_tomo_contour_figure(stem, yaw_values, pitch_values, vss_grid, method=method)
        contour_path = OUT_DIR / f"{stem}_{html_suffix}.html"
        fig.write_html(contour_path, include_plotlyjs="cdn")
        record[sec_key] = dll_sec
        record[cached_key] = cached
        record[html_key] = contour_path.name
        record[best_key] = tomo_best_row(yaw_values, pitch_values, vss_grid)
    except Exception as exc:  # a backend may fail on some meshes; keep other output
        record[error_key] = f"{type(exc).__name__}: {exc}"
        print(f"  {method} FAILED: {record[error_key]}", flush=True)


def process_mesh(
    mesh_path: Path,
    *,
    run_sftf: bool,
    run_cpu: bool,
    run_cuda: bool,
    run_sftf_cpp: bool,
) -> dict[str, object]:
    stem = mesh_path.stem
    group, gid = parse_group_id(stem)

    # Start from a full blank template overlaid with any prior result, so a
    # selective run keeps the stages it does not recompute (and old JSONs that
    # predate the TOMO_CUDA fields still get those keys, defaulted to blank).
    record = blank_record(mesh_path)
    prior = load_per_mesh_record(stem)
    if prior:
        record.update(prior)
    record["group"], record["group_id"], record["mesh"] = group, gid, mesh_path.name
    record["angle_step_deg"] = float(ANGLE_STEP)
    record["critical_angle_deg"] = float(CRITICAL_ANGLE)

    def save_progress() -> None:
        SFTF_RESULT_DIR.mkdir(parents=True, exist_ok=True)
        per_mesh_json = SFTF_RESULT_DIR / f"{stem}.json"
        per_mesh_json.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        if "refresh_accumulated_outputs" in globals():
            refresh_accumulated_outputs()

    # --- SFTF candidate pool + landscape ---
    if run_sftf:
        start = time.perf_counter()
        mesh = load_mesh(str(mesh_path))
        pool = evaluate_support_flow_candidate_pool(mesh)
        directions = support_flow_directions_from_candidate_pool(pool)
        elapsed = time.perf_counter() - start

        scores = np.asarray([row[0] for row in pool], dtype=np.float64) if pool else np.zeros(0)
        figure = build_landscape_figure(stem, pool, directions)
        SFTF_RESULT_DIR.mkdir(parents=True, exist_ok=True)
        html_path = SFTF_RESULT_DIR / f"{stem}.html"
        figure.write_html(html_path, include_plotlyjs="cdn")
        pool_csv_path = SFTF_RESULT_DIR / f"{stem}_candidates.csv"
        save_candidate_pool_csv(pool_csv_path, pool)

        record.update({
            "face_count": int(len(mesh.faces)),
            "coarse_direction_count": int(SUPPORT_FLOW_COARSE_DIRECTION_COUNT),
            "candidate_pool_size": int(len(pool)),
            "score_min": float(np.min(scores)) if scores.size else None,
            "score_median": float(np.median(scores)) if scores.size else None,
            "score_max": float(np.max(scores)) if scores.size else None,
            "top_directions": [direction_record(item) for item in directions],
            "html": output_link(html_path),
            "candidates_csv": output_link(pool_csv_path),
            "elapsed_sec": elapsed,
        })
        save_progress()

    # --- TOMO_CPU (CPU) reference: cached grid sweep + contour ---
    if run_cpu:
        _run_tomo_stage(
            mesh_path, stem, record,
            loader=load_or_run_tomo_cpu, method="TOMO_CPU", html_suffix="tomo_cpu",
            sec_key="tomo_cpu_dll_sec", cached_key="tomo_cpu_cached",
            html_key="tomo_cpu_html", best_key="tomo_cpu_best", error_key="tomo_cpu_error",
        )
        save_progress()

    # --- TOMO_CUDA (GPU) reference: cached grid sweep + contour ---
    if run_cuda:
        _run_tomo_stage(
            mesh_path, stem, record,
            loader=load_or_run_tomo_cuda, method="TOMO_CUDA", html_suffix="tomo_cuda",
            sec_key="tomo_cuda_dll_sec", cached_key="tomo_cuda_cached",
            html_key="tomo_cuda_html", best_key="tomo_cuda_best", error_key="tomo_cuda_error",
        )
        save_progress()

    # --- SFTF candidate generator via sftf_cpp.dll (C++) ---
    # Fast and deterministic, so it always runs when enabled (no .npz cache);
    # records the optimal/worst orientations and the pure-compute time (ms).
    if run_sftf_cpp:
        record["sftf_cpp_error"] = None
        try:
            sftf = compute_sftf_directions_cpp(str(mesh_path))
            record["sftf_cpp_ms"] = float(sftf["compute_ms"])
            record["sftf_cpp_optimal"] = sftf["optimal"]
            record["sftf_cpp_worst"] = sftf["worst"]
            if record.get("face_count") is None:
                record["face_count"] = int(sftf["face_count"])
        except Exception as exc:  # keep other stages' output on failure
            record["sftf_cpp_error"] = f"{type(exc).__name__}: {exc}"
            print(f"  SFTF_C++ FAILED: {record['sftf_cpp_error']}", flush=True)
        save_progress()

    save_progress()
    return record


def write_summary(records: list[dict[str, object]]) -> None:
    json_path = OUT_DIR / "G5Test_summary.json"
    csv_path = OUT_DIR / "G5Test_summary.csv"
    json_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    fieldnames = [
        "group", "group_id", "mesh", "face_count", "candidate_pool_size",
        "score_min", "score_median", "score_max",
        "top1_score", "top1_x", "top1_y", "top1_z", "top1_hit",
        "top2_score", "top3_score", "elapsed_sec",
        "tomo_cpu_dll_sec", "tomo_cuda_dll_sec", "sftf_cpp_ms", "html",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            tops = r["top_directions"]
            row = {
                "group": r["group"], "group_id": r["group_id"], "mesh": r["mesh"],
                "face_count": r["face_count"], "candidate_pool_size": r["candidate_pool_size"],
                "score_min": r["score_min"], "score_median": r["score_median"], "score_max": r["score_max"],
                "elapsed_sec": r["elapsed_sec"],
                "tomo_cpu_dll_sec": r.get("tomo_cpu_dll_sec"),
                "tomo_cuda_dll_sec": r.get("tomo_cuda_dll_sec"),
                "sftf_cpp_ms": r.get("sftf_cpp_ms"),
                "html": r["html"],
            }
            if len(tops) > 0:
                d = tops[0]["direction"]
                row.update({
                    "top1_score": tops[0]["tuned_score"], "top1_x": d[0], "top1_y": d[1], "top1_z": d[2],
                    "top1_hit": tops[0]["hit_count"],
                })
            if len(tops) > 1:
                row["top2_score"] = tops[1]["tuned_score"]
            if len(tops) > 2:
                row["top3_score"] = tops[2]["tuned_score"]
            writer.writerow(row)


def _fmt(value: object, spec: str = "") -> str:
    """Format a value for an HTML cell, blanking ``None``."""
    if value is None:
        return ""
    if spec:
        try:
            return format(value, spec)
        except (TypeError, ValueError):
            return html.escape(str(value))
    return html.escape(str(value))


def _file_link(file_name: object, error: object = None, text: str = "open") -> str:
    """Cell content for an artifact: a link when present, a hover-titled
    'failed' marker on error, else blank (stage not run)."""
    if file_name:
        return f'<a href="{html.escape(str(file_name))}">{html.escape(text)}</a>'
    if error:
        return '<span title="{}">failed</span>'.format(html.escape(str(error)))
    return ""


def _direction_text(direction: object) -> str:
    """Format a 3-vector as '(x, y, z)' for an HTML cell."""
    if not direction:
        return ""
    return "({:.3f}, {:.3f}, {:.3f})".format(
        float(direction[0]), float(direction[1]), float(direction[2])
    )


def _sftf_entry(entries: object, index: int = 0) -> dict[str, object] | None:
    """Return one SFTF direction entry from a Python/C++ top-direction list."""
    if not entries:
        return None
    try:
        return entries[index]
    except (IndexError, TypeError):
        return None


def _sftf_cells(entry: dict[str, object] | None) -> list[str]:
    """Detailed columns shared by Python SFTF and SFTF_C++ entries."""
    if not entry:
        return [""] * 7
    return [
        _fmt(entry.get("tuned_score"), ".4g"),
        _direction_text(entry.get("direction")),
        _fmt(entry.get("hit_count"), ",d"),
        _fmt(entry.get("rayleigh_score"), ".4g"),
        _fmt(entry.get("pair_score"), ".4g"),
        _fmt(entry.get("bed_score"), ".4g"),
        _fmt(entry.get("sigma1") or (entry.get("singular_values") or [None])[0], ".4g"),
    ]


def _tomo_cells(record: dict[str, object], prefix: str) -> list[str]:
    """Detailed columns available for a TOMO backend."""
    best = record.get(f"{prefix}_best") or {}
    return [
        _fmt(record.get(f"{prefix}_dll_sec"), ".2f"),
        "yes" if record.get(f"{prefix}_cached") else ("no" if record.get(f"{prefix}_dll_sec") is not None else ""),
        _fmt(best.get("vss"), ".6g"),
        _fmt(best.get("yaw"), ".3f"),
        _fmt(best.get("pitch"), ".3f"),
    ]


def write_summary_table_html(records: list[dict[str, object]]) -> None:
    """Write a single standalone HTML page tabulating every mesh's result.

    One row per mesh with method-grouped columns. Python SFTF and SFTF_C++ use
    the same detailed score/direction/hit/R/P/B/sigma1 layout; TOMO_CPU and
    TOMO_CUDA list the values available from the grid sweep cache (time,
    cache flag, and best yaw/pitch/vss).
    """
    table_path = four_method_table_path()

    identity_columns = ["group", "group_id", "mesh", "faces"]
    python_columns = [
        "pool", "score min", "score median", "score max", "elapsed (s)",
        "top1 score", "top1 direction (x, y, z)", "top1 hit",
        "top1 R", "top1 P", "top1 B", "top1 sigma1",
        "top2 score", "top2 direction (x, y, z)", "top2 hit",
        "top3 score", "top3 direction (x, y, z)", "top3 hit",
    ]
    tomo_columns = ["DLL (s)", "cached", "best vss", "best yaw", "best pitch"]
    cpp_columns = [
        "compute (ms)",
        "top1 score", "top1 direction (x, y, z)", "top1 hit",
        "top1 R", "top1 P", "top1 B", "top1 sigma1",
        "top2 score", "top2 direction (x, y, z)", "top2 hit",
        "top3 score", "top3 direction (x, y, z)", "top3 hit",
        "worst score", "worst direction (x, y, z)", "worst hit",
        "worst R", "worst P", "worst B", "worst sigma1",
    ]
    artifact_columns = ["Python landscape", "candidates csv", "TOMO_CPU contour", "TOMO_CUDA contour"]
    header_top = (
        f'<tr class="groups"><th colspan="{len(identity_columns)}">Mesh</th>'
        f'<th colspan="{len(python_columns)}">Python SFTF</th>'
        f'<th colspan="{len(tomo_columns)}">TOMO_CPU</th>'
        f'<th colspan="{len(tomo_columns)}">TOMO_CUDA</th>'
        f'<th colspan="{len(cpp_columns)}">SFTF_C++</th>'
        f'<th colspan="{len(artifact_columns)}">Artifacts</th></tr>'
    )
    header_bottom = "<tr>" + "".join(
        f"<th>{html.escape(c)}</th>"
        for c in (
            identity_columns
            + python_columns
            + tomo_columns
            + tomo_columns
            + cpp_columns
            + artifact_columns
        )
    ) + "</tr>"

    body_rows: list[str] = []
    for r in records:
        tops = r["top_directions"]
        py1 = _sftf_entry(tops, 0)
        py2 = _sftf_entry(tops, 1)
        py3 = _sftf_entry(tops, 2)
        cpp1 = _sftf_entry(r.get("sftf_cpp_optimal"), 0)
        cpp2 = _sftf_entry(r.get("sftf_cpp_optimal"), 1)
        cpp3 = _sftf_entry(r.get("sftf_cpp_optimal"), 2)
        cpp_worst = _sftf_entry(r.get("sftf_cpp_worst"), 0)
        cpp_time = _fmt(r.get("sftf_cpp_ms"), ".1f")
        if not cpp_time and r.get("sftf_cpp_error"):
            cpp_time = '<span title="{}">failed</span>'.format(html.escape(str(r["sftf_cpp_error"])))

        cells = [
            _fmt(r["group"]),
            _fmt(r["group_id"]),
            _fmt(r["mesh"]),
            _fmt(r["face_count"], ",d"),
            _fmt(r["candidate_pool_size"], ",d"),
            _fmt(r["score_min"], ".4g"),
            _fmt(r["score_median"], ".4g"),
            _fmt(r["score_max"], ".4g"),
            _fmt(r["elapsed_sec"], ".2f"),
        ]
        cells += _sftf_cells(py1)
        cells += _sftf_cells(py2)[:3]
        cells += _sftf_cells(py3)[:3]
        cells += _tomo_cells(r, "tomo_cpu")
        cells += _tomo_cells(r, "tomo_cuda")
        cells += [cpp_time]
        cells += _sftf_cells(cpp1)
        cells += _sftf_cells(cpp2)[:3]
        cells += _sftf_cells(cpp3)[:3]
        cells += _sftf_cells(cpp_worst)
        cells += [
            _file_link(r.get("html")),
            _file_link(r.get("candidates_csv"), text="csv"),
            _file_link(r.get("tomo_cpu_html"), r.get("tomo_cpu_error")),
            _file_link(r.get("tomo_cuda_html"), r.get("tomo_cuda_error")),
        ]
        pending = r.get("face_count") is None
        row_open = '<tr class="pending">' if pending else "<tr>"
        body_rows.append(row_open + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")

    n_done = sum(1 for r in records if r.get("face_count") is not None)
    generated = (
        f"{n_done}/{len(records)} meshes computed &middot; "
        f"critical angle {CRITICAL_ANGLE:g}&deg; &middot; "
        f"angle step {ANGLE_STEP:g}&deg; &middot; "
        "blank cells are not yet run or not stored &middot; lower SFTF score and TOMO vss are better"
    )
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Five-group verification &mdash; {angle_file_tag(CRITICAL_ANGLE)} 4 methods table</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
         margin: 24px; color: #222; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  p.meta {{ color: #666; margin: 0 0 16px; font-size: 13px; }}
  .table-wrap {{ overflow-x: auto; border: 1px solid #e2e2e2; }}
  table {{ border-collapse: collapse; font-size: 12px; width: max-content; min-width: 100%; }}
  th, td {{ padding: 6px 10px; border-bottom: 1px solid #e2e2e2; text-align: right;
            white-space: nowrap; }}
  th {{ position: sticky; top: 0; background: #f5f5f5; text-align: right;
        border-bottom: 2px solid #ccc; cursor: default; }}
  thead tr.groups th {{ top: 0; background: #e8eef8; text-align: center; }}
  thead tr:not(.groups) th {{ top: 31px; }}
  td:nth-child(-n+3), thead tr:not(.groups) th:nth-child(-n+3) {{ text-align: left; }}
  tbody tr:hover {{ background: #fafafe; }}
  tr.pending td {{ color: #bbb; background: #fcfcfc; }}
  a {{ color: #2a6fdb; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>Five-group verification &mdash; 4 methods table ({CRITICAL_ANGLE:g}&deg; critical angle)</h1>
<p class="meta">{generated}</p>
<div class="table-wrap">
<table>
<thead>{header_top}{header_bottom}</thead>
<tbody>
{chr(10).join(body_rows)}
</tbody>
</table>
</div>
</body>
</html>
"""
    table_path.write_text(doc, encoding="utf-8")


def _stage_note(
    record: dict[str, object], sec_key: str, cached_key: str, error_key: str, label: str
) -> str:
    """One ' label=..' fragment for the per-mesh run log. Blank when the stage
    neither ran this session nor has a stored result; 'FAILED' on error."""
    if record.get(error_key):
        return f" {label}=FAILED"
    sec = record.get(sec_key)
    if sec is None:
        return ""
    suffix = "(cached)" if record.get(cached_key) else ""
    return f" {label}={sec:.2f}s{suffix}"


def refresh_accumulated_outputs() -> tuple[int, int]:
    """Rebuild summary files and the HTML table from all per-mesh JSON files.

    This is intentionally cheap compared with TOMO/SFTF computation and is
    called after every completed mesh, so an interrupted long batch still leaves
    the table current up to the most recent finished mesh.
    """
    all_rows = collect_roster_records()
    computed_records = [r for r in all_rows if r.get("face_count") is not None]
    if computed_records:
        write_summary(computed_records)
    write_summary_table_html(all_rows)
    return len(computed_records), len(all_rows)


def _stage_complete(
    record: dict[str, object],
    *,
    sec_key: str | None = None,
    best_key: str | None = None,
    html_key: str | None = None,
) -> bool:
    """True when a stage already has the headline values shown in the table."""
    return (
        (sec_key is None or record.get(sec_key) is not None)
        and (best_key is None or record.get(best_key) is not None)
        and (html_key is None or bool(record.get(html_key)))
    )


def enabled_stages_complete(mesh_path: Path) -> bool:
    """Whether every enabled stage is already complete for this mesh."""
    if not RUN_ONLY_MISSING:
        return False
    record = blank_record(mesh_path)
    prior = load_per_mesh_record(mesh_path.stem)
    if prior:
        record.update(prior)
    checks: list[bool] = []
    if RUN_SFTF:
        checks.append(_stage_complete(record, sec_key="elapsed_sec", html_key="html"))
    if RUN_TOMO_CPU:
        checks.append(_stage_complete(
            record, sec_key="tomo_cpu_dll_sec", best_key="tomo_cpu_best", html_key="tomo_cpu_html"
        ))
    if RUN_TOMO_CUDA:
        checks.append(_stage_complete(
            record, sec_key="tomo_cuda_dll_sec", best_key="tomo_cuda_best", html_key="tomo_cuda_html"
        ))
    if RUN_SFTF_CPP:
        checks.append(_stage_complete(record, sec_key="sftf_cpp_ms", best_key="sftf_cpp_optimal"))
    return bool(checks) and all(checks)


def main() -> None:
    # CLI arguments override the RUN_GROUPS flags; with no args, use the flags.
    if sys.argv[1:]:
        wanted_groups = {g.upper() for g in sys.argv[1:]}
    else:
        wanted_groups = {g.upper() for g, on in RUN_GROUPS.items() if on}
    if not wanted_groups:
        raise SystemExit("no groups enabled: set at least one RUN_GROUPS flag to True")

    mesh_paths = sorted(
        p for p in MESH_DIR.glob(MESH_GLOB)
        if p.is_file() and p.suffix.lower() in MESH_EXTENSIONS
    )
    # drop mislabeled cross-group duplicates (e.g. Group_D10_65942 == Group_E10_65942)
    # before the group filter, so the E number is still visible when running group D alone.
    _e_numbers = {p.stem.split("_")[-1] for p in mesh_paths if parse_group_id(p.stem)[0].upper() == "E"}
    mesh_paths = [
        p for p in mesh_paths
        if not (parse_group_id(p.stem)[0].upper() == "D" and p.stem.split("_")[-1] in _e_numbers)
    ]
    mesh_paths = [p for p in mesh_paths if parse_group_id(p.stem)[0].upper() in wanted_groups]
    if not mesh_paths:
        raise FileNotFoundError(
            f"no Group meshes found in {MESH_DIR} for groups {sorted(wanted_groups)} (glob {MESH_GLOB})"
        )

    stages = ", ".join(
        name for name, on in (
            ("SFTF", RUN_SFTF), ("TOMO_CPU", RUN_TOMO_CPU), ("TOMO_CUDA", RUN_TOMO_CUDA),
            ("SFTF_C++", RUN_SFTF_CPP),
        ) if on
    ) or "none"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(
        f"five-group verification: {len(mesh_paths)} meshes "
        f"(groups {', '.join(sorted(wanted_groups))}; stages {stages}) -> {OUT_DIR}",
        flush=True,
    )

    records, failures = [], []
    total_start = time.perf_counter()
    for mesh_id, mesh_path in enumerate(mesh_paths, start=1):
        if enabled_stages_complete(mesh_path):
            print(f"[{mesh_id}/{len(mesh_paths)}] {mesh_path.name} skipped (already complete)", flush=True)
            continue
        print(f"[{mesh_id}/{len(mesh_paths)}] {mesh_path.name}", flush=True)
        try:
            record = process_mesh(
                mesh_path,
                run_sftf=RUN_SFTF,
                run_cpu=RUN_TOMO_CPU,
                run_cuda=RUN_TOMO_CUDA,
                run_sftf_cpp=RUN_SFTF_CPP,
            )
        except Exception as exc:  # keep the batch going on a bad mesh
            print(f"  FAILED: {type(exc).__name__}: {exc}", flush=True)
            failures.append({"mesh": mesh_path.name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        records.append(record)
        top1 = record["top_directions"][0] if record["top_directions"] else None
        notes = (
            _stage_note(record, "tomo_cpu_dll_sec", "tomo_cpu_cached", "tomo_cpu_error", "cpu")
            + _stage_note(record, "tomo_cuda_dll_sec", "tomo_cuda_cached", "tomo_cuda_error", "cuda")
        )
        if record.get("sftf_cpp_error"):
            notes += " sftf_cpp=FAILED"
        elif record.get("sftf_cpp_ms") is not None:
            notes += f" sftf_cpp={record['sftf_cpp_ms']:.1f}ms"
        elapsed = record.get("elapsed_sec")
        elapsed_str = f"{elapsed:.2f}s" if elapsed is not None else "n/a"
        print(
            (
                f"  faces={record['face_count']} pool={record['candidate_pool_size']} "
                f"top1_score={top1['tuned_score']:.4g} hit={top1['hit_count']} "
                f"({elapsed_str}){notes}"
                if top1
                else f"  no candidates ({elapsed_str}){notes}"
            ),
            flush=True,
        )
        computed_count, roster_count = refresh_accumulated_outputs()
        print(
            f"  updated {four_method_table_path().name} ({computed_count}/{roster_count} meshes)",
            flush=True,
        )

    # Always rebuild the summary + table from EVERY per-mesh JSON on disk (not
    # just this run's groups), so group-by-group runs accumulate. The table lists
    # the full A/B/C/D/E roster and leaves not-yet-computed meshes blank.
    computed_count, roster_count = refresh_accumulated_outputs()
    if failures:
        (OUT_DIR / "G5Test_failures.json").write_text(
            json.dumps(failures, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    print(
        f"\ndone: {len(records)} ok this run, {len(failures)} failed; "
        f"table now has {computed_count}/{roster_count} meshes computed; "
        f"total {time.perf_counter() - total_start:.1f}s -> {OUT_DIR}",
        flush=True,
    )


if __name__ == "__main__":
    main()
