from __future__ import annotations

from dataclasses import dataclass, field
import importlib.util
import io
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from matplotlib import colormaps
from matplotlib.colors import to_hex
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import trimesh
from scipy.spatial.transform import Rotation

ArrayLike = Sequence[float] | np.ndarray

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOMO_PROJECT_ROOT = PROJECT_ROOT.parent / "Tomo_GPU2024_CODEX"
GREEN = "\033[92m"
RESET = "\033[0m"
PRINT_FULL_ARRAYS = False
LARGE_MESH_FACE_THRESHOLD = 10_000
SHADER_ANGLE_STEP = 5.0
SHADER_CRITICAL_ANGLE = 60.0
SHADER_FBO_VOXEL_SIZE = 128
SHADER_FBO_BATCH_COLS = 18
SHADER_FBO_BATCH_ROWS = 18
SHADER_USE_TOMO_CPU_REFERENCES = True

# Rough calibration from local Bunny_69k runs:
# FboVtc 18x18 batch ~= 1.03 s for 69,662 faces, and ShTensor 60x60
# ~= 10.45 s for the same mesh after vectorization.
FBO_SECONDS_PER_FACE_DIRECTION = 4.6e-8
PY_SHADOW_SECONDS_PER_FACE_DIRECTION = 4.2e-8
VISFACEPAIR_REFERENCE_FACES = 69_662
VISFACEPAIR_REFERENCE_SECONDS = 240.0
CPP_SHADOW_SPEEDUP_FACTOR = 8.0
DEFAULT_MESH_PATH = "Experimental/etc/(7)Bunny_1k.obj"
SHADER_MESH_PATHS = [
    # "./Experimental/etc/box5cm_f16.stl",
    # "./Experimental/etc/sphere5cm_f169.stl",
    # "./Experimental/etc/FTree4x.stl",
    # "./Experimental/etc/(7)Bunny_1k.obj",
    "./Experimental/etc/(3)manikin.ply",
]


@dataclass
class TSE6Config:
    mesh: trimesh.Trimesh
    angles_yaw: Sequence[float] = field(default_factory=lambda: (0.0,))
    angles_pitch: Sequence[float] = field(default_factory=lambda: (0.0,))
    critical_angle: float = 60.0
    fbo_voxel_size: int | None = None
    renderer: Any | None = None
    orientation_pairs: np.ndarray | None = None
    orientation_inverse: np.ndarray | None = None
    timer_start: float | None = field(default=None, init=False, repr=False)

    def start_timer(self) -> None:
        self.timer_start = time.perf_counter()

    def end_timer(self, label: str = "TSE6 total time") -> float:
        if self.timer_start is None:
            raise RuntimeError("start_timer() must be called before end_timer().")

        elapsed = time.perf_counter() - self.timer_start
        print(f"{label}: {elapsed:.3f} s")
        self.timer_start = None
        return elapsed

    @property
    def full_direction_count(self) -> int:
        return len(self.angles_yaw) * len(self.angles_pitch)

    @property
    def compute_direction_count(self) -> int:
        if self.orientation_pairs is None:
            return self.full_direction_count
        return len(self.orientation_pairs)


def print_time(label: str, elapsed: float) -> None:
    print(f"{GREEN}{label}: {elapsed:.3f} s{RESET}", flush=True)


def format_duration(seconds: float) -> str:
    seconds = max(float(seconds), 0.0)
    if seconds < 60.0:
        return f"{seconds:.0f} s"
    minutes = seconds / 60.0
    if minutes < 60.0:
        return f"{minutes:.1f} min"
    hours = minutes / 60.0
    return f"{hours:.1f} h"


def estimate_runtime_seconds(config: TSE6Config, *, pipeline: str) -> dict[str, float]:
    face_count = len(config.mesh.faces)
    direction_count = config.compute_direction_count

    fbo_seconds = face_count * direction_count * FBO_SECONDS_PER_FACE_DIRECTION
    vis_seconds = VISFACEPAIR_REFERENCE_SECONDS * (face_count / VISFACEPAIR_REFERENCE_FACES)
    python_shadow_seconds = face_count * direction_count * PY_SHADOW_SECONDS_PER_FACE_DIRECTION

    if pipeline == "cpp":
        shadow_seconds = python_shadow_seconds / CPP_SHADOW_SPEEDUP_FACTOR
    elif pipeline == "python":
        shadow_seconds = python_shadow_seconds
    else:
        raise ValueError(f"unknown pipeline: {pipeline}")

    return {
        "fbo": fbo_seconds,
        "visfacepair": vis_seconds,
        "shadow": shadow_seconds,
        "total": fbo_seconds + vis_seconds + shadow_seconds,
    }


def print_runtime_estimate(config: TSE6Config, *, pipeline: str) -> None:
    face_count = len(config.mesh.faces)
    if face_count < LARGE_MESH_FACE_THRESHOLD:
        return

    full_direction_count = config.full_direction_count
    direction_count = config.compute_direction_count
    estimate = estimate_runtime_seconds(config, pipeline=pipeline)
    shadow_label = "C++ ShTensor" if pipeline == "cpp" else "Python ShTensor"

    print()
    print(f"{GREEN}Large mesh runtime estimate{RESET}", flush=True)
    print(f"faces: {face_count:,}")
    print(f"angle grid: {len(config.angles_yaw)} x {len(config.angles_pitch)} = {full_direction_count:,} yaw/pitch pairs")
    if direction_count != full_direction_count:
        print(f"unique compute directions: {direction_count:,}")
    print(f"estimated FboVtc: {format_duration(estimate['fbo'])}")
    print(f"estimated VisFacePair: {format_duration(estimate['visfacepair'])}")
    print(f"estimated {shadow_label}: {format_duration(estimate['shadow'])}")
    print(f"{GREEN}estimated total before plot/viewer: {format_duration(estimate['total'])}{RESET}")
    print("estimate is approximate; GPU, CPU threads, driver, and visibility candidates can change it.")
    print()


def print_array(label: str, values: np.ndarray) -> None:
    values = np.asarray(values)
    if PRINT_FULL_ARRAYS:
        print(f"{label}: \n", values)
        return

    print(
        f"{label}: shape={values.shape}, "
        f"min={np.nanmin(values):.6g}, max={np.nanmax(values):.6g}, "
        f"mean={np.nanmean(values):.6g}",
        flush=True,
    )


