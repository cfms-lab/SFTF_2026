# Shared SFTF Mesh Data

This folder centralizes mesh/data assets that were previously stored inside the
individual project folders in this workspace. Duplicate mesh files have been
collapsed by content hash.

Project code should refer to this folder through each project's `_mesh_paths.py`
helper, or the package-level `moldability.data_paths` helper in
`SFTF_InjMold_dev`.

Layout:

- `g5test/`: shared G5 raw mesh set plus the G5 source manifests.
- `thingi10k/`: deduplicated Thingi10K STL corpus (`thingi_*.stl`).
- Repository root: all other shared meshes, application-case images, source
  notes, caches, and corpus manifests.
- `SFTF_InjMold_dev/`: restored legacy data/manifests from the pre-git backup,
  kept in its original relative layout for traceability.

The active shared mesh folders are intentionally shallow except for the large
G5 and Thingi10K corpora.
