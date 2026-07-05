# Support Flow Tensor Field (SFTF)

This repository is the source-code and data snapshot for the manuscript
submitted to *3D Printing and Additive Manufacturing*. It contains the
implementation of the Support Flow Tensor Field (SFTF) build-orientation
candidate generator, stored TOMO validation outputs, paper-generation scripts,
and the small-to-medium mesh data needed for reviewer-side reproduction.

SFTF is a fast pre-screening method for additive manufacturing build
orientation. Instead of sweeping all yaw/pitch directions with a TOMO or slicer
support-volume computation, SFTF estimates direction-dependent self-support
relations between mesh faces and ranks a compact set of promising build
directions. The stored TOMO grids in this snapshot are used as the reference
for the paper comparisons.

## Reviewer Quick Start

The following commands run the unit tests and the main non-GPU paper summary
regeneration path.

```powershell
git clone https://github.com/cfms-lab/SFTF_2026.git
cd SFTF_2026
uv sync
uv run python -m pytest
uv run python scripts\regenerate_sftf_vs_saved_tomo_summary.py
```

If `uv` is not available, use a Python 3.12 virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest
python scripts\regenerate_sftf_vs_saved_tomo_summary.py
```

Expected summary outputs are written to:

```text
Experimental/etc/support_flow_tensor_field_vs_saved_tomo_int3_summary.csv
Experimental/etc/support_flow_tensor_field_vs_saved_tomo_int3_summary.json
```

## Requirements

- Python 3.12 or later
- Windows is recommended for DLL-backed TOMO validation scripts
- `uv` is recommended but not required
- Optional for visualization: a desktop session capable of opening Polyscope or
  Plotly HTML outputs

The core package depends on `numpy`, `trimesh`, `scipy`, `embreex`, and `rtree`.
The repository tooling group also installs plotting and visualization packages
such as `plotly`, `polyscope`, `matplotlib`, `scikit-learn`, and `manifold3d`.

## Data Layout

The review snapshot includes `sftf_Mesh_Data/` inside the repository. Scripts
resolve mesh data from this in-repository folder first, and then fall back to a
sibling `../sftf_Mesh_Data/` folder for the authors' development checkout.

Mesh files larger than 10 MB are intentionally excluded from the GitHub
snapshot to keep the repository manageable. See
[`DATA_AVAILABILITY.md`](DATA_AVAILABILITY.md) for the exact excluded-file list
and where to place downloaded copies.

Important data locations:

| Path | Purpose |
| --- | --- |
| `sftf_Mesh_Data/g5test/` | Included G5 validation meshes, except files listed in `DATA_AVAILABILITY.md` |
| `Experimental/etc/` | Stored TOMO INT3 grids and paper summary CSV/JSON/HTML outputs |
| `Experimental/G5Test/` | G5 validation records, cached TOMO grids, SFTF candidate CSV files, and figures |
| `comparison_outputs/` | Additional comparison artifacts retained for manuscript review |
| `draft/` | Manuscript source and submission-support files |

## Main Reproduction Commands

### 1. Run the Test Suite

```powershell
uv run python -m pytest
```

The tests cover mesh-orientation handling, Pareto helper logic, spherical
sampling, candidate de-duplication, rank-normalized features, build-direction
rotation, and SFTF candidate-pool invariants.

### 2. Regenerate the Paper Summary Table

This path uses the stored TOMO INT3 grids and re-evaluates the SFTF candidates
with the current Python implementation. It does not require a GPU.

```powershell
uv run python scripts\regenerate_sftf_vs_saved_tomo_summary.py
```

Outputs:

```text
Experimental/etc/support_flow_tensor_field_vs_saved_tomo_int3_summary.csv
Experimental/etc/support_flow_tensor_field_vs_saved_tomo_int3_summary.json
```

### 3. Regenerate TOMO Contour Comparison Figures

```powershell
uv run python scripts\plot_sftf_tomo_cpu_contours.py
```

The generated HTML files are written under `Experimental/etc/` and show where
the SFTF-selected directions lie on the stored TOMO support-volume landscapes.

### 4. Run the Interactive SFTF Demo

```powershell
uv run python TSE6_SFTF_main.py
```

This opens the Polyscope-based visualization path for the meshes listed in
`python_src/SupportFlowTensorField/support_flow_tensor_field.py` under
`MESH_PATHS`. Edit that list to inspect a different included mesh.

### 5. Optional DLL-Backed TOMO Validation

The following script exercises the Windows TOMO DLL bridge and is intended for
Windows environments where the bundled DLL can be loaded:

```powershell
uv run python scripts\validate_ccave_eigen_tomo.py
```

For routine manuscript-table checks, prefer the stored-grid workflow in step 2.
It is faster and does not depend on GPU or DLL runtime availability.

## Repository Layout

| Path | Description |
| --- | --- |
| `python_src/SupportFlowTensorField/` | Active SFTF implementation: mesh loading, candidate sampling, ray-hit features, tensor scoring, Pareto helpers |
| `scripts/_mesh_paths.py` | Mesh-data path resolver for both the GitHub snapshot and the authors' sibling-data checkout |
| `scripts/regenerate_sftf_vs_saved_tomo_summary.py` | Recreates the SFTF-vs-stored-TOMO manuscript summary files |
| `scripts/plot_sftf_tomo_cpu_contours.py` | Generates TOMO contour visualizations with SFTF markers |
| `scripts/validate_ccave_eigen_tomo.py` | Windows DLL-backed TOMO validation path |
| `cpp_src/Tomo_GPU2026/` | TOMO CPU/CUDA bridge code and bundled DLL used by validation scripts |
| `Experimental/etc/` | Stored TOMO grids and paper-level outputs |
| `Experimental/G5Test/` | G5 validation artifacts and cached grids |
| `tests/` | Unit tests for the active Python implementation |
| `obsolete/` | Historical code retained for traceability; not the active paper pipeline |

## Notes for Reviewers

- The active paper pipeline is centered on
  `python_src/SupportFlowTensorField/` and the scripts listed above.
- `obsolete/` contains earlier FBO, VisFacePair, ShTensor, and draft-era code.
  It is not required for the main SFTF reproduction path.
- Some scripts generate visual HTML files and may overwrite existing outputs in
  `Experimental/etc/` or `Experimental/G5Test/`.
- If a script reports a missing large D/E-group mesh, consult
  `DATA_AVAILABILITY.md`, download that file from the manuscript data archive,
  and place it at the same relative path under `sftf_Mesh_Data/`.