def rotation_key(yaw_deg: float, pitch_deg: float, rotation_tol: float = 1e-9) -> tuple[int, ...]:
    rotation = yaw_pitch_matrix(yaw_deg, pitch_deg)
    return tuple(np.round(rotation.reshape(-1) / rotation_tol).astype(np.int64))


def unique_orientation_grid(
    angles_yaw: Sequence[float],
    angles_pitch: Sequence[float],
    rotation_tol: float = 1e-9,
) -> tuple[np.ndarray, np.ndarray]:
    unique_pairs = []
    key_to_id = {}
    inverse = np.empty((len(angles_pitch), len(angles_yaw)), dtype=np.int64)

    for pitch_id, pitch_deg in enumerate(angles_pitch):
        for yaw_id, yaw_deg in enumerate(angles_yaw):
            key = rotation_key(float(yaw_deg), float(pitch_deg), rotation_tol=rotation_tol)
            unique_id = key_to_id.get(key)
            if unique_id is None:
                unique_id = len(unique_pairs)
                key_to_id[key] = unique_id
                unique_pairs.append((float(yaw_deg), float(pitch_deg)))
            inverse[pitch_id, yaw_id] = unique_id

    return np.asarray(unique_pairs, dtype=np.float64), inverse


def inclusive_angle_grid(angle_step: float) -> np.ndarray:
    step = float(angle_step)
    if step <= 0.0:
        raise ValueError("angle_step must be positive.")
    count = int(round(360.0 / step)) + 1
    return np.linspace(0.0, 360.0, num=count, endpoint=True, dtype=np.float64)


def compute_v_ss(config: TSE6Config, vis_pairs):
    from .FboVtc import FboVtc
    from .ShTensor import ShTensor

    def print_debug_values(label: str, values: np.ndarray) -> None:
        first_values = np.asarray(values, dtype=float).reshape(-1)[:3]
        formatted = ", ".join(f"{value:.6g}" for value in first_values)
        print(f"{label}: [{formatted}]", flush=True)

    f_vtc = FboVtc(config)
    sh_tensor = ShTensor(config)

    v_tc = f_vtc.run()
    sh_result = sh_tensor.run(vis_pairs)

    v_al_bt = sh_result.volumes["V_al_bt"]
    v_be_bt = sh_result.volumes["V_be_bt"]
    v_nv_bt = sh_result.volumes["V_nv_bt"]
    v_ss_bt = v_tc - (v_al_bt - v_be_bt) - v_nv_bt

    v_nv_vpair = sh_result.volumes["V_nv_vpair"]
    v_ss_vpair = sh_result.volumes["V_ss_vpair"]

    v_a = v_al_bt
    v_b = v_be_bt
    v_nv = v_nv_bt# + v_nv_vpair
    # if "V_nv" in sh_result.volumes and not np.allclose(sh_result.volumes["V_nv"], v_nv):
    #     raise ValueError("ShTensor V_nv must equal V_nv_bt + V_nv_vpair.")
    v_o = v_a - v_b
    v_ss = v_tc - v_o - v_nv# + v_ss_vpair

    print("compute_v_ss debug first 3 values:", flush=True)
    for label, values in (
        ("v_tc", v_tc),
        ("v_al_bt", v_al_bt),
        ("v_be_bt", v_be_bt),
        ("v_nv_bt", v_nv_bt),
        ("v_ss_bt", v_ss_bt),
        ("v_nv_vpair", v_nv_vpair),
        ("v_ss_vpair", v_ss_vpair),
        ("v_al", v_a),
        ("v_be", v_b),
        ("v_nv", v_nv),
        ("v_o", v_o),
        ("v_ss", v_ss),
    ):
        print_debug_values(label, values)

    return f_vtc, \
        np.array(v_tc, dtype=np.float64), \
        np.array(v_o, dtype=np.float64), \
        np.array(v_nv_bt, dtype=np.float64), \
        np.array(v_ss, dtype=np.float64), 


def write_numbers(f, values: np.ndarray, per_line: int = 8) -> None:
    flat = np.asarray(values).reshape(-1)
    for start in range(0, len(flat), per_line):
        row = flat[start : start + per_line]
        f.write(" ".join(f"{float(v):.17g}" for v in row))
        f.write("\n")


def visible_face_ids_from_pairs(vis_pairs) -> np.ndarray | None:
    if vis_pairs is None:
        return None

    face_ids = np.asarray(vis_pairs, dtype=np.int64).reshape(-1)
    if face_ids.size == 0:
        return np.empty(0, dtype=np.int64)
    return np.unique(face_ids)


def triangles_from_config_mesh(config: TSE6Config) -> np.ndarray:
    mesh = config.mesh.copy()
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    return np.asarray(mesh.triangles, dtype=np.float64)


def write_cpp_sh_tensor_input(
    f,
    *,
    angles_yaw: np.ndarray,
    angles_pitch: np.ndarray,
    critical_angle: float,
    vtc: np.ndarray,
    tris: np.ndarray,
    visible_face_ids: np.ndarray,
) -> None:
    f.write("TSE6VSS2\n")
    f.write(
        f"COUNTS {len(angles_yaw)} {len(angles_pitch)} {len(tris)} "
        f"{len(visible_face_ids)}\n"
    )
    f.write(f"CRITICAL_ANGLE_RAD {np.deg2rad(critical_angle):.17g}\n")

    f.write("VTC\n")
    write_numbers(f, vtc)

    f.write("ANGLES_YAW\n")
    write_numbers(f, angles_yaw)

    f.write("ANGLES_PITCH\n")
    write_numbers(f, angles_pitch)

    f.write("TRIANGLES\n")
    for tri in tris:
        write_numbers(f, tri.reshape(1, 9), per_line=9)

    f.write("VISIBLE_FACE_IDS\n")
    for start_id in range(0, len(visible_face_ids), 16):
        f.write(" ".join(str(int(v)) for v in visible_face_ids[start_id : start_id + 16]))
        f.write("\n")


