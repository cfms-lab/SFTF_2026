"""Pre-registered prospective slicer confirmation of the SFTF candidate regime.

Protocol: GATE_2026-09-16_prospective_slicer_confirmation.md (repo root).  The
policies, budgets, slicing protocol and analysis are copied from the TDP v2
budget-slicer study (draft/src/legacy/TDP_v2/scripts/run_tdp_v2_budget_slicer.py)
so that nothing is re-implemented.

Phases (all resumable; run in this order):
  score    SFTF v2 scores (K=4096, 8192) on 2,048 Fibonacci directions per mesh
  slice    CuraEngine 5.13 + PrusaSlicer 2.9.6 on the union of uniform(5,10,20)
           and SFTF top-20 canonical grid cells; raw rows appended to JSONL
  tomo     dense 1 deg / 60 deg TOMO grids for meshes that do not have one
  analyze  pre-specified analysis; the only phase that prints outcome values
  status   progress counts only (no outcome values)
  smoke    end-to-end check on a development mesh (not a study mesh)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
LEGACY = PROJECT_ROOT / "draft" / "src" / "legacy" / "TDP_v2"
MESH_ROOT = Path(r"D:\__SFTF_Projects(2026)\sftf_Mesh_Data")
CURA_CLI_SRC = PROJECT_ROOT.parent / "_Cura_CLI" / "python" / "src"
PRUSA_EXE = Path(r"D:\__PFTF_Projects(2026)\_tools_prusa\extracted\PrusaSlicer-2.9.6\prusa-slicer-console.exe")
PRUSA_PROFILE = LEGACY / "profiles" / "prusa_support_tdp_v2.ini"
TOMO_ROOT = PROJECT_ROOT / "cpp_src" / "Tomo_GPU2026"
MANIFEST = HERE / "prospective_manifest.csv"
SCORE_DIR = HERE / "scores"
GRID_DIR = HERE / "tomo_grids"
RAW_JSONL = HERE / "slicer_raw.jsonl"
CELLS_JSON = HERE / "policy_cells.json"
RESULTS_JSON = HERE / "prospective_results.json"
RESULTS_CSV = HERE / "prospective_results.csv"
SUMMARY_MD = HERE / "RESULTS.md"

for p in (str(PROJECT_ROOT / "python_src"), str(LEGACY / "scripts"), str(CURA_CLI_SRC), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import analyze_tdp_v2_tomo_external as base  # noqa: E402  (fibonacci, nms, expand, uniform_cells, evaluate_v2_arrays)
from cura_cli import mesh_rotation  # noqa: E402
from cura_cli.cura_slicer import CuraSlicer  # noqa: E402
from cura_cli.gcode_support import parse_gcode_support  # noqa: E402

CANDIDATE_COUNT = 2048
BUDGETS = [5, 10, 20]
PRIMARY_BUDGET = 10
TARGET_DIAGONAL_MM = 140.0
CURA_ANGLE = 60.0
PRUSA_THRESHOLD = 30.0
ENGINES = ("cura_5_13", "prusa_2_9_6")
COMPLEX = ("faces_50k_150k", "faces_150k_250k")
LATTICE = np.arange(0.0, 361.0, 1.0)  # 361 yaw x 361 pitch, identical cell indexing to the TOMO grids
SEEDS = {"cura_5_13": 20260916, "prusa_2_9_6": 20260917, "tomo": 20260918}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_manifest() -> list[dict[str, Any]]:
    with MANIFEST.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["face_count"] = int(r["face_count"])
    return rows


def mesh_path_of(row: dict[str, Any]) -> Path:
    path = (MESH_ROOT / row["relative_path"]).resolve()
    if sha256_file(path) != row["sha256"].lower():
        raise RuntimeError(f"{row['study_id']}: mesh hash mismatch")
    return path


def load_mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(str(path), force="mesh", process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)
    return mesh


# ----------------------------------------------------------------------------- score
def score_one(row: dict[str, Any], mesh: trimesh.Trimesh | None = None) -> dict[str, Any]:
    out = SCORE_DIR / f"{row['study_id']}.npz"
    if out.is_file():
        with np.load(out, allow_pickle=False) as d:
            return {k: d[k] for k in d.files}
    if mesh is None:
        mesh = load_mesh(mesh_path_of(row))
    directions = base.fibonacci_directions(CANDIDATE_COUNT)
    s4096, k4096, t4096 = base.evaluate_v2_arrays(mesh, directions, 4096)
    s8192, k8192, t8192 = base.evaluate_v2_arrays(mesh, directions, 8192)
    SCORE_DIR.mkdir(exist_ok=True)
    payload = dict(directions=directions, scores_4096=s4096, scores_8192=s8192, skew_4096=k4096,
                   skew_8192=k8192, time_4096_s=np.asarray(t4096), time_8192_s=np.asarray(t8192))
    tmp = out.with_suffix(".tmp.npz")
    with tmp.open("wb") as fh:
        np.savez_compressed(fh, **payload)
    os.replace(tmp, out)
    return payload


def gate_diagnostics(sc: dict[str, Any]) -> dict[str, Any]:
    directions = np.asarray(sc["directions"])
    s4096 = np.asarray(sc["scores_4096"], dtype=np.float64)
    s8192 = np.asarray(sc["scores_8192"], dtype=np.float64)
    k8192 = np.asarray(sc["skew_8192"], dtype=np.float64)
    b4096 = base.nms_basins(directions, s4096)
    b8192 = base.nms_basins(directions, s8192)
    align = np.max(directions[b8192] @ directions[b4096].T, axis=1)
    stability = float(np.degrees(np.mean(np.arccos(np.clip(align, -1.0, 1.0)))))
    med = float(np.median(s8192))
    dispersion = float((np.percentile(s8192, 90) - np.percentile(s8192, 10)) / max(abs(med), 1e-12))
    skew = float(np.median(k8192[b8192[:8]]))
    accepted = bool(stability <= 15.0 and dispersion >= 0.08 and skew <= 1.0)
    return {"stability_mean_angle_deg": stability, "score_dispersion": dispersion,
            "top8_median_skew_ratio": skew, "gate_accepted": accepted, "basin_ids_8192": b8192}


def policy_cells(sc: dict[str, Any]) -> dict[str, Any]:
    """Uniform(5,10,20) and SFTF top-20 canonical cells on the 1-degree lattice."""
    directions = np.asarray(sc["directions"])
    s8192 = np.asarray(sc["scores_8192"], dtype=np.float64)
    canonical_flat, canonical_dirs = base.canonical_grid_cells(LATTICE, LATTICE)
    basins = directions[base.nms_basins(directions, s8192)]
    sftf20 = [int(c) for c in base.expand_around_basins(basins, canonical_flat, canonical_dirs, max(BUDGETS))]
    uniform = {b: [int(c) for c in base.uniform_cells(LATTICE, LATTICE, b)] for b in BUDGETS}
    sftf = {b: sftf20[:b] for b in BUDGETS}
    union = sorted(set(sftf20).union(*uniform.values()))
    return {"uniform": uniform, "sftf": sftf, "union": union}


def cmd_score(rows: list[dict[str, Any]]) -> None:
    cells_all = json.loads(CELLS_JSON.read_text(encoding="utf-8")) if CELLS_JSON.is_file() else {}
    for i, row in enumerate(rows, start=1):
        sid = row["study_id"]
        t0 = time.perf_counter()
        sc = score_one(row)
        if sid not in cells_all:
            pc = policy_cells(sc)
            g = gate_diagnostics(sc)
            cells_all[sid] = {"uniform": {str(b): v for b, v in pc["uniform"].items()},
                              "sftf": {str(b): v for b, v in pc["sftf"].items()}, "union": pc["union"],
                              "gate": {k: v for k, v in g.items() if k != "basin_ids_8192"},
                              "time_4096_s": float(sc["time_4096_s"]), "time_8192_s": float(sc["time_8192_s"])}
            CELLS_JSON.write_text(json.dumps(cells_all, indent=1), encoding="utf-8")
        print(f"[score {i}/{len(rows)}] {sid} faces={row['face_count']} K8192={float(sc['time_8192_s']):.2f}s "
              f"union={len(cells_all[sid]['union'])} gate={cells_all[sid]['gate']['gate_accepted']} "
              f"({time.perf_counter()-t0:.1f}s)", flush=True)


# ----------------------------------------------------------------------------- slice
def load_raw(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def append_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
        fh.flush()


def run_prusa(stl: Path, gcode: Path) -> tuple[dict[str, float], float, str]:
    command = [str(PRUSA_EXE), "--load", str(PRUSA_PROFILE), "--support-material-threshold", str(PRUSA_THRESHOLD),
               "--gcode-comments", "--dont-arrange", "--ensure-on-bed", "--export-gcode", "--output", str(gcode), str(stl)]
    t0 = time.perf_counter()
    proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    elapsed = time.perf_counter() - t0
    if proc.returncode != 0 or not gcode.is_file():
        return {}, elapsed, (((proc.stderr or "") + "\n" + (proc.stdout or "")).strip())[-1500:]
    return parse_gcode_support(gcode).as_dict(), elapsed, ""


def slice_direction(mesh: trimesh.Trimesh, sid: str, flat: int, cura: CuraSlicer) -> list[dict[str, Any]]:
    yaw = float(LATTICE[flat % 361]); pitch = float(LATTICE[flat // 361])
    started = utc_now()
    with tempfile.TemporaryDirectory(prefix=f"psc_{sid}_{flat}_") as tmp:
        work = Path(tmp)
        stl = work / "oriented.stl"
        mesh_rotation.write_oriented_stl(mesh, yaw, pitch, stl)
        t0 = time.perf_counter()
        cres = cura.slice_stl(stl)
        cel = time.perf_counter() - t0
        common = {"study_id": sid, "direction_id": f"g{flat:06d}", "grid_flat": int(flat), "yaw_deg": yaw,
                  "pitch_deg": pitch, "started_utc": started}
        rows = [{**common, "engine": "cura_5_13", "support_volume_mm3": float(cres.support_volume_mm3),
                 "total_volume_mm3": float(cres.total_volume_mm3), "elapsed_wall_s": float(cel),
                 "ok": bool(cres.ok), "error": str(cres.error), "completed_utc": utc_now()}]
        prep, pel, perr = run_prusa(stl, work / "prusa.gcode")
        rows.append({**common, "engine": "prusa_2_9_6",
                     "support_volume_mm3": float(prep.get("support_volume_mm3", math.nan)),
                     "total_volume_mm3": float(prep.get("total_volume_mm3", math.nan)),
                     "elapsed_wall_s": float(pel), "ok": not bool(perr), "error": perr, "completed_utc": utc_now()})
    return rows


def completed_keys(raw: list[dict[str, Any]]) -> set[tuple[str, int, str]]:
    return {(r["study_id"], int(r["grid_flat"]), r["engine"]) for r in raw if bool(r.get("ok"))}


def cmd_slice(rows: list[dict[str, Any]], jobs: int) -> None:
    cells_all = json.loads(CELLS_JSON.read_text(encoding="utf-8"))
    done = completed_keys(load_raw(RAW_JSONL))
    cura = CuraSlicer(engine="modern", critical_angle=CURA_ANGLE)
    for i, row in enumerate(rows, start=1):
        sid = row["study_id"]
        union = cells_all[sid]["union"]
        pending = [f for f in union if not all((sid, f, e) in done for e in ENGINES)]
        print(f"[slice {i}/{len(rows)}] {sid} ({row['stratum']}, {row['face_count']} faces): union={len(union)} pending={len(pending)}", flush=True)
        if not pending:
            continue
        mesh = load_mesh(mesh_path_of(row))
        mesh.apply_scale(TARGET_DIAGONAL_MM / float(np.linalg.norm(mesh.extents)))
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
            futures = {ex.submit(slice_direction, mesh, sid, f, cura): f for f in pending}
            n = 0
            for fut in as_completed(futures):
                out = fut.result()
                append_rows(RAW_JSONL, out)
                for r in out:
                    if bool(r.get("ok")):
                        done.add((sid, int(r["grid_flat"]), r["engine"]))
                n += 1
                if n == 1 or n % 10 == 0 or n == len(pending):
                    fails = sum(not bool(r.get("ok")) for r in out)
                    print(f"  {n}/{len(pending)} (last failures={fails}) {time.perf_counter()-t0:.0f}s", flush=True)


# ----------------------------------------------------------------------------- tomo
def grid_path_of(row: dict[str, Any]) -> Path:
    if row.get("tomo_grid_existing"):
        return (PROJECT_ROOT / row["tomo_grid_existing"]).resolve()
    return GRID_DIR / f"{row['study_id']}.npz"


def cmd_tomo(rows: list[dict[str, Any]]) -> None:
    from scripts.validate_ccave_eigen_tomo import compute_tomo_cpu_vss_grid
    GRID_DIR.mkdir(exist_ok=True)
    dll_sha = sha256_file(TOMO_ROOT / "Tomo_Shell2026.dll")
    todo = [r for r in rows if not grid_path_of(r).is_file()]
    print(f"[tomo] {len(todo)} grids to compute (DLL {dll_sha[:12]})", flush=True)
    for i, row in enumerate(todo, start=1):
        sid = row["study_id"]
        path = mesh_path_of(row)
        t0 = time.perf_counter()
        res = compute_tomo_cpu_vss_grid(path, tomo_project_root=TOMO_ROOT, critical_angle=60.0, angle_step=1.0)
        el = time.perf_counter() - t0
        grid = np.asarray(res["vss_grid"], dtype=np.float64)
        if grid.shape != (361, 361) or not np.all(np.isfinite(grid)):
            raise RuntimeError(f"{sid}: invalid grid {grid.shape}")
        meta = {"study_id": sid, "thingi_id": row["thingi_id"], "relative_path": row["relative_path"],
                "mesh_sha256": row["sha256"], "dll_sha256": dll_sha, "backend": "TomoSh_INT3 corrected int32",
                "critical_angle_deg": 60.0, "angle_step_deg": 1.0,
                "tomo_internal_mesh_scale": float(res.get("tomo_internal_mesh_scale", 1.0)),
                "elapsed_wall_s": el, "created_at_utc": utc_now(), "pid": os.getpid(), "simplification_method": "none"}
        out = GRID_DIR / f"{sid}.npz"
        tmp = out.with_suffix(".tmp")
        with tmp.open("wb") as fh:
            np.savez_compressed(fh, yaw_values=np.asarray(res["yaw_values"], dtype=np.float64),
                                pitch_values=np.asarray(res["pitch_values"], dtype=np.float64), vss_grid=grid,
                                metadata_json=np.asarray(json.dumps(meta)))
        os.replace(tmp, out)
        print(f"[tomo {i}/{len(todo)}] {sid} {el:.0f}s", flush=True)


# ----------------------------------------------------------------------------- analysis
def paired_stats(values: list[float], seed: int, n_boot: int = 10000, n_perm: int = 100000) -> dict[str, Any]:
    d = np.asarray(values, dtype=np.float64)
    if len(d) == 0:
        return {"n": 0}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    boot = np.mean(d[idx], axis=1)
    signs = rng.choice(np.asarray([-1.0, 1.0]), size=(n_perm, len(d)))
    perm = np.mean(signs * d[None, :], axis=1)
    obs = float(np.mean(d))
    return {"n": int(len(d)), "mean": obs, "median": float(np.median(d)), "sd": float(np.std(d, ddof=1)) if len(d) > 1 else None,
            "bootstrap_ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            "sign_flip_p_two_sided": float((1 + np.sum(np.abs(perm) >= abs(obs) - 1e-15)) / (n_perm + 1)),
            "sftf_better": int(np.sum(d < -1e-9)), "uniform_better": int(np.sum(d > 1e-9)), "ties": int(np.sum(np.abs(d) <= 1e-9)),
            "seed": seed, "bootstrap_replicates": n_boot, "permutation_replicates": n_perm}


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items); adj = {}; running = 0.0
    for k, (name, p) in enumerate(items):
        val = min(1.0, (m - k) * p)
        running = max(running, val)
        adj[name] = running
    return adj


def nrr(v: float, lo: float, hi: float) -> float:
    return 0.0 if abs(hi - lo) <= 1e-12 else float((v - lo) / (hi - lo))


def cmd_analyze(rows: list[dict[str, Any]]) -> None:
    cells_all = json.loads(CELLS_JSON.read_text(encoding="utf-8"))
    raw = load_raw(RAW_JSONL)
    latest: dict[tuple[str, int, str], dict[str, Any]] = {}
    for r in raw:
        if bool(r.get("ok")) and np.isfinite(float(r["support_volume_mm3"])):
            latest[(r["study_id"], int(r["grid_flat"]), r["engine"])] = r
    per_mesh = []
    for row in rows:
        sid = row["study_id"]; c = cells_all[sid]
        entry = {"study_id": sid, "source_set": row["source_set"], "stratum": row["stratum"], "face_count": row["face_count"],
                 "thingi_id": row["thingi_id"], "gate_accepted": c["gate"]["gate_accepted"], "sftf_k8192_wall_s": c["time_8192_s"]}
        for eng in ENGINES:
            sup = {f: float(r["support_volume_mm3"]) for (s, f, e), r in latest.items() if s == sid and e == eng}
            times = [float(r["elapsed_wall_s"]) for (s, f, e), r in latest.items() if s == sid and e == eng]
            entry[f"{eng}_sliced"] = len(sup); entry[f"{eng}_union"] = len(c["union"])
            entry[f"{eng}_mean_slice_s"] = float(np.mean(times)) if times else None
            lo = min(sup.values()) if sup else float("nan"); hi = max(sup.values()) if sup else float("nan")
            entry[f"{eng}_ref_min_mm3"] = lo; entry[f"{eng}_ref_max_mm3"] = hi
            for b in BUDGETS:
                u_cells = c["uniform"][str(b)]; s_cells = c["sftf"][str(b)]
                u_have = [sup[f] for f in u_cells if f in sup]; s_have = [sup[f] for f in s_cells if f in sup]
                entry[f"{eng}_u_{b}_missing"] = len(u_cells) - len(u_have); entry[f"{eng}_s_{b}_missing"] = len(s_cells) - len(s_have)
                u = nrr(min(u_have), lo, hi) if u_have else None; s = nrr(min(s_have), lo, hi) if s_have else None
                entry[f"{eng}_u_{b}"] = u; entry[f"{eng}_s_{b}"] = s
                entry[f"{eng}_diff_{b}"] = (s - u) if (u is not None and s is not None) else None
                entry[f"{eng}_complete_{b}"] = bool(u_have and s_have and len(u_have) == len(u_cells) and len(s_have) == len(s_cells))
        # TOMO reference (dense grid, full-grid min/max as in the paper)
        gp = grid_path_of(row)
        if gp.is_file():
            with np.load(gp, allow_pickle=False) as d:
                g = np.asarray(d["vss_grid"], dtype=np.float64).reshape(-1)
            lo, hi = float(g.min()), float(g.max())
            for b in BUDGETS:
                u = nrr(float(np.min(g[np.asarray(c["uniform"][str(b)])])), lo, hi)
                s = nrr(float(np.min(g[np.asarray(c["sftf"][str(b)])])), lo, hi)
                entry[f"tomo_u_{b}"] = u; entry[f"tomo_s_{b}"] = s; entry[f"tomo_diff_{b}"] = s - u
        per_mesh.append(entry)

    def collect(subset, key):
        return [e[key] for e in subset if e.get(key) is not None]

    summary: dict[str, Any] = {"n_meshes": len(per_mesh), "primary_budget": PRIMARY_BUDGET}
    # primary: complete-case at B=10 per engine
    pvals = {}
    for eng in ENGINES:
        cc = [e for e in per_mesh if e.get(f"{eng}_complete_{PRIMARY_BUDGET}")]
        st = paired_stats(collect(cc, f"{eng}_diff_{PRIMARY_BUDGET}"), SEEDS[eng])
        summary[f"primary_{eng}"] = st
        pvals[eng] = st["sign_flip_p_two_sided"]
        summary[f"primary_{eng}_excluded_incomplete"] = len(per_mesh) - len(cc)
        # sensitivity: best-available (as in the original small-budget study)
        summary[f"sensitivity_bestavailable_{eng}"] = paired_stats(collect(per_mesh, f"{eng}_diff_{PRIMARY_BUDGET}"), SEEDS[eng])
    summary["primary_holm_adjusted_p"] = holm(pvals)
    verdict = {}
    for eng in ENGINES:
        st = summary[f"primary_{eng}"]
        confirmed = st["mean"] < 0 and summary["primary_holm_adjusted_p"][eng] < 0.05
        reversed_ = st["mean"] > 0 and summary["primary_holm_adjusted_p"][eng] < 0.05
        verdict[eng] = "confirmed" if confirmed else ("reversed" if reversed_ else "not confirmed")
    n_conf = sum(v == "confirmed" for v in verdict.values())
    summary["verdict_per_engine"] = verdict
    summary["verdict_regime"] = "confirmed" if n_conf == 2 else ("partially confirmed" if n_conf == 1 else "not confirmed")
    # secondary
    sec: dict[str, Any] = {}
    for eng in ENGINES:
        for b in BUDGETS:
            sec[f"{eng}_B{b}_complete"] = paired_stats(collect([e for e in per_mesh if e.get(f"{eng}_complete_{b}")], f"{eng}_diff_{b}"), SEEDS[eng] + b)
        for s in COMPLEX:
            sub = [e for e in per_mesh if e["stratum"] == s and e.get(f"{eng}_complete_{PRIMARY_BUDGET}")]
            sec[f"{eng}_B{PRIMARY_BUDGET}_{s}"] = paired_stats(collect(sub, f"{eng}_diff_{PRIMARY_BUDGET}"), SEEDS[eng] + 100)
        for src in ("confirm80", "new"):
            sub = [e for e in per_mesh if e["source_set"] == src and e.get(f"{eng}_complete_{PRIMARY_BUDGET}")]
            sec[f"{eng}_B{PRIMARY_BUDGET}_{src}"] = paired_stats(collect(sub, f"{eng}_diff_{PRIMARY_BUDGET}"), SEEDS[eng] + 200)
    for b in BUDGETS:
        sec[f"tomo_B{b}"] = paired_stats(collect(per_mesh, f"tomo_diff_{b}"), SEEDS["tomo"] + b)
    both = [e for e in per_mesh if all(e.get(f"{eng}_complete_{PRIMARY_BUDGET}") for eng in ENGINES)]
    sc = np.sign([e[f"cura_5_13_diff_{PRIMARY_BUDGET}"] for e in both]); sp = np.sign([e[f"prusa_2_9_6_diff_{PRIMARY_BUDGET}"] for e in both])
    sec["engine_sign_agreement_B10"] = {"n": len(both), "agree": int(np.sum(sc == sp))}
    tomo_both = [e for e in both if e.get(f"tomo_diff_{PRIMARY_BUDGET}") is not None]
    sec["tomo_vs_cura_sign_agreement_B10"] = int(np.sum([np.sign(e["tomo_diff_10"]) == np.sign(e["cura_5_13_diff_10"]) for e in tomo_both]))
    sec["tomo_vs_prusa_sign_agreement_B10"] = int(np.sum([np.sign(e["tomo_diff_10"]) == np.sign(e["prusa_2_9_6_diff_10"]) for e in tomo_both]))
    sec["gate_accepted"] = int(sum(e["gate_accepted"] for e in per_mesh))
    # workflow cost
    tgen = [e["sftf_k8192_wall_s"] for e in per_mesh]
    cost = {"sftf_k8192_mean_s": float(np.mean(tgen)), "sftf_k8192_max_s": float(np.max(tgen))}
    for eng in ENGINES:
        ts = [e[f"{eng}_mean_slice_s"] for e in per_mesh if e.get(f"{eng}_mean_slice_s")]
        cost[f"{eng}_mean_slice_s"] = float(np.mean(ts)) if ts else None
        ov = [e["sftf_k8192_wall_s"] / (PRIMARY_BUDGET * e[f"{eng}_mean_slice_s"]) for e in per_mesh if e.get(f"{eng}_mean_slice_s")]
        cost[f"{eng}_overhead_B10_mean"] = float(np.mean(ov)) if ov else None
        cost[f"{eng}_overhead_B10_max"] = float(np.max(ov)) if ov else None
        cost[f"{eng}_overhead_B10_pooled"] = (cost["sftf_k8192_mean_s"] / (PRIMARY_BUDGET * cost[f"{eng}_mean_slice_s"])) if ts else None
    summary["secondary"] = sec; summary["workflow_cost"] = cost
    prov = {"manifest_sha256": sha256_file(MANIFEST), "cells_sha256": sha256_file(CELLS_JSON), "raw_rows": len(raw),
            "raw_ok_rows": int(sum(bool(r.get("ok")) for r in raw)), "raw_failed_rows": int(sum(not bool(r.get("ok")) for r in raw)),
            "cura_sha256": sha256_file(Path(r"C:\Program Files\UltiMaker Cura 5.13.0\CuraEngine.exe")),
            "prusa_sha256": sha256_file(PRUSA_EXE), "prusa_profile_sha256": sha256_file(PRUSA_PROFILE),
            "dll_sha256": sha256_file(TOMO_ROOT / "Tomo_Shell2026.dll"), "analyzed_utc": utc_now()}
    payload = {"provenance": prov, "summary": summary, "rows": per_mesh}
    RESULTS_JSON.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    fields: list[str] = []
    for e in per_mesh:
        for k in e:
            if k not in fields:
                fields.append(k)
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(per_mesh)

    def fmt(st):
        if not st or st.get("n", 0) == 0:
            return "n=0"
        lo, hi = st["bootstrap_ci95"]
        return (f"n={st['n']} mean={st['mean']:+.4f} [{lo:+.4f}, {hi:+.4f}] sd={st['sd']:.4f} p={st['sign_flip_p_two_sided']:.4f} "
                f"w/t/l={st['sftf_better']}/{st['ties']}/{st['uniform_better']}")

    lines = ["# Prospective slicer confirmation — results", "", f"analyzed {prov['analyzed_utc']}; meshes {len(per_mesh)}; raw ok rows {prov['raw_ok_rows']} / failed {prov['raw_failed_rows']}", "",
             "## Primary (B=10, complete-case, SFTF minus uniform NRR; negative favors SFTF)", ""]
    for eng in ENGINES:
        lines.append(f"- {eng}: {fmt(summary[f'primary_{eng}'])}; Holm p={summary['primary_holm_adjusted_p'][eng]:.4f}; excluded={summary[f'primary_{eng}_excluded_incomplete']} -> **{verdict[eng]}**")
    lines += ["", f"**Regime verdict (pre-registered rule): {summary['verdict_regime']}**", "", "## Secondary", ""]
    for k, v in sec.items():
        lines.append(f"- {k}: {fmt(v) if isinstance(v, dict) and 'mean' in v else v}")
    lines += ["", "## Workflow cost", ""] + [f"- {k}: {v}" for k, v in cost.items()]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)


# ----------------------------------------------------------------------------- status / smoke
def cmd_status(rows: list[dict[str, Any]]) -> None:
    cells_all = json.loads(CELLS_JSON.read_text(encoding="utf-8")) if CELLS_JSON.is_file() else {}
    raw = load_raw(RAW_JSONL); done = completed_keys(raw)
    scored = sum((SCORE_DIR / f"{r['study_id']}.npz").is_file() for r in rows)
    total_dirs = sum(len(cells_all.get(r["study_id"], {}).get("union", [])) for r in rows)
    done_dirs = {e: sum(1 for r in rows for f in cells_all.get(r["study_id"], {}).get("union", []) if (r["study_id"], f, e) in done) for e in ENGINES}
    grids = sum(grid_path_of(r).is_file() for r in rows)
    fails = sum(not bool(r.get("ok")) for r in raw)
    meshes_done = sum(1 for r in rows if cells_all.get(r["study_id"]) and all((r["study_id"], f, e) in done for f in cells_all[r["study_id"]]["union"] for e in ENGINES))
    print(f"scored {scored}/{len(rows)} | directions cura {done_dirs['cura_5_13']}/{total_dirs} prusa {done_dirs['prusa_2_9_6']}/{total_dirs} | meshes fully sliced {meshes_done}/{len(rows)} | failed rows {fails} | grids {grids}/{len(rows)}")


def cmd_smoke(jobs: int) -> None:
    dev = MESH_ROOT / "(4)Bunny_69k.stl"
    row = {"study_id": "SMOKE_bunny", "relative_path": dev.name, "sha256": sha256_file(dev), "face_count": 0, "thingi_id": "", "source_set": "dev", "stratum": "dev"}
    mesh = load_mesh(dev)
    t0 = time.perf_counter()
    directions = base.fibonacci_directions(CANDIDATE_COUNT)
    s8192, k8192, t8192 = base.evaluate_v2_arrays(mesh, directions, 8192)
    sc = {"directions": directions, "scores_8192": s8192, "scores_4096": s8192, "skew_8192": k8192}
    pc = policy_cells(sc)
    print(f"score K8192 {t8192:.2f}s; union {len(pc['union'])} cells; uniform10={pc['uniform'][10]} sftf10={pc['sftf'][10]}")
    mesh.apply_scale(TARGET_DIAGONAL_MM / float(np.linalg.norm(mesh.extents)))
    cura = CuraSlicer(engine="modern", critical_angle=CURA_ANGLE)
    print("cura engine:", cura.curaengine)
    for flat in pc["union"][:2]:
        out = slice_direction(mesh, "SMOKE_bunny", flat, cura)
        for r in out:
            print(f"  {r['engine']} flat={flat} ok={r['ok']} support={r['support_volume_mm3']:.1f} mm3 {r['elapsed_wall_s']:.1f}s err={r['error'][:80]}")
    print(f"smoke done in {time.perf_counter()-t0:.1f}s")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase", choices=["score", "slice", "tomo", "analyze", "status", "smoke", "all"])
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--ids", nargs="*", default=[])
    args = ap.parse_args()
    if args.phase == "smoke":
        cmd_smoke(args.jobs); return
    rows = load_manifest()
    if args.ids:
        want = {v.upper() for v in args.ids}; rows = [r for r in rows if r["study_id"].upper() in want]
    if args.phase in ("score", "all"):
        cmd_score(rows)
    if args.phase in ("slice", "all"):
        cmd_slice(rows, args.jobs)
    if args.phase in ("tomo", "all"):
        cmd_tomo(rows)
    if args.phase in ("analyze", "all"):
        cmd_analyze(rows)
    if args.phase == "status":
        cmd_status(rows)


if __name__ == "__main__":
    main()
