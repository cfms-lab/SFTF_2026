"""Sweep the five-group verification + capture over several critical angles.

For each critical angle in ANGLES this driver:

  1. runs ``G5Test.py`` (TOMO_CPU + TOMO_CUDA over groups
     A-E at that angle), which writes ``_5G_CA<angle>deg_4Method_table.html``
     and the per-angle ``.npz`` grid caches, then
  2. runs ``capture_five_group_best_worst_polyscope.py`` for that angle, writing
     ``_5G_CA<angle>deg_best_worst_polyscope.png``.

The SFTF methods ignore the critical angle (USE_CRITICAL_ANGLE is False in both
the Python and C++ SFTF modules), so their best/worst directions are computed
once up front (Phase 0) and reused; only the TOMO sweeps repeat per angle.

Resumable: completed angles are recorded in ``_5G_sweep_progress.json`` and
skipped on a re-run; within an angle the per-angle ``.npz`` caches make finished
meshes reload instantly. Subprocess output is teed to
``_5G_sweep_logs/CA<angle>deg_{verify,capture}.log``.

Run with the project venv python:
    .venv\\Scripts\\python.exe scripts\\run_five_group_all_angles.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "Experimental" / "G5Test"
LOG_DIR = OUT_DIR / "_5G_sweep_logs"
PROGRESS_PATH = OUT_DIR / "_5G_sweep_progress.json"

ANGLES = [0.0, 30.0, 45.0, 60.0, 90.0]
# Yaw/pitch sweep resolution (degrees). Coarser = far cheaper (cost ~ 1/step^2);
# embedded in the .npz cache key and the resume tag, so changing it forces a
# fresh sweep that does not collide with caches from a different step.
ANGLE_STEP = 3.0
GROUPS = "A,B,C,D,E"

VERIFY = PROJECT_ROOT / "scripts" / "G5Test.py"
CAPTURE = PROJECT_ROOT / "scripts" / "capture_five_group_best_worst_polyscope.py"


def angle_tag(angle: float) -> str:
    text = f"{float(angle):g}".replace("-", "m").replace(".", "p")
    return f"CA{text}deg"


def load_progress() -> dict:
    if PROGRESS_PATH.exists():
        try:
            return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"done": [], "phase0": False}


def save_progress(progress: dict) -> None:
    PROGRESS_PATH.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def run(cmd: list[str], env: dict, log_path: Path) -> None:
    """Run a subprocess, teeing combined stdout/stderr to a log file and the
    console. Raises CalledProcessError on non-zero exit."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"  $ {' '.join(cmd)}", flush=True)
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            cmd, env=env, cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            log.flush()
            sys.stdout.write(line)
            sys.stdout.flush()
        code = proc.wait()
    if code != 0:
        raise subprocess.CalledProcessError(code, cmd)


def main() -> None:
    progress = load_progress()
    overall_start = time.perf_counter()

    # --- Phase 0: ensure every mesh has angle-independent SFTF directions. ---
    if not progress.get("phase0"):
        print("=== Phase 0: fill missing SFTF (angle-independent) ===", flush=True)
        env = dict(os.environ)
        env.update({
            "FGV_GROUPS": GROUPS,
            "FGV_SFTF": "1", "FGV_SFTFCPP": "1",
            "FGV_CPU": "0", "FGV_CUDA": "0",
            "FGV_ONLY_MISSING": "1",  # only meshes still missing SFTF
        })
        run([sys.executable, str(VERIFY)], env, LOG_DIR / "phase0_sftf.log")
        progress["phase0"] = True
        save_progress(progress)
    else:
        print("=== Phase 0 already complete; skipping ===", flush=True)

    # --- Phase 1: per-angle TOMO sweep + capture. ---
    for angle in ANGLES:
        tag = angle_tag(angle)
        done_key = f"{tag}_step{ANGLE_STEP:g}"
        if done_key in progress.get("done", []):
            print(f"=== {done_key}: already complete; skipping ===", flush=True)
            continue
        print(f"\n=== {tag} @ {ANGLE_STEP:g}deg step: TOMO_CPU + TOMO_CUDA over groups {GROUPS} ===", flush=True)
        angle_start = time.perf_counter()

        env = dict(os.environ)
        env.update({
            "TOMO_CRITICAL_ANGLE": f"{angle:g}",
            "TOMO_ANGLE_STEP": f"{ANGLE_STEP:g}",
            "FGV_GROUPS": GROUPS,
            "FGV_SFTF": "0", "FGV_SFTFCPP": "0",  # SFTF already done, angle-independent
            "FGV_CPU": "1", "FGV_CUDA": "1",
            "FGV_ONLY_MISSING": "0",  # force this angle's TOMO (reuses .npz cache when present)
        })
        run([sys.executable, str(VERIFY)], env, LOG_DIR / f"{tag}_verify.log")

        print(f"--- {tag}: capture ---", flush=True)
        cap_env = dict(os.environ)
        cap_env["TOMO_CRITICAL_ANGLE"] = f"{angle:g}"
        cap_env["TOMO_ANGLE_STEP"] = f"{ANGLE_STEP:g}"
        run(
            [sys.executable, str(CAPTURE), "--critical-angle", f"{angle:g}"],
            cap_env, LOG_DIR / f"{tag}_capture.log",
        )

        progress.setdefault("done", []).append(done_key)
        save_progress(progress)
        print(
            f"=== {tag} done in {(time.perf_counter() - angle_start) / 60:.1f} min "
            f"({len(progress['done'])}/{len(ANGLES)} angles) ===",
            flush=True,
        )

    print(
        f"\nALL DONE: {len(progress.get('done', []))}/{len(ANGLES)} angles; "
        f"total {(time.perf_counter() - overall_start) / 3600:.2f} h",
        flush=True,
    )


if __name__ == "__main__":
    main()