def build_cpp_input(
    config: TSE6Config,
    *,
    vis_pairs=None,
    tris: np.ndarray | None = None,
) -> str:
    from .FboVtc import FboVtc
    from .VisFacePair import VisFacePair

    angles_yaw = np.asarray(config.angles_yaw, dtype=np.float64)
    angles_pitch = np.asarray(config.angles_pitch, dtype=np.float64)

    start = time.perf_counter()
    vtc = FboVtc(config).run()
    if vis_pairs is None:
        vis_pairs = VisFacePair(config).run()
    if tris is None:
        tris = triangles_from_config_mesh(config)
    elapsed = time.perf_counter() - start

    visible_face_ids = visible_face_ids_from_pairs(vis_pairs)
    if visible_face_ids is None:
        visible_face_ids = np.arange(len(tris), dtype=np.int64)
    visible_face_ids = np.asarray(visible_face_ids, dtype=np.int64).reshape(-1)

    buffer = io.StringIO(newline="\n")
    write_cpp_sh_tensor_input(
        buffer,
        angles_yaw=angles_yaw,
        angles_pitch=angles_pitch,
        critical_angle=config.critical_angle,
        vtc=vtc,
        tris=tris,
        visible_face_ids=visible_face_ids,
    )

    print_time("Python FboVtc + C++ input prep time", elapsed)
    return buffer.getvalue()


def export_input(
    output: Path,
    config: TSE6Config,
    *,
    vis_pairs=None,
    tris: np.ndarray | None = None,
) -> None:
    input_text = build_cpp_input(config, vis_pairs=vis_pairs, tris=tris)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(input_text, encoding="utf-8", newline="\n")
    print(f"wrote: {output}")


def parse_vss_from_stdout(stdout: str, yaw_count: int, pitch_count: int) -> np.ndarray:
    for line in stdout.splitlines():
        if not line.startswith("VSS_FLAT"):
            continue
        values = np.fromstring(line[len("VSS_FLAT") :], sep=" ", dtype=np.float64)
        expected = yaw_count * pitch_count
        if values.size != expected:
            raise ValueError(f"expected {expected} v_ss values from C++, got {values.size}")
        return values.reshape(pitch_count, yaw_count)

    raise RuntimeError("C++ output did not contain VSS_FLAT data.")


def run_cpp_benchmark(
    exe_path: Path,
    input_path: Path,
    config: TSE6Config,
    *,
    threads: int | None = None,
    input_text: str | None = None,
) -> np.ndarray:
    if not exe_path.exists():
        raise FileNotFoundError(f"tse6_vss.exe not found: {exe_path}")

    command = [
        str(exe_path),
        "-" if input_text is not None else str(input_path),
        "--quiet",
        "--emit-vss",
    ]
    if threads is not None:
        command.extend(["--threads", str(threads)])

    start = time.perf_counter()
    completed = subprocess.run(
        command,
        input=input_text,
        text=True,
        capture_output=True,
        check=True,
    )
    print_time("tse6_vss.exe wall time", time.perf_counter() - start)
    for line in completed.stdout.splitlines():
        if not line.startswith("VSS_FLAT"):
            print(line)
    return parse_vss_from_stdout(
        completed.stdout,
        len(config.angles_yaw),
        len(config.angles_pitch),
    )


def export_input_and_run_cpp(
    output: Path,
    exe_path: Path,
    config: TSE6Config,
    *,
    renderer=None,
    threads: int | None = None,
    pipe: bool = False,
) -> None:
    from .VisFacePair import VisFacePair

    vis_pairs = VisFacePair(config).run()
    tris = triangles_from_config_mesh(config)

    if pipe:
        input_text = build_cpp_input(config, vis_pairs=vis_pairs, tris=tris)
        vss = run_cpp_benchmark(exe_path, output, config, threads=threads, input_text=input_text)
    else:
        export_input(output, config, vis_pairs=vis_pairs, tris=tris)
        vss = run_cpp_benchmark(exe_path, output, config, threads=threads)

    min_vss_rows, max_vss_rows = summarize_v_ss_extremes(
        config,
        vss,
    )

    fig = make_support_volume_figure(
        config.angles_yaw,
        config.angles_pitch,
        vss,
    )
    add_v_ss_extreme_annotations(fig, min_vss_rows, max_vss_rows)
    fig.show()

    if renderer is not None:
        renderer.init()
        renderer.set_up_dir("z_up")
        render_v_ss_extreme_orientations(
            renderer,
            config.mesh,
            min_vss_rows,
            max_vss_rows,
        )
        renderer.show()


def make_tse6_config(
    renderer: Any | None = None,
    mesh_path: str = DEFAULT_MESH_PATH,
    angle_step: float = 10.0,
    critical_angle: float = 60.0,
    fbo_voxel_size: int | None = None,
    deduplicate_orientations: bool = True,
) -> TSE6Config:
    angles = inclusive_angle_grid(angle_step)
    np.set_printoptions(precision=1, suppress=True)
    mesh = trimesh.load_mesh(mesh_path, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)

    orientation_pairs = None
    orientation_inverse = None
    if deduplicate_orientations:
        orientation_pairs, orientation_inverse = unique_orientation_grid(angles, angles)
        removed = len(angles) * len(angles) - len(orientation_pairs)
        if removed > 0:
            print(
                f"{GREEN}unique rotation grid: {len(orientation_pairs):,} compute directions "
                f"from {len(angles) * len(angles):,} yaw/pitch pairs "
                f"({removed:,} duplicates skipped){RESET}",
                flush=True,
            )

    return TSE6Config(
        mesh=mesh,
        angles_yaw=angles,
        angles_pitch=angles,
        critical_angle=float(critical_angle),
        fbo_voxel_size=None if fbo_voxel_size is None else int(fbo_voxel_size),
        renderer=renderer,
        orientation_pairs=orientation_pairs,
        orientation_inverse=orientation_inverse,
    )


