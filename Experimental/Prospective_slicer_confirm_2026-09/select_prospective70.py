"""Select the 70-mesh prospective slicer-confirmation sample (outcome-blind).

Part A: the 33 complex-stratum meshes (>=50k faces) of the v2.1 confirmation
set N001-N080 (Experimental/R_term_recalib/confirm80_manifest.csv).  They have
never been sliced.  Their dense TOMO grids already exist.

Part B: 37 NEW meshes continuing the exact TDP v2 selection order — same
thingi10k_strict source, same salted-hash ranking (salt sftf-tdp-v2-holdout-v1),
same geometry checks — excluding the 60 holdout meshes, the 80 confirmation
meshes and the known development Thingi IDs.  The 150k-250k stratum is nearly
exhausted, so Part B takes every remaining valid 150k-250k mesh (at most 4) and
fills the rest from 50k-150k.

No TOMO or slicer outcome is read or computed here.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
LEGACY = PROJECT_ROOT / "draft" / "src" / "legacy" / "TDP_v2"
sys.path.insert(0, str(LEGACY / "scripts"))

from select_tdp_v2_holdout import (  # noqa: E402
    _rank,
    _stratum_for,
    _thingi_id,
    binary_stl_face_count,
    geometry_metadata,
    sha256_file,
)

PROTOCOL = json.loads((LEGACY / "experiments" / "tdp_v2" / "protocol.json").read_text(encoding="utf-8"))
EXT = PROTOCOL["external_selection"]
SALT = EXT["selection_salt"]
STRATA = EXT["strata"]
COMPLEX = ("faces_50k_150k", "faces_150k_250k")
DEV_IDS = set(EXT["known_development_thingi_ids"])
SOURCE = Path(str(EXT["source_root_default"])) / str(EXT["source_subdirectory"])
HOLDOUT_CSV = LEGACY / "experiments" / "tdp_v2" / "manifests" / "holdout_manifest.csv"
CONFIRM80_CSV = PROJECT_ROOT / "Experimental" / "R_term_recalib" / "confirm80_manifest.csv"
CONFIRM80_GRIDS = PROJECT_ROOT / "Experimental" / "R_term_recalib" / "confirm80_grids"
TARGET_TOTAL = 70
MAX_150K_NEW = 4
OUT_CSV = HERE / "prospective_manifest.csv"
OUT_AUDIT = HERE / "prospective_selection_audit.json"


def main() -> None:
    with HOLDOUT_CSV.open(newline="", encoding="utf-8") as fh:
        holdout_sha = {r["sha256"].lower() for r in csv.DictReader(fh)}
    with CONFIRM80_CSV.open(newline="", encoding="utf-8") as fh:
        confirm80 = list(csv.DictReader(fh))
    confirm80_sha = {r["sha256"].lower() for r in confirm80}

    # ---- Part A: complex meshes of the confirmation set (grids exist, never sliced)
    part_a = []
    for r in confirm80:
        if r["stratum"] in COMPLEX:
            grid = CONFIRM80_GRIDS / f"{r['holdout_id']}.npz"
            assert grid.is_file(), grid
            part_a.append({
                "study_id": r["holdout_id"], "source_set": "confirm80",
                "thingi_id": r["thingi_id"], "relative_path": r["relative_path"],
                "face_count": int(r["face_count"]), "stratum": r["stratum"],
                "sha256": r["sha256"].lower(), "selection_rank": r["selection_rank"],
                "tomo_grid_existing": str(grid.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            })
    part_a.sort(key=lambda r: r["selection_rank"])
    print(f"Part A: {len(part_a)} complex meshes from confirm80 "
          f"({sum(r['stratum']=='faces_50k_150k' for r in part_a)} / {sum(r['stratum']=='faces_150k_250k' for r in part_a)})")

    # ---- Part B: continue the hash order on untouched meshes
    files = sorted(SOURCE.glob("*.stl"))
    print(f"source files: {len(files)}")
    ranked: dict[str, list[dict]] = {s: [] for s in COMPLEX}
    seen_sha: set[str] = set()
    counts = {"dev": 0, "holdout": 0, "confirm80": 0, "outside_complex": 0, "dup": 0, "bad_stl": 0}
    for path in files:
        tid = _thingi_id(path)
        if tid is not None and tid in DEV_IDS:
            counts["dev"] += 1
            continue
        try:
            faces = binary_stl_face_count(path)
        except ValueError:
            counts["bad_stl"] += 1
            continue
        stratum = _stratum_for(faces, STRATA)
        if stratum not in COMPLEX:
            counts["outside_complex"] += 1
            continue
        sha = sha256_file(path).lower()
        if sha in seen_sha:
            counts["dup"] += 1
            continue
        seen_sha.add(sha)
        if sha in holdout_sha:
            counts["holdout"] += 1
            continue
        if sha in confirm80_sha:
            counts["confirm80"] += 1
            continue
        rel = str(path.relative_to(SOURCE.parent)).replace("\\", "/")
        ranked[stratum].append({
            "relative_path": rel, "path": path, "thingi_id": tid or "",
            "face_count": faces, "sha256": sha, "selection_rank": _rank(SALT, rel, sha),
        })
    print("exclusions:", counts)
    print({s: len(v) for s, v in ranked.items()}, "untouched candidates before geometry checks")

    need_new = TARGET_TOTAL - len(part_a)
    quota = {}
    taken: list[dict] = []
    examined = {}
    rejected: dict[str, int] = {}
    # 150k-250k first (all remaining valid, capped), then 50k-150k fills the rest
    for stratum, cap in (("faces_150k_250k", MAX_150K_NEW), ("faces_50k_150k", None)):
        pool = sorted(ranked[stratum], key=lambda r: r["selection_rank"])
        want = cap if cap is not None else need_new - len(taken)
        quota[stratum] = want
        got, checked = [], 0
        for cand in pool:
            if len(got) >= want:
                break
            checked += 1
            meta, reason = geometry_metadata(cand["path"])
            if meta is None:
                rejected[reason] = rejected.get(reason, 0) + 1
                continue
            if int(meta["face_count_loaded"]) != cand["face_count"]:
                rejected["header_loaded_face_count_mismatch"] = rejected.get("header_loaded_face_count_mismatch", 0) + 1
                continue
            got.append(cand)
        examined[stratum] = checked
        print(f"{stratum}: pool {len(pool)}, examined {checked}, selected {len(got)} (wanted {want})")
        taken.extend(got)
    assert len(taken) == need_new, f"Part B produced {len(taken)}/{need_new}"

    part_b = []
    for index, cand in enumerate(sorted(taken, key=lambda r: r["selection_rank"]), start=1):
        part_b.append({
            "study_id": f"P{index:03d}", "source_set": "new",
            "thingi_id": cand["thingi_id"], "relative_path": cand["relative_path"],
            "face_count": cand["face_count"], "stratum": _stratum_for(cand["face_count"], STRATA),
            "sha256": cand["sha256"], "selection_rank": cand["selection_rank"],
            "tomo_grid_existing": "",
        })

    rows = part_a + part_b
    fields = list(rows[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    manifest_sha = hashlib.sha256(OUT_CSV.read_bytes()).hexdigest()
    audit = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_id": PROTOCOL["protocol_id"],
        "selection_salt": SALT,
        "purpose": "prospective slicer confirmation of the candidate regime (complex geometry, B=10)",
        "part_a_confirm80_complex": len(part_a),
        "part_b_new": len(part_b),
        "part_b_quota": quota,
        "part_b_examined_by_stratum": examined,
        "part_b_geometry_rejections": rejected,
        "untouched_candidates_by_stratum": {s: len(v) for s, v in ranked.items()},
        "exclusion_counts": counts,
        "by_stratum": {s: sum(r["stratum"] == s for r in rows) for s in COMPLEX},
        "selected_total": len(rows),
        "manifest_sha256": manifest_sha,
        "outcome_seal": "No TOMO or slicer values were read or computed during selection. "
                        "Part A TOMO grids pre-exist (computed 2026-07-29 for the v2.1 study); "
                        "no slicer outcome exists for any selected mesh.",
    }
    OUT_AUDIT.write_text(json.dumps(audit, indent=1), encoding="utf-8")
    print(f"wrote {OUT_CSV} ({len(rows)} meshes; sha256 {manifest_sha}) and audit")


if __name__ == "__main__":
    main()
