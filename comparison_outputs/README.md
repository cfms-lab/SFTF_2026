# comparison_outputs Calculation Notes

This folder stores CPU INT3 vs TSE6 `v_ss` comparison outputs.

## Repeat Request Shortcut

When the user asks to recalculate `comparison_outputs`, run the 10 degree
comparison calculation and save updated outputs in this folder.

## Current Repeatable Command

From the project root:

```powershell
.venv\Scripts\python.exe scripts\measure_tse6_false_compare.py
```

This computes TSE6 `v_ss` with:

- mesh: `Experimental/etc/Bunny_1k.ply`
- angle grid: `angle_step=10.0`
- grid shape: `37 x 37`
- `critical_angle=60.0`
- `fbo_voxel_size=64`
- `deduplicate_orientations=True`
- CPU comparison source: `comparison_outputs/Bunny_1k_tomo_cpu_vss_10deg_theta60.npz`

The script writes:

- `bunny1k_vss_trend_cpu_vs_tse6_10deg_coarse_false.npz`
- `bunny1k_vss_trend_cpu_vs_tse6_10deg_coarse_false.html`

## Testing Other Meshes

To compare another mesh, run the comparison script with the mesh path:

```powershell
.venv\Scripts\python.exe scripts\measure_tse6_false_compare.py --mesh-path .\Experimental\etc\sphere5cm_f169.obj
```

When `--reference` is omitted, the script runs CPU INT3 through the local
`cpp_src/Tomo_GPU2026/Tomo_Shell2026.dll` bridge with the same `--mesh-path`,
writes a mesh-specific CPU reference NPZ into this folder, and then runs TSE6
with that same mesh.

When `--mesh-path` is provided, the output basename is inferred from the mesh
file stem. For example, `.\Experimental\etc\sphere5cm_f169.obj` writes:

- `sphere5cm_f169_cpu_int3_vss_10deg_theta60.npz`
- `sphere5cm_f169_vss_trend_cpu_vs_tse6_10deg_coarse_false.npz`
- `sphere5cm_f169_vss_trend_cpu_vs_tse6_10deg_coarse_false.html`

Use `--mesh-label` only when the plot title or output basename should differ
from the mesh filename. Use `--out-base` only for a fully custom comparison
output path. Use `--reference` only when intentionally comparing against a
specific precomputed CPU NPZ.

Going forward, repeatable comparison outputs are maintained at 10 degree
intervals only. Other angle steps are experiment-only and should use explicit
filenames when needed.

## Required Plotly Graph Format

All Plotly graphs written to this folder should use the same format as:

```text
bunny1k_vss_trend_cpu_vs_tse6_10deg_coolwarm_equal_aspect.html
```

Required style:

- use `COOLWARM_COLORSCALE` for every Plotly contour trace
- use equal-aspect axes for yaw/pitch contour plots
- remove yaw-direction auto margins by setting explicit axis ranges
- set yaw/pitch contour axes to `range=[0, 360]`
- set normalized scatter axes to `range=[0, 1]`
- set `constrain="domain"` on all subplot axes
- keep subplot spacing equivalent to `horizontal_spacing=0.08` and `vertical_spacing=0.12`
- mark the three minimum orientations as `o1`, `o2`, `o3` on CPU and TSE6 `v_ss` yaw/pitch contour plots
- mark the three maximum orientations as `w1`, `w2`, `w3` on CPU and TSE6 `v_ss` yaw/pitch contour plots
- do not mark `o*` or `w*` labels on normalized difference contour plots
- use blue circle markers for `o*` labels and red x markers for `w*` labels
- include yaw, pitch, and the plotted value in marker hover text

Expected subplot domains:

- left column x domain: `[0.0, 0.46]`
- right column x domain: `[0.54, 1.0]`
- top row y domain: `[0.56, 1.0]`
- bottom row y domain: `[0.0, 0.44]`

The repeatable script currently applies this format in `build_comparison_figure()`.

## Latest Recorded Run

Date: 2026-06-15

Refreshed: 2026-06-15 KST

Command:

```powershell
.venv\Scripts\python.exe scripts\measure_tse6_false_compare.py
```

Metrics:

- normalized RMSE: `0.14821742196833163`
- Pearson: `0.7121366348791685`
- Spearman: `0.5376010182480383`
- bottom10 overlap: `0.3357664233576642`
- top10 overlap: `0.6642335766423357`
- top1 overlap: `0.0`
- top5 overlap: `0.0`
- top10 rank overlap: `0.0`

Optimal rows:

- CPU optimal: `yaw=200.0`, `pitch=130.0`, `v_ss=22608.651405523633`
- TSE6 optimal: `yaw=180.0`, `pitch=180.0`, `v_ss=119442.70355800976`

TSE6 `v_ss` stats:

- min: `119442.70355800976`
- max: `234352.58906295744`
- mean: `153912.42012639355`

TSE6 `V_nv` stats:

- min: `0.0`
- max: `0.0`
- mean: `0.0`

Run parameters:

- angle grid: `angle_step=10.0`
- grid shape: `37 x 37`
- `critical_angle=60.0`
- `fbo_voxel_size=64`
- `deduplicate_orientations=True`

Note: CPU component arrays are not currently present in the reference NPZ, so
component comparison HTML files are skipped. The script saves TSE6 components as
`tse_vtc`, `tse_vo`, and `tse_vnv`; if future CPU references add matching
`cpu_vtc`, `cpu_vo`, and `cpu_vnv` keys, component comparison graphs will be
generated automatically.
