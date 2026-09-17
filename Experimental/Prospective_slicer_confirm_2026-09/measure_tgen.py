"""End-to-end SFTF candidate-generation time on the 60 holdout meshes (sequential, one process).

Motivated by the 2026-09-17 internal review: the 4.57 s reported in the submitted
manuscript is the K = 8,192 per-direction scoring loop only (evaluate_v2_arrays starts
its timer after surface sampling and stops before NMS and cell expansion). This script
times every stage the hybrid / ungated policy actually needs, per mesh:

  sample   deterministic_surface_samples(mesh, 8192)
  score    evaluate_sftf_v2 over 2,048 Fibonacci directions with the K = 8,192 sample
  nms      24 basins at 12 deg
  cells    canonical 1-degree cells + expand_around_basins to 2,400 (top-20/top-5 are prefixes)
  gate     (separately) the K = 4,096 sample + scoring needed only by the gated selective policy
  uniform  uniform_cells(5), (10), (20) for the baseline (for completeness)

Mesh loading is excluded (both policies load the mesh once). Results: tgen_measurement.json
"""
import csv, hashlib, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LEGACY = ROOT / "draft" / "src" / "legacy" / "TDP_v2"
for p in (str(ROOT / "python_src"), str(LEGACY / "scripts")):
    sys.path.insert(0, p)
import analyze_tdp_v2_tomo_external as base  # noqa: E402
from SupportFlowTensorField.sftf_v2 import SFTFV2Config, deterministic_surface_samples, evaluate_sftf_v2  # noqa: E402

MESH_ROOT = Path(r"D:\__SFTF_Projects(2026)\sftf_Mesh_Data")
MANIFEST = LEGACY / "experiments" / "tdp_v2" / "manifests" / "holdout_manifest.csv"
LATTICE = np.arange(0.0, 361.0, 1.0)
OUT = HERE / "tgen_measurement.json"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    with MANIFEST.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    directions = base.fibonacci_directions(2048)
    cfg8 = SFTFV2Config(sample_count=8192, critical_angle_deg=60.0)
    cfg4 = SFTFV2Config(sample_count=4096, critical_angle_deg=60.0)
    records = []
    t_all = time.perf_counter()
    for i, r in enumerate(rows, start=1):
        path = MESH_ROOT / r["relative_path"]
        assert sha256_file(path) == r["sha256"].lower(), r["holdout_id"]
        mesh = trimesh.load_mesh(str(path), force="mesh", process=False)
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)
        # --- ungated / hybrid path: one continuous outer timer around every stage the policy needs ---
        t_outer0 = time.perf_counter()
        t0 = time.perf_counter(); surf = deterministic_surface_samples(mesh, 8192); t_sample = time.perf_counter() - t0
        t0 = time.perf_counter(); vals = [evaluate_sftf_v2(mesh, d, config=cfg8, samples=surf) for d in directions]
        scores = np.asarray([v.score for v in vals], dtype=np.float64); skew = np.asarray([v.skew_ratio for v in vals], dtype=np.float64)
        t_score = time.perf_counter() - t0
        t0 = time.perf_counter(); basins = base.nms_basins(directions, scores); t_nms = time.perf_counter() - t0
        t0 = time.perf_counter()
        cf, cd = base.canonical_grid_cells(LATTICE, LATTICE)
        cells2400 = base.expand_around_basins(directions[basins], cf, cd, 2400)
        t_cells = time.perf_counter() - t0
        t_gen_outer = time.perf_counter() - t_outer0
        # --- gated selective policy: the additional K=4,096 pass plus the gate diagnostics themselves ---
        t_outer1 = time.perf_counter()
        surf4 = deterministic_surface_samples(mesh, 4096)
        vals4 = [evaluate_sftf_v2(mesh, d, config=cfg4, samples=surf4) for d in directions]
        scores4 = np.asarray([v.score for v in vals4], dtype=np.float64)
        b4 = base.nms_basins(directions, scores4)
        align = np.max(directions[basins] @ directions[b4].T, axis=1)
        stability = float(np.degrees(np.mean(np.arccos(np.clip(align, -1.0, 1.0)))))
        med = float(np.median(scores)); dispersion = float((np.percentile(scores, 90) - np.percentile(scores, 10)) / max(abs(med), 1e-12))
        top_skew = float(np.median(skew[basins[:8]]))
        accepted = bool(stability <= 15.0 and dispersion >= 0.08 and top_skew <= 1.0)
        t_gate_full = time.perf_counter() - t_outer1
        t0 = time.perf_counter(); u = [base.uniform_cells(LATTICE, LATTICE, b) for b in (5, 10, 20)]; t_uniform = time.perf_counter() - t0
        rec = {"holdout_id": r["holdout_id"], "stratum": r["stratum"], "face_count": int(r["face_count"]),
               "t_sample_8192_s": t_sample, "t_score_8192_s": t_score, "t_nms_s": t_nms, "t_cells_2400_s": t_cells,
               "t_uniform_cells_s": t_uniform,
               "t_gen_ungated_s": t_gen_outer,                       # continuous outer timer (sampling -> scoring -> NMS -> cell expansion)
               "t_gate_4096_sample_and_score_s": t_gate_full,        # K=4,096 sampling + scoring + NMS + cross-K alignment + gate diagnostics
               "t_gen_gated_s": t_gen_outer + t_gate_full,
               "gate_accepted": accepted, "n_cells_2400": int(len(cells2400))}
        records.append(rec)
        print(f"[{i}/{len(rows)}] {r['holdout_id']} faces={r['face_count']} sample={t_sample:.2f} score={t_score:.2f} nms={t_nms:.3f} cells={t_cells:.2f} gate={t_gate_full:.2f} -> T_gen(outer)={rec['t_gen_ungated_s']:.2f}s gated={rec['t_gen_gated_s']:.2f}s", flush=True)
    def agg(key):
        a = np.array([x[key] for x in records]); return {"mean": float(a.mean()), "median": float(np.median(a)), "min": float(a.min()), "max": float(a.max())}
    summary = {k: agg(k) for k in ("t_sample_8192_s", "t_score_8192_s", "t_nms_s", "t_cells_2400_s", "t_uniform_cells_s",
                                    "t_gate_4096_sample_and_score_s", "t_gen_ungated_s", "t_gen_gated_s")}
    cx = [x for x in records if x["stratum"] in ("faces_50k_150k", "faces_150k_250k")]
    summary["t_gen_ungated_s_complex25"] = {"mean": float(np.mean([x["t_gen_ungated_s"] for x in cx])), "max": float(np.max([x["t_gen_ungated_s"] for x in cx]))}
    payload = {"measured_utc": datetime.now(timezone.utc).isoformat(), "wall_total_s": time.perf_counter() - t_all,
               "note": "Sequential single-process run on the workstation of the manuscript; see cpu_load_note. Mesh loading excluded. "
                       "t_gen_ungated_s is one continuous timer around sampling, K=8,192 scoring, NMS and cell expansion (the hybrid/ungated path); "
                       "t_gate_4096_sample_and_score_s covers the extra K=4,096 sampling+scoring plus NMS, cross-K alignment and the gate diagnostics. "
                       "The submitted manuscript's 4.57 s corresponds to t_score_8192_s only.",
               "cpu_load_note": os.environ.get("TGEN_LOAD_NOTE", ""), "summary": summary, "records": records}
    out_path = Path(os.environ.get("TGEN_OUT", str(OUT)))
    out_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
