"""Part 2 of GATE_2026-09-16: hybrid (uniform-5 + SFTF top-5) versus uniform-10 on the 30-mesh
holdout slicer panel, recomputed from the raw inputs. Self-contained reproduction of the
pre-specified analysis whose result is stored in part2_mixed_policy_holdout30.json.

Inputs (all in inputs_part2/ of this folder in the public repository, or in the development
snapshot draft/src/legacy/TDP_v2/experiments/tdp_v2/):
  budget_slicer_raw.jsonl           per-direction Cura/Prusa support volumes of the original
                                    small-budget slicer study (uniform 5/10/20 and SFTF top-20 cells)
  sftf_candidate_cache/H*.npz       SFTF v2 scores (scores_8192) on 2,048 Fibonacci directions
  holdout_manifest.csv              the 60-mesh holdout manifest (cross_slicer flag selects the 30)

Cells are rebuilt with the same functions as the original study (copied verbatim below), on the
1-degree yaw-pitch lattice; NRR uses, per mesh and engine, the min/max over all successfully
sliced cells of that mesh (finite-panel reference). Seeds: Cura 20260919, Prusa 20260920.

Note on provenance: the stored part2 JSON was produced on 2026-09-17 by an inline script with
this exact logic; this file saves that logic so that reviewers can rerun it with one command:
    python analyze_part2.py [--inputs inputs_part2] [--manifest ../../experiments/tdp_v2/manifests/holdout_manifest.csv]
"""
from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ENGINES = ("cura_5_13", "prusa_2_9_6")
LATTICE = np.arange(0.0, 361.0, 1.0)
COMPLEX = ("faces_50k_150k", "faces_150k_250k")


# ---- helper functions copied from draft/src/legacy/TDP_v2/scripts/analyze_tdp_v2_tomo_external.py ----
def fibonacci_directions(count):
    i = np.arange(int(count), dtype=np.float64)
    z = 1.0 - 2.0 * (i + 0.5) / float(count)
    angle = 2.0 * np.pi * i / ((1.0 + math.sqrt(5.0)) * 0.5)
    radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    return np.column_stack((radius * np.cos(angle), radius * np.sin(angle), z))


def grid_direction_vectors(yaw_deg, pitch_deg):
    yaw = np.deg2rad(np.rint(np.asarray(yaw_deg, dtype=np.float64)))[None, :]
    pitch = np.deg2rad(np.rint(np.asarray(pitch_deg, dtype=np.float64)))[:, None]
    sin_p = np.sin(pitch); cos_p = np.cos(pitch); sin_y = np.sin(yaw); cos_y = np.cos(yaw)
    x = np.broadcast_to(-sin_p, (len(pitch_deg), len(yaw_deg))); y = cos_p * sin_y; z = cos_p * cos_y
    return np.stack((x, y, z), axis=-1).reshape(-1, 3)


def canonical_grid_cells(yaw_deg, pitch_deg):
    directions = grid_direction_vectors(yaw_deg, pitch_deg)
    _unique, first = np.unique(np.round(directions, 8), axis=0, return_index=True)
    flat = np.sort(first.astype(np.int64))
    return flat, directions[flat]


def nearest_grid_flat(direction, yaw_deg, pitch_deg):
    unit = np.asarray(direction, dtype=np.float64); unit /= max(float(np.linalg.norm(unit)), 1.0e-15)
    pitch_target = (-math.degrees(math.asin(float(np.clip(unit[0], -1.0, 1.0))))) % 360.0
    yaw_target = math.degrees(math.atan2(float(unit[1]), float(unit[2]))) % 360.0
    def nearest(values, target):
        delta = np.abs((np.asarray(values) - target + 180.0) % 360.0 - 180.0); return int(np.argmin(delta))
    return nearest(pitch_deg, pitch_target) * len(yaw_deg) + nearest(yaw_deg, yaw_target)


