#!/usr/bin/env python3
"""Generate AAMA/ASTM-style garment block DXF files from body measurements.

Examples
--------
    # all five blocks, women's size 12, into ./out (mm units), with a preview PNG
    uv run python scripts/garment_dxf/make_patterns.py --size 12 --preview

    # just the skirt, size 14, keep centimetre units
    uv run python scripts/garment_dxf/make_patterns.py --size 14 \
        --blocks skirt_front skirt_back --units cm

    # override individual measurements (cm)
    uv run python scripts/garment_dxf/make_patterns.py --size 12 --waist 72 --hip 98

One DXF per piece is written (the usual AAMA piece-per-file convention), plus an
optional combined preview PNG so you can eyeball the blocks. Each DXF carries the
AAMA layer convention: 1=boundary, 8=darts, 11=notches, 13=grain, 15=label.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import drafting
from blocks import ALL_BLOCKS
from dxf_aama import (DxfWriter, LAYER_BOUNDARY, LAYER_INTERNAL, LAYER_NOTCH,
                      LAYER_TEXT, read_dxf)

NOTCH_LEN = 0.6   # drafting units (cm)


def piece_to_dxf(piece, path: str, scale: float) -> None:
    w = DxfWriter(scale=scale)
    w.polyline(piece.boundary, LAYER_BOUNDARY, closed=True)
    for legs in piece.internals:
        w.polyline(legs, LAYER_INTERNAL, closed=False)
    for (x, y, nx, ny) in piece.notches:
        L = math.hypot(nx, ny) or 1.0
        w.line((x, y), (x + nx / L * NOTCH_LEN, y + ny / L * NOTCH_LEN), LAYER_NOTCH)
    if piece.grain:
        w.grainline(piece.grain[0], piece.grain[1])
    w.text(piece.label_pos, f"{piece.name} sz{piece.size}", LAYER_TEXT, height=8.0)
    w.save(path)


def preview(dxf_paths: list[str], png_path: str) -> None:
    """Read the generated DXFs back and plot them — proves the files round-trip."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"[preview] matplotlib unavailable ({e}); skipping PNG.")
        return
    n = len(dxf_paths)
    cols = min(n, 3)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 4.6 * rows))
    axes = (axes.ravel() if hasattr(axes, "ravel") else [axes])
    colour = {LAYER_BOUNDARY: "#1f4e79", LAYER_INTERNAL: "#c0504d",
              LAYER_NOTCH: "#7f7f7f", "13": "#2e8b57", LAYER_TEXT: "#000000"}
    for ax, path in zip(axes, dxf_paths):
        r = read_dxf(path)
        for layer, verts, closed in r.polylines:
            xs = [p[0] for p in verts] + ([verts[0][0]] if closed and verts else [])
            ys = [p[1] for p in verts] + ([verts[0][1]] if closed and verts else [])
            ax.plot(xs, ys, color=colour.get(layer, "#888"),
                    lw=2 if layer == LAYER_BOUNDARY else 1)
        for layer, a, b in r.lines:
            ax.plot([a[0], b[0]], [a[1], b[1]], color=colour.get(layer, "#888"), lw=1)
        for layer, pos, s in r.texts:
            ax.text(pos[0], pos[1], s, fontsize=7, ha="center")
        ax.set_aspect("equal")
        ax.set_title(Path(path).stem, fontsize=9)
        ax.grid(True, ls=":", alpha=0.4)
    for ax in axes[len(dxf_paths):]:
        ax.axis("off")
    fig.suptitle("Garment block DXF preview (read back from file)")
    fig.tight_layout()
    fig.savefig(png_path, dpi=130)
    print(f"wrote {png_path}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", default="12", help=f"preset: {', '.join(drafting.PRESETS)}")
    ap.add_argument("--blocks", nargs="+", default=list(ALL_BLOCKS),
                    choices=list(ALL_BLOCKS), help="which blocks to generate")
    ap.add_argument("--units", choices=["mm", "cm"], default="mm")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "out"))
    ap.add_argument("--preview", action="store_true", help="also write preview.png")
    # measurement overrides (cm)
    for fld in ("bust", "waist", "hip", "nape_to_waist", "skirt_length",
                "sleeve_length", "bicep", "hip_depth"):
        ap.add_argument(f"--{fld.replace('_', '-')}", type=float, default=None)
    args = ap.parse_args()

    m = drafting.get_measurements(args.size)
    for fld in ("bust", "waist", "hip", "nape_to_waist", "skirt_length",
                "sleeve_length", "bicep", "hip_depth"):
        v = getattr(args, fld)
        if v is not None:
            setattr(m, fld, v)

    scale = 10.0 if args.units == "mm" else 1.0
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for name in args.blocks:
        piece = ALL_BLOCKS[name](m)
        path = out_dir / f"{name}_sz{m.size}.dxf"
        piece_to_dxf(piece, str(path), scale)
        written.append(str(path))
        x0, y0, x1, y1 = piece.bbox()
        print(f"wrote {path}  ({(x1-x0):.1f} x {(y1-y0):.1f} cm)")

    if args.preview:
        preview(written, str(out_dir / f"preview_sz{m.size}.png"))

    print(f"\n{len(written)} DXF file(s) in {out_dir}  (units: {args.units}, "
          f"layers: 1=boundary 8=dart 11=notch 13=grain 15=label)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
