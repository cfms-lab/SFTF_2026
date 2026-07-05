"""Phase B onboarding: TOMO_CUDA sweeps for the swapped-in E-group meshes,
plus the stale Group_E8_64445 CUDA grids left from the inverted-mesh repair.

Per stem the target combos are:
  * every existing `tomo_cuda_cache/{stem}_tomo_cuda_*deg_*deg.npz` not yet
    marked `regenerated` (covers E8's six stale grids), and
  * the record combo 1deg/60deg (covers the four new meshes with no cache,
    Supplementary S1 t_CUDA column).

For the record combo (angle_step_deg/critical_angle_deg from the JSON,
1deg/60deg) the contour HTML `{stem}_tomo_cuda.html` and the JSON
`tomo_cuda_*` fields are refreshed as well.

Incremental: npz marked `regenerated` are skipped, JSON is saved after each
stem, so the script can be interrupted and re-run safely. Run only on an
otherwise idle machine (S1 timing-session consistency) -- in particular NOT
while the Phase A CPU sweeps are still running.

Usage: python scripts/onboard_new_meshes_phaseB.py [stem ...]
       (no args = all five default stems)

NOTE: the local session saw the E8 CUDA 1deg sweep run 6h+ without finishing
(historical record 212 s) -- suspected large-mesh CUDA performance regression
in the new Tomo_Shell2026.dll. If a sweep stalls far beyond the historical
timing, interrupt and investigate rather than letting it spin.
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
from cpp_src.Tomo_GPU2026.tomo_cpu import (  # noqa: E402
    compute_tomo_cuda_vss_grid,
    tomo_best_row,
)

OUT_DIR = PROJECT_ROOT / "Experimental" / "G5Test"
SFTF_RESULT_DIR = OUT_DIR / "SFTF_result"
CUDA_CACHE = OUT_DIR / "tomo_cuda_cache"
MESH_DIR = PROJECT_ROOT.parent / "sftf_Mesh_Data" / "g5test"

# E8 last: its CUDA 1deg sweep is the known 6h+ regression risk, so it must
# not block the four new-roster meshes.
STEMS = [
    "Group_E2_790253",
    "Group_E3_931902",
    "Group_E4_439142",
    "Group_E9_82675",
    "Group_E8_64445",
]
CACHE_RE = re.compile(r"_tomo_cuda_([0-9p.]+)deg_([0-9p.]+)deg\.npz$")


def mesh_path_for(stem: str) -> Path:
    matches = sorted(p for p in MESH_DIR.glob(stem + ".*")
                     if p.suffix.lower() in {".stl", ".obj", ".ply"})
    if not matches:
        raise FileNotFoundError(stem)
    return matches[0]


def save_record(stem: str, record: dict) -> None:
    (SFTF_RESULT_DIR / f"{stem}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def target_combos(stem: str, rec_step: float, rec_ca: float) -> list[tuple[float, float]]:
    combos: dict[tuple[float, float], None] = {}
    for npz_path in sorted(CUDA_CACHE.glob(f"{stem}_tomo_cuda_*deg_*deg.npz")):
        m = CACHE_RE.search(npz_path.name)
        if m:
            combos[(float(m.group(1).replace("p", ".")),
                    float(m.group(2).replace("p", ".")))] = None
    combos[(rec_step, rec_ca)] = None
    # coarser (cheaper) sweeps first: early per-evaluation timing signal before
    # committing to the expensive 1deg sweep
    return sorted(combos, key=lambda c: (-c[0], c[1]))


def main() -> None:
    only = set(sys.argv[1:])
    for stem in STEMS:
        if only and stem not in only:
            continue
        try:
            mesh_path = mesh_path_for(stem)
        except FileNotFoundError:
            print(f"== {stem}: MESH NOT FOUND, skipping ==", flush=True)
            continue
        json_path = SFTF_RESULT_DIR / f"{stem}.json"
        record = json.loads(json_path.read_text(encoding="utf-8"))
        rec_step = float(record.get("angle_step_deg") or 1.0)
        rec_ca = float(record.get("critical_angle_deg") or 60.0)
        print(f"== {stem} ({mesh_path.name}) ==", flush=True)

        for step, ca in target_combos(stem, rec_step, rec_ca):
            npz_path = CUDA_CACHE / f"{stem}_tomo_cuda_{step:g}deg_{ca:g}deg.npz"
            grid = None
            dll_sec = None
            if npz_path.exists():
                try:
                    with np.load(npz_path, allow_pickle=False) as old:
                        if "regenerated" in old.files:
                            print(f"  [tomo_cuda {step:g}deg/{ca:g}deg] already regenerated; skip",
                                  flush=True)
                            grid = {k: np.asarray(old[k], dtype=np.float64)
                                    for k in ("yaw_values", "pitch_values", "vss_grid")}
                            dll_sec = float(old["dll_sec"]) if "dll_sec" in old.files else None
                except Exception:
                    grid = None  # unreadable -> recompute

            if grid is None:
                start = time.perf_counter()
                try:
                    tomo = compute_tomo_cuda_vss_grid(mesh_path, critical_angle=ca, angle_step=step)
                except Exception as exc:
                    print(f"  [tomo_cuda {step:g}deg/{ca:g}deg] FAILED: "
                          f"{type(exc).__name__}: {exc}", flush=True)
                    if (step, ca) == (rec_step, rec_ca):
                        record["tomo_cuda_error"] = f"{type(exc).__name__}: {exc}"
                        save_record(stem, record)
                    continue
                dll_sec = time.perf_counter() - start
                grid = {
                    "yaw_values": np.asarray(tomo["yaw_values"], dtype=np.float64),
                    "pitch_values": np.asarray(tomo["pitch_values"], dtype=np.float64),
                    "vss_grid": np.asarray(tomo["vss_grid"], dtype=np.float64),
                }
                np.savez_compressed(npz_path, **grid, dll_sec=np.float64(dll_sec),
                                    regenerated=np.int8(1))
                best = tomo_best_row(grid["yaw_values"], grid["pitch_values"], grid["vss_grid"])
                print(f"  [tomo_cuda {step:g}deg/{ca:g}deg] {dll_sec:.1f}s "
                      f"best vss={best['vss']:.6g} yaw={best['yaw']:.1f} pitch={best['pitch']:.1f}",
                      flush=True)

            if (step, ca) == (rec_step, rec_ca):
                fig = g5.build_tomo_contour_figure(
                    stem, grid["yaw_values"], grid["pitch_values"], grid["vss_grid"],
                    method="TOMO_CUDA")
                fig.write_html(OUT_DIR / f"{stem}_tomo_cuda.html", include_plotlyjs="cdn")
                record.update({
                    "tomo_cuda_dll_sec": dll_sec, "tomo_cuda_cached": False,
                    "tomo_cuda_html": f"{stem}_tomo_cuda.html",
                    "tomo_cuda_best": tomo_best_row(grid["yaw_values"], grid["pitch_values"],
                                                    grid["vss_grid"]),
                    "tomo_cuda_error": None,
                })
                save_record(stem, record)

    print("PHASE B DONE", flush=True)


if __name__ == "__main__":
    main()
