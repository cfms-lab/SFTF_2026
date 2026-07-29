"""Re-render the ESM Figure S1 overview using TOMO-grid best/worst orientations.

The legacy figure oriented each mesh by the LEGACY SFTF score's rank-1
best/worst directions.  The caption, however, says "best and worst verified
build orientation" — so this script recomputes both orientations directly
from the saved dense TOMO_INT3 grids (argmin / argmax v_ss), making the
figure match its caption exactly.  Layout, colors, and mesh roster
(A1-5, B1-5, C1-5, D1-10, E1-10) follow the existing figure.

Output: draft/TDP_v2.1/pics/sftf_s1_tomo_best_worst.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Experimental" / "R_term_recalib"))

from extract_and_calibrate import grid_from_html  # noqa: E402
import scripts.render_figure6_grouped as rfg  # noqa: E402
from scripts.capture_four_group_best_worst_polyscope import (  # noqa: E402
    RESULT_DIR,
    load_records,
)

G5 = PROJECT_ROOT / "Experimental" / "G5Test"
KEEP = ({f"A{i}" for i in range(1, 6)} | {f"B{i}" for i in range(1, 6)}
        | {f"C{i}" for i in range(1, 6)} | {f"D{i}" for i in range(1, 11)}
        | {f"E{i}" for i in range(1, 11)})


def direction_from_yaw_pitch(yaw: float, pitch: float) -> np.ndarray:
    yr, pr = np.deg2rad(float(yaw)), np.deg2rad(float(pitch))
    d = np.array([-np.sin(pr), np.cos(pr) * np.sin(yr), np.cos(pr) * np.cos(yr)])
    return d / max(float(np.linalg.norm(d)), 1e-12)


_CACHE: dict[str, tuple[np.ndarray, np.ndarray]] = {}


def tomo_best_worst(record: dict) -> tuple[np.ndarray | None, np.ndarray | None]:
    stem = Path(str(record["mesh"])).stem
    if stem not in _CACHE:
        html = G5 / f"{stem}_tomo_int3.html"
        if not html.exists():
            print(f"  [warn] no TOMO sweep for {stem}; skipping best/worst")
            _CACHE[stem] = (None, None)
        else:
            yaw, pitch, grid = grid_from_html(html)
            b_p, b_y = np.unravel_index(int(np.argmin(grid)), grid.shape)
            w_p, w_y = np.unravel_index(int(np.argmax(grid)), grid.shape)
            _CACHE[stem] = (
                direction_from_yaw_pitch(yaw[b_y], pitch[b_p]),
                direction_from_yaw_pitch(yaw[w_y], pitch[w_p]),
            )
    return _CACHE[stem]


def canonical_records() -> list[dict]:
    records = rfg.dedupe_records(load_records(RESULT_DIR, set(rfg.GROUP_ORDER)))
    by_gid: dict[str, dict] = {}
    for r in records:
        gid = str(r["_gid"])
        if gid not in KEEP:
            continue
        prev = by_gid.get(gid)
        if prev is None:
            by_gid[gid] = r
        else:
            def mtime(rec):
                p = rec.get("_json_path")
                return Path(p).stat().st_mtime if p else 0.0
            if mtime(r) > mtime(prev):
                print(f"  duplicate gid {gid}: keeping newer {r['mesh']} over {prev['mesh']}")
                by_gid[gid] = r
            else:
                print(f"  duplicate gid {gid}: keeping newer {prev['mesh']} over {r['mesh']}")
    rows = sorted(by_gid.values(), key=lambda r: (str(r["_group"]), int(r["_order"])))
    return rows


def main() -> None:
    rfg.best_worst_directions = tomo_best_worst  # replace legacy-score lookup
    records = canonical_records()
    for g in rfg.GROUP_ORDER:
        print(f"group {g}: {[str(r['_gid']) for r in records if r['_group'] == g]}")
    rfg.init_polyscope()
    images = {}
    for group in rfg.GROUP_ORDER:
        print(f"rendering group {group} ...", flush=True)
        images[group] = rfg.render_group(records, group, max_faces=100000)
    out = PROJECT_ROOT / "draft" / "TDP_v2.1" / "pics" / "sftf_s1_tomo_best_worst.png"
    rfg.compose(images, out)


if __name__ == "__main__":
    main()
