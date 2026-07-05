from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import moderngl
import numpy as np
import trimesh

from ..tse6_config import TSE6Config, yaw_pitch_matrix


DEFAULT_MESH_PATH = Path("Experimental/etc/_1_MashaPNG/masha1.obj")
DEFAULT_BATCH_COLS = 18
DEFAULT_BATCH_ROWS = DEFAULT_BATCH_COLS
DEFAULT_ANGLE_STEP = 10.0
DEFAULT_VERBOSE = False
GREEN = "\033[92m"
RESET = "\033[0m"

def log_time(label, start_time):
    print(f"{GREEN}{label}: {time.perf_counter() - start_time:.3f}s{RESET}", flush=True)


def print_dot_progress(label: str, index: int, total: int, dot_count: int = 20) -> None:
    if total <= 0:
        return
    previous = math.ceil(dot_count * (index - 1) / total)
    current = math.ceil(dot_count * index / total)
    if index == 1:
        print(f"{label}: ", end="", flush=True)
    if current > previous:
        print("." * (current - previous), end="", flush=True)
    if index >= total:
        print(" done", flush=True)


VERTEX_SHADER = """
#version 330

in vec3 in_position;

uniform mat4 u_mvp;

out float v_world_z;

void main() {
    v_world_z = in_position.z;
    gl_Position = u_mvp * vec4(in_position, 1.0);
}
"""


FRAGMENT_SHADER = """
#version 330

in float v_world_z;

out float out_z;

void main() {
    out_z = v_world_z;
}
"""


TOP_COVER_FRAGMENT_SHADER = """
#version 330

in float v_world_z;

layout(location = 0) out vec2 out_data;

void main() {
    out_data = vec2(v_world_z, float(gl_PrimitiveID) + 1.0);
}
"""


BETA_CONTRIBUTION_VERTEX_SHADER = """
#version 330

in vec3 in_position;
in vec3 in_weights;

uniform mat4 u_mvp;

out float v_world_z;
out vec3 v_weights;

void main() {
    v_world_z = in_position.z;
    v_weights = in_weights;
    gl_Position = u_mvp * vec4(in_position, 1.0);
}
"""


BETA_CONTRIBUTION_FRAGMENT_SHADER = """
#version 330

in float v_world_z;
in vec3 v_weights;

layout(location = 0) out vec3 out_components;

void main() {
    out_components = max(v_world_z, 0.0) * v_weights;
}
"""


@dataclass(frozen=True)
class VtcRow:
    yaw_deg: float
    pitch_deg: float
    volume: float
    bounds_min: np.ndarray
    bounds_max: np.ndarray


@dataclass(frozen=True)
class VtcVssVnvRow:
    yaw_deg: float
    pitch_deg: float
    v_tc: float
    v_ss: float
    v_nv: float
    object_volume: float
    bounds_min: np.ndarray
    bounds_max: np.ndarray


@dataclass(frozen=True)
class BetaComponentRow:
    yaw_deg: float
    pitch_deg: float
    v_al: float
    v_be: float
    v_o: float
    v_nv: float
    bounds_min: np.ndarray
    bounds_max: np.ndarray