def nms_basins(directions, scores, *, count=24, separation_deg=12.0):
    order = np.lexsort((np.arange(len(scores), dtype=np.int64), scores))
    cosine = math.cos(math.radians(float(separation_deg))); selected = []
    for index in order:
        direction = directions[int(index)]
        if selected and np.max(directions[selected] @ direction) > cosine:
            continue
        selected.append(int(index))
        if len(selected) >= int(count):
            break
    return np.asarray(selected, dtype=np.int64)


def expand_around_basins(basin_directions, canonical_flat, canonical_directions, budget):
    proximity = np.max(canonical_directions @ basin_directions.T, axis=1)
    order = np.lexsort((canonical_flat, -proximity))
    return canonical_flat[order[: int(budget)]]


def uniform_cells(yaw_deg, pitch_deg, budget):
    selected = []; seen = set()
    for count in (int(budget), int(budget) * 4, int(budget) * 8):
        for direction in fibonacci_directions(count):
            flat = nearest_grid_flat(direction, yaw_deg, pitch_deg)
            if flat in seen:
                continue
            seen.add(flat); selected.append(flat)
            if len(selected) >= int(budget):
                return np.asarray(selected, dtype=np.int64)
    raise RuntimeError("could not map uniform cells")
# ---------------------------------------------------------------------------------------------


def nrr(v, lo, hi):
    return 0.0 if abs(hi - lo) <= 1e-12 else (v - lo) / (hi - lo)


def stats(d, seed, n_boot=10000, n_perm=100000):
    d = np.asarray(d, float); r = np.random.default_rng(seed)
    idx = r.integers(0, len(d), size=(n_boot, len(d))); b = d[idx].mean(1)
    signs = r.choice([-1.0, 1.0], size=(n_perm, len(d))); perm = (signs * d[None, :]).mean(1); obs = d.mean()
    return {"n": int(len(d)), "mean": float(obs), "median": float(np.median(d)), "sd": float(d.std(ddof=1)) if len(d) > 1 else None,
            "ci": [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))],
            "p": float((1 + np.sum(np.abs(perm) >= abs(obs) - 1e-15)) / (n_perm + 1)),
            "wtl": [int((d < -1e-9).sum()), int((np.abs(d) <= 1e-9).sum()), int((d > 1e-9).sum())]}


