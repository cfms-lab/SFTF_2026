"""Re-compose Figure 6 (five-group best/worst overview) into a compact, titled layout.

The original single-scene capture left a large empty bottom-left quadrant because
groups A/B/C have 5 meshes while D/E have 10. Here each group is rendered on its
own (uniform per-mesh scale, top-down print-orientation view) and the five group
images are tiled into a compact landscape figure with "Group A".."Group E" titles:

    Row 1:  Group A | Group B | Group C        (each a vertical 5-row stack)
    Row 2:  Group D | Group E                  (each a vertical 5-row x 2-column
                                                stack), both rows packed centered.

Originals are gray, best orientations blue, worst orientations red.

Note: the mesh folder contains a stray ``Group_D10_65942.stl`` whose number 65942
is actually E10 (``Group_E10_65942.stl``). It is a mislabeled duplicate of E10, so
it is dropped from group D here (group D keeps its 10 canonical meshes D1..D10).

Run:  .venv\\Scripts\\python.exe scripts\\render_figure6_grouped.py
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np
import polyscope as ps
from PIL import Image

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.capture_four_group_best_worst_polyscope import (  # noqa: E402
    BEST_COLOR,
    ORIGINAL_COLOR,
    PLATE_BEST,
    PLATE_ORIGINAL,
    PLATE_WORST,
    RESULT_DIR,
    WORST_COLOR,
    best_worst_directions,
    display_mesh,
    load_records,
    oriented_vertices,
    plate_geometry,
)

CELL = 1.28
TARGET_EXTENT = 0.82 * CELL
VARIANT_STRIDE = 1.18 * CELL
ROW_STRIDE = 1.42 * CELL
COL_GAP = 0.70 * CELL  # horizontal gap between mesh-columns within a group

K_PX_PER_WORLD = 330.0  # constant world->pixel scale => uniform mesh size (hi-res)
PAD_WORLD = 0.5 * CELL  # margin around a group, in world units
FOV_DEG = 20.0

# Layout: every group is a vertical stack of up to NROWS rows; meshes beyond NROWS
# fold into the next column (so 10-mesh groups D/E become 5 rows x 2 columns).
GROUP_NROWS = 5
GROUP_ORDER = ["A", "B", "C", "D", "E"]
GROUP_TITLES = {k: f"Group {k}" for k in GROUP_ORDER}
BANDS = [["A", "B", "C"], ["D", "E"]]
VARIANTS = (
    ("original", None, ORIGINAL_COLOR, PLATE_ORIGINAL),
    ("best", "best", BEST_COLOR, PLATE_BEST),
    ("worst", "worst", WORST_COLOR, PLATE_WORST),
)


def init_polyscope() -> None:
    ps.set_view_projection_mode("perspective")
    ps.set_program_name("SFTF Figure 6 grouped overview")
    ps.init()
    ps.set_up_dir("z_up")
    ps.set_ground_plane_mode("none")


def mesh_number(name: str) -> str:
    """Trailing token of a Group_XN_<id> stem, used to spot cross-group duplicates."""
    stem = Path(str(name)).stem
    return stem.split("_")[-1]


def dedupe_records(records: list[dict]) -> list[dict]:
    """Drop group-D meshes whose number also appears in group E (mislabeled dups)."""
    e_numbers = {mesh_number(r["mesh"]) for r in records if r["_group"] == "E"}
    cleaned = []
    for r in records:
        if r["_group"] == "D" and mesh_number(r["mesh"]) in e_numbers:
            print(f"  dropping mislabeled duplicate from D: {r['mesh']} (already in E)")
            continue
        cleaned.append(r)
    return cleaned


def placements(n_meshes: int, nrows: int) -> list[tuple[int, int]]:
    """Column-major (col, row) placement: fill a column of ``nrows`` top-to-bottom,
    then move to the next column (vertical stacks)."""
    return [(idx // nrows, idx % nrows) for idx in range(n_meshes)]


def set_camera(cx: float, cy: float, view_w: float, view_h: float, win_w: int, win_h: int) -> None:
    half = math.tan(math.radians(FOV_DEG) / 2.0)
    dist = (0.5 * view_h) / half
    cam = np.array([cx, cy, dist], dtype=np.float64)
    intr = ps.CameraIntrinsics(fov_vertical_deg=FOV_DEG, aspect=win_w / win_h)
    extr = ps.CameraExtrinsics(
        root=cam,
        look_dir=np.array([0.0, 0.0, -1.0]),
        up_dir=np.array([0.0, 1.0, 0.0]),
    )
    ps.set_view_camera_parameters(ps.CameraParameters(intrinsics=intr, extrinsics=extr))


def render_group(records: list[dict], group: str, max_faces: int) -> Image.Image:
    recs = [r for r in records if r["_group"] == group]
    places = placements(len(recs), GROUP_NROWS)
    col_stride = 3 * VARIANT_STRIDE + COL_GAP

    ps.remove_all_structures()
    vmin = np.array([np.inf, np.inf], dtype=np.float64)
    vmax = np.array([-np.inf, -np.inf], dtype=np.float64)
    for mesh_index, (record, (col, row)) in enumerate(zip(recs, places)):
        mesh = display_mesh(Path(str(record["_mesh_path"])), int(max_faces))
        faces = np.asarray(mesh.faces, dtype=np.int64)
        best_dir, worst_dir = best_worst_directions(record)
        dir_lookup = {"best": best_dir, "worst": worst_dir}
        for variant_index, (label, dir_key, color, plate_color) in enumerate(VARIANTS):
            direction = None if dir_key is None else dir_lookup[dir_key]
            if dir_key is not None and direction is None:
                continue
            cx = col * col_stride + variant_index * VARIANT_STRIDE
            cy = -row * ROW_STRIDE
            center = np.array([cx, cy, 0.0], dtype=np.float64)
            verts = oriented_vertices(mesh, direction, center, TARGET_EXTENT)
            name = f"{group}_{mesh_index}_{label}"
            ps_mesh = ps.register_surface_mesh(name, verts, faces, smooth_shade=True)
            ps_mesh.set_color(color)
            ps_mesh.set_edge_width(0.0)
            pv, pf = plate_geometry(center, 0.88 * CELL, float(verts[:, 2].min()) - 0.01 * CELL)
            plate = ps.register_surface_mesh(f"{name}_plate", pv, pf, smooth_shade=False)
            plate.set_color(plate_color)
            plate.set_transparency(0.35)
            vmin = np.minimum(vmin, verts[:, :2].min(axis=0))
            vmax = np.maximum(vmax, verts[:, :2].max(axis=0))

    center_xy = 0.5 * (vmin + vmax)
    view_w = float(vmax[0] - vmin[0]) + 2 * PAD_WORLD
    view_h = float(vmax[1] - vmin[1]) + 2 * PAD_WORLD
    win_w = max(64, int(view_w * K_PX_PER_WORLD))
    win_h = max(64, int(view_h * K_PX_PER_WORLD))
    ps.set_window_size(win_w, win_h)
    set_camera(float(center_xy[0]), float(center_xy[1]), view_w, view_h, win_w, win_h)

    tmp = PROJECT_ROOT / f"_grp_{group}.png"
    ps.screenshot(str(tmp), transparent_bg=True)
    img = autocrop(Image.open(tmp).convert("RGBA"))
    tmp.unlink(missing_ok=True)
    return img


def autocrop(img: Image.Image, pad: int = 18) -> Image.Image:
    arr = np.asarray(img)
    ys, xs = np.where(arr[:, :, 3] > 8)
    if xs.size == 0:
        return img
    x0 = max(0, int(xs.min()) - pad)
    y0 = max(0, int(ys.min()) - pad)
    x1 = min(img.width - 1, int(xs.max()) + pad)
    y1 = min(img.height - 1, int(ys.max()) + pad)
    return img.crop((x0, y0, x1 + 1, y1 + 1))


def compose(images: dict[str, Image.Image], output: Path) -> None:
    gap = int(0.03 * max(images[k].width for k in images))
    title_h = 150
    band_gap = int(0.06 * max(images[k].height for k in images))

    def band_natural_width(keys):
        return sum(images[k].width for k in keys) + gap * (len(keys) - 1)

    content_w = max(band_natural_width(b) for b in BANDS)
    band_h = [max(images[k].height for k in b) for b in BANDS]
    content_h = sum(title_h + h for h in band_h) + band_gap * (len(BANDS) - 1)

    dpi = 300
    fig = plt.figure(figsize=(content_w / dpi, content_h / dpi), dpi=dpi)
    fig.patch.set_facecolor("white")

    y_cursor = 0  # pixels from top
    for band, bh in zip(BANDS, band_h):
        widths = [images[k].width for k in band]
        # Pack the groups together with a fixed gap and center the block on the page.
        total = sum(widths) + gap * (len(band) - 1)
        x = (content_w - total) / 2.0
        xs = []
        for w in widths:
            xs.append(x)
            x += w + gap
        for k, x, w in zip(band, xs, widths):
            im = images[k]
            ax = fig.add_axes(
                [
                    x / content_w,
                    1.0 - (y_cursor + title_h + im.height) / content_h,
                    w / content_w,
                    im.height / content_h,
                ]
            )
            ax.imshow(im)
            ax.axis("off")
            ax.set_title(GROUP_TITLES[k], fontsize=34, fontweight="bold", pad=10)
        y_cursor += title_h + bh + band_gap

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=dpi, facecolor="white", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print(f"saved {output}  ({content_w}x{content_h} px content)")


def main() -> None:
    records = dedupe_records(load_records(RESULT_DIR, set(GROUP_ORDER)))
    if not records:
        raise SystemExit(f"no records found in {RESULT_DIR}")
    init_polyscope()
    images = {}
    for group in GROUP_ORDER:
        n = sum(1 for r in records if r["_group"] == group)
        print(f"rendering group {group} ({n} meshes) ...", flush=True)
        images[group] = render_group(records, group, max_faces=100000)
    out_dir = PROJECT_ROOT / "draft" / "pics"
    compose(images, out_dir / "_5G_CA60deg_best_worst_grouped.png")


if __name__ == "__main__":
    main()