class FboVtc:
    def __init__(
        self,
        config: TSE6Config | None = None,
        *,
        meshpath: str | Path | None = None,
        mesh: trimesh.Trimesh | None = None,
        angles_yaw: Sequence[float] | None = None,
        angles_pitch: Sequence[float] | None = None,
        filament_critical_angle: float | None = None,
        batch_cols: int = DEFAULT_BATCH_COLS,
        batch_rows: int = DEFAULT_BATCH_ROWS,
        ctx: moderngl.Context | None = None,
        program: moderngl.Program | None = None,
        renderer=None,
        vertex_shader: str = VERTEX_SHADER,
        fragment_shader: str = FRAGMENT_SHADER,
    ):
        if config is not None:
            mesh = config.mesh if mesh is None else mesh
            angles_yaw = config.angles_yaw if angles_yaw is None else angles_yaw
            angles_pitch = config.angles_pitch if angles_pitch is None else angles_pitch
            orientation_pairs = config.orientation_pairs
            orientation_inverse = config.orientation_inverse
            fbo_voxel_size = config.fbo_voxel_size
            if filament_critical_angle is None:
                filament_critical_angle = config.critical_angle
            if renderer is None:
                renderer = config.renderer
        else:
            orientation_pairs = None
            orientation_inverse = None
            fbo_voxel_size = None

        self.batch_cols = batch_cols
        self.batch_rows = batch_rows
        self.ctx = ctx
        self.program = program
        self.top_cover_program: moderngl.Program | None = None
        self.beta_contribution_program: moderngl.Program | None = None
        self.vertex_shader = vertex_shader
        self.fragment_shader = fragment_shader
        self._owns_context = ctx is None
        self.meshpath = Path(meshpath) if meshpath is not None else None
        self.mesh = mesh if mesh is not None else self._load_mesh_from_path()
        self.angles_yaw = self._as_angle_array(angles_yaw)
        self.angles_pitch = self._as_angle_array(angles_pitch)
        self.orientation_pairs = None if orientation_pairs is None else np.asarray(orientation_pairs, dtype=np.float64)
        self.orientation_inverse = None if orientation_inverse is None else np.asarray(orientation_inverse, dtype=np.int64)
        self.filament_critical_angle = 60.0 if filament_critical_angle is None else float(filament_critical_angle)
        self.renderer = renderer
        self._rendered = False
        self.tc_face_ids: np.ndarray | None = None
        self.tc_tri_mesh: trimesh.Trimesh | None = None
        self.tc_mesh: trimesh.Trimesh | None = None
        self.rows: list[VtcRow] = []
        self.component_rows: list[VtcVssVnvRow] = []
        self.component_params: tuple[float, float] | None = None
        self.beta_rows: list[BetaComponentRow] = []
        self.beta_params: tuple[float] | None = None
        self.voxel_size: int | None = None if fbo_voxel_size is None else int(fbo_voxel_size)

        if self.mesh is not None and self.voxel_size is None:
            mesh = self.require_mesh()
            self.voxel_size = nearest_power_of_2(max(mesh.bounding_box.extents))

    def __enter__(self) -> FboVtc:
        self.ensure_context()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()

    def ensure_context(self) -> tuple[moderngl.Context, moderngl.Program]:
        if self.ctx is None:
            self.ctx = moderngl.create_context(standalone=True)
            self._owns_context = True

        if self.program is None:
            self.program = self.ctx.program(
                vertex_shader=self.vertex_shader,
                fragment_shader=self.fragment_shader,
            )

        return self.ctx, self.program

    def release(self) -> None:
        if self._owns_context and self.ctx is not None:
            self.ctx.release()

        self.ctx = None
        self.program = None
        self.top_cover_program = None
        self.beta_contribution_program = None

    def ensure_top_cover_program(self) -> moderngl.Program:
        ctx, _program = self.ensure_context()
        if self.top_cover_program is None:
            self.top_cover_program = ctx.program(
                vertex_shader=self.vertex_shader,
                fragment_shader=TOP_COVER_FRAGMENT_SHADER,
            )
        return self.top_cover_program

    def ensure_beta_contribution_program(self) -> moderngl.Program:
        ctx, _program = self.ensure_context()
        if self.beta_contribution_program is None:
            self.beta_contribution_program = ctx.program(
                vertex_shader=BETA_CONTRIBUTION_VERTEX_SHADER,
                fragment_shader=BETA_CONTRIBUTION_FRAGMENT_SHADER,
            )
        return self.beta_contribution_program

    def print_run_info(self) -> None:
        mesh = self.require_mesh()
        if self.voxel_size is None:
            self.voxel_size = nearest_power_of_2(max(mesh.bounding_box.extents))

        print_context_info(self.ctx)
        print(f"mesh: {self.meshpath if self.meshpath is not None else '<TSE6Config.mesh>'}")
        print(f"faces: {len(mesh.faces)}")
        print(f"vertices: {len(mesh.vertices)}")
        print(f"voxel dimension: {self.voxel_size} x {self.voxel_size}")
        print(f"batch grid: {self.batch_cols} x {self.batch_rows}")
        print(f"angle grid: {len(self.angles_yaw)} x {len(self.angles_pitch)}")
        if self.orientation_pairs is not None:
            print(f"unique compute directions: {len(self.orientation_pairs)}")
        print(f"filament critical angle: {self.filament_critical_angle}")
        print(f"watertight: {mesh.is_watertight}")
        print(f"bounds={mesh.bounding_box.extents}")
        print()

        if mesh.is_watertight:
            print(f"trimesh signed volume: {mesh.volume:.6f}")
            print(f"abs(trimesh volume): {abs(mesh.volume):.6f}")
        else:
            print("trimesh volume comparison skipped: mesh is not watertight")

    @staticmethod
    def _as_angle_array(values: Sequence[float] | None) -> np.ndarray:
        if values is None:
            return np.linspace(
                0.0,
                360.0,
                num=int(round(360.0 / DEFAULT_ANGLE_STEP)) + 1,
                endpoint=True,
                dtype=np.float64,
            )
        return np.asarray(values, dtype=np.float64).reshape(-1)

    def _load_mesh_from_path(self) -> trimesh.Trimesh | None:
        if self.meshpath is None:
            return None
        return load_mesh(self.meshpath)

    def require_mesh(self, mesh: trimesh.Trimesh | None = None) -> trimesh.Trimesh:
        mesh = mesh if mesh is not None else self.mesh
        if mesh is None:
            raise ValueError("mesh or meshpath must be provided.")
        return mesh

    @staticmethod
    def make_ortho_matrix(bounds: np.ndarray, padding_ratio: float = 0.02):
        """Project mesh bounds to NDC while looking from +Z toward -Z."""
        bounds_min, bounds_max = np.asarray(bounds, dtype=np.float32)
        xmin, ymin, zmin = bounds_min
        xmax, ymax, zmax = bounds_max

        extent = bounds_max - bounds_min
        if padding_ratio > 0.0:
            pad_x = max(float(extent[0]) * padding_ratio, 1e-6)
            pad_y = max(float(extent[1]) * padding_ratio, 1e-6)
            pad_z = max(float(extent[2]) * padding_ratio, 1e-6)
        else:
            pad_x = 0.0
            pad_y = 0.0
            pad_z = 1e-6

        xmin -= pad_x
        xmax += pad_x
        ymin -= pad_y
        ymax += pad_y
        zmin -= pad_z
        zmax += pad_z

        matrix = np.array(
            [
                [2.0 / (xmax - xmin), 0.0, 0.0, -(xmax + xmin) / (xmax - xmin)],
                [0.0, 2.0 / (ymax - ymin), 0.0, -(ymax + ymin) / (ymax - ymin)],
                [0.0, 0.0, -2.0 / (zmax - zmin), (2.0 * zmax) / (zmax - zmin) - 1.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        )
        return matrix, (xmin, xmax, ymin, ymax, zmin, zmax)

    @staticmethod
    def rotation_matrix_yaw_pitch(yaw_deg: float, pitch_deg: float) -> np.ndarray:
        """Rotation.from_euler('xyz', [yaw, pitch, 0]) using degree inputs."""
        return yaw_pitch_matrix(yaw_deg, pitch_deg)

    @classmethod
    def make_rotated_vertices_at_origin(
        cls,
        vertices: np.ndarray,
        yaw_deg: float,
        pitch_deg: float,
    ) -> np.ndarray:
        rotation = cls.rotation_matrix_yaw_pitch(yaw_deg, pitch_deg)
        rotated = np.asarray(vertices, dtype=np.float64) @ rotation.T
        rotated -= rotated.min(axis=0)
        return rotated

    @staticmethod
    def thickness_from_front_back(front_z: np.ndarray, back_z: np.ndarray):
        valid = np.isfinite(front_z) & np.isfinite(back_z)
        thickness = np.zeros_like(front_z, dtype=np.float32)
        thickness[valid] = np.maximum(front_z[valid], 0.0)
        return thickness, valid

    @staticmethod
    def support_mask_from_normals(normals: np.ndarray, critical_angle_deg: float) -> np.ndarray:
        normals = np.asarray(normals, dtype=np.float64)
        if critical_angle_deg <= 0.0:
            return np.ones(len(normals), dtype=bool)
        if critical_angle_deg >= 90.0:
            return np.zeros(len(normals), dtype=bool)
        z_abs = np.clip(np.abs(normals[:, 2]), 0.0, 1.0)
        support_angle = np.rad2deg(np.arccos(z_abs))
        return support_angle >= float(critical_angle_deg)

    def make_fbo(self, size: int | tuple[int, int], components: int = 1):
        ctx, _program = self.ensure_context()
        if isinstance(size, int):
            size = (size, size)

        z_texture = ctx.texture(size, components=components, dtype="f4")
        z_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        depth = ctx.depth_renderbuffer(size)
        fbo = ctx.framebuffer(color_attachments=[z_texture], depth_attachment=depth)
        return fbo, z_texture

    def render_z_pass(self, vao, fbo, z_texture, depth_func: str, clear_z: float) -> np.ndarray:
        ctx, _program = self.ensure_context()
        fbo.use()
        ctx.viewport = (0, 0, fbo.size[0], fbo.size[1])
        ctx.enable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.CULL_FACE)
        ctx.depth_func = depth_func
        fbo.clear(red=clear_z, depth=1.0 if depth_func == "<" else 0.0)
        vao.render()

        data = z_texture.read(alignment=1)
        return np.frombuffer(data, dtype=np.float32).reshape(fbo.size[1], fbo.size[0])

    def make_mesh_vao(self, vertices: np.ndarray, faces: np.ndarray, program: moderngl.Program | None = None):
        ctx, default_program = self.ensure_context()
        program = default_program if program is None else program
        vbo = ctx.buffer(np.asarray(vertices, dtype=np.float32).tobytes())
        ibo = ctx.buffer(np.asarray(faces, dtype=np.uint32).reshape(-1).tobytes())
        return ctx.vertex_array(program, [(vbo, "3f", "in_position")], index_buffer=ibo)

    def render_top_cover_pass(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        yaw_deg: float,
        pitch_deg: float,
        size: int | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        program = self.ensure_top_cover_program()
        mesh = self.require_mesh()
        if size is None:
            if self.voxel_size is None:
                self.voxel_size = nearest_power_of_2(max(mesh.bounding_box.extents))
            size = self.voxel_size

        rotated_vertices = self.make_rotated_vertices_at_origin(vertices, yaw_deg, pitch_deg)
        bounds = np.asarray([rotated_vertices.min(axis=0), rotated_vertices.max(axis=0)], dtype=np.float32)
        mvp, _padded_bounds = self.make_ortho_matrix(bounds, padding_ratio=0.02)
        program["u_mvp"].write(mvp.T.tobytes())

        vao = self.make_mesh_vao(rotated_vertices, faces, program=program)
        fbo, data_texture = self.make_fbo(size, components=2)
        try:
            ctx, _program = self.ensure_context()
            fbo.use()
            ctx.viewport = (0, 0, fbo.size[0], fbo.size[1])
            ctx.enable(moderngl.DEPTH_TEST)
            ctx.disable(moderngl.CULL_FACE)
            ctx.depth_func = "<"
            fbo.clear(red=np.nan, green=0.0, depth=1.0)
            vao.render()

            data = data_texture.read(alignment=1)
            image = np.frombuffer(data, dtype=np.float32).reshape(fbo.size[1], fbo.size[0], 2)
            front_z = image[:, :, 0]
            primitive_ids_plus_one = image[:, :, 1]
            return front_z, primitive_ids_plus_one, rotated_vertices
        finally:
            vao.release()
            fbo.release()
            data_texture.release()

    def extract_top_cover_face_ids(
        self,
        mesh: trimesh.Trimesh | None = None,
        yaw_deg: float = 0.0,
        pitch_deg: float = 0.0,
        size: int | None = None,
    ) -> np.ndarray:
        mesh = self.require_mesh(mesh)
        faces = np.asarray(mesh.faces, dtype=np.uint32)
        front_z, primitive_ids_plus_one, _rotated_vertices = self.render_top_cover_pass(
            np.asarray(mesh.vertices, dtype=np.float64),
            faces,
            yaw_deg,
            pitch_deg,
            size=size,
        )
        valid = np.isfinite(front_z) & (primitive_ids_plus_one > 0.0)
        if not np.any(valid):
            return np.empty(0, dtype=np.int64)
        face_ids = np.rint(primitive_ids_plus_one[valid] - 1.0).astype(np.int64)
        face_ids = face_ids[(0 <= face_ids) & (face_ids < len(faces))]
        return np.unique(face_ids)

    @staticmethod
    def make_vertical_prism_mesh_from_triangles(
        top_vertices: np.ndarray,
        top_faces: np.ndarray,
        bottom_z: float = 0.0,
    ) -> trimesh.Trimesh:
        vertices_out: list[np.ndarray] = []
        faces_out: list[list[int]] = []
        for tri in np.asarray(top_vertices, dtype=np.float64)[np.asarray(top_faces, dtype=np.int64)]:
            bottom = tri.copy()
            bottom[:, 2] = bottom_z
            base = len(vertices_out)
            vertices_out.extend([tri[0], tri[1], tri[2], bottom[0], bottom[1], bottom[2]])
            faces_out.extend(
                [
                    [base + 0, base + 1, base + 2],
                    [base + 5, base + 4, base + 3],
                    [base + 0, base + 3, base + 4],
                    [base + 0, base + 4, base + 1],
                    [base + 1, base + 4, base + 5],
                    [base + 1, base + 5, base + 2],
                    [base + 2, base + 5, base + 3],
                    [base + 2, base + 3, base + 0],
                ]
            )
        if not vertices_out:
            return trimesh.Trimesh(vertices=np.empty((0, 3)), faces=np.empty((0, 3), dtype=np.int64), process=False)
        return trimesh.Trimesh(
            vertices=np.asarray(vertices_out, dtype=np.float64),
            faces=np.asarray(faces_out, dtype=np.int64),
            process=False,
        )

    def build_tc_mesh(
        self,
        mesh: trimesh.Trimesh | None = None,
        yaw_deg: float = 0.0,
        pitch_deg: float = 0.0,
        size: int | None = None,
    ) -> tuple[np.ndarray, trimesh.Trimesh, trimesh.Trimesh]:
        mesh = self.require_mesh(mesh)
        faces = np.asarray(mesh.faces, dtype=np.int64)
        front_z, primitive_ids_plus_one, rotated_vertices = self.render_top_cover_pass(
            np.asarray(mesh.vertices, dtype=np.float64),
            np.asarray(mesh.faces, dtype=np.uint32),
            yaw_deg,
            pitch_deg,
            size=size,
        )
        valid = np.isfinite(front_z) & (primitive_ids_plus_one > 0.0)
        if np.any(valid):
            face_ids = np.rint(primitive_ids_plus_one[valid] - 1.0).astype(np.int64)
            face_ids = np.unique(face_ids[(0 <= face_ids) & (face_ids < len(faces))])
        else:
            face_ids = np.empty(0, dtype=np.int64)
        tc_faces = faces[face_ids] if len(face_ids) else np.empty((0, 3), dtype=np.int64)
        tc_tri_mesh = trimesh.Trimesh(vertices=rotated_vertices.copy(), faces=tc_faces, process=False)
        tc_mesh = self.make_vertical_prism_mesh_from_triangles(rotated_vertices, tc_faces, bottom_z=0.0)
        self.tc_face_ids = face_ids
        self.tc_tri_mesh = tc_tri_mesh
        self.tc_mesh = tc_mesh
        return face_ids, tc_tri_mesh, tc_mesh

    def make_atlas_vao(
        self,
        base_vertices: np.ndarray,
        base_faces: np.ndarray,
        angle_pairs: list[tuple[float, float]],
        program: moderngl.Program | None = None,
    ):
        rotated_items = []
        max_extent = np.zeros(3, dtype=np.float64)

        for yaw_deg, pitch_deg in angle_pairs:
            vertices = self.make_rotated_vertices_at_origin(base_vertices, yaw_deg, pitch_deg)
            bounds_max = vertices.max(axis=0)
            max_extent = np.maximum(max_extent, bounds_max)
            rotated_items.append((vertices, bounds_max))

        max_extent = np.maximum(max_extent, 1e-6)
        atlas_vertices = []
        atlas_faces = []

        for item_idx, (vertices, _bounds_max) in enumerate(rotated_items):
            col = item_idx % self.batch_cols
            row = item_idx // self.batch_cols
            offset = np.array([col * max_extent[0], row * max_extent[1], 0.0])

            base_index = item_idx * len(base_vertices)
            atlas_vertices.append(vertices + offset)
            atlas_faces.append(base_faces + base_index)

        return (
            self.make_mesh_vao(np.vstack(atlas_vertices), np.vstack(atlas_faces), program=program),
            rotated_items,
            max_extent,
        )

    def make_beta_contribution_atlas_vao(
        self,
        base_vertices: np.ndarray,
        base_faces: np.ndarray,
        base_normals: np.ndarray,
        angle_pairs: list[tuple[float, float]],
        critical_angle_deg: float,
    ):
        ctx, _default_program = self.ensure_context()
        program = self.ensure_beta_contribution_program()
        rotated_items = []
        max_extent = np.zeros(3, dtype=np.float64)

        for yaw_deg, pitch_deg in angle_pairs:
            vertices = self.make_rotated_vertices_at_origin(base_vertices, yaw_deg, pitch_deg)
            bounds_max = vertices.max(axis=0)
            max_extent = np.maximum(max_extent, bounds_max)
            rotated_items.append((vertices, bounds_max, self.rotation_matrix_yaw_pitch(yaw_deg, pitch_deg)))

        max_extent = np.maximum(max_extent, 1e-6)
        cos_critical = math.cos(math.radians(float(critical_angle_deg)))
        position_chunks = []
        weight_chunks = []

        for item_idx, (vertices, _bounds_max, rotation) in enumerate(rotated_items):
            col = item_idx % self.batch_cols
            row = item_idx // self.batch_cols
            offset = np.array([col * max_extent[0], row * max_extent[1], 0.0], dtype=np.float64)

            tris = vertices[np.asarray(base_faces, dtype=np.int64)] + offset
            rotated_normals = np.asarray(base_normals, dtype=np.float64) @ rotation.T
            normal_z = rotated_normals[:, 2]
            alpha_mask = normal_z < 0.0
            beta_mask = ~alpha_mask
            alpha_nv_mask = alpha_mask & (normal_z >= -cos_critical)
            weights = np.column_stack(
                [
                    alpha_mask.astype(np.float32),
                    beta_mask.astype(np.float32),
                    alpha_nv_mask.astype(np.float32),
                ]
            )
            position_chunks.append(tris.reshape(-1, 3))
            weight_chunks.append(np.repeat(weights, 3, axis=0))

        positions = np.ascontiguousarray(np.vstack(position_chunks), dtype=np.float32)
        weights = np.ascontiguousarray(np.vstack(weight_chunks), dtype=np.float32)
        vbo_positions = ctx.buffer(positions.tobytes())
        vbo_weights = ctx.buffer(weights.tobytes())
        vao = ctx.vertex_array(
            program,
            [
                (vbo_positions, "3f", "in_position"),
                (vbo_weights, "3f", "in_weights"),
            ],
        )
        return vao, rotated_items, max_extent

    def make_fused_beta_atlas_vaos(
        self,
        base_vertices: np.ndarray,
        base_faces: np.ndarray,
        base_normals: np.ndarray,
        angle_pairs: list[tuple[float, float]],
        critical_angle_deg: float,
    ):
        ctx, vtc_program = self.ensure_context()
        beta_program = self.ensure_beta_contribution_program()
        rotated_items = []
        max_extent = np.zeros(3, dtype=np.float64)

        for yaw_deg, pitch_deg in angle_pairs:
            vertices = self.make_rotated_vertices_at_origin(base_vertices, yaw_deg, pitch_deg)
            bounds_max = vertices.max(axis=0)
            max_extent = np.maximum(max_extent, bounds_max)
            rotated_items.append((vertices, bounds_max, self.rotation_matrix_yaw_pitch(yaw_deg, pitch_deg)))

        max_extent = np.maximum(max_extent, 1e-6)
        cos_critical = math.cos(math.radians(float(critical_angle_deg)))
        position_chunks = []
        weight_chunks = []

        for item_idx, (vertices, _bounds_max, rotation) in enumerate(rotated_items):
            col = item_idx % self.batch_cols
            row = item_idx // self.batch_cols
            offset = np.array([col * max_extent[0], row * max_extent[1], 0.0], dtype=np.float64)

            tris = vertices[np.asarray(base_faces, dtype=np.int64)] + offset
            rotated_normals = np.asarray(base_normals, dtype=np.float64) @ rotation.T
            normal_z = rotated_normals[:, 2]
            alpha_mask = normal_z < 0.0
            beta_mask = ~alpha_mask
            alpha_nv_mask = alpha_mask & (normal_z >= -cos_critical)
            weights = np.column_stack(
                [
                    alpha_mask.astype(np.float32),
                    beta_mask.astype(np.float32),
                    alpha_nv_mask.astype(np.float32),
                ]
            )
            position_chunks.append(tris.reshape(-1, 3))
            weight_chunks.append(np.repeat(weights, 3, axis=0))

        positions = np.ascontiguousarray(np.vstack(position_chunks), dtype=np.float32)
        weights = np.ascontiguousarray(np.vstack(weight_chunks), dtype=np.float32)
        vbo_positions = ctx.buffer(positions.tobytes())
        vbo_weights = ctx.buffer(weights.tobytes())
        vtc_vao = ctx.vertex_array(vtc_program, [(vbo_positions, "3f", "in_position")])
        beta_vao = ctx.vertex_array(
            beta_program,
            [
                (vbo_positions, "3f", "in_position"),
                (vbo_weights, "3f", "in_weights"),
            ],
        )
        return vtc_vao, beta_vao, rotated_items, max_extent

    def render_angle_batch(
        self,
        base_vertices: np.ndarray,
        base_faces: np.ndarray,
        angle_pairs: list[tuple[float, float]],
        cell_pixels: int,
    ) -> list[VtcRow]:
        _ctx, program = self.ensure_context()
        cols = self.batch_cols
        rows = int(np.ceil(len(angle_pairs) / cols))
        atlas_size = (cols * cell_pixels, rows * cell_pixels)

        vao, rotated_items, max_extent = self.make_atlas_vao(
            base_vertices,
            base_faces,
            angle_pairs,
        )

        atlas_bounds = np.array(
            [
                [0.0, 0.0, 0.0],
                [cols * max_extent[0], rows * max_extent[1], max_extent[2]],
            ],
            dtype=np.float32,
        )
        mvp, padded_bounds = self.make_ortho_matrix(atlas_bounds, padding_ratio=0.0)
        program["u_mvp"].write(mvp.T.tobytes())

        fbo, z_texture = self.make_fbo(atlas_size)
        try:
            front_z = self.render_z_pass(vao, fbo, z_texture, depth_func="<", clear_z=np.nan)
            back_z = self.render_z_pass(vao, fbo, z_texture, depth_func=">", clear_z=np.nan)

            xmin, xmax, ymin, ymax, _zmin, _zmax = padded_bounds
            pixel_area = ((xmax - xmin) / atlas_size[0]) * ((ymax - ymin) / atlas_size[1])

            rows_out = []
            for item_idx, ((yaw_deg, pitch_deg), (_vertices, bounds_max)) in enumerate(
                zip(angle_pairs, rotated_items)
            ):
                col = item_idx % cols
                row = item_idx // cols

                x0 = col * cell_pixels
                x1 = x0 + cell_pixels
                y0 = row * cell_pixels
                y1 = y0 + cell_pixels

                thickness, _valid = self.thickness_from_front_back(
                    front_z[y0:y1, x0:x1],
                    back_z[y0:y1, x0:x1],
                )
                volume = float(thickness.sum(dtype=np.float64) * pixel_area)

                rows_out.append(
                    VtcRow(
                        yaw_deg=float(yaw_deg),
                        pitch_deg=float(pitch_deg),
                        volume=volume,
                        bounds_min=np.zeros(3, dtype=np.float64),
                        bounds_max=bounds_max.copy(),
                    )
                )

            return rows_out
        finally:
            fbo.release()
            z_texture.release()

    def render_beta_contribution_angle_batch(
        self,
        base_vertices: np.ndarray,
        base_faces: np.ndarray,
        base_normals: np.ndarray,
        angle_pairs: list[tuple[float, float]],
        cell_pixels: int,
        critical_angle_deg: float,
    ) -> list[BetaComponentRow]:
        program = self.ensure_beta_contribution_program()
        cols = self.batch_cols
        rows = int(np.ceil(len(angle_pairs) / cols))
        atlas_size = (cols * cell_pixels, rows * cell_pixels)

        vao, rotated_items, max_extent = self.make_beta_contribution_atlas_vao(
            base_vertices,
            base_faces,
            base_normals,
            angle_pairs,
            critical_angle_deg,
        )

        atlas_bounds = np.array(
            [
                [0.0, 0.0, 0.0],
                [cols * max_extent[0], rows * max_extent[1], max_extent[2]],
            ],
            dtype=np.float32,
        )
        mvp, padded_bounds = self.make_ortho_matrix(atlas_bounds, padding_ratio=0.0)
        program["u_mvp"].write(mvp.T.tobytes())

        fbo, contribution_texture = self.make_fbo(atlas_size, components=3)
        try:
            ctx, _default_program = self.ensure_context()
            fbo.use()
            ctx.viewport = (0, 0, fbo.size[0], fbo.size[1])
            ctx.disable(moderngl.DEPTH_TEST)
            ctx.disable(moderngl.CULL_FACE)
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = (moderngl.ONE, moderngl.ONE)
            fbo.clear(red=0.0, green=0.0, blue=0.0, depth=1.0)
            vao.render(moderngl.TRIANGLES)
            ctx.disable(moderngl.BLEND)

            data = contribution_texture.read(alignment=1)
            image = np.frombuffer(data, dtype=np.float32).reshape(fbo.size[1], fbo.size[0], 3)

            xmin, xmax, ymin, ymax, _zmin, _zmax = padded_bounds
            pixel_area = ((xmax - xmin) / atlas_size[0]) * ((ymax - ymin) / atlas_size[1])

            rows_out = []
            for item_idx, ((yaw_deg, pitch_deg), (_vertices, bounds_max, _rotation)) in enumerate(
                zip(angle_pairs, rotated_items)
            ):
                col = item_idx % cols
                row = item_idx // cols

                x0 = col * cell_pixels
                x1 = x0 + cell_pixels
                y0 = row * cell_pixels
                y1 = y0 + cell_pixels

                cell = image[y0:y1, x0:x1, :]
                sums = cell.sum(axis=(0, 1), dtype=np.float64) * pixel_area
                v_al = float(sums[0])
                v_be = float(sums[1])
                v_nv = float(sums[2])
                v_o = v_be - v_al
                rows_out.append(
                    BetaComponentRow(
                        yaw_deg=float(yaw_deg),
                        pitch_deg=float(pitch_deg),
                        v_al=v_al,
                        v_be=v_be,
                        v_o=v_o,
                        v_nv=v_nv,
                        bounds_min=np.zeros(3, dtype=np.float64),
                        bounds_max=bounds_max.copy(),
                    )
                )
            return rows_out
        finally:
            vao.release()
            fbo.release()
            contribution_texture.release()

    def render_fused_beta_angle_batch(
        self,
        base_vertices: np.ndarray,
        base_faces: np.ndarray,
        base_normals: np.ndarray,
        angle_pairs: list[tuple[float, float]],
        cell_pixels: int,
        critical_angle_deg: float,
    ) -> tuple[list[VtcRow], list[BetaComponentRow]]:
        _ctx, vtc_program = self.ensure_context()
        beta_program = self.ensure_beta_contribution_program()
        cols = self.batch_cols
        rows = int(np.ceil(len(angle_pairs) / cols))
        atlas_size = (cols * cell_pixels, rows * cell_pixels)

        vtc_vao, beta_vao, rotated_items, max_extent = self.make_fused_beta_atlas_vaos(
            base_vertices,
            base_faces,
            base_normals,
            angle_pairs,
            critical_angle_deg,
        )

        atlas_bounds = np.array(
            [
                [0.0, 0.0, 0.0],
                [cols * max_extent[0], rows * max_extent[1], max_extent[2]],
            ],
            dtype=np.float32,
        )
        mvp, padded_bounds = self.make_ortho_matrix(atlas_bounds, padding_ratio=0.0)
        vtc_program["u_mvp"].write(mvp.T.tobytes())
        beta_program["u_mvp"].write(mvp.T.tobytes())

        z_fbo, z_texture = self.make_fbo(atlas_size)
        contribution_fbo, contribution_texture = self.make_fbo(atlas_size, components=3)
        try:
            front_z = self.render_z_pass(vtc_vao, z_fbo, z_texture, depth_func="<", clear_z=np.nan)
            back_z = self.render_z_pass(vtc_vao, z_fbo, z_texture, depth_func=">", clear_z=np.nan)

            ctx, _default_program = self.ensure_context()
            contribution_fbo.use()
            ctx.viewport = (0, 0, contribution_fbo.size[0], contribution_fbo.size[1])
            ctx.disable(moderngl.DEPTH_TEST)
            ctx.disable(moderngl.CULL_FACE)
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = (moderngl.ONE, moderngl.ONE)
            contribution_fbo.clear(red=0.0, green=0.0, blue=0.0, depth=1.0)
            beta_vao.render(moderngl.TRIANGLES)
            ctx.disable(moderngl.BLEND)

            data = contribution_texture.read(alignment=1)
            contribution_image = np.frombuffer(data, dtype=np.float32).reshape(
                contribution_fbo.size[1],
                contribution_fbo.size[0],
                3,
            )

            xmin, xmax, ymin, ymax, _zmin, _zmax = padded_bounds
            pixel_area = ((xmax - xmin) / atlas_size[0]) * ((ymax - ymin) / atlas_size[1])

            vtc_rows = []
            beta_rows = []
            for item_idx, ((yaw_deg, pitch_deg), (_vertices, bounds_max, _rotation)) in enumerate(
                zip(angle_pairs, rotated_items)
            ):
                col = item_idx % cols
                row = item_idx // cols

                x0 = col * cell_pixels
                x1 = x0 + cell_pixels
                y0 = row * cell_pixels
                y1 = y0 + cell_pixels

                thickness, _valid = self.thickness_from_front_back(
                    front_z[y0:y1, x0:x1],
                    back_z[y0:y1, x0:x1],
                )
                v_tc = float(thickness.sum(dtype=np.float64) * pixel_area)
                cell = contribution_image[y0:y1, x0:x1, :]
                sums = cell.sum(axis=(0, 1), dtype=np.float64) * pixel_area
                v_al = float(sums[0])
                v_be = float(sums[1])
                v_nv = float(sums[2])
                v_o = v_be - v_al

                vtc_rows.append(
                    VtcRow(
                        yaw_deg=float(yaw_deg),
                        pitch_deg=float(pitch_deg),
                        volume=v_tc,
                        bounds_min=np.zeros(3, dtype=np.float64),
                        bounds_max=bounds_max.copy(),
                    )
                )
                beta_rows.append(
                    BetaComponentRow(
                        yaw_deg=float(yaw_deg),
                        pitch_deg=float(pitch_deg),
                        v_al=v_al,
                        v_be=v_be,
                        v_o=v_o,
                        v_nv=v_nv,
                        bounds_min=np.zeros(3, dtype=np.float64),
                        bounds_max=bounds_max.copy(),
                    )
                )
            return vtc_rows, beta_rows
        finally:
            vtc_vao.release()
            beta_vao.release()
            z_fbo.release()
            z_texture.release()
            contribution_fbo.release()
            contribution_texture.release()

    def render_component_angle_batch(
        self,
        base_vertices: np.ndarray,
        base_faces: np.ndarray,
        base_normals: np.ndarray,
        angle_pairs: list[tuple[float, float]],
        cell_pixels: int,
        object_volume: float,
        critical_angle_deg: float,
    ) -> list[VtcVssVnvRow]:
        program = self.ensure_top_cover_program()
        cols = self.batch_cols
        rows = int(np.ceil(len(angle_pairs) / cols))
        atlas_size = (cols * cell_pixels, rows * cell_pixels)
        face_count = len(base_faces)

        vao, rotated_items, max_extent = self.make_atlas_vao(
            base_vertices,
            base_faces,
            angle_pairs,
            program=program,
        )

        atlas_bounds = np.array(
            [
                [0.0, 0.0, 0.0],
                [cols * max_extent[0], rows * max_extent[1], max_extent[2]],
            ],
            dtype=np.float32,
        )
        mvp, padded_bounds = self.make_ortho_matrix(atlas_bounds, padding_ratio=0.0)
        program["u_mvp"].write(mvp.T.tobytes())

        fbo, data_texture = self.make_fbo(atlas_size, components=2)
        try:
            ctx, _default_program = self.ensure_context()
            fbo.use()
            ctx.viewport = (0, 0, fbo.size[0], fbo.size[1])
            ctx.enable(moderngl.DEPTH_TEST)
            ctx.disable(moderngl.CULL_FACE)
            ctx.depth_func = "<"
            fbo.clear(red=np.nan, green=0.0, depth=1.0)
            vao.render()

            data = data_texture.read(alignment=1)
            image = np.frombuffer(data, dtype=np.float32).reshape(fbo.size[1], fbo.size[0], 2)
            front_z = image[:, :, 0]
            primitive_ids_plus_one = image[:, :, 1]

            xmin, xmax, ymin, ymax, _zmin, _zmax = padded_bounds
            pixel_area = ((xmax - xmin) / atlas_size[0]) * ((ymax - ymin) / atlas_size[1])

            rows_out = []
            for item_idx, ((yaw_deg, pitch_deg), (_vertices, bounds_max)) in enumerate(
                zip(angle_pairs, rotated_items)
            ):
                col = item_idx % cols
                row = item_idx // cols

                x0 = col * cell_pixels
                x1 = x0 + cell_pixels
                y0 = row * cell_pixels
                y1 = y0 + cell_pixels

                cell_z = front_z[y0:y1, x0:x1]
                cell_primitive_ids = primitive_ids_plus_one[y0:y1, x0:x1]
                valid = np.isfinite(cell_z) & (cell_primitive_ids > 0.0)
                heights = np.zeros_like(cell_z, dtype=np.float32)
                heights[valid] = np.maximum(cell_z[valid], 0.0)
                v_tc = float(heights.sum(dtype=np.float64) * pixel_area)

                rotation = self.rotation_matrix_yaw_pitch(yaw_deg, pitch_deg)
                rotated_normals = np.asarray(base_normals, dtype=np.float64) @ rotation.T
                support_mask = self.support_mask_from_normals(rotated_normals, critical_angle_deg)

                support_pixels = np.zeros_like(valid, dtype=bool)
                if np.any(valid) and face_count > 0:
                    primitive_ids = np.rint(cell_primitive_ids[valid] - 1.0).astype(np.int64)
                    local_face_ids = primitive_ids % face_count
                    local_face_ids = np.clip(local_face_ids, 0, face_count - 1)
                    support_pixels[valid] = support_mask[local_face_ids]
                v_ss = float(heights[support_pixels].sum(dtype=np.float64) * pixel_area)
                v_nv = max(0.0, v_tc - float(object_volume) - v_ss)

                rows_out.append(
                    VtcVssVnvRow(
                        yaw_deg=float(yaw_deg),
                        pitch_deg=float(pitch_deg),
                        v_tc=v_tc,
                        v_ss=v_ss,
                        v_nv=v_nv,
                        object_volume=float(object_volume),
                        bounds_min=np.zeros(3, dtype=np.float64),
                        bounds_max=bounds_max.copy(),
                    )
                )

            return rows_out
        finally:
            vao.release()
            fbo.release()
            data_texture.release()

    def volumes_for_yaw_pitch_grid(
        self,
        mesh: trimesh.Trimesh | None = None,
        yaw_values: np.ndarray | None = None,
        pitch_values: np.ndarray | None = None,
        size: int = 512,
        show_progress: bool = True,
    ) -> list[VtcRow]:
        mesh = self.require_mesh(mesh)
        use_unique_pairs = yaw_values is None and pitch_values is None and self.orientation_pairs is not None
        if yaw_values is None:
            yaw_values = self.angles_yaw
        if pitch_values is None:
            pitch_values = self.angles_pitch

        self.ensure_context()
        base_vertices = np.asarray(mesh.vertices, dtype=np.float64)
        base_faces = np.asarray(mesh.faces, dtype=np.uint32)

        if use_unique_pairs:
            angle_pairs = [(float(yaw_deg), float(pitch_deg)) for yaw_deg, pitch_deg in self.orientation_pairs]
            grid_label = f"{len(angle_pairs)} unique rotations"
        else:
            angle_pairs = [
                (float(yaw_deg), float(pitch_deg))
                for pitch_deg in pitch_values
                for yaw_deg in yaw_values
            ]
            grid_label = f"{len(yaw_values)} x {len(pitch_values)}"

        batch_size = self.batch_cols * self.batch_rows
        total_batches = int(np.ceil(len(angle_pairs) / batch_size)) if angle_pairs else 0
        rows = []
        for batch_index, start in enumerate(range(0, len(angle_pairs), batch_size), start=1):
            rows.extend(
                self.render_angle_batch(
                    base_vertices,
                    base_faces,
                    angle_pairs[start : start + batch_size],
                    cell_pixels=size,
                )
            )
            if show_progress:
                print_dot_progress(f"FboVtc {grid_label}", batch_index, total_batches)
        return rows

    def component_volumes_for_yaw_pitch_grid(
        self,
        mesh: trimesh.Trimesh | None = None,
        yaw_values: np.ndarray | None = None,
        pitch_values: np.ndarray | None = None,
        size: int = 512,
        object_volume: float | None = None,
        critical_angle_deg: float | None = None,
        show_progress: bool = True,
    ) -> list[VtcVssVnvRow]:
        mesh = self.require_mesh(mesh)
        use_unique_pairs = yaw_values is None and pitch_values is None and self.orientation_pairs is not None
        if yaw_values is None:
            yaw_values = self.angles_yaw
        if pitch_values is None:
            pitch_values = self.angles_pitch
        if object_volume is None:
            object_volume = abs(float(mesh.volume))
        if critical_angle_deg is None:
            critical_angle_deg = self.filament_critical_angle

        self.ensure_context()
        base_vertices = np.asarray(mesh.vertices, dtype=np.float64)
        base_faces = np.asarray(mesh.faces, dtype=np.uint32)
        base_normals = np.asarray(mesh.face_normals, dtype=np.float64)

        if use_unique_pairs:
            angle_pairs = [(float(yaw_deg), float(pitch_deg)) for yaw_deg, pitch_deg in self.orientation_pairs]
            grid_label = f"{len(angle_pairs)} unique rotations"
        else:
            angle_pairs = [
                (float(yaw_deg), float(pitch_deg))
                for pitch_deg in pitch_values
                for yaw_deg in yaw_values
            ]
            grid_label = f"{len(yaw_values)} x {len(pitch_values)}"

        batch_size = self.batch_cols * self.batch_rows
        total_batches = int(np.ceil(len(angle_pairs) / batch_size)) if angle_pairs else 0
        rows = []
        for batch_index, start in enumerate(range(0, len(angle_pairs), batch_size), start=1):
            rows.extend(
                self.render_component_angle_batch(
                    base_vertices,
                    base_faces,
                    base_normals,
                    angle_pairs[start : start + batch_size],
                    cell_pixels=size,
                    object_volume=float(object_volume),
                    critical_angle_deg=float(critical_angle_deg),
                )
            )
            if show_progress:
                print_dot_progress(f"FboVtc components {grid_label}", batch_index, total_batches)
        return rows

    def beta_contribution_volumes_for_yaw_pitch_grid(
        self,
        mesh: trimesh.Trimesh | None = None,
        yaw_values: np.ndarray | None = None,
        pitch_values: np.ndarray | None = None,
        size: int = 512,
        critical_angle_deg: float | None = None,
        show_progress: bool = True,
    ) -> list[BetaComponentRow]:
        mesh = self.require_mesh(mesh)
        use_unique_pairs = yaw_values is None and pitch_values is None and self.orientation_pairs is not None
        if yaw_values is None:
            yaw_values = self.angles_yaw
        if pitch_values is None:
            pitch_values = self.angles_pitch
        if critical_angle_deg is None:
            critical_angle_deg = self.filament_critical_angle

        self.ensure_context()
        base_vertices = np.asarray(mesh.vertices, dtype=np.float64)
        base_faces = np.asarray(mesh.faces, dtype=np.uint32)
        base_normals = np.asarray(mesh.face_normals, dtype=np.float64)

        if use_unique_pairs:
            angle_pairs = [(float(yaw_deg), float(pitch_deg)) for yaw_deg, pitch_deg in self.orientation_pairs]
            grid_label = f"{len(angle_pairs)} unique rotations"
        else:
            angle_pairs = [
                (float(yaw_deg), float(pitch_deg))
                for pitch_deg in pitch_values
                for yaw_deg in yaw_values
            ]
            grid_label = f"{len(yaw_values)} x {len(pitch_values)}"

        batch_size = self.batch_cols * self.batch_rows
        total_batches = int(np.ceil(len(angle_pairs) / batch_size)) if angle_pairs else 0
        rows = []
        for batch_index, start in enumerate(range(0, len(angle_pairs), batch_size), start=1):
            rows.extend(
                self.render_beta_contribution_angle_batch(
                    base_vertices,
                    base_faces,
                    base_normals,
                    angle_pairs[start : start + batch_size],
                    cell_pixels=size,
                    critical_angle_deg=float(critical_angle_deg),
                )
            )
            if show_progress:
                print_dot_progress(f"FboVtc beta components {grid_label}", batch_index, total_batches)
        return rows

    def fused_beta_volumes_for_yaw_pitch_grid(
        self,
        mesh: trimesh.Trimesh | None = None,
        yaw_values: np.ndarray | None = None,
        pitch_values: np.ndarray | None = None,
        size: int = 512,
        critical_angle_deg: float | None = None,
        show_progress: bool = True,
    ) -> tuple[list[VtcRow], list[BetaComponentRow]]:
        mesh = self.require_mesh(mesh)
        use_unique_pairs = yaw_values is None and pitch_values is None and self.orientation_pairs is not None
        if yaw_values is None:
            yaw_values = self.angles_yaw
        if pitch_values is None:
            pitch_values = self.angles_pitch
        if critical_angle_deg is None:
            critical_angle_deg = self.filament_critical_angle

        self.ensure_context()
        base_vertices = np.asarray(mesh.vertices, dtype=np.float64)
        base_faces = np.asarray(mesh.faces, dtype=np.uint32)
        base_normals = np.asarray(mesh.face_normals, dtype=np.float64)

        if use_unique_pairs:
            angle_pairs = [(float(yaw_deg), float(pitch_deg)) for yaw_deg, pitch_deg in self.orientation_pairs]
            grid_label = f"{len(angle_pairs)} unique rotations"
        else:
            angle_pairs = [
                (float(yaw_deg), float(pitch_deg))
                for pitch_deg in pitch_values
                for yaw_deg in yaw_values
            ]
            grid_label = f"{len(yaw_values)} x {len(pitch_values)}"

        batch_size = self.batch_cols * self.batch_rows
        total_batches = int(np.ceil(len(angle_pairs) / batch_size)) if angle_pairs else 0
        vtc_rows = []
        beta_rows = []
        for batch_index, start in enumerate(range(0, len(angle_pairs), batch_size), start=1):
            vtc_batch, beta_batch = self.render_fused_beta_angle_batch(
                base_vertices,
                base_faces,
                base_normals,
                angle_pairs[start : start + batch_size],
                cell_pixels=size,
                critical_angle_deg=float(critical_angle_deg),
            )
            vtc_rows.extend(vtc_batch)
            beta_rows.extend(beta_batch)
            if show_progress:
                print_dot_progress(f"FboVtc fused beta components {grid_label}", batch_index, total_batches)
        return vtc_rows, beta_rows

    def get_Vtc_Vss_Vnv(
        self,
        *,
        object_volume: float | None = None,
        critical_angle_deg: float | None = None,
        show_progress: bool = True,
    ) -> dict[str, np.ndarray]:
        mesh = self.require_mesh()
        if object_volume is None:
            object_volume = abs(float(mesh.volume))
        if critical_angle_deg is None:
            critical_angle_deg = self.filament_critical_angle
        component_params = (float(object_volume), float(critical_angle_deg))

        if not self.component_rows or self.component_params != component_params:
            if self.voxel_size is None:
                self.voxel_size = nearest_power_of_2(max(mesh.bounding_box.extents))

            with self:
                self.print_run_info()
                print(f"component object volume: {float(object_volume):.6f}")
                print(f"component critical angle: {float(critical_angle_deg):.6f}")
                self.component_rows = self.component_volumes_for_yaw_pitch_grid(
                    size=self.voxel_size,
                    object_volume=float(object_volume),
                    critical_angle_deg=float(critical_angle_deg),
                    show_progress=show_progress,
                )
                self.component_params = component_params

        v_tc = np.asarray([row.v_tc for row in self.component_rows], dtype=np.float64)
        v_ss = np.asarray([row.v_ss for row in self.component_rows], dtype=np.float64)
        v_nv = np.asarray([row.v_nv for row in self.component_rows], dtype=np.float64)
        if self.orientation_inverse is not None:
            return {
                "V_tc": v_tc[self.orientation_inverse],
                "V_ss": v_ss[self.orientation_inverse],
                "V_nv": v_nv[self.orientation_inverse],
            }
        shape = (len(self.angles_pitch), len(self.angles_yaw))
        return {
            "V_tc": v_tc.reshape(shape),
            "V_ss": v_ss.reshape(shape),
            "V_nv": v_nv.reshape(shape),
        }

    def get_beta_components(
        self,
        *,
        critical_angle_deg: float | None = None,
        show_progress: bool = True,
    ) -> dict[str, np.ndarray]:
        mesh = self.require_mesh()
        if critical_angle_deg is None:
            critical_angle_deg = self.filament_critical_angle
        beta_params = (float(critical_angle_deg),)

        if self.voxel_size is None:
            self.voxel_size = nearest_power_of_2(max(mesh.bounding_box.extents))

        if not self.rows or not self.beta_rows or self.beta_params != beta_params:
            with self:
                self.print_run_info()
                print(f"beta contribution critical angle: {float(critical_angle_deg):.6f}")
                fused_start = time.perf_counter()
                self.rows, self.beta_rows = self.fused_beta_volumes_for_yaw_pitch_grid(
                    size=self.voxel_size,
                    critical_angle_deg=float(critical_angle_deg),
                    show_progress=show_progress,
                )
                log_time("FboVtc fused V_tc + beta raster pass time", fused_start)
                self.beta_params = beta_params

        v_tc = np.asarray([row.volume for row in self.rows], dtype=np.float64)
        v_al = np.asarray([row.v_al for row in self.beta_rows], dtype=np.float64)
        v_be = np.asarray([row.v_be for row in self.beta_rows], dtype=np.float64)
        v_o = np.asarray([row.v_o for row in self.beta_rows], dtype=np.float64)
        v_nv = np.asarray([row.v_nv for row in self.beta_rows], dtype=np.float64)
        v_ss = v_tc - v_o - v_nv
        if self.orientation_inverse is not None:
            return {
                "V_tc": v_tc[self.orientation_inverse],
                "V_al": v_al[self.orientation_inverse],
                "V_be": v_be[self.orientation_inverse],
                "V_o": v_o[self.orientation_inverse],
                "V_nv": v_nv[self.orientation_inverse],
                "V_ss": v_ss[self.orientation_inverse],
            }
        shape = (len(self.angles_pitch), len(self.angles_yaw))
        return {
            "V_tc": v_tc.reshape(shape),
            "V_al": v_al.reshape(shape),
            "V_be": v_be.reshape(shape),
            "V_o": v_o.reshape(shape),
            "V_nv": v_nv.reshape(shape),
            "V_ss": v_ss.reshape(shape),
        }

    def get_Vtc(self) -> np.ndarray:
        if not self.rows:
            mesh = self.require_mesh()
            if self.voxel_size is None:
                self.voxel_size = nearest_power_of_2(max(mesh.bounding_box.extents))

            with self:
                self.print_run_info()
                self.rows = self.volumes_for_yaw_pitch_grid(
                    size=self.voxel_size,
                    show_progress=True,
                )

            if DEFAULT_VERBOSE:
                print()
                print("yaw,pitch,volume")
                for row in self.rows:
                    print(f"{row.yaw_deg:.1f},{row.pitch_deg:.1f},{row.volume:.1f}")

        volumes = np.asarray([row.volume for row in self.rows], dtype=np.float64)
        if self.orientation_inverse is not None:
            return volumes[self.orientation_inverse]
        return volumes.reshape(len(self.angles_pitch), len(self.angles_yaw))

    def run(self) -> np.ndarray:
        t0 = time.perf_counter()
        v_tc = self.get_Vtc()
        log_time("FboVtc calc. time", t0)
        return v_tc

    def run_components(
        self,
        *,
        object_volume: float | None = None,
        critical_angle_deg: float | None = None,
    ) -> dict[str, np.ndarray]:
        t0 = time.perf_counter()
        components = self.get_Vtc_Vss_Vnv(
            object_volume=object_volume,
            critical_angle_deg=critical_angle_deg,
        )
        log_time("FboVtc component calc. time", t0)
        return components

    def run_beta_components(
        self,
        *,
        critical_angle_deg: float | None = None,
    ) -> dict[str, np.ndarray]:
        t0 = time.perf_counter()
        components = self.get_beta_components(critical_angle_deg=critical_angle_deg)
        log_time("FboVtc beta component calc. time", t0)
        return components

    def render(
        self,
        yaw_deg: float = 0.0,
        pitch_deg: float = 0.0,
        show_tc_mesh: bool = True,
        top_cover_size: int | None = None,
    ) -> None:
        if self._rendered or self.renderer is None or self.mesh is None:
            return

        ps_mesh = self.renderer.register_surface_mesh(
            "FboVtc input mesh",
            np.asarray(self.mesh.vertices, dtype=np.float64),
            np.asarray(self.mesh.faces, dtype=np.int32),
            smooth_shade=False,
            color=(0.12, 0.62, 0.92),
            transparency=0.28,
        )
        ps_mesh.set_enabled(False)
        group = self.renderer.create_group("FboVtc top cover") if hasattr(self.renderer, "create_group") else None
        if group is not None:
            ps_mesh.add_to_group(group)

        if show_tc_mesh:
            face_ids, tc_tri_mesh, tc_mesh = self.build_tc_mesh(
                self.mesh,
                yaw_deg=yaw_deg,
                pitch_deg=pitch_deg,
                size=top_cover_size,
            )
            if len(face_ids):
                tc_tri_ps = self.renderer.register_surface_mesh(
                    f"TC_tri yaw={yaw_deg:.1f} pitch={pitch_deg:.1f}",
                    np.asarray(tc_tri_mesh.vertices, dtype=np.float64),
                    np.asarray(tc_tri_mesh.faces, dtype=np.int32),
                    smooth_shade=False,
                    color=(1.0, 0.74, 0.12),
                    transparency=0.08,
                )
                tc_mesh_ps = self.renderer.register_surface_mesh(
                    f"TC_mesh yaw={yaw_deg:.1f} pitch={pitch_deg:.1f}",
                    np.asarray(tc_mesh.vertices, dtype=np.float64),
                    np.asarray(tc_mesh.faces, dtype=np.int32),
                    smooth_shade=False,
                    color=(0.12, 0.72, 0.58),
                    transparency=0.62,
                )
                if group is not None:
                    tc_tri_ps.add_to_group(group)
                    tc_mesh_ps.add_to_group(group)
                print(
                    f"TC_tri: {len(face_ids)} faces, TC_mesh: "
                    f"{len(tc_mesh.vertices)} vertices / {len(tc_mesh.faces)} faces",
                    flush=True,
                )
            else:
                print("TC_tri: no top-cover faces found", flush=True)
        self._rendered = True


def nearest_power_of_2(n: float) -> int:
    if n <= 0:
        return 1
    return 2 ** round(math.log2(n))


def load_mesh(path: str | Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)
    return mesh


def log_time(label: str, start_time: float) -> None:
    print(f"{GREEN}{label}: {time.perf_counter() - start_time:.3f}s{RESET}", flush=True)


def print_context_info(ctx: moderngl.Context) -> None:
    print()
    print(ctx.info["GL_RENDERER"])
    print("GL_MAX_TEXTURE_SIZE:", ctx.info["GL_MAX_TEXTURE_SIZE"])
    print("GL_MAX_RENDERBUFFER_SIZE:", ctx.info["GL_MAX_RENDERBUFFER_SIZE"])
    print("GL_MAX_VIEWPORT_DIMS:", ctx.info["GL_MAX_VIEWPORT_DIMS"])
    print()

