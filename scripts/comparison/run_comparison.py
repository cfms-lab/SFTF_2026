#!/usr/bin/env python3
"""Run the three baselines (and optionally SFTF) on one mesh and tabulate metrics.

Examples
--------
    uv run python scripts/comparison/run_comparison.py MeshData/big_part.stl \
        --parts 4 --printer-dims 250 250 300

    # include your SFTF result: a .npy / .csv with one integer label per face
    uv run python scripts/comparison/run_comparison.py MeshData/big_part.stl \
        --parts 4 --sftf-labels out/sftf_labels.npy

Outputs (into --out, default scripts/comparison/out/):
    comparison.csv           — the metric table
    comparison.html / .png   — grouped bar chart (plotly + kaleido)
    <method>_labels.npy      — per-face labels for each method (for visualisation)
    <method>_colored.ply     — mesh coloured by part (optional, --export-parts)

Lower is better for support_* and seam_* columns. Each part is scored at its own
best build orientation over the candidate direction set (parts print separately).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))   # make sibling modules importable

import common
import metrics as M
import baseline_planar
import baseline_spectral


def _load_sftf_labels(path: str, n_faces: int) -> np.ndarray:
    p = Path(path)
    if p.suffix.lower() == ".npy":
        lab = np.load(p)
    else:
        lab = np.loadtxt(p, dtype=int, delimiter=",")
    lab = np.asarray(lab, dtype=int).ravel()
    if len(lab) != n_faces:
        raise SystemExit(
            f"SFTF labels length {len(lab)} != mesh face count {n_faces}. "
            "Export one integer label per face on the SAME mesh."
        )
    return lab


def _directions(spec: str) -> np.ndarray:
    if spec.startswith("fib:"):
        return common.fibonacci_directions(int(spec.split(":")[1]))
    return common.axis_directions()


def _print_table(rows: list[dict], cols: list[str]) -> None:
    widths = {c: max(len(c), *(len(_fmt(r[c])) for r in rows)) for c in cols}
    line = "  ".join(c.ljust(widths[c]) for c in cols)
    print(line)
    print("  ".join("-" * widths[c] for c in cols))
    for r in rows:
        print("  ".join(_fmt(r[c]).ljust(widths[c]) for c in cols))


def _fmt(x) -> str:
    if isinstance(x, float):
        return f"{x:.4g}"
    return str(x)


def _save_chart(rows: list[dict], out_dir: Path) -> None:
    try:
        import plotly.graph_objects as go
    except Exception:
        print("[chart] plotly not available — skipping chart.")
        return
    metric_cols = ["support_proxy", "support_per_part_max",
                   "seam_length", "seam_roughness_deg", "seam_planarity"]
    # normalise each metric to its max across methods so bars are comparable
    norm = {}
    for c in metric_cols:
        mx = max((r[c] for r in rows), default=0.0) or 1.0
        norm[c] = mx
    fig = go.Figure()
    for r in rows:
        fig.add_bar(name=r["method"],
                    x=metric_cols,
                    y=[r[c] / norm[c] for c in metric_cols])
    fig.update_layout(barmode="group", template="simple_white",
                      title="Partitioning baselines vs SFTF (normalised, lower=better)",
                      yaxis_title="metric / max-across-methods")
    html = out_dir / "comparison.html"
    fig.write_html(str(html))
    print(f"wrote {html}")
    try:
        png = out_dir / "comparison.png"
        fig.write_image(str(png), width=1000, height=600, scale=2)
        print(f"wrote {png}")
    except Exception as e:
        print(f"[chart] png export skipped ({e}); html written.")


def _export_colored(mesh, labels, path: Path) -> None:
    import trimesh
    labs = np.unique(labels)
    palette = (np.random.RandomState(0).rand(len(labs), 3) * 255).astype(np.uint8)
    cmap = {l: palette[i] for i, l in enumerate(labs)}
    fc = np.array([cmap[l] for l in labels], dtype=np.uint8)
    m2 = mesh.copy()
    m2.visual.face_colors = np.hstack([fc, np.full((len(fc), 1), 255, np.uint8)])
    m2.export(str(path))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesh", help="input mesh (stl/obj/ply/off/3mf ...)")
    ap.add_argument("--parts", type=int, default=4, help="target number of parts")
    ap.add_argument("--printer-dims", type=float, nargs=3, default=None,
                    metavar=("X", "Y", "Z"), help="build volume; parts must fit")
    ap.add_argument("--overhang-deg", type=float, default=common.DEFAULT_OVERHANG_DEG)
    ap.add_argument("--directions", default="axis",
                    help="'axis' (6 dirs) or 'fib:N' (N sphere samples)")
    ap.add_argument("--decimate", type=int, default=None,
                    help="decimate to N faces first (helps the spectral baseline)")
    ap.add_argument("--sftf-labels", default=None,
                    help="per-face labels (.npy/.csv) of YOUR SFTF result to include")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "out"))
    ap.add_argument("--export-parts", action="store_true",
                    help="also write <method>_colored.ply for visual inspection")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    mesh = common.load_mesh(args.mesh, decimate_to=args.decimate)
    dirs = _directions(args.directions)
    dims = np.array(args.printer_dims) if args.printer_dims else None
    n = len(mesh.faces)
    print(f"mesh: {args.mesh}  faces={n}  target parts={args.parts}")

    methods = []
    methods.append(("planar", lambda: baseline_planar.partition(
        mesh, args.parts, printer_dims=dims, directions=dirs)))
    try:
        import baseline_graphcut
        if baseline_graphcut.HAVE_MAXFLOW:
            methods.append(("graphcut", lambda: baseline_graphcut.partition(
                mesh, args.parts, printer_dims=dims, directions=dirs)))
        else:
            print("[graphcut] PyMaxflow missing — skipping. `uv add pymaxflow` to enable.")
    except Exception as e:
        print(f"[graphcut] unavailable ({e}) — skipping.")
    methods.append(("spectral", lambda: baseline_spectral.partition(
        mesh, args.parts, printer_dims=dims)))

    rows: list[dict] = []
    for name, fn in methods:
        print(f"\n== running {name} ==")
        try:
            labels = fn()
        except Exception as e:
            print(f"[{name}] FAILED: {e}")
            continue
        np.save(out_dir / f"{name}_labels.npy", labels)
        if args.export_parts:
            _export_colored(mesh, labels, out_dir / f"{name}_colored.ply")
        met = M.evaluate(mesh, labels, directions=dirs, printer_dims=dims,
                         threshold_deg=args.overhang_deg)
        met = {"method": name, **met}
        rows.append(met)
        print({k: _fmt(v) for k, v in met.items()})

    if args.sftf_labels:
        print("\n== evaluating SFTF (your labels) ==")
        labels = _load_sftf_labels(args.sftf_labels, n)
        met = M.evaluate(mesh, labels, directions=dirs, printer_dims=dims,
                         threshold_deg=args.overhang_deg)
        rows.append({"method": "SFTF", **met})

    if not rows:
        print("no methods produced a result.")
        return 1

    cols = ["method", "n_parts", "support_proxy", "support_per_part_max",
            "seam_length", "seam_roughness_deg", "seam_planarity",
            "parts_fit", "parts_total"]
    print("\n=== comparison ===")
    _print_table(rows, cols)

    csv_path = out_dir / "comparison.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})
    print(f"\nwrote {csv_path}")
    _save_chart(rows, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
