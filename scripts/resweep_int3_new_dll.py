"""Re-sweep every stored tomo_int3 grid with the int16-overflow-fixed dll.

Background: the pre-2026-07-03 Tomo_Shell2026.dll accumulated per-slot voxel
z-sums in int16 (SLOT_BUFFER_TYPE). Large/complex columns wrapped, poisoning
v_ss for the big E-group meshes (negative-million best values) and shifting
values on ordinary meshes too (a full 256-high column sums to 32,640 -- right
at the int16 edge). The fixed dll (SLOT_SUM_TYPE=int32 accumulators, separate
SlotVo_32i/SlotVss_32i totals) changes every stored INT3 grid, so all of them
are recomputed here. See Tomo_Shell2026-dev/BUGREPORT_2026-07-03_INT16_vss_overflow.md.

Per cache npz (every `{stem}_tomo_int3_{step}deg_{ca}deg.npz`):
  * skipped when already marked `dll_int32fix` (re-run safe);
  * otherwise re-swept with the current dll and overwritten in place
    (keys unchanged + markers `regenerated`, `dll_int32fix`); dll_sec is the
    fresh wall time -- this run doubles as the single-session t_CPU re-timing
    for Supplementary S1, so run on an otherwise idle machine.
For the record combo (JSON angle_step/critical_angle, 1deg/60deg) the contour
HTML and the JSON tomo_int3_* fields are refreshed.

Orphan grids whose mesh no longer exists (old-roster E2_45809/E3_45811/
E4_46012) are left untouched and reported.

CUDA grids are deliberately NOT re-swept: the CUDA kernel race (zero cells,
run-to-run nondeterminism) and the large-mesh slowdown are still open.

Usage: python scripts/resweep_int3_new_dll.py [stem ...]
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import scripts.G5Test as g5  # noqa: E402
from cpp_src.Tomo_GPU2026.tomo_cpu import compute_tomo_cpu_vss_grid, tomo_best_row  # noqa: E402
from scripts._mesh_paths import G5_RAW_MESH  # noqa: E402

OUT_DIR = PROJECT_ROOT / "Experimental" / "G5Test"
SFTF_RESULT_DIR = OUT_DIR / "SFTF_result"
INT3_CACHE = OUT_DIR / "tomo_int3_cache"
MESH_DIR = G5_RAW_MESH

CACHE_RE = re.compile(r"^(?P<stem>.+)_tomo_int3_(?P<step>[0-9p.]+)deg_(?P<ca>[0-9p.]+)deg\.npz$")
MESH_EXTS = {".stl", ".obj", ".ply", ".off", ".3mf", ".glb"}


def mesh_path_for(stem: str) -> Path | None:
    matches = sorted(p for p in MESH_DIR.glob(stem + ".*") if p.suffix.lower() in MESH_EXTS)
    return matches[0] if matches else None


def main() -> None:
    only = set(sys.argv[1:])

    jobs: dict[str, list[tuple[float, float, Path]]] = {}
    for npz_path in sorted(INT3_CACHE.glob("*_tomo_int3_*deg_*deg.npz")):
        m = CACHE_RE.match(npz_path.name)
        if not m:
            print(f"[skip] unrecognized cache name {npz_path.name}", flush=True)
            continue
        stem = m.group("stem")
        if only and stem not in only:
            continue
        step = float(m.group("step").replace("p", "."))
        ca = float(m.group("ca").replace("p", "."))
        jobs.setdefault(stem, []).append((step, ca, npz_path))

    for stem in sorted(jobs):  # A -> E: cheap groups land first
        mesh_path = mesh_path_for(stem)
        if mesh_path is None:
            print(f"== {stem}: ORPHAN (mesh not in roster), left untouched ==", flush=True)
            continue
        print(f"== {stem} ({mesh_path.name}) ==", flush=True)

        json_path = SFTF_RESULT_DIR / f"{stem}.json"
        record = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else None
        rec_step = float(record.get("angle_step_deg") or 1.0) if record else 1.0
        rec_ca = float(record.get("critical_angle_deg") or 60.0) if record else 60.0

        for step, ca, npz_path in sorted(jobs[stem], key=lambda c: (-c[0], c[1])):
            try:
                with np.load(npz_path, allow_pickle=False) as old:
                    if "dll_int32fix" in old.files:
                        print(f"  [tomo_int3 {step:g}deg/{ca:g}deg] already re-swept; skip", flush=True)
                        continue
            except Exception:
                pass  # unreadable -> recompute

            start = time.perf_counter()
            try:
                tomo = compute_tomo_cpu_vss_grid(mesh_path, critical_angle=ca, angle_step=step)
            except Exception as exc:
                print(f"  [tomo_int3 {step:g}deg/{ca:g}deg] FAILED: {type(exc).__name__}: {exc}", flush=True)
                if record is not None and (step, ca) == (rec_step, rec_ca):
                    record["tomo_int3_error"] = f"{type(exc).__name__}: {exc}"
                    json_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
                continue
            dll_sec = time.perf_counter() - start
            yaw = np.asarray(tomo["yaw_values"], dtype=np.float64)
            pitch = np.asarray(tomo["pitch_values"], dtype=np.float64)
            grid = np.asarray(tomo["vss_grid"], dtype=np.float64)
            np.savez_compressed(npz_path, yaw_values=yaw, pitch_values=pitch,
                                vss_grid=grid, dll_sec=np.float64(dll_sec),
                                regenerated=np.int8(1), dll_int32fix=np.int8(1))
            best = tomo_best_row(yaw, pitch, grid)
            print(f"  [tomo_int3 {step:g}deg/{ca:g}deg] {dll_sec:.1f}s "
                  f"best vss={best['vss']:.6g} yaw={best['yaw']:.1f} pitch={best['pitch']:.1f} "
                  f"negatives={(grid < 0).sum()}", flush=True)

            if record is not None and (step, ca) == (rec_step, rec_ca):
                fig = g5.build_tomo_contour_figure(stem, yaw, pitch, grid, method="TOMO_CPU")
                fig.write_html(OUT_DIR / f"{stem}_tomo_int3.html", include_plotlyjs="cdn")
                record.update({
                    "tomo_int3_dll_sec": dll_sec, "tomo_int3_cached": False,
                    "tomo_int3_html": f"{stem}_tomo_int3.html",
                    "tomo_int3_best": best, "tomo_int3_error": None,
                })
                json_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

    print("RESWEEP DONE", flush=True)


if __name__ == "__main__":
    main()