def find_v_ss_extreme_orientations(
    v_ss: np.ndarray,
    angles_yaw: np.ndarray,
    angles_pitch: np.ndarray,
    count: int = 3,
    rotation_tol: float = 1e-9,
) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    values = np.asarray(v_ss, dtype=float)
    finite_flat_ids = np.flatnonzero(np.isfinite(values).reshape(-1))
    if finite_flat_ids.size == 0:
        raise ValueError("v_ss has no finite values.")

    flat_values = values.reshape(-1)
    sorted_by_value = finite_flat_ids[np.argsort(flat_values[finite_flat_ids], kind="stable")]

    def unique_flat_ids(flat_ids: np.ndarray) -> list[int]:
        selected = []
        seen_rotations = set()
        for flat_id in flat_ids:
            pitch_id, yaw_id = np.unravel_index(int(flat_id), values.shape)
            key = rotation_key(float(angles_yaw[yaw_id]), float(angles_pitch[pitch_id]), rotation_tol=rotation_tol)
            if key in seen_rotations:
                continue
            seen_rotations.add(key)
            selected.append(int(flat_id))
            if len(selected) >= count:
                break
        return selected

    min_flat_ids = unique_flat_ids(sorted_by_value)
    max_flat_ids = unique_flat_ids(sorted_by_value[::-1])

    def make_rows(flat_ids: Sequence[int]) -> list[dict[str, float]]:
        rows = []
        for flat_id in flat_ids:
            pitch_id, yaw_id = np.unravel_index(int(flat_id), values.shape)
            rows.append(
                {
                    "yaw": float(angles_yaw[yaw_id]),
                    "pitch": float(angles_pitch[pitch_id]),
                    "value": float(values[pitch_id, yaw_id]),
                }
            )
        return rows

    return make_rows(min_flat_ids), make_rows(max_flat_ids)


def print_v_ss_extreme_orientations(
    min_rows: list[dict[str, float]],
    max_rows: list[dict[str, float]],
) -> None:
    print()
    print("v_ss minimum orientations:")
    for rank, row in enumerate(min_rows, start=1):
        print(f"{rank}. yaw={row['yaw']:.1f}, pitch={row['pitch']:.1f}, v_ss={row['value']:.6g}")

    if max_rows:
        print("v_ss maximum orientations:")
        for rank, row in enumerate(max_rows, start=1):
            print(f"{rank}. yaw={row['yaw']:.1f}, pitch={row['pitch']:.1f}, v_ss={row['value']:.6g}")
    print()


def rotated_vertices_at_origin(vertices: np.ndarray, yaw_deg: float, pitch_deg: float) -> np.ndarray:
    rotation = yaw_pitch_matrix(yaw_deg, pitch_deg)
    rotated = np.asarray(vertices, dtype=np.float64) @ rotation.T
    rotated -= rotated.min(axis=0)
    return rotated


def render_v_ss_extreme_orientations(
    renderer,
    mesh: trimesh.Trimesh,
    min_rows: list[dict[str, float]],
    max_rows: list[dict[str, float]],
) -> None:
    clean_mesh = mesh.copy()
    clean_mesh.remove_unreferenced_vertices()
    vertices = np.ascontiguousarray(clean_mesh.vertices, dtype=np.float64)
    faces = np.ascontiguousarray(clean_mesh.faces, dtype=np.int32)

    input_mesh = renderer.register_surface_mesh(
        "input mesh reference",
        vertices,
        faces,
        smooth_shade=False,
        color=(0.72, 0.72, 0.72),
    )
    if hasattr(input_mesh, "set_transparency"):
        input_mesh.set_transparency(0.22)

    optimal_group = renderer.create_group("optimals") if hasattr(renderer, "create_group") else None
    worst_group = renderer.create_group("worsts") if hasattr(renderer, "create_group") else None
    render_items = []

    for row_id, (group_name, label_prefix, rows, color, group) in enumerate(
        (
            ("optimals", "o", min_rows, (0.10, 0.55, 0.95), optimal_group),
            ("worsts", "w", max_rows, (0.95, 0.36, 0.20), worst_group),
        )
    ):
        for col_id, (rank, row) in enumerate(zip(range(1, len(rows) + 1), rows)):
            rotated_vertices = rotated_vertices_at_origin(vertices, row["yaw"], row["pitch"])
            mesh_label = f"{label_prefix}{rank}"
            render_items.append((group_name, group, row_id, col_id, mesh_label, row, color, rotated_vertices))

    if not render_items:
        return

    input_bounds = np.asarray(clean_mesh.bounds, dtype=np.float64)
    input_extent = np.maximum(input_bounds[1] - input_bounds[0], 1e-6)
    rotated_extents = np.asarray(
        [item[-1].max(axis=0) - item[-1].min(axis=0) for item in render_items],
        dtype=np.float64,
    )
    cell_extent = np.maximum(rotated_extents.max(axis=0), 1e-6)
    gap = 0.15 * max(float(input_extent.max()), float(cell_extent.max()), 1e-6)
    grid_origin = np.array(
        [
            input_bounds[1, 0] + gap,
            input_bounds[0, 1],
            input_bounds[0, 2],
        ],
        dtype=np.float64,
    )
    cell_step = cell_extent + gap

    for group_name, group, row_id, col_id, mesh_label, row, color, rotated_vertices in render_items:
        offset = grid_origin + np.array(
            [
                col_id * cell_step[0],
                row_id * cell_step[1],
                0.0,
            ],
            dtype=np.float64,
        )
        placed_vertices = np.ascontiguousarray(rotated_vertices + offset, dtype=np.float64)
        ps_mesh = renderer.register_surface_mesh(
            f"{mesh_label} {group_name} yaw={row['yaw']:.1f} pitch={row['pitch']:.1f}",
            placed_vertices,
            faces,
            smooth_shade=False,
            color=color,
        )
        if hasattr(ps_mesh, "set_transparency"):
            ps_mesh.set_transparency(0.42)
        if group is not None:
            ps_mesh.add_to_group(group)
        ps_mesh.add_scalar_quantity(
            "v_ss",
            np.full(len(placed_vertices), row["value"], dtype=np.float64),
            enabled=False,
        )


def summarize_v_ss_extremes(
    config: TSE6Config,
    v_ss: np.ndarray,
    count: int = 3,
    include_max: bool = True,
) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    min_rows, max_rows = find_v_ss_extreme_orientations(
        v_ss,
        np.asarray(config.angles_yaw, dtype=float),
        np.asarray(config.angles_pitch, dtype=float),
        count=count,
    )
    if not include_max:
        max_rows = []
    print_v_ss_extreme_orientations(min_rows, max_rows)
    return min_rows, max_rows


def as_array(x: ArrayLike, dtype=float) -> np.ndarray:
    return np.asarray(x, dtype=dtype)


def normalize(v: ArrayLike, *, eps: float = 1e-15) -> np.ndarray:
    v = as_array(v)
    length = np.linalg.norm(v)
    if length < eps:
        raise ValueError("cannot normalize a zero-length vector")
    return v / length


