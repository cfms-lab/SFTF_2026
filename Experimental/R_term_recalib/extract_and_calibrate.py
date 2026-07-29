"""R-term recalibration study: why SFTF v2 under-credits internal landings.

Hypothesis (from the Bunny Io-basin diagnosis): TOMO v_ss counts the support
material between an overhang and its receiver, i.e. a HIT-VOLUME term
E[I_hit * O * h].  SFTF v2 routes hit samples only into the attenuated
Rayleigh tensor, whose magnitude is ~1/100 of the bed term, so the score is
effectively a plate-only estimate.

Per direction this script extracts sufficient statistics from ONE ray pass:

    F_hm  = E[I_hit O]        hit mass
    F_hv  = E[I_hit O h]      hit volume proxy      <-- the missing term
    F_bm  = E[I_bed O]        bed mass
    F_bv  = E[I_bed O h_bed]  bed volume proxy
    R     = current Rayleigh term (attenuated tensor contraction)

(current v2 score = R + F_bm + F_bv).  It then scores variant families
against the dense TOMO grid of each development mesh:

    V0 current      R + F_bm + F_bv
    V1 volume       F_hv + F_bv
    V2 vol+mass     F_hv + F_bv + a*(F_hm + F_bm)
    V3 current+hit  R + F_bm + F_bv + w*F_hv

Metrics per mesh: Spearman rank correlation with v_ss over the 2,048-direction
sweep, NRR of the rank-1 candidate, and the best NRR within the 24 NMS basins
(the paper's candidate set).  Usage:

    python extract_and_calibrate.py extract [--group C|D|E|all]
    python extract_and_calibrate.py analyze [--group C|D|E|all]
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "python_src"))

from SupportFlowTensorField.sftf_v2 import (  # noqa: E402
    SFTFV2Config,
    _first_receiver_hits,
    _unit,
    deterministic_surface_samples,
)

MESH_DIR = Path(r"D:\__SFTF_Projects(2026)\sftf_Mesh_Data\g5test")
ETC = PROJECT_ROOT / "Experimental" / "etc"
G5 = PROJECT_ROOT / "Experimental" / "G5Test"
OUT = HERE / "features"
OUT.mkdir(exist_ok=True)
NPZ_SUFFIX = "_tomo_int3_vss_grid_1deg_60deg.npz"
SAMPLE_COUNT = 8192
DIRECTION_COUNT = 2048

GROUP_C = {
    "Group_C1_Bunny_69k": ETC / f"(1)Bunny_69k{NPZ_SUFFIX}",
    "Group_C2_manikin": ETC / f"(2)manikin{NPZ_SUFFIX}",
    "Group_C3_dragon_100k_1.5x": ETC / f"(3)dragon_100k_1.5x{NPZ_SUFFIX}",
    "Group_C4_happy_50k_0.75x": ETC / f"(4)happy_50k_0.75x{NPZ_SUFFIX}",
    "Group_C5_lucy_50k": ETC / f"(5)lucy_50k{NPZ_SUFFIX}",
}


def fibonacci_directions(count: int) -> np.ndarray:
    i = np.arange(int(count), dtype=np.float64)
    z = 1.0 - 2.0 * (i + 0.5) / float(count)
    angle = 2.0 * np.pi * i / ((1.0 + math.sqrt(5.0)) * 0.5)
    radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    return np.column_stack((radius * np.cos(angle), radius * np.sin(angle), z))


def decode_bdata(bdata: str) -> np.ndarray:
    raw = bdata.encode("utf-8").decode("unicode_escape")
    return np.frombuffer(base64.b64decode(raw), dtype="<f8")


def grid_from_html(html_path: Path):
    s = html_path.read_text(encoding="utf-8", errors="replace")

    def arr(key):
        m = re.search(r'"%s":\{"dtype":"f8","bdata":"([^"]+)"(?:,"shape":"([^"]+)")?\}' % key, s)
        if not m:
            raise RuntimeError(f"{html_path.name}: no {key}")
        a = decode_bdata(m.group(1))
        if m.group(2):
            a = a.reshape(tuple(int(v) for v in m.group(2).replace(" ", "").split(",")))
        return a

    x, y, z = arr("x"), arr("y"), arr("z")
    if z.ndim == 1:
        z = z.reshape(len(y), len(x))
    return x, y, z


def grid_for(name: str):
    if name in GROUP_C:
        data = np.load(GROUP_C[name], allow_pickle=False)
        return (np.asarray(data["yaw_values"]), np.asarray(data["pitch_values"]),
                np.asarray(data["vss_grid"]))
    return grid_from_html(G5 / f"{name}_tomo_int3.html")


def mesh_path_for(name: str) -> Path | None:
    for ext in (".ply", ".stl", ".obj"):
        p = MESH_DIR / f"{name}{ext}"
        if p.exists():
            return p
    return None


def mesh_names(group: str) -> list[str]:
    if group == "C":
        return list(GROUP_C)
    names = []
    for html in sorted(G5.glob(f"Group_[{group}]*_tomo_int3.html")):
        name = html.name[: -len("_tomo_int3.html")]
        if mesh_path_for(name) is not None:
            names.append(name)
    return names


def extract_features(name: str) -> Path:
    """One ray pass per direction -> sufficient statistics + current R."""
    out_path = OUT / f"{name}_features.npz"
    if out_path.exists():
        print(f"[skip] {name} (cached)")
        return out_path
    mesh = trimesh.load_mesh(str(mesh_path_for(name)), force="mesh", process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)
    settings = SFTFV2Config(sample_count=SAMPLE_COUNT, critical_angle_deg=60.0)
    surface = deterministic_surface_samples(mesh, SAMPLE_COUNT)
    directions = fibonacci_directions(DIRECTION_COUNT)
    total = len(surface.points)
    threshold = float(np.cos(np.deg2rad(settings.critical_angle_deg)))
    face_normals = np.asarray(mesh.face_normals, dtype=np.float64)
    vertices = np.asarray(mesh.vertices, dtype=np.float64)

    cols = {k: np.zeros(DIRECTION_COUNT) for k in
            ("F_hm", "F_hv", "F_bm", "F_bv", "R", "hit_frac", "active_frac")}
    started = time.perf_counter()
    for di, direction in enumerate(directions):
        n = _unit(direction)
        overhang_all = np.maximum(0.0, -(surface.normals @ n))
        active = (overhang_all > 0.0) & (overhang_all >= threshold)
        ids = np.flatnonzero(active)
        if ids.size == 0:
            continue
        receiver_ids, pair_heights = _first_receiver_hits(
            mesh, surface.points[ids], surface.face_ids[ids], n,
            diameter=surface.diameter,
            receiver_normal_min=settings.receiver_normal_min,
            ray_epsilon_scale=settings.ray_epsilon_scale,
        )
        hit = receiver_ids >= 0
        O = overhang_all[ids]
        h = np.zeros(ids.size)
        if np.any(hit):
            h[hit] = pair_heights[hit] / surface.diameter
        bed = ~hit
        if np.any(bed):
            floor = float(np.min(vertices @ n))
            h[bed] = np.maximum(0.0, (surface.points[ids][bed] @ n - floor) / surface.diameter)

        cols["F_hm"][di] = float(np.sum(O[hit]) / total)
        cols["F_hv"][di] = float(np.sum(O[hit] * h[hit]) / total)
        cols["F_bm"][di] = float(np.sum(O[bed]) / total)
        cols["F_bv"][di] = float(np.sum(O[bed] * h[bed]) / total)
        cols["hit_frac"][di] = float(np.mean(hit))
        cols["active_frac"][di] = ids.size / total
        if np.any(hit):
            w = O[hit] / (1.0 + h[hit])
            tensor = np.einsum("i,ij,ik->jk", w / total,
                               surface.normals[ids][hit], face_normals[receiver_ids[hit]])
            sym = 0.5 * (tensor + tensor.T)
            cols["R"][di] = max(0.0, -float(n @ sym @ n))
    elapsed = time.perf_counter() - started

    yaw, pitch, grid = grid_for(name)
    pitch_t = (-np.degrees(np.arcsin(np.clip(directions[:, 0], -1, 1)))) % 360.0
    yaw_t = np.degrees(np.arctan2(directions[:, 1], directions[:, 2])) % 360.0
    yi = np.argmin(np.abs((yaw[None, :] - yaw_t[:, None] + 180.0) % 360.0 - 180.0), axis=1)
    pi = np.argmin(np.abs((pitch[None, :] - pitch_t[:, None] + 180.0) % 360.0 - 180.0), axis=1)
    vss = grid[pi, yi]
    gmin, gmax = float(grid.min()), float(grid.max())
    nrr = (vss - gmin) / max(gmax - gmin, 1e-12)

    np.savez_compressed(out_path, directions=directions, vss=vss, nrr=nrr,
                        grid_min=gmin, grid_max=gmax, elapsed_s=elapsed, **cols)
    print(f"[done] {name}: {elapsed:.1f}s")
    return out_path


# ---------------- analysis ----------------

def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a)).astype(np.float64)
    rb = np.argsort(np.argsort(b)).astype(np.float64)
    ra -= ra.mean(); rb -= rb.mean()
    d = float(np.sqrt(np.sum(ra * ra) * np.sum(rb * rb)))
    return float(np.sum(ra * rb) / d) if d > 0 else float("nan")


def nms_basins(directions, scores, count=24, sep_deg=12.0):
    order = np.lexsort((np.arange(len(scores)), scores))
    cos = np.cos(np.deg2rad(sep_deg))
    sel = []
    for idx in order:
        d = directions[int(idx)]
        if sel and np.max(directions[sel] @ d) > cos:
            continue
        sel.append(int(idx))
        if len(sel) >= count:
            break
    return np.asarray(sel)


def variant_metrics(name, data, score):
    directions = data["directions"]
    nrr = data["nrr"]
    rho = spearman(score, data["vss"])
    top1 = float(nrr[int(np.lexsort((np.arange(len(score)), score))[0])])
    basins = nms_basins(directions, score)
    basin_best = float(np.min(nrr[basins]))
    return rho, top1, basin_best


def analyze(names: list[str]) -> None:
    rows = []
    for name in names:
        path = OUT / f"{name}_features.npz"
        if not path.exists():
            print(f"[missing] {name}")
            continue
        d = np.load(path, allow_pickle=False)
        F_hm, F_hv = d["F_hm"], d["F_hv"]
        F_bm, F_bv = d["F_bm"], d["F_bv"]
        R = d["R"]
        variants = {
            "V0 current (R+Bm+Bv)": R + F_bm + F_bv,
            "V1 volume (Hv+Bv)": F_hv + F_bv,
            "V2 vol+0.25*mass": F_hv + F_bv + 0.25 * (F_hm + F_bm),
            "V3 current+5*Hv": R + F_bm + F_bv + 5.0 * F_hv,
            "V3 current+1*Hv": R + F_bm + F_bv + 1.0 * F_hv,
            "F_bv only": F_bv.copy(),
            "F_hv only": F_hv.copy(),
        }
        print(f"=== {name} ===")
        print("  feature Spearman vs vss:  "
              + "  ".join(f"{k}={spearman(d[k], d['vss']):+.3f}"
                          for k in ("F_hm", "F_hv", "F_bm", "F_bv", "R")))
        for label, score in variants.items():
            rho, top1, basin = variant_metrics(name, d, score)
            rows.append({"mesh": name, "variant": label, "spearman": round(rho, 4),
                         "top1_nrr": round(top1, 4), "basin24_best_nrr": round(basin, 4)})
            print(f"  {label:24s} rho {rho:+.3f}  top1-NRR {top1:.3f}  basin24 {basin:.4f}")
    # summary means per variant
    print()
    print("== mean over meshes ==")
    labels = sorted({r["variant"] for r in rows})
    for label in labels:
        sub = [r for r in rows if r["variant"] == label]
        print(f"  {label:24s} rho {np.mean([r['spearman'] for r in sub]):+.3f}  "
              f"top1 {np.mean([r['top1_nrr'] for r in sub]):.3f}  "
              f"basin24 {np.mean([r['basin24_best_nrr'] for r in sub]):.4f}  (n={len(sub)})")
    (HERE / "calibration_results.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["extract", "analyze"])
    parser.add_argument("--group", default="C", choices=["C", "D", "E", "all"])
    args = parser.parse_args()
    groups = ["C", "D", "E"] if args.group == "all" else [args.group]
    names = [n for g in groups for n in mesh_names(g)]
    if args.mode == "extract":
        for name in names:
            extract_features(name)
    else:
        analyze(names)


if __name__ == "__main__":
    main()
