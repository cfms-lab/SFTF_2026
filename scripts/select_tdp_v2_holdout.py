"""Create the geometry-only, hash-ranked TDP v2 external holdout manifest.

This script deliberately computes no TOMO or slicer outcome.  It may be run
before ``policy_lock.json`` exists because selection uses only file identity,
binary-STL face count, and geometry validity.  Running any outcome script on
the selected paths before policy lock would violate ``experiments/tdp_v2/protocol.json``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import struct
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import trimesh


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = PROJECT_ROOT / "experiments" / "tdp_v2" / "protocol.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "tdp_v2" / "manifests"


@dataclass(frozen=True)
class Candidate:
    path: Path
    relative_path: str
    face_count: int
    byte_count: int
    sha256: str
    selection_rank: str
    stratum: str


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binary_stl_face_count(path: Path) -> int:
    size = path.stat().st_size
    if size < 84:
        raise ValueError("short_stl")
    with path.open("rb") as stream:
        header = stream.read(84)
    count = int(struct.unpack("<I", header[80:84])[0])
    if 84 + 50 * count != size:
        raise ValueError("not_binary_stl_or_size_mismatch")
    return count


def _rank(salt: str, relative_path: str, file_sha256: str) -> str:
    payload = f"{salt}\0{relative_path}\0{file_sha256}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _thingi_id(path: Path) -> str | None:
    match = re.fullmatch(r"thingi_(\d+)", path.stem, flags=re.IGNORECASE)
    return None if match is None else match.group(1)


def _stratum_for(face_count: int, strata: list[dict[str, Any]]) -> str | None:
    for item in strata:
        if (
            int(item["min_faces_inclusive"])
            <= face_count
            < int(item["max_faces_exclusive"])
        ):
            return str(item["name"])
    return None


def geometry_metadata(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Return geometry-only metadata or a stable rejection reason."""

    try:
        # Binary STL repeats vertices per triangle.  Topology checks therefore
        # require Trimesh's deterministic vertex merge; with process=False a
        # valid closed STL appears as one disconnected body per triangle.
        loaded = trimesh.load_mesh(path, process=True)
        if isinstance(loaded, trimesh.Scene):
            if not loaded.geometry:
                return None, "empty_scene"
            mesh = trimesh.util.concatenate(tuple(loaded.geometry.values()))
        elif isinstance(loaded, trimesh.Trimesh):
            mesh = loaded
        else:
            return None, "unsupported_geometry_type"

        vertices = np.asarray(mesh.vertices, dtype=np.float64)
        faces = np.asarray(mesh.faces, dtype=np.int64)
        if vertices.size == 0 or faces.size == 0:
            return None, "empty_mesh"
        if not np.all(np.isfinite(vertices)):
            return None, "nonfinite_vertices"
        area = float(mesh.area)
        if not np.isfinite(area) or area <= 0.0:
            return None, "nonpositive_area"
        diagonal = float(np.linalg.norm(np.asarray(mesh.extents, dtype=np.float64)))
        if not np.isfinite(diagonal) or diagonal <= 0.0:
            return None, "nonpositive_bbox_diagonal"
        if not bool(mesh.is_watertight):
            return None, "not_watertight"
        body_count = int(mesh.body_count)
        if body_count != 1:
            return None, "not_single_component"

        return (
            {
                "vertex_count": int(len(vertices)),
                "face_count_loaded": int(len(faces)),
                "surface_area": area,
                "bbox_diagonal": diagonal,
                "body_count": body_count,
                "watertight": True,
                "euler_number": int(mesh.euler_number),
            },
            None,
        )
    except Exception as exc:  # geometry libraries expose several backend exceptions
        return None, f"load_error:{type(exc).__name__}"


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def select_holdout(
    protocol_path: Path,
    output_dir: Path,
    source_root_override: Path | None = None,
) -> dict[str, Any]:
    protocol_bytes = protocol_path.read_bytes()
    protocol = json.loads(protocol_bytes)
    selection = protocol["external_selection"]
    source_root = (
        source_root_override
        if source_root_override is not None
        else Path(selection["source_root_default"])
    )
    source_dir = source_root / selection["source_subdirectory"]
    if not source_dir.is_dir():
        raise FileNotFoundError(f"external source directory not found: {source_dir}")

    strata = list(selection["strata"])
    strata_by_name = {str(item["name"]): item for item in strata}
    excluded_ids = {str(value) for value in selection["known_development_thingi_ids"]}
    extensions = {str(value).lower() for value in selection["filters"]["extensions"]}
    rejection_counts: Counter[str] = Counter()
    candidates_by_stratum: dict[str, list[Candidate]] = {
        name: [] for name in strata_by_name
    }

    paths = sorted(
        path
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in extensions
    )
    for path in paths:
        thingi_id = _thingi_id(path)
        if thingi_id in excluded_ids:
            rejection_counts["known_development_id"] += 1
            continue
        try:
            face_count = binary_stl_face_count(path)
        except ValueError as exc:
            rejection_counts[str(exc)] += 1
            continue
        stratum = _stratum_for(face_count, strata)
        if stratum is None:
            rejection_counts["outside_face_count_strata"] += 1
            continue
        relative_path = path.relative_to(source_root).as_posix()
        file_hash = sha256_file(path)
        candidates_by_stratum[stratum].append(
            Candidate(
                path=path,
                relative_path=relative_path,
                face_count=face_count,
                byte_count=path.stat().st_size,
                sha256=file_hash,
                selection_rank=_rank(
                    str(selection["selection_salt"]), relative_path, file_hash
                ),
                stratum=stratum,
            )
        )

    selected_rows: list[dict[str, Any]] = []
    selected_hashes: set[str] = set()
    examined_by_stratum: Counter[str] = Counter()
    for stratum_name, item in strata_by_name.items():
        quota = int(item["holdout_quota"])
        ordered = sorted(
            candidates_by_stratum[stratum_name],
            key=lambda candidate: (candidate.selection_rank, candidate.relative_path),
        )
        selected_in_stratum = 0
        for candidate in ordered:
            if selected_in_stratum >= quota:
                break
            examined_by_stratum[stratum_name] += 1
            if candidate.sha256 in selected_hashes:
                rejection_counts["duplicate_sha256"] += 1
                continue
            metadata, reason = geometry_metadata(candidate.path)
            if reason is not None:
                rejection_counts[reason] += 1
                continue
            assert metadata is not None
            if int(metadata["face_count_loaded"]) != candidate.face_count:
                rejection_counts["header_loaded_face_count_mismatch"] += 1
                continue
            selected_hashes.add(candidate.sha256)
            selected_in_stratum += 1
            selected_rows.append(
                {
                    "holdout_id": "",
                    "stratum": stratum_name,
                    "stratum_index": selected_in_stratum,
                    "relative_path": candidate.relative_path,
                    "thingi_id": _thingi_id(candidate.path),
                    "sha256": candidate.sha256,
                    "selection_rank": candidate.selection_rank,
                    "byte_count": candidate.byte_count,
                    "face_count": candidate.face_count,
                    **metadata,
                    "cross_slicer": False,
                    "cross_slicer_rank": "",
                }
            )
        if selected_in_stratum != quota:
            raise RuntimeError(
                f"stratum {stratum_name} produced {selected_in_stratum}/{quota} valid meshes"
            )

    selected_rows.sort(key=lambda row: (row["stratum"], row["selection_rank"]))
    for index, row in enumerate(selected_rows, start=1):
        row["holdout_id"] = f"H{index:03d}"

    cross_slicer_salt = str(selection["cross_slicer_salt"])
    for stratum_name, item in strata_by_name.items():
        quota = int(item["cross_slicer_quota"])
        rows = [row for row in selected_rows if row["stratum"] == stratum_name]
        for row in rows:
            row["cross_slicer_rank"] = _rank(
                cross_slicer_salt, row["relative_path"], row["sha256"]
            )
        for row in sorted(rows, key=lambda value: value["cross_slicer_rank"])[:quota]:
            row["cross_slicer"] = True

    expected_holdout = int(selection["holdout_total"])
    expected_cross_slicer = int(selection["cross_slicer_total"])
    if len(selected_rows) != expected_holdout:
        raise RuntimeError(f"selected {len(selected_rows)} meshes, expected {expected_holdout}")
    if sum(bool(row["cross_slicer"]) for row in selected_rows) != expected_cross_slicer:
        raise RuntimeError("cross-slicer quota total mismatch")

    manifest = {
        "schema_version": 1,
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "selection_is_geometry_only": True,
        "external_outcomes_computed": False,
        "dataset_subdirectory": str(selection["source_subdirectory"]),
        "mesh_count": len(selected_rows),
        "cross_slicer_count": sum(
            bool(row["cross_slicer"]) for row in selected_rows
        ),
        "meshes": selected_rows,
    }
    manifest_bytes = _canonical_json_bytes(manifest)
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    audit = {
        "protocol_id": protocol["protocol_id"],
        "source_file_count": len(paths),
        "candidate_count_by_stratum": {
            name: len(values) for name, values in candidates_by_stratum.items()
        },
        "examined_by_stratum": dict(examined_by_stratum),
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "selected_count": len(selected_rows),
        "cross_slicer_count": sum(
            bool(row["cross_slicer"]) for row in selected_rows
        ),
        "manifest_sha256": manifest_sha256,
        "outcome_seal": "No TOMO or slicer values were read or computed.",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "holdout_manifest.json").write_bytes(manifest_bytes)
    (output_dir / "selection_audit.json").write_bytes(_canonical_json_bytes(audit))
    (output_dir / "holdout_manifest.sha256").write_text(
        f"{manifest_sha256}  holdout_manifest.json\n", encoding="ascii"
    )
    fieldnames = list(selected_rows[0].keys())
    with (output_dir / "holdout_manifest.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected_rows)
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-root", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = select_holdout(args.protocol, args.output_dir, args.source_root)
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