def yaw_pitch_rotation(yaw_deg: float, pitch_deg: float) -> Rotation:
    return Rotation.from_euler("xyz", [float(yaw_deg), float(pitch_deg), 0.0], degrees=True)


def yaw_pitch_matrix(yaw_deg: float, pitch_deg: float) -> np.ndarray:
    return yaw_pitch_rotation(yaw_deg, pitch_deg).as_matrix()


def get_center(vertices: np.ndarray) -> np.ndarray:
    return as_array(vertices).mean(axis=0)


def get_tri_normal(tri: np.ndarray) -> np.ndarray:
    tri = as_array(tri)
    return normalize(np.cross(tri[1] - tri[0], tri[2] - tri[0]))


def get_tri_list_normal(trilist: np.ndarray) -> np.ndarray:
    return np.asarray([get_tri_normal(tri) for tri in trilist], dtype=float)


def triangle_areas(tris: np.ndarray) -> np.ndarray:
    tris = as_array(tris)
    return 0.5 * np.linalg.norm(
        np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]),
        axis=1,
    )


def project_tris_to_plane(tris: np.ndarray, plane: Mapping[str, ArrayLike]) -> np.ndarray:
    tris = as_array(tris)
    normal = normalize(plane["normal"])
    origin = as_array(plane["origin"])
    flat = tris.reshape(-1, 3)
    projected = flat - np.outer((flat - origin) @ normal, normal)
    return projected.reshape(tris.shape)


def get_tris_on_plane(tris: np.ndarray, plane: Mapping[str, ArrayLike]) -> np.ndarray:
    return project_tris_to_plane(tris, plane)


def arrow_color_values(sizes: ArrayLike) -> np.ndarray:
    sizes = as_array(sizes)
    out = np.zeros_like(sizes, dtype=float)
    positive = sizes > 0
    negative = sizes < 0
    if np.any(positive):
        out[positive] = sizes[positive] / np.max(sizes[positive])
    if np.any(negative):
        out[negative] = -sizes[negative] / np.min(sizes[negative])
    return out


def draw_tri_struc(ts: Mapping[str, ArrayLike], orientation_vectors: np.ndarray) -> dict[str, np.ndarray]:
    center = as_array(ts["center"])
    sizes = as_array(ts["tensorsize"])
    orientation_vectors = as_array(orientation_vectors)
    vectors = np.abs(sizes)[:, None] * orientation_vectors
    return {
        "start": np.repeat(center[None, :], len(vectors), axis=0),
        "end": center[None, :] - vectors,
        "color_value": arrow_color_values(sizes),
    }


COOLWARM_COLORSCALE = [
    (i / 255.0, to_hex(colormaps["coolwarm"](i / 255.0)))
    for i in range(256)
]


def axis_data_range(values: Sequence[float]) -> list[float]:
    values_arr = np.asarray(values, dtype=float)
    return [float(np.nanmin(values_arr)), float(np.nanmax(values_arr))]


def make_support_volume_figure(
    angles_yaw: Sequence[float],
    angles_pitch: Sequence[float],
    support_volume: np.ndarray,
    colorscale=COOLWARM_COLORSCALE,
) -> go.Figure:
    yaw_range = axis_data_range(angles_yaw)
    pitch_range = axis_data_range(angles_pitch)
    fig = go.Figure(
        data=go.Contour(
            x=np.asarray(angles_yaw, dtype=float),
            y=np.asarray(angles_pitch, dtype=float),
            z=np.asarray(support_volume, dtype=float),
            colorscale=colorscale,
            contours=dict(showlabels=True),
            colorbar=dict(title="v_ss"),
        )
    )
    fig.update_layout(
        title="Support Structure Volume (v_ss)",
        xaxis_title="Yaw angle (deg)",
        yaxis_title="Pitch angle (deg)",
        xaxis=dict(
            range=yaw_range,
            constrain="domain",
        ),
        yaxis=dict(
            range=pitch_range,
            scaleanchor="x",
            scaleratio=1,
            constrain="domain",
        ),
    )
    return fig


def add_v_ss_extreme_annotations(
    fig: go.Figure,
    min_rows: Sequence[Mapping[str, float]],
    max_rows: Sequence[Mapping[str, float]],
) -> go.Figure:
    optimal_labels = [f"o{rank}" for rank in range(1, len(min_rows) + 1)]
    worst_labels = [f"w{rank}" for rank in range(1, len(max_rows) + 1)]

    fig.add_trace(
        go.Scatter(
            x=[row["yaw"] for row in min_rows],
            y=[row["pitch"] for row in min_rows],
            mode="markers+text",
            name="optimals",
            text=optimal_labels,
            textposition="top center",
            marker=dict(
                symbol="circle",
                size=12,
                color="#1874d1",
                line=dict(color="#ffffff", width=2),
            ),
            customdata=[row["value"] for row in min_rows],
            hovertemplate="optimal %{text}<br>yaw=%{x:.1f}<br>pitch=%{y:.1f}<br>v_ss=%{customdata:.6g}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[row["yaw"] for row in max_rows],
            y=[row["pitch"] for row in max_rows],
            mode="markers+text",
            name="worsts",
            text=worst_labels,
            textposition="bottom center",
            marker=dict(
                symbol="x",
                size=14,
                color="#d9472b",
                line=dict(color="#ffffff", width=2),
            ),
            customdata=[row["value"] for row in max_rows],
            hovertemplate="worst %{text}<br>yaw=%{x:.1f}<br>pitch=%{y:.1f}<br>v_ss=%{customdata:.6g}<extra></extra>",
        )
    )
    return fig


def mesh_label(mesh_path: str) -> str:
    return Path(mesh_path).stem