def holm(pvals):
    items = sorted(pvals.items(), key=lambda kv: kv[1]); m = len(items); adj = {}; run = 0.0
    for k, (name, p) in enumerate(items):
        run = max(run, min(1.0, (m - k) * p)); adj[name] = run
    return adj


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path, default=HERE / "inputs_part2")
    ap.add_argument("--manifest", type=Path, default=HERE.parents[1] / "draft/src/legacy/TDP_v2/experiments/tdp_v2/manifests/holdout_manifest.csv")
    ap.add_argument("--out", type=Path, default=HERE / "part2_mixed_policy_holdout30_reproduced.json")
    args = ap.parse_args()
    with args.manifest.open(newline="", encoding="utf-8") as fh:
        manifest = [r for r in csv.DictReader(fh)]
    sel = [m for m in manifest if m["cross_slicer"].lower() == "true"]
    raw = [json.loads(l) for l in (args.inputs / "budget_slicer_raw.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    latest = {}
    for r in raw:
        if r.get("ok") and np.isfinite(float(r["support_volume_mm3"])):
            latest[(r["holdout_id"], r["engine"], int(r["grid_flat"]))] = float(r["support_volume_mm3"])
    directions = fibonacci_directions(2048)
    cf, cd = canonical_grid_cells(LATTICE, LATTICE)
    u_by = {b: [int(c) for c in uniform_cells(LATTICE, LATTICE, b)] for b in (5, 10, 20)}
    rows = []
    for m in sel:
        hid = m["holdout_id"]
        with np.load(args.inputs / "sftf_candidate_cache" / f"{hid}.npz", allow_pickle=False) as z:
            s8192 = np.asarray(z["scores_8192"], dtype=np.float64)
        sftf20 = [int(c) for c in expand_around_basins(directions[nms_basins(directions, s8192)], cf, cd, 20)]
        e = {"holdout_id": hid, "stratum": m["stratum"], "face_count": int(m["face_count"])}
        for eng in ENGINES:
            sup = {f: v for (h, en, f), v in latest.items() if h == hid and en == eng}
            lo, hi = min(sup.values()), max(sup.values())
            best = lambda cells: [sup[c] for c in cells if c in sup]
            u5, u10, u20, s5, s10 = best(u_by[5]), best(u_by[10]), best(u_by[20]), best(sftf20[:5]), best(sftf20[:10])
            e[f"{eng}_u10"] = nrr(min(u10), lo, hi); e[f"{eng}_s10"] = nrr(min(s10), lo, hi); e[f"{eng}_mix10"] = nrr(min(u5 + s5), lo, hi)
            e[f"{eng}_u20"] = nrr(min(u20), lo, hi); e[f"{eng}_mix20"] = nrr(min(u10 + s10), lo, hi)
            e[f"{eng}_missing"] = sum(c not in sup for c in u_by[5] + u_by[10] + sftf20[:10])
            e[f"{eng}_hybrid_cells_distinct"] = len(set(u_by[5]) | set(sftf20[:5]))
        rows.append(e)
    pv = {}; prim = {}
    for eng, seed in (("cura_5_13", 20260919), ("prusa_2_9_6", 20260920)):
        prim[eng] = stats([e[f"{eng}_mix10"] - e[f"{eng}_u10"] for e in rows], seed); pv[eng] = prim[eng]["p"]
    hm = holm(pv)
    verdict = {eng: ("criterion met" if (prim[eng]["mean"] < 0 and hm[eng] < 0.05) else "criterion not met") for eng in ENGINES}
    sec = {}
    for eng in ENGINES:
        cx = [e for e in rows if e["stratum"] in COMPLEX]
        sec[f"{eng} complex12 mix10-u10"] = stats([e[f"{eng}_mix10"] - e[f"{eng}_u10"] for e in cx], 1)
        sec[f"{eng} all30 mix20-u20"] = stats([e[f"{eng}_mix20"] - e[f"{eng}_u20"] for e in rows], 1)
        sec[f"{eng} all30 mix10-s10"] = stats([e[f"{eng}_mix10"] - e[f"{eng}_s10"] for e in rows], 1)
        sec[f"{eng} all30 s10-u10 (paper)"] = stats([e[f"{eng}_s10"] - e[f"{eng}_u10"] for e in rows], 1)
    out = {"rows": rows, "primary": prim, "holm": hm, "verdict": verdict, "secondary": sec,
           "missing_cells_total": {eng: int(sum(e[f"{eng}_missing"] for e in rows)) for eng in ENGINES}}
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    for eng in ENGINES:
        p = prim[eng]
        print(f"{eng}: n={p['n']} mean={p['mean']:+.7f} CI=[{p['ci'][0]:+.7f},{p['ci'][1]:+.7f}] p={p['p']:.7f} Holm={hm[eng]:.7f} w/t/l={p['wtl']} missing={out['missing_cells_total'][eng]} -> {verdict[eng]}")
    # compare with the stored file if present
    stored = HERE / "part2_mixed_policy_holdout30.json"
    if stored.is_file():
        S = json.loads(stored.read_text(encoding="utf-8")); srows = {e["holdout_id"]: e for e in S["rows"]}
        maxdiff = max(abs(e[f"{eng}_{k}"] - srows[e["holdout_id"]][f"{eng}_{k}"]) for e in rows for eng in ENGINES for k in ("u10", "s10", "mix10", "u20", "mix20"))
        print(f"max |difference| versus stored part2 JSON per-mesh values: {maxdiff:.2e}")


if __name__ == "__main__":
    main()
