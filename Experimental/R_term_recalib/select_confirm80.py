"""Select 80 NEW confirmation meshes for the v2.1 budget-5 test (outcome-blind).

Continues the exact TDP v2 selection order: same thingi10k_strict source, same
salted-hash ranking (salt ``sftf-tdp-v2-holdout-v1``), same geometry checks,
same strata — excluding the 60 already-used holdout meshes and the known
development Thingi IDs.  Per-stratum quotas scale the original 15/20/15/10 by
4/3 to 20/27/20/13 (=80).  No TOMO or slicer outcome is read or computed here.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
SNAPSHOT = PROJECT_ROOT / "draft" / "TDP_v2"
sys.path.insert(0, str(SNAPSHOT / "scripts"))

from select_tdp_v2_holdout import (  # noqa: E402
    _rank,
    _stratum_for,
    _thingi_id,
    binary_stl_face_count,
    geometry_metadata,
    sha256_file,
)

PROTOCOL = json.loads((SNAPSHOT / "experiments" / "tdp_v2" / "protocol.json").read_text(encoding="utf-8"))
EXT = PROTOCOL["external_selection"]
SALT = EXT["selection_salt"]
STRATA = EXT["strata"]
DEV_IDS = set(EXT["known_development_thingi_ids"])
SOURCE = Path(str(EXT["source_root_default"])) / str(EXT["source_subdirectory"])
MANIFEST = SNAPSHOT / "experiments" / "tdp_v2" / "manifests" / "holdout_manifest.csv"
QUOTA = {"faces_1k_10k": 20, "faces_10k_50k": 27, "faces_50k_150k": 20, "faces_150k_250k": 13}
OUT_CSV = HERE / "confirm80_manifest.csv"
OUT_AUDIT = HERE / "confirm80_selection_audit.json"


def main() -> None:
    with MANIFEST.open(newline="", encoding="utf-8") as fh:
        used_sha = {r["sha256"].lower() for r in csv.DictReader(fh)}
    print(f"existing holdout: {len(used_sha)} meshes excluded")

    files = sorted(SOURCE.glob("*.stl"))
    print(f"source files: {len(files)}")
    ranked: dict[str, list[dict]] = {s["name"]: [] for s in STRATA}
    seen_sha: set[str] = set()
    skipped_dev = skipped_used = outside = dup = bad_stl = 0
    for path in files:
        tid = _thingi_id(path)
        if tid is not None and tid in DEV_IDS:
            skipped_dev += 1
            continue
        try:
            faces = binary_stl_face_count(path)
        except ValueError:
            bad_stl += 1
            continue
        stratum = _stratum_for(faces, STRATA)
        if stratum is None:
            outside += 1
            continue
        sha = sha256_file(path).lower()
        if sha in seen_sha:
            dup += 1
            continue
        seen_sha.add(sha)
        if sha in used_sha:
            skipped_used += 1
            continue
        rel = str(path.relative_to(SOURCE.parent)).replace("\\", "/")
        ranked[stratum].append({
            "relative_path": rel, "path": path, "thingi_id": tid or "",
            "face_count": faces, "sha256": sha,
            "selection_rank": _rank(SALT, rel, sha),
        })
    print(f"skipped: dev {skipped_dev}, already-used {skipped_used}, "
          f"outside-strata {outside}, dup {dup}, bad-stl {bad_stl}")

    selected: list[dict] = []
    examined = {}
    rejected = {}
    for s in STRATA:
        name = s["name"]
        pool = sorted(ranked[name], key=lambda r: r["selection_rank"])
        quota = QUOTA[name]
        take, checked = [], 0
        for cand in pool:
            checked += 1
            meta, reason = geometry_metadata(cand["path"])
            if meta is None:
                rejected[reason] = rejected.get(reason, 0) + 1
                continue
            take.append(cand)
            if len(take) >= quota:
                break
        examined[name] = checked
        print(f"{name}: pool {len(pool)}, examined {checked}, selected {len(take)}")
        assert len(take) == quota, f"{name}: quota not met"
        selected.extend(take)

    rows = []
    for index, cand in enumerate(sorted(selected, key=lambda r: r["selection_rank"]), start=1):
        rows.append({
            "holdout_id": f"N{index:03d}",
            "thingi_id": cand["thingi_id"],
            "relative_path": cand["relative_path"],
            "face_count": cand["face_count"],
            "stratum": _stratum_for(cand["face_count"], STRATA),
            "sha256": cand["sha256"],
            "selection_rank": cand["selection_rank"],
            "cross_slicer": "false",
        })
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    OUT_AUDIT.write_text(json.dumps({
        "protocol_id": PROTOCOL["protocol_id"],
        "selection_salt": SALT,
        "purpose": "v2.1 budget-5 confirmatory set (FREEZE.md part 3)",
        "quota": QUOTA,
        "selected_count": len(rows),
        "examined_by_stratum": examined,
        "geometry_rejections": rejected,
        "excluded_existing_holdout": len(used_sha),
        "outcome_seal": "No TOMO or slicer values were read or computed during selection.",
    }, indent=1), encoding="utf-8")
    print(f"wrote {OUT_CSV} ({len(rows)} meshes) and audit")


if __name__ == "__main__":
    main()