def add_grid_v_ss_extreme_markers(
    fig: go.Figure,
    min_rows: Sequence[Mapping[str, float]],
    max_rows: Sequence[Mapping[str, float]],
    *,
    row: int,
    col: int,
    showlegend: bool,
) -> None:
    fig.add_trace(
        go.Scatter(
            x=[item["yaw"] for item in min_rows],
            y=[item["pitch"] for item in min_rows],
            mode="markers+text",
            name="optimals",
            legendgroup="optimals",
            showlegend=showlegend,
            text=[f"o{rank}" for rank in range(1, len(min_rows) + 1)],
            textposition="top center",
            marker=dict(
                symbol="circle",
                size=10,
                color="#1874d1",
                line=dict(color="#ffffff", width=2),
            ),
            customdata=[item["value"] for item in min_rows],
            hovertemplate="optimal %{text}<br>yaw=%{x:.1f}<br>pitch=%{y:.1f}<br>v_ss=%{customdata:.6g}<extra></extra>",
        ),
        row=row,
        col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=[item["yaw"] for item in max_rows],
            y=[item["pitch"] for item in max_rows],
            mode="markers+text",
            name="worsts",
            legendgroup="worsts",
            showlegend=showlegend,
            text=[f"w{rank}" for rank in range(1, len(max_rows) + 1)],
            textposition="bottom center",
            marker=dict(
                symbol="x",
                size=12,
                color="#d9472b",
                line=dict(color="#ffffff", width=2),
            ),
            customdata=[item["value"] for item in max_rows],
            hovertemplate="worst %{text}<br>yaw=%{x:.1f}<br>pitch=%{y:.1f}<br>v_ss=%{customdata:.6g}<extra></extra>",
        ),
        row=row,
        col=col,
    )


def make_grid_support_volume_figure(results: Sequence[Mapping[str, object]]) -> go.Figure:
    cols = 2
    rows = int(np.ceil(len(results) / cols))
    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=[str(result["label"]) for result in results],
        horizontal_spacing=0.08,
        vertical_spacing=0.12,
    )

    for result_id, result in enumerate(results):
        row = result_id // cols + 1
        col = result_id % cols + 1
        cfg = result["cfg"]
        fig.add_trace(
            go.Contour(
                x=np.asarray(cfg.angles_yaw, dtype=float),
                y=np.asarray(cfg.angles_pitch, dtype=float),
                z=np.asarray(result["v_ss"], dtype=float),
                colorscale=COOLWARM_COLORSCALE,
                contours=dict(showlabels=True),
                colorbar=dict(title="v_ss") if result_id == len(results) - 1 else None,
                showscale=result_id == len(results) - 1,
                hovertemplate="yaw=%{x:.1f}<br>pitch=%{y:.1f}<br>v_ss=%{z:.6g}<extra></extra>",
            ),
            row=row,
            col=col,
        )
        add_grid_v_ss_extreme_markers(
            fig,
            result["min_rows"],
            result["max_rows"],
            row=row,
            col=col,
            showlegend=result_id == 0,
        )
        axis_id = result_id + 1
        x_anchor = "x" if axis_id == 1 else f"x{axis_id}"
        yaw_range = axis_data_range(cfg.angles_yaw)
        pitch_range = axis_data_range(cfg.angles_pitch)
        fig.update_yaxes(
            title_text="Pitch angle (deg)",
            range=pitch_range,
            scaleanchor=x_anchor,
            scaleratio=1,
            constrain="domain",
            row=row,
            col=col,
        )
        fig.update_xaxes(
            title_text="Yaw angle (deg)",
            range=yaw_range,
            constrain="domain",
            row=row,
            col=col,
        )

    fig.update_layout(
        title="Support Structure Volume (v_ss)",
        height=max(420 * rows, 520),
        width=1100,
    )
    return fig


def compute_tomo_cpu_reference_grid(*args, **kwargs) -> dict[str, object]:
    module_path = PROJECT_ROOT / "python_src" / "VisPairAApprx" / "tomo_cpu.py"
    spec = importlib.util.spec_from_file_location("tse6_shader_tomo_cpu", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"failed to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.compute_tomo_cpu_reference_grid(*args, **kwargs)


def run_shader_mesh(
    renderer,
    mesh_path: str,
    *,
    angle_step: float = SHADER_ANGLE_STEP,
    critical_angle: float = SHADER_CRITICAL_ANGLE,
    fbo_voxel_size: int = SHADER_FBO_VOXEL_SIZE,
    batch_cols: int = SHADER_FBO_BATCH_COLS,
    batch_rows: int = SHADER_FBO_BATCH_ROWS,
) -> dict[str, object]:
    from .FboVtc import FboVtc

    cfg = make_tse6_config(
        renderer=renderer,
        mesh_path=mesh_path,
        angle_step=angle_step,
        critical_angle=critical_angle,
        fbo_voxel_size=fbo_voxel_size,
        deduplicate_orientations=True,
    )
    print(f"\n=== {mesh_path} ===", flush=True)
    f_vtc = FboVtc(
        cfg,
        batch_cols=batch_cols,
        batch_rows=batch_rows,
    )
    components = f_vtc.run_beta_components()
    fbo_v_tc = np.asarray(components["V_tc"], dtype=np.float64)
    fbo_v_nv = np.asarray(components["V_nv"], dtype=np.float64)
    fbo_v_ss = np.asarray(components["V_ss"], dtype=np.float64)
    min_rows, max_rows = find_v_ss_extreme_orientations(
        fbo_v_ss,
        np.asarray(cfg.angles_yaw, dtype=np.float64),
        np.asarray(cfg.angles_pitch, dtype=np.float64),
        count=3,
    )

    return {
        "mesh_path": mesh_path,
        "label": mesh_label(mesh_path),
        "cfg": cfg,
        "f_vtc": f_vtc,
        "v_tc": fbo_v_tc,
        "v_nv": fbo_v_nv,
        "v_ss": fbo_v_ss,
        "min_rows": min_rows,
        "max_rows": max_rows,
    }


def attach_tomo_cpu_references(
    results: list[dict[str, object]],
    *,
    tomo_project_root: Path = TOMO_PROJECT_ROOT,
    critical_angle: float = SHADER_CRITICAL_ANGLE,
    angle_step: float = SHADER_ANGLE_STEP,
) -> None:
    for result in results:
        tomo = compute_tomo_cpu_reference_grid(
            mesh_path=str(result["mesh_path"]),
            tomo_project_root=tomo_project_root,
            critical_angle=critical_angle,
            angle_step=angle_step,
        )
        result["tomo_yaw"] = np.asarray(tomo["yaw_values"], dtype=np.float64)
        result["tomo_pitch"] = np.asarray(tomo["pitch_values"], dtype=np.float64)
        result["tomo_v_tc"] = np.asarray(tomo["vtc_grid"], dtype=np.float64)
        result["tomo_v_nv"] = np.asarray(tomo["vnv_grid"], dtype=np.float64)
        result["tomo_v_ss"] = np.asarray(tomo["vss_grid"], dtype=np.float64)


def add_shader_extreme_markers(
    fig: go.Figure,
    min_rows: list[dict[str, float]],
    max_rows: list[dict[str, float]],
    *,
    value_label: str,
    row: int,
    col: int,
    showlegend: bool,
) -> None:
    fig.add_trace(
        go.Scatter(
            x=[item["yaw"] for item in min_rows],
            y=[item["pitch"] for item in min_rows],
            mode="markers+text",
            name="optimal",
            legendgroup="optimal",
            showlegend=showlegend,
            text=[f"o{rank}" for rank in range(1, len(min_rows) + 1)],
            textposition="top center",
            marker=dict(
                symbol="circle",
                size=10,
                color="#1874d1",
                line=dict(color="#ffffff", width=2),
            ),
            customdata=[item["value"] for item in min_rows],
            hovertemplate=(
                "optimal %{text}<br>"
                "yaw=%{x:.1f}<br>"
                "pitch=%{y:.1f}<br>"
                f"{value_label}=%{{customdata:.6g}}<extra></extra>"
            ),
        ),
        row=row,
        col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=[item["yaw"] for item in max_rows],
            y=[item["pitch"] for item in max_rows],
            mode="markers+text",
            name="worst",
            legendgroup="worst",
            showlegend=showlegend,
            text=[f"w{rank}" for rank in range(1, len(max_rows) + 1)],
            textposition="bottom center",
            marker=dict(
                symbol="x",
                size=12,
                color="#d9472b",
                line=dict(color="#ffffff", width=2),
            ),
            customdata=[item["value"] for item in max_rows],
            hovertemplate=(
                "worst %{text}<br>"
                "yaw=%{x:.1f}<br>"
                "pitch=%{y:.1f}<br>"
                f"{value_label}=%{{customdata:.6g}}<extra></extra>"
            ),
        ),
        row=row,
        col=col,
    )


