"""Capture a Polyscope overview of five-group best/worst SFTF orientations.

The figure is intended for insertion in the SFTF paper draft. It lays out all
five verification groups in one frame:

    Group A block, Group B block, Group C block, Group D block, Group E block

Each mesh row contains the original mesh, the best orientation, and the worst
orientation along +x. The remaining meshes in the same group are stacked along
-y, and the next group starts farther along +x. Large meshes are downsampled for
display only, while preserving triangles from the original surface. The build
direction stored in the per-mesh JSON is rotated to world +Z, so every thumbnail
shows the mesh in the corresponding print orientation. Originals are gray, best
copies are blue, and worst copies are red.

Usage:
    .venv\\Scripts\\python.exe scripts\\capture_five_group_best_worst_polyscope.py
    .venv\\Scripts\\python.exe scripts\\capture_five_group_best_worst_polyscope.py --show
    .venv\\Scripts\\python.exe scripts\\capture_five_group_best_worst_polyscope.py --groups A B
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import polyscope as ps
import trimesh

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cpp_src.Tomo_GPU2026.tomo_cpu import CRITICAL_ANGLE  # noqa: E402
from scripts._mesh_paths import G5_RAW_MESH

RESULT_DIR = PROJECT_ROOT / "Experimental" / "G5Test"
RAW_MESH_DIR = G5_RAW_MESH
SFTF_RESULT_DIR = RESULT_DIR / "SFTF_result"
MESH_EXTENSIONS = {".stl", ".obj", ".ply", ".off", ".3mf", ".glb"}
ORIGINAL_COLOR = (0.50, 0.53, 0.56)
BEST_COLOR = (0.20, 0.43, 0.86)
WORST_COLOR = (0.82, 0.22, 0.16)
PLATE_ORIGINAL = (0.78, 0.80, 0.82)
PLATE_BEST = (0.72, 0.81, 1.0)
PLATE_WORST = (1.0, 0.74, 0.70)


def angle_file_tag(angle_deg: float) -> str:
    """Filesystem-friendly critical-angle tag, e.g. 45 -> CA45deg."""
    text = f"{float(angle_deg):g}".replace("-", "m").replace(".", "p")
    return f"CA{text}deg"


def default_output_path(critical_angle_deg: float) -> Path:
    return RESULT_DIR / f"_5G_{angle_file_tag(critical_angle_deg)}_best_worst_polyscope.png"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-dir", type=Path, default=RESULT_DIR)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--critical-angle",
        type=float,
        default=None,
        help="Critical angle to embed in the default output filename. Defaults to result metadata, then current TOMO config.",
    )
    parser.add_argument("--groups", nargs="*", default=["A", "B", "C", "D", "E"])
    parser.add_argument("--max-faces", type=int, default=100000)
    parser.add_argument("--cell", type=float, default=1.28)
    parser.add_argument("--mesh-scale", type=float, default=0.82)
    parser.add_argument("--width", type=int, default=3840, help="Screenshot/window width in pixels.")
    parser.add_argument("--height", type=int, default=2140, help="Screenshot/window height in pixels.")
    parser.add_argument("--show", action="store_true", help="Open an interactive Polyscope window instead of only capturing.")
    parser.add_argument("--dry-run", action="store_true", help="List records and planned layout without opening Polyscope.")
    return parser.parse_args()


def group_id_from_stem(stem: str) -> tuple[str, str, int]:
    parts = stem.split("_")
    gid = parts[1] if len(parts) > 1 else ""
    group = gid[:1].upper() if gid else ""
    suffix = gid[1:]
    return group, gid, int(suffix) if suffix.isdigit() else 0


def load_records(result_dir: Path, groups: set[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    raw_mesh_dir = G5_RAW_MESH if result_dir.resolve() == RESULT_DIR.resolve() else result_dir / "RawMesh"
    sftf_result_dir = result_dir / "SFTF_result"
    mesh_paths = sorted(
        (p for p in raw_mesh_dir.glob("Group_*.*") if p.is_file() and p.suffix.lower() in MESH_EXTENSIONS),
        key=lambda p: group_id_from_stem(p.stem),
    )
    for mesh_path in mesh_paths:
        group, gid, order = group_id_from_stem(mesh_path.stem)
        if group not in groups:
            continue
        json_path = sftf_result_dir / f"{mesh_path.stem}.json"
        if not json_path.exists():
            json_path = result_dir / f"{mesh_path.stem}.json"
        if json_path.exists():
            record = json.loads(json_path.read_text(encoding="utf-8"))
        else:
            record = {"group": group, "group_id": gid, "mesh": mesh_path.name}
        record["group"] = group
        record["group_id"] = gid
        record["mesh"] = mesh_path.name
        record["_json_path"] = str(json_path) if json_path.exists() else None
        record["_mesh_path"] = str(mesh_path)
        record["_group"] = group
        record["_gid"] = gid
        record["_order"] = order
        rows.append(record)
    return sorted(rows, key=lambda r: (str(r["_group"]), int(r["_order"]), str(r.get("mesh"))))


def infer_critical_angle(records: list[dict[str, object]], explicit_angle: float | None) -> float:
    if explicit_angle is not None:
        return float(explicit_angle)
    angles = {
        float(r["critical_angle_deg"])
        for r in records
        if r.get("critical_angle_deg") is not None
    }
    if len(angles) == 1:
        return angles.pop()
    if len(angles) > 1:
        joined = ", ".join(f"{angle:g}" for angle in sorted(angles))
        print(f"warning: mixed critical_angle_deg values in result JSONs ({joined}); using {CRITICAL_ANGLE:g}", flush=True)
    return float(CRITICAL_ANGLE)


def direction_from_entry(entry: object) -> np.ndarray | None:
    if not isinstance(entry, dict):
        return None
    direction = entry.get("direction")
    if not direction:
        return None
    v = np.asarray(direction, dtype=np.float64)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else None


def best_worst_directions(record: dict[str, object]) -> tuple[np.ndarray | None, np.ndarray | None]:
    best = None
    worst = None
    cpp_best = record.get("sftf_cpp_optimal")
    cpp_worst = record.get("sftf_cpp_worst")
    if isinstance(cpp_best, list) and cpp_best:
        best = direction_from_entry(cpp_best[0])
    if isinstance(cpp_worst, list) and cpp_worst:
        worst = direction_from_entry(cpp_worst[0])

    # Fallback: Python SFTF stores top directions but not a worst list.
    if best is None:
        tops = record.get("top_directions")
        if isinstance(tops, list) and tops:
            best = direction_from_entry(tops[0])
    return best, worst


def rotation_between(source: np.ndarray, target: np.ndarray = np.array([0.0, 0.0, 1.0])) -> np.ndarray:
    """Rotation matrix mapping source unit vector to target unit vector."""
    source = source / max(float(np.linalg.norm(source)), 1e-12)
    target = target / max(float(np.linalg.norm(target)), 1e-12)
    cross = np.cross(source, target)
    dot = float(np.clip(np.dot(source, target), -1.0, 1.0))
    norm_cross = float(np.linalg.norm(cross))
    if norm_cross < 1e-12:
        if dot > 0.0:
            return np.eye(3)
        axis = np.array([1.0, 0.0, 0.0])
        if abs(source[0]) > 0.9:
            axis = np.array([0.0, 1.0, 0.0])
        axis = axis - source * np.dot(axis, source)
        axis /= max(float(np.linalg.norm(axis)), 1e-12)
        return axis_angle(axis, math.pi)
    axis = cross / norm_cross
    angle = math.atan2(norm_cross, dot)
    return axis_angle(axis, angle)


def axis_angle(axis: np.ndarray, angle: float) -> np.ndarray:
    x, y, z = axis
    c = math.cos(angle)
    s = math.sin(angle)
    t = 1.0 - c
    return np.array(
        [
            [t * x * x + c, t * x * y - s * z, t * x * z + s * y],
            [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
            [t * x * z - s * y, t * y * z + s * x, t * z * z + c],
        ],
        dtype=np.float64,
    )


def display_mesh(mesh_path: Path, max_faces: int) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(mesh_path, force="mesh", process=False)
    if not isinstance(mesh, trimesh.Trimesh):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if len(mesh.faces) <= max_faces:
        return mesh

    try:
        simplified = mesh.simplify_quadric_decimation(face_count=max_faces)
        if isinstance(simplified, trimesh.Trimesh) and len(simplified.faces) > 0:
            return simplified
    except Exception:
        pass

    # Fallback when optional simplification backends are absent. Keep sampled
    # original faces rather than a convex-hull proxy, so Groups C/D remain
    # visually recognizable in the overview.
    areas = np.asarray(mesh.area_faces, dtype=np.float64)
    if areas.shape[0] == len(mesh.faces) and float(areas.sum()) > 0.0:
        cdf = np.cumsum(areas)
        samples = (np.arange(max_faces, dtype=np.float64) + 0.5) * (cdf[-1] / max_faces)
        face_ids = np.searchsorted(cdf, samples, side="left")
        face_ids = np.unique(np.clip(face_ids, 0, len(mesh.faces) - 1))
    else:
        face_ids = np.linspace(0, len(mesh.faces) - 1, max_faces, dtype=np.int64)
    faces = np.asarray(mesh.faces[face_ids], dtype=np.int64)
    used, inverse = np.unique(faces.reshape(-1), return_inverse=True)
    vertices = np.asarray(mesh.vertices[used], dtype=np.float64)
    faces = inverse.reshape((-1, 3))
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def oriented_vertices(
    mesh: trimesh.Trimesh,
    build_direction: np.ndarray | None,
    center: np.ndarray,
    target_extent: float,
) -> np.ndarray:
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    vertices = vertices - 0.5 * (vertices.min(axis=0) + vertices.max(axis=0))
    if build_direction is not None:
        rot = rotation_between(build_direction)
        vertices = vertices @ rot.T
    extent = max(float(np.ptp(vertices, axis=0).max()), 1e-12)
    vertices = vertices * (target_extent / extent)
    vertices[:, 2] -= vertices[:, 2].min()
    vertices += center
    return vertices


def plate_geometry(center: np.ndarray, size: float, z: float) -> tuple[np.ndarray, np.ndarray]:
    half = 0.46 * size
    verts = np.array(
        [
            [center[0] - half, center[1] - half, z],
            [center[0] + half, center[1] - half, z],
            [center[0] + half, center[1] + half, z],
            [center[0] - half, center[1] + half, z],
        ],
        dtype=np.float64,
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    return verts, faces


def register_scene(records: list[dict[str, object]], args: argparse.Namespace) -> dict[str, object]:
    groups = [g for g in ["A", "B", "C", "D", "E"] if g in {str(r["_group"]) for r in records}]
    cell = float(args.cell)
    target_extent = float(args.mesh_scale) * cell
    variant_stride = 1.18 * cell
    row_stride = 1.38 * cell
    group_stride = 4.25 * cell

    ps.set_view_projection_mode("perspective")
    ps.set_program_name("SFTF five-group best/worst overview")
    ps.init()
    ps.set_up_dir("z_up")
    ps.set_ground_plane_mode("none")
    ps.set_window_size(int(args.width), int(args.height))

    scene_min = np.array([np.inf, np.inf, np.inf], dtype=np.float64)
    scene_max = np.array([-np.inf, -np.inf, -np.inf], dtype=np.float64)
    registered = 0
    skipped: list[str] = []

    max_rows = 0
    for group_index, group in enumerate(groups):
        group_records = [r for r in records if r["_group"] == group]
        max_rows = max(max_rows, len(group_records))
        group_x = group_index * group_stride
        for row, record in enumerate(group_records):
            mesh_path = Path(str(record["_mesh_path"]))
            mesh = display_mesh(mesh_path, int(args.max_faces))
            faces = np.asarray(mesh.faces, dtype=np.int64)
            best_dir, worst_dir = best_worst_directions(record)
            variants = [
                ("original", None, ORIGINAL_COLOR, PLATE_ORIGINAL),
                ("best", best_dir, BEST_COLOR, PLATE_BEST),
                ("worst", worst_dir, WORST_COLOR, PLATE_WORST),
            ]
            for variant_index, (label, direction, color, plate_color) in enumerate(variants):
                if direction is None and label != "original":
                    skipped.append(f"{record['_gid']} {label}")
                    continue
                center = np.array(
                    [
                        group_x + variant_index * variant_stride,
                        -row * row_stride,
                        0.0,
                    ],
                    dtype=np.float64,
                )
                verts = oriented_vertices(mesh, direction, center, target_extent)
                name = f"{record['_gid']}_{label}_{Path(str(record['mesh'])).stem}"
                ps_mesh = ps.register_surface_mesh(name, verts, faces, smooth_shade=True)
                ps_mesh.set_color(color)
                ps_mesh.set_edge_width(0.0)
                pv, pf = plate_geometry(center, 0.88 * cell, float(verts[:, 2].min()) - 0.01 * cell)
                plate = ps.register_surface_mesh(f"{record['_gid']}_{label}_plate", pv, pf, smooth_shade=False)
                plate.set_color(plate_color)
                plate.set_transparency(0.35)
                scene_min = np.minimum(scene_min, np.vstack([verts, pv]).min(axis=0))
                scene_max = np.maximum(scene_max, np.vstack([verts, pv]).max(axis=0))
                registered += 1

    center = 0.5 * (scene_min + scene_max)
    span = np.maximum(scene_max - scene_min, 1e-6)
    pad = 0.10 * max(float(span[0]), float(span[1]), cell)
    ps.set_bounding_box(tuple(scene_min - pad), tuple(scene_max + pad))
    fov_deg = 24.0
    aspect = float(args.width) / float(args.height)
    half = math.tan(math.radians(fov_deg) / 2.0)
    margin = 1.08
    dist_height = span[1] * margin / (2.0 * half)
    dist_width = span[0] * margin / (2.0 * half * aspect)
    dist = max(dist_height, dist_width, cell)
    camera_location = center + np.array([0.0, 0.0, dist], dtype=np.float64)
    intrinsics = ps.CameraIntrinsics(fov_vertical_deg=fov_deg, aspect=aspect)
    extrinsics = ps.CameraExtrinsics(
        root=camera_location,
        look_dir=center - camera_location,
        up_dir=np.array([0.0, 1.0, 0.0], dtype=np.float64),
    )
    ps.set_view_camera_parameters(ps.CameraParameters(intrinsics=intrinsics, extrinsics=extrinsics))
    return {
        "registered": registered,
        "skipped": skipped,
        "groups": groups,
        "rows": max_rows,
        "columns": 3 * len(groups),
        "window": (int(args.width), int(args.height)),
    }


def main() -> None:
    args = parse_args()
    groups = {g.upper() for g in args.groups}
    records = load_records(args.result_dir, groups)
    if not records:
        raise SystemExit(f"no records found in {args.result_dir} for groups {sorted(groups)}")
    critical_angle = infer_critical_angle(records, args.critical_angle)
    if args.output is None:
        args.output = default_output_path(critical_angle)

    if args.dry_run:
        by_group = {g: sum(1 for r in records if r["_group"] == g) for g in sorted(groups)}
        print(f"records={len(records)} groups={by_group}")
        print(f"critical_angle={critical_angle:g} output={args.output}")
        missing = []
        for record in records:
            best, worst = best_worst_directions(record)
            if best is None or worst is None:
                missing.append(str(record.get("mesh")))
        print(f"missing best/worst records={len(missing)}")
        for item in missing:
            print(f"  {item}")
        return

    info = register_scene(records, args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ps.screenshot(str(args.output), transparent_bg=False)
    try:
        framebuffer_size = tuple(int(v) for v in ps.get_buffer_size())
    except Exception:
        framebuffer_size = info["window"]
    print(
        f"saved {args.output}  requested={info['window'][0]}x{info['window'][1]} "
        f"framebuffer={framebuffer_size[0]}x{framebuffer_size[1]} "
        f"registered={info['registered']} groups={','.join(info['groups'])}",
        flush=True,
    )
    if info["skipped"]:
        print("skipped missing directions: " + ", ".join(info["skipped"]), flush=True)
    if args.show:
        ps.show()


if __name__ == "__main__":
    main()