def make_shader_volume_figure(results: list[dict[str, object]]) -> go.Figure:
    component_keys = ("v_tc", "v_nv", "v_ss")
    has_tomo_references = all(
        all(f"tomo_{key}" in result for key in component_keys)
        and "tomo_yaw" in result
        and "tomo_pitch" in result
        for result in results
    )
    source_specs = []
    if has_tomo_references:
        source_specs.append(
            ("tomo", "TOMO_CPU", "tomo_yaw", "tomo_pitch", tuple(f"tomo_{key}" for key in component_keys))
        )
    source_specs.append(("shader", "Shader", "angles_yaw", "angles_pitch", component_keys))

    rows = len(results) * len(source_specs)
    cols = len(component_keys)
    subplot_titles = [
        f"{result['label']} {source_title} {component_key}"
        for result in results
        for _source_id, source_title, _yaw_key, _pitch_key, keys in source_specs
        for component_key, _data_key in zip(component_keys, keys)
    ]
    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=subplot_titles,
        horizontal_spacing=0.08,
        vertical_spacing=0.12,
    )

    for result_id, result in enumerate(results):
        cfg = result["cfg"]
        for source_index, (_source_id, source_title, yaw_key, pitch_key, data_keys) in enumerate(source_specs):
            row = result_id * len(source_specs) + source_index + 1
            yaw_values = np.asarray(getattr(cfg, yaw_key, result.get(yaw_key)), dtype=float)
            pitch_values = np.asarray(getattr(cfg, pitch_key, result.get(pitch_key)), dtype=float)
            yaw_range = axis_data_range(yaw_values)
            pitch_range = axis_data_range(pitch_values)
            for col, (component_key, data_key) in enumerate(zip(component_keys, data_keys), start=1):
                title = f"{source_title} {component_key}"
                values = np.asarray(result[data_key], dtype=float)
                min_rows, max_rows = find_v_ss_extreme_orientations(
                    values,
                    yaw_values,
                    pitch_values,
                    count=3,
                )
                fig.add_trace(
                    go.Contour(
                        x=yaw_values,
                        y=pitch_values,
                        z=values,
                        colorscale=COOLWARM_COLORSCALE,
                        contours=dict(showlabels=True),
                        colorbar=dict(title=component_key) if row == rows and col == cols else None,
                        showscale=row == rows and col == cols,
                        hovertemplate=(
                            "yaw=%{x:.1f}<br>"
                            "pitch=%{y:.1f}<br>"
                            f"{title}=%{{z:.6g}}<extra></extra>"
                        ),
                    ),
                    row=row,
                    col=col,
                )
                add_shader_extreme_markers(
                    fig,
                    min_rows,
                    max_rows,
                    value_label=component_key,
                    row=row,
                    col=col,
                    showlegend=result_id == 0 and source_index == 0 and col == 1,
                )
                axis_id = (row - 1) * cols + col
                x_anchor = "x" if axis_id == 1 else f"x{axis_id}"
                fig.update_yaxes(
                    title_text="Pitch angle (deg)",
                    range=pitch_range,
                    scaleanchor=x_anchor,
                    scaleratio=1,
                    constrain="domain",
                    row=row,
                    col=col,
                )
                fig.update_xaxes(
                    title_text="Yaw angle (deg)",
                    range=yaw_range,
                    constrain="domain",
                    row=row,
                    col=col,
                )

    fig.update_layout(
        title=(
            "Shader vs TOMO_CPU Volume Components (v_tc, v_nv, v_ss)"
            if has_tomo_references
            else "Shader Volume Components (v_tc, v_nv, v_ss)"
        ),
        height=max(420 * rows, 520),
        width=1500,
    )
    return fig


def mesh_vertices_faces_at_origin(mesh: trimesh.Trimesh) -> tuple[np.ndarray, np.ndarray]:
    clean_mesh = mesh.copy()
    clean_mesh.remove_unreferenced_vertices()
    vertices = np.asarray(clean_mesh.vertices, dtype=np.float64)
    vertices = vertices - vertices.min(axis=0)
    faces = np.asarray(clean_mesh.faces, dtype=np.int32)
    return vertices, faces


def render_input_meshes(renderer, results: list[dict[str, object]]) -> None:
    extents = []
    for result in results:
        vertices, _faces = mesh_vertices_faces_at_origin(result["cfg"].mesh)
        extents.append(vertices.max(axis=0) - vertices.min(axis=0))

    max_extent = np.maximum(np.max(np.asarray(extents, dtype=np.float64), axis=0), 1e-6)
    item_gap = 0.25 * float(max_extent.max())
    item_step = max_extent + item_gap
    row_step = item_step[1] + item_gap

    for result_id, result in enumerate(results):
        mesh = result["cfg"].mesh
        cell_origin = np.array([0.0, -result_id * row_step, 0.0], dtype=np.float64)
        mesh_min = np.asarray(mesh.vertices, dtype=np.float64).min(axis=0)
        display_offset = cell_origin - mesh_min
        label = str(result["label"])
        ps_mesh = renderer.register_surface_mesh(
            f"{label} input mesh",
            np.asarray(mesh.vertices, dtype=np.float64) + display_offset,
            np.asarray(mesh.faces, dtype=np.int32),
            smooth_shade=False,
            color=(0.72, 0.74, 0.78),
            transparency=0.38,
        )
        if hasattr(renderer, "create_group"):
            ps_mesh.add_to_group(renderer.create_group(f"{label} input"))


def render_shader_extreme_orientations(renderer, results: list[dict[str, object]]) -> None:
    extents = []
    for result in results:
        vertices, _faces = mesh_vertices_faces_at_origin(result["cfg"].mesh)
        extents.append(vertices.max(axis=0) - vertices.min(axis=0))
    max_extent = np.maximum(np.max(np.asarray(extents, dtype=np.float64), axis=0), 1e-6)
    item_gap = 0.25 * float(max_extent.max())
    item_step = max_extent + item_gap
    row_step = item_step[1] + item_gap

    for result_id, result in enumerate(results):
        cell_origin = np.array([0.0, -result_id * row_step, 0.0], dtype=np.float64)
        group = renderer.create_group(f"{result['label']} shader extrema") if hasattr(renderer, "create_group") else None
        _vertices, faces = mesh_vertices_faces_at_origin(result["cfg"].mesh)
        raw_vertices = np.asarray(result["cfg"].mesh.vertices, dtype=np.float64)

        extreme_rows = [
            *[
                (-rank, f"o{rank}", row, (0.10, 0.55, 0.95))
                for rank, row in zip(range(1, len(result["min_rows"]) + 1), result["min_rows"])
            ],
            *[
                (rank, f"w{rank}", row, (0.95, 0.36, 0.20))
                for rank, row in zip(range(1, len(result["max_rows"]) + 1), result["max_rows"])
            ],
        ]
        for item_id, label, row_data, color in extreme_rows:
            rotated_vertices = rotated_vertices_at_origin(
                raw_vertices,
                row_data["yaw"],
                row_data["pitch"],
            )
            offset = cell_origin + np.array([item_id * item_step[0], 0.0, 0.0], dtype=np.float64)
            placed_vertices = np.ascontiguousarray(rotated_vertices + offset, dtype=np.float64)
            ps_mesh = renderer.register_surface_mesh(
                f"{result['label']} shader {label} yaw={row_data['yaw']:.1f} pitch={row_data['pitch']:.1f}",
                placed_vertices,
                faces,
                smooth_shade=False,
                color=color,
                transparency=0.42,
            )
            if group is not None:
                ps_mesh.add_to_group(group)
            ps_mesh.add_scalar_quantity(
                "shader v_ss",
                np.full(len(placed_vertices), row_data["value"], dtype=np.float64),
                enabled=False,
            )


def render_results_line(renderer, results: Sequence[Mapping[str, object]]) -> None:
    from .VisFacePair.vis_face_pair import display_coacd_hulls

    extents = []
    for result in results:
        vertices, _faces = mesh_vertices_faces_at_origin(result["cfg"].mesh)
        extents.append(vertices.max(axis=0) - vertices.min(axis=0))
    max_extent = np.maximum(np.max(np.asarray(extents, dtype=np.float64), axis=0), 1e-6)
    item_gap = 0.25 * float(max_extent.max())
    item_step = max_extent + item_gap
    row_step = item_step[1] + item_gap

    for result_id, result in enumerate(results):
        cell_origin = np.array([0.0, -result_id * row_step, 0.0], dtype=np.float64)
        group = renderer.create_group(str(result["label"])) if hasattr(renderer, "create_group") else None
        _vertices, faces = mesh_vertices_faces_at_origin(result["cfg"].mesh)
        mesh_min = np.asarray(result["cfg"].mesh.vertices, dtype=np.float64).min(axis=0)
        display_offset = cell_origin - mesh_min

        display_coacd_hulls(
            result.get("coacd_broad_phase"),
            enabled=True,
            renderer=renderer,
            offset=display_offset,
            name_prefix=str(result["label"]),
            show_centers=False,
        )
        result["vis_face_pair"].display_visible_triangle_pairs(
            result["cfg"].mesh,
            result["visible_pair_infos"],
            broad_phase=result.get("coacd_broad_phase"),
            renderer=renderer,
            show=False,
            offset=display_offset,
            name_prefix=str(result["label"]),
            show_mesh=False,
            show_hulls=False,
        )

        extreme_rows = [
            *[
                (-rank, f"o{rank}", row, (0.10, 0.55, 0.95))
                for rank, row in zip(range(1, len(result["min_rows"]) + 1), result["min_rows"])
            ],
            *[
                (rank, f"w{rank}", row, (0.95, 0.36, 0.20))
                for rank, row in zip(range(1, len(result["max_rows"]) + 1), result["max_rows"])
            ],
        ]
        raw_vertices = np.asarray(result["cfg"].mesh.vertices, dtype=np.float64)
        for item_id, label, row_data, color in extreme_rows:
            rotated_vertices = rotated_vertices_at_origin(
                raw_vertices,
                row_data["yaw"],
                row_data["pitch"],
            )
            offset = cell_origin + np.array([item_id * item_step[0], 0.0, 0.0], dtype=np.float64)
            placed_vertices = np.ascontiguousarray(rotated_vertices + offset, dtype=np.float64)
            ps_mesh = renderer.register_surface_mesh(
                f"{result['label']} {label} yaw={row_data['yaw']:.1f} pitch={row_data['pitch']:.1f}",
                placed_vertices,
                faces,
                smooth_shade=False,
                color=color,
                transparency=0.42,
            )
            if group is not None:
                ps_mesh.add_to_group(group)
            ps_mesh.add_scalar_quantity(
                "v_ss",
                np.full(len(placed_vertices), row_data["value"], dtype=np.float64),
                enabled=False,
            )
