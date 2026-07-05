import math
import time
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

import moderngl
import numpy as np
import trimesh
import coacd
from scipy.spatial import ConvexHull

from ..tse6_config import TSE6Config

EPS = 1e-8

fname = "Experimental/etc/FTree4x.obj"
fname = "Experimental/etc/_1_MashaPNG/masha1.obj"
fname = "Experimental/etc/(5)Bunny_69k.ply"
fname = "Experimental/etc/(7)Bunny_1k.obj"

opposite_normal_dot = 0.01
normal_line_dot = 0.15
sample_radius_px = 1
max_candidate_pairs = 25000
use_exact_outside_test = True
use_coacd_broad_phase = True
show_polyscope = True

use_fbo_candidate_broad_phase = True
FBO_max_size = 256 # final pair test, or sometimes also 256
FBO_grid_cols = 32
FBO_grid_rows = FBO_grid_cols

coacd_threshold = 0.1
coacd_resolution = 100
coacd_mcts_nodes = 10
coacd_mcts_iterations = 10
coacd_mcts_max_depth = 3
coacd_hull_assign_scale = 1.02
coacd_hull_occluder_scale = 1.02
coacd_hull_visible_scale = 0.98
coacd_visibility_samples = 4
candidate_fbo_size_for_broad_phase = 128 
candidate_sample_radius_px = 2
include_same_hull_cpu_candidates = False
candidate_cpu_block_pair_limit = 5000
final_pair_atlas_cols = 16
final_pair_atlas_rows = 16


VERTEX_SHADER = """
#version 330

in vec3 in_position;

uniform mat4 u_mvp;
uniform vec3 u_axis_dir;

out float v_axis_t;

void main() {
    v_axis_t = dot(in_position, u_axis_dir);
    gl_Position = u_mvp * vec4(in_position, 1.0);
}
"""


FRAGMENT_SHADER = """
#version 330

out uint out_face_id;

in float v_axis_t;

uniform bool u_use_axis_clip;
uniform float u_axis_min;
uniform float u_axis_max;

void main() {
    if (u_use_axis_clip && (v_axis_t < u_axis_min || v_axis_t > u_axis_max)) {
        discard;
    }
    out_face_id = uint(gl_PrimitiveID + 1);
}
"""


ATLAS_VERTEX_SHADER = """
#version 330

in vec3 in_position;
in float in_face_id;

flat out float v_face_id;

void main() {
    v_face_id = in_face_id;
    gl_Position = vec4(in_position, 1.0);
}
"""


ATLAS_FRAGMENT_SHADER = """
#version 330

out uint out_face_id;

flat in float v_face_id;

void main() {
    out_face_id = uint(v_face_id + 0.5);
}
"""


def log_time(label, start_time):
    print(f"{label}: {time.perf_counter() - start_time:.3f}s")


def normalize(v, eps=EPS):
    v = np.asarray(v, dtype=np.float64)
    length = np.linalg.norm(v)
    if length < eps:
        return None
    return v / length


def nearest_power_of_2(n):
    if n <= 0:
        return 1
    return 2 ** round(math.log2(n))


def minimal_power_of_2_fbo_size(mesh, min_size=1, max_size=None):
    max_extent = float(np.max(mesh.bounding_box.extents))
    if max_extent <= 0.0:
        size = int(min_size)
    else:
        size = 2 ** math.ceil(math.log2(max_extent))
        size = max(size, int(min_size))

    if max_size is not None:
        size = min(size, int(max_size))
    return int(size)


def make_view_basis(view_dir):
    """Return rows of a world-to-view rotation. View direction becomes +Z."""
    z_axis = normalize(view_dir)
    if z_axis is None:
        raise ValueError("view_dir must be non-zero")

    up = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    if abs(float(np.dot(up, z_axis))) > 0.95:
        up = np.array([0.0, 1.0, 0.0], dtype=np.float64)

    x_axis = normalize(np.cross(up, z_axis))
    y_axis = np.cross(z_axis, x_axis)
    return np.vstack([x_axis, y_axis, z_axis])


def make_ortho_matrix_for_basis(points, basis, padding_ratio=0.03):
    view_points = np.asarray(points, dtype=np.float64) @ basis.T

    bounds_min = view_points.min(axis=0)
    bounds_max = view_points.max(axis=0)
    extent = np.maximum(bounds_max - bounds_min, EPS)
    pad = np.maximum(extent * padding_ratio, EPS)
    bounds_min -= pad
    bounds_max += pad

    xmin, ymin, zmin = bounds_min
    xmax, ymax, zmax = bounds_max

    sx = 2.0 / (xmax - xmin)
    sy = 2.0 / (ymax - ymin)
    sz = -2.0 / (zmax - zmin)
    tx = -(xmax + xmin) / (xmax - xmin)
    ty = -(ymax + ymin) / (ymax - ymin)
    tz = (2.0 * zmax) / (zmax - zmin) - 1.0

    proj = np.array(
        [
            [sx, 0.0, 0.0, tx],
            [0.0, sy, 0.0, ty],
            [0.0, 0.0, sz, tz],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )

    view = np.eye(4, dtype=np.float64)
    view[:3, :3] = basis
    mvp = proj @ view
    return mvp.astype(np.float32), (xmin, xmax, ymin, ymax, zmin, zmax), basis


def make_ortho_matrix_for_view(points, view_dir, padding_ratio=0.03):
    return make_ortho_matrix_for_basis(points, make_view_basis(view_dir), padding_ratio)


def project_point_to_pixel(point, basis, padded_bounds, size):
    xmin, xmax, ymin, ymax, _zmin, _zmax = padded_bounds
    p_view = np.asarray(point, dtype=np.float64) @ basis.T

    u = (p_view[0] - xmin) / (xmax - xmin)
    v = (p_view[1] - ymin) / (ymax - ymin)
    x = int(np.clip(round(u * (size - 1)), 0, size - 1))
    y = int(np.clip(round(v * (size - 1)), 0, size - 1))
    return x, y


def make_face_id_fbo(ctx, size):
    if isinstance(size, int):
        size = (size, size)

    texture = ctx.texture(size, components=1, dtype="u4")
    texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
    depth = ctx.depth_renderbuffer(size)
    fbo = ctx.framebuffer(color_attachments=[texture], depth_attachment=depth)
    return fbo, texture


def make_mesh_vao(ctx, program, mesh):
    vertices = np.asarray(mesh.vertices, dtype=np.float32)
    faces = np.asarray(mesh.faces, dtype=np.uint32)
    vbo = ctx.buffer(vertices.tobytes())
    ibo = ctx.buffer(faces.reshape(-1).tobytes())
    vao = ctx.vertex_array(program, [(vbo, "3f", "in_position")], index_buffer=ibo)
    return vao


def render_face_ids_to_texture(
    ctx,
    program,
    vao,
    mesh,
    view_dir,
    fbo,
    texture,
    size,
    axis_clip=None,
    bounds_points=None,
    basis=None,
):
    if bounds_points is None:
        bounds_points = mesh.vertices

    if basis is None:
        mvp, padded_bounds, basis = make_ortho_matrix_for_view(bounds_points, view_dir)
    else:
        mvp, padded_bounds, basis = make_ortho_matrix_for_basis(bounds_points, basis)
    program["u_mvp"].write(mvp.T.tobytes())
    program["u_axis_dir"].value = tuple(np.asarray(view_dir, dtype=np.float32))
    if axis_clip is None:
        program["u_use_axis_clip"].value = False
        program["u_axis_min"].value = 0.0
        program["u_axis_max"].value = 0.0
    else:
        axis_min, axis_max = axis_clip
        program["u_use_axis_clip"].value = True
        program["u_axis_min"].value = float(axis_min)
        program["u_axis_max"].value = float(axis_max)

    fbo.use()
    ctx.viewport = (0, 0, size, size)
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.disable(moderngl.CULL_FACE)
    ctx.depth_func = "<"
    fbo.clear(red=0, depth=1.0)
    vao.render()

    data = texture.read(alignment=1)
    face_ids = np.frombuffer(data, dtype=np.uint32).reshape(size, size)
    return face_ids, padded_bounds, basis


def render_face_ids(ctx, program, vao, mesh, view_dir, size, axis_clip=None):
    fbo, texture = make_face_id_fbo(ctx, size)
    face_ids, padded_bounds, basis = render_face_ids_to_texture(
        ctx,
        program,
        vao,
        mesh,
        view_dir,
        fbo,
        texture,
        size,
        axis_clip=axis_clip,
    )

    fbo.release()
    texture.release()
    return face_ids, padded_bounds, basis


def id_in_neighborhood(face_ids, x, y, expected_face, radius=1):
    expected_id = int(expected_face) + 1
    y0 = max(0, y - radius)
    y1 = min(face_ids.shape[0], y + radius + 1)
    x0 = max(0, x - radius)
    x1 = min(face_ids.shape[1], x + radius + 1)
    return np.any(face_ids[y0:y1, x0:x1] == expected_id)


def candidate_visible_pairs(mesh, opposite_dot=-0.65, line_dot=0.15, max_pairs=None):
    centers = np.asarray(mesh.triangles_center, dtype=np.float64)
    normals = np.asarray(mesh.face_normals, dtype=np.float64)
    pairs = []

    for i in range(len(centers)):
        delta = centers[i + 1 :] - centers[i]
        distance = np.linalg.norm(delta, axis=1)
        valid_distance = distance > EPS
        if not np.any(valid_distance):
            continue

        j_ids = np.arange(i + 1, len(centers))[valid_distance]
        directions = delta[valid_distance] / distance[valid_distance, None]

        # "Visible pair" here means both normals face the center-to-center gap.
        # They do not need to be anti-parallel; many valid FTree4x pairs are
        # perpendicular, with normal dot == 0.
        normal_opposed = normals[j_ids] @ normals[i] <= opposite_dot
        faces_toward_gap = (
            (directions @ normals[i] >= line_dot)
            & (np.einsum("ij,ij->i", normals[j_ids], directions) <= -line_dot)
        )
        valid = normal_opposed & faces_toward_gap
        if not np.any(valid):
            continue

        for j, d, dist in zip(j_ids[valid], directions[valid], distance[valid_distance][valid]):
            pairs.append((i, int(j), d, float(dist)))
            if max_pairs is not None and len(pairs) >= max_pairs:
                return pairs

    return pairs


def resize_hulls(hulls, scale_factor=1.02):
    resized = []
    for vertices, faces in hulls:
        vertices = np.asarray(vertices, dtype=np.float64).copy()
        center = vertices.mean(axis=0)
        vertices = (vertices - center) * scale_factor + center
        resized.append((vertices, np.asarray(faces, dtype=np.int64).copy()))
    return resized


def sort_hulls_by_center(hulls):
    centers = np.array([np.mean(vertices, axis=0) for vertices, _faces in hulls])
    order = np.lexsort((centers[:, 2], centers[:, 1], centers[:, 0]))
    return [hulls[i] for i in order]


def make_hull_data(hulls):
    hull_data = []
    for vertices, faces in hulls:
        vertices = np.asarray(vertices, dtype=np.float64)
        faces = np.asarray(faces, dtype=np.int64)
        triangles = vertices[faces]

        # ConvexHull equations are oriented as A*x + b <= 0 for inside points.
        equations = ConvexHull(vertices).equations
        hull_data.append(
            {
                "vertices": vertices,
                "faces": faces,
                "triangles": triangles,
                "face_centers": triangles.mean(axis=1),
                "bounds_min": vertices.min(axis=0),
                "bounds_max": vertices.max(axis=0),
                "equations": equations,
            }
        )
    return hull_data


def representative_hull_points(hull, max_points=12):
    points = hull["face_centers"]
    if len(points) <= max_points:
        return points

    # Always include the hull center, then spread samples evenly through the
    # existing face-center list. This keeps hull visibility conservative enough
    # for broad-phase use without making it the bottleneck.
    center = hull["vertices"].mean(axis=0, keepdims=True)
    sample_count = max(max_points - 1, 1)
    ids = np.linspace(0, len(points) - 1, sample_count, dtype=np.int64)
    return np.vstack((center, points[ids]))


def assign_faces_to_hulls(mesh, hull_data):
    centers = np.asarray(mesh.triangles_center, dtype=np.float64)
    face_to_hull = np.full(len(centers), -1, dtype=np.int64)
    hull_face_ids = [[] for _hull in hull_data]

    remaining = np.arange(len(centers), dtype=np.int64)
    for hull_id, hull in enumerate(hull_data):
        if len(remaining) == 0:
            break

        equations = hull["equations"]
        values = centers[remaining] @ equations[:, :3].T + equations[:, 3]
        inside = np.all(values <= 1e-8, axis=1)
        if not np.any(inside):
            continue

        face_ids = remaining[inside]
        face_to_hull[face_ids] = hull_id
        hull_face_ids[hull_id].extend(face_ids.tolist())
        remaining = remaining[~inside]

    missed = np.flatnonzero(face_to_hull < 0)
    if len(missed) > 0:
        hull_centers = np.array([hull["vertices"].mean(axis=0) for hull in hull_data])
        for face_id in missed:
            hull_id = int(np.argmin(np.linalg.norm(hull_centers - centers[face_id], axis=1)))
            face_to_hull[face_id] = hull_id
            hull_face_ids[hull_id].append(int(face_id))

    return face_to_hull, [np.asarray(ids, dtype=np.int64) for ids in hull_face_ids]


def segment_intersects_hull(p0, p1, hull, eps=1e-9):
    p0 = np.asarray(p0, dtype=np.float64)
    p1 = np.asarray(p1, dtype=np.float64)
    seg_min = np.minimum(p0, p1)
    seg_max = np.maximum(p0, p1)
    if np.any(seg_max < hull["bounds_min"]) or np.any(seg_min > hull["bounds_max"]):
        return False

    direction = p1 - p0
    t_enter = 0.0
    t_exit = 1.0

    for equation in hull["equations"]:
        normal = equation[:3]
        denom = float(np.dot(normal, direction))
        dist = float(np.dot(normal, p0) + equation[3])

        if abs(denom) < eps:
            if dist > eps:
                return False
            continue

        t = -dist / denom
        if denom > 0.0:
            t_exit = min(t_exit, t)
        else:
            t_enter = max(t_enter, t)

        if t_enter > t_exit:
            return False

    return bool(t_enter < 1.0 - eps and t_exit > eps)


def segment_occluded_by_hulls(p0, p1, occluder_hulls, hull_i, hull_j):
    for hull_id, hull in enumerate(occluder_hulls):
        if hull_id == hull_i or hull_id == hull_j:
            continue
        if segment_intersects_hull(p0, p1, hull):
            return True
    return False


def hull_pair_is_visible(visible_hulls, occluder_hulls, hull_i, hull_j):
    centers_i = representative_hull_points(visible_hulls[hull_i], coacd_visibility_samples)
    centers_j = representative_hull_points(visible_hulls[hull_j], coacd_visibility_samples)

    for p0 in centers_i:
        for p1 in centers_j:
            if not segment_occluded_by_hulls(p0, p1, occluder_hulls, hull_i, hull_j):
                return True
    return False


def get_hull_visibility_matrix(visible_hulls, occluder_hulls):
    visibility = np.eye(len(visible_hulls), dtype=bool)
    for i in range(len(visible_hulls)):
        for j in range(i + 1, len(visible_hulls)):
            visibility[i, j] = visibility[j, i] = hull_pair_is_visible(
                visible_hulls,
                occluder_hulls,
                i,
                j,
            )
    return visibility


def build_coacd_broad_phase(mesh):
    coacd_mesh = coacd.Mesh(mesh.vertices, mesh.faces)
    coacd.set_log_level("warning")
    hulls = coacd.run_coacd(
        coacd_mesh,
        threshold=coacd_threshold,
        max_convex_hull=-1,
        preprocess_mode="auto",
        preprocess_resolution=10,
        resolution=coacd_resolution,
        mcts_nodes=coacd_mcts_nodes,
        mcts_iterations=coacd_mcts_iterations,
        mcts_max_depth=coacd_mcts_max_depth,
        pca=False,
        merge=True,
        seed=0,
    )
    hulls = sort_hulls_by_center(hulls)

    assign_hulls = make_hull_data(resize_hulls(hulls, coacd_hull_assign_scale))
    visible_hulls = make_hull_data(resize_hulls(hulls, coacd_hull_visible_scale))
    occluder_hulls = make_hull_data(resize_hulls(hulls, coacd_hull_occluder_scale))
    face_to_hull, hull_face_ids = assign_faces_to_hulls(mesh, assign_hulls)
    hull_visibility = get_hull_visibility_matrix(visible_hulls, occluder_hulls)

    assigned = sum(len(ids) for ids in hull_face_ids)
    visible_blocks = int(np.count_nonzero(np.triu(hull_visibility)))
    total_blocks = len(hulls) * (len(hulls) + 1) // 2
    print(
        f"hull-assigned faces: {assigned}/{len(mesh.faces)}, "
        f"visible hull blocks: {visible_blocks}/{total_blocks}"
    )

    return {
        "hulls": hulls,
        "face_to_hull": face_to_hull,
        "hull_face_ids": hull_face_ids,
        "hull_visibility": hull_visibility,
    }


def candidate_visible_pairs_by_hulls_cpu(
    mesh,
    broad_phase,
    opposite_dot=-0.65,
    line_dot=0.15,
    max_pairs=None,
):
    centers = np.asarray(mesh.triangles_center, dtype=np.float64)
    normals = np.asarray(mesh.face_normals, dtype=np.float64)
    hull_face_ids = broad_phase["hull_face_ids"]
    hull_visibility = broad_phase["hull_visibility"]
    pairs = []

    for hull_i, faces_i in enumerate(hull_face_ids):
        if len(faces_i) == 0:
            continue

        for hull_j in range(hull_i, len(hull_face_ids)):
            if not hull_visibility[hull_i, hull_j]:
                continue

            faces_j = hull_face_ids[hull_j]
            if len(faces_j) == 0:
                continue

            for face_i in faces_i:
                if hull_i == hull_j:
                    compare_faces = faces_j[faces_j > face_i]
                else:
                    compare_faces = faces_j
                if len(compare_faces) == 0:
                    continue

                delta = centers[compare_faces] - centers[face_i]
                distance = np.linalg.norm(delta, axis=1)
                valid_distance = distance > EPS
                if not np.any(valid_distance):
                    continue

                j_ids = compare_faces[valid_distance]
                directions = delta[valid_distance] / distance[valid_distance, None]
                normal_opposed = normals[j_ids] @ normals[face_i] <= opposite_dot
                faces_toward_gap = (
                    (directions @ normals[face_i] >= line_dot)
                    & (np.einsum("ij,ij->i", normals[j_ids], directions) <= -line_dot)
                )
                valid = normal_opposed & faces_toward_gap
                if not np.any(valid):
                    continue

                for face_j, direction, dist in zip(
                    j_ids[valid],
                    directions[valid],
                    distance[valid_distance][valid],
                ):
                    a = int(min(face_i, face_j))
                    b = int(max(face_i, face_j))
                    sorted_direction = centers[b] - centers[a]
                    sorted_dist = float(np.linalg.norm(sorted_direction))
                    if sorted_dist <= EPS:
                        continue

                    pairs.append((a, b, sorted_direction / sorted_dist, sorted_dist))
                    if max_pairs is not None and len(pairs) >= max_pairs:
                        return pairs

    return pairs


def filter_candidate_pair_ids(mesh, pair_ids, opposite_dot, line_dot):
    if len(pair_ids) == 0:
        return []

    centers = np.asarray(mesh.triangles_center, dtype=np.float64)
    normals = np.asarray(mesh.face_normals, dtype=np.float64)
    face_i = pair_ids[:, 0]
    face_j = pair_ids[:, 1]
    delta = centers[face_j] - centers[face_i]
    distance = np.linalg.norm(delta, axis=1)
    valid_distance = distance > EPS
    if not np.any(valid_distance):
        return []

    face_i = face_i[valid_distance]
    face_j = face_j[valid_distance]
    delta = delta[valid_distance]
    distance = distance[valid_distance]
    directions = delta / distance[:, None]
    normal_opposed = np.einsum("ij,ij->i", normals[face_j], normals[face_i]) <= opposite_dot
    faces_toward_gap = (
        np.einsum("ij,ij->i", directions, normals[face_i]) >= line_dot
    ) & (np.einsum("ij,ij->i", normals[face_j], directions) <= -line_dot)
    valid = normal_opposed & faces_toward_gap
    if not np.any(valid):
        return []

    filtered = []
    seen = set()
    for i, j in zip(face_i[valid], face_j[valid]):
        a = int(min(i, j))
        b = int(max(i, j))
        if a == b or (a, b) in seen:
            continue

        direction = centers[b] - centers[a]
        dist = float(np.linalg.norm(direction))
        if dist <= EPS:
            continue

        seen.add((a, b))
        filtered.append((a, b, direction / dist, dist))
    return filtered


def unique_visible_faces_from_ids(face_ids_list, allowed_faces):
    allowed_faces = np.asarray(allowed_faces, dtype=np.int64)
    visible = []
    for face_ids in face_ids_list:
        ids = np.unique(face_ids.astype(np.int64) - 1)
        ids = ids[ids >= 0]
        if len(ids) == 0:
            continue
        visible.append(np.intersect1d(ids, allowed_faces, assume_unique=False))

    if not visible:
        return np.empty(0, dtype=np.int64)
    return np.unique(np.concatenate(visible))


def make_oriented_pair_ids(faces_a, faces_b):
    faces_a = np.asarray(faces_a, dtype=np.int64)
    faces_b = np.asarray(faces_b, dtype=np.int64)
    if len(faces_a) == 0 or len(faces_b) == 0:
        return np.empty((0, 2), dtype=np.int64)

    ab = np.column_stack(
        (
            np.repeat(faces_a, len(faces_b)),
            np.tile(faces_b, len(faces_a)),
        )
    )
    ba = ab[:, ::-1]
    return np.vstack((ab, ba))


def candidate_pairs_for_face_sets(mesh, faces_a, faces_b, opposite_dot, line_dot):
    pair_ids = make_oriented_pair_ids(faces_a, faces_b)
    return filter_candidate_pair_ids(
        mesh,
        pair_ids,
        opposite_dot=opposite_dot,
        line_dot=line_dot,
    )


def hull_pair_axis_clip_and_bounds(hulls, hull_i, hull_j, direction):
    vertices_i = np.asarray(hulls[hull_i][0], dtype=np.float64)
    vertices_j = np.asarray(hulls[hull_j][0], dtype=np.float64)
    points = np.vstack((vertices_i, vertices_j))
    axis_values = points @ direction
    axis_min = float(axis_values.min())
    axis_max = float(axis_values.max())
    axis_margin = max((axis_max - axis_min) * 0.02, 1e-4)
    return (axis_min - axis_margin, axis_max + axis_margin), points


def transform_points_for_atlas_cell(points, mvp, cell_id, cols, rows):
    clip = np.column_stack((points, np.ones(len(points), dtype=np.float64))) @ mvp.T
    ndc = clip[:, :3] / clip[:, 3:4]

    col = cell_id % cols
    row = cell_id // cols
    ndc[:, 0] = ((ndc[:, 0] + 1.0) * 0.5 + col) * (2.0 / cols) - 1.0
    ndc[:, 1] = ((ndc[:, 1] + 1.0) * 0.5 + row) * (2.0 / rows) - 1.0
    return ndc


def make_candidate_atlas_vertices(mesh, tasks, reverse=False):
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    centers = np.asarray(mesh.triangles_center, dtype=np.float64)
    cols = int(FBO_grid_cols)
    rows = int(FBO_grid_rows)
    atlas_vertices = []
    atlas_face_ids = []

    for cell_id, task in enumerate(tasks):
        direction = task["direction"]
        axis_clip = task["axis_clip"]
        bounds_points = task["bounds_points"]
        if reverse:
            basis = task["basis"].copy()
            basis[2] *= -1.0
            view_dir = -direction
            axis_min, axis_max = -axis_clip[1], -axis_clip[0]
        else:
            basis = task["basis"]
            view_dir = direction
            axis_min, axis_max = axis_clip

        mvp, _bounds, _basis = make_ortho_matrix_for_basis(bounds_points, basis)
        axis_values = centers @ view_dir
        selected_faces = np.flatnonzero((axis_values >= axis_min) & (axis_values <= axis_max))
        if len(selected_faces) == 0:
            continue

        tri_vertices = vertices[faces[selected_faces]].reshape(-1, 3)
        atlas_vertices.append(
            transform_points_for_atlas_cell(tri_vertices, mvp, cell_id, cols, rows)
        )
        atlas_face_ids.append(np.repeat(selected_faces.astype(np.float32) + 1.0, 3))

    if not atlas_vertices:
        return None

    return np.column_stack(
        (
            np.vstack(atlas_vertices).astype(np.float32),
            np.concatenate(atlas_face_ids).astype(np.float32),
        )
    )


def render_candidate_atlas(ctx, atlas_program, mesh, tasks, reverse=False):
    cell_size = int(candidate_fbo_size_for_broad_phase)
    cols = int(FBO_grid_cols)
    rows = int(FBO_grid_rows)
    atlas_size = (cell_size * cols, cell_size * rows)

    fbo, texture = make_face_id_fbo(ctx, atlas_size)
    fbo.use()
    ctx.viewport = (0, 0, atlas_size[0], atlas_size[1])
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.disable(moderngl.CULL_FACE)
    ctx.depth_func = "<"
    fbo.clear(red=0, depth=1.0)

    data = make_candidate_atlas_vertices(mesh, tasks, reverse=reverse)
    if data is not None:
        vbo = ctx.buffer(data.tobytes())
        vao = ctx.vertex_array(
            atlas_program,
            [(vbo, "3f 1f", "in_position", "in_face_id")],
        )
        vao.render(mode=moderngl.TRIANGLES)
        vao.release()
        vbo.release()

    image = np.frombuffer(texture.read(alignment=1), dtype=np.uint32).reshape(
        atlas_size[1],
        atlas_size[0],
    )
    fbo.release()
    texture.release()

    cells = []
    for cell_id in range(len(tasks)):
        col = cell_id % cols
        row = cell_id // cols
        x0 = col * cell_size
        y0 = row * cell_size
        cells.append(image[y0 : y0 + cell_size, x0 : x0 + cell_size])
    return cells


def make_final_pair_atlas_tasks(mesh, candidates):
    centers = np.asarray(mesh.triangles_center, dtype=np.float64)
    bounds_points = np.asarray(mesh.vertices, dtype=np.float64)
    tasks = []

    for face_i, face_j, direction, distance in candidates:
        face_i = int(face_i)
        face_j = int(face_j)
        direction = np.asarray(direction, dtype=np.float64)
        midpoint = 0.5 * (centers[face_i] + centers[face_j])

        axis_i = float(np.dot(centers[face_i], direction))
        axis_j = float(np.dot(centers[face_j], direction))
        axis_margin = max(abs(axis_j - axis_i) * 0.02, 1e-4)
        axis_clip = (
            min(axis_i, axis_j) - axis_margin,
            max(axis_i, axis_j) + axis_margin,
        )
        _mvp, bounds, basis = make_ortho_matrix_for_view(bounds_points, direction)

        reverse_basis = basis.copy()
        reverse_basis[2] *= -1.0
        reverse_axis_clip = (-axis_clip[1], -axis_clip[0])
        _reverse_mvp, reverse_bounds, _reverse_basis = make_ortho_matrix_for_basis(
            bounds_points,
            reverse_basis,
        )

        tasks.append(
            {
                "face_i": face_i,
                "face_j": face_j,
                "direction": direction,
                "distance": float(distance),
                "midpoint": midpoint,
                "axis_clip": axis_clip,
                "bounds_points": bounds_points,
                "basis": basis,
                "bounds": bounds,
                "reverse_basis": reverse_basis,
                "reverse_axis_clip": reverse_axis_clip,
                "reverse_bounds": reverse_bounds,
            }
        )

    return tasks


def render_final_pair_viewport_atlas(
    ctx,
    program,
    vao,
    tasks,
    cell_size,
    cols,
    rows,
    reverse=False,
    fbo=None,
    texture=None,
):
    atlas_size = (int(cell_size) * int(cols), int(cell_size) * int(rows))

    owns_fbo = fbo is None or texture is None
    if owns_fbo:
        fbo, texture = make_face_id_fbo(ctx, atlas_size)

    fbo.use()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.disable(moderngl.CULL_FACE)
    ctx.depth_func = "<"
    fbo.clear(red=0, depth=1.0)

    for cell_id, task in enumerate(tasks):
        col = cell_id % cols
        row = cell_id // cols
        x0 = col * cell_size
        y0 = row * cell_size
        ctx.viewport = (x0, y0, cell_size, cell_size)

        if reverse:
            basis = task["reverse_basis"]
            view_dir = -task["direction"]
            axis_clip = task["reverse_axis_clip"]
        else:
            basis = task["basis"]
            view_dir = task["direction"]
            axis_clip = task["axis_clip"]

        mvp, _bounds, _basis = make_ortho_matrix_for_basis(task["bounds_points"], basis)
        program["u_mvp"].write(mvp.T.tobytes())
        program["u_axis_dir"].value = tuple(np.asarray(view_dir, dtype=np.float32))
        program["u_use_axis_clip"].value = True
        program["u_axis_min"].value = float(axis_clip[0])
        program["u_axis_max"].value = float(axis_clip[1])
        vao.render()

    image = np.frombuffer(texture.read(alignment=1), dtype=np.uint32).reshape(
        atlas_size[1],
        atlas_size[0],
    )
    if owns_fbo:
        fbo.release()
        texture.release()

    cells = []
    for cell_id in range(len(tasks)):
        col = cell_id % cols
        row = cell_id // cols
        x0 = col * cell_size
        y0 = row * cell_size
        cells.append(image[y0 : y0 + cell_size, x0 : x0 + cell_size])
    return cells


def final_pair_visibility_batch(
    ctx,
    program,
    vao,
    mesh,
    candidates,
    size,
    cols,
    rows,
    fbo=None,
    texture=None,
):
    tasks = make_final_pair_atlas_tasks(mesh, candidates)
    forward_cells = render_final_pair_viewport_atlas(
        ctx,
        program,
        vao,
        tasks,
        size,
        cols,
        rows,
        reverse=False,
        fbo=fbo,
        texture=texture,
    )
    reverse_cells = render_final_pair_viewport_atlas(
        ctx,
        program,
        vao,
        tasks,
        size,
        cols,
        rows,
        reverse=True,
        fbo=fbo,
        texture=texture,
    )

    visible = np.zeros(len(tasks), dtype=bool)
    for index, (task, forward_ids, reverse_ids) in enumerate(
        zip(tasks, forward_cells, reverse_cells)
    ):
        x_forward, y_forward = project_point_to_pixel(
            task["midpoint"],
            task["basis"],
            task["bounds"],
            size,
        )
        sees_j = id_in_neighborhood(
            forward_ids,
            x_forward,
            y_forward,
            task["face_j"],
            sample_radius_px,
        )
        if not sees_j:
            continue

        x_reverse, y_reverse = project_point_to_pixel(
            task["midpoint"],
            task["reverse_basis"],
            task["reverse_bounds"],
            size,
        )
        visible[index] = id_in_neighborhood(
            reverse_ids,
            x_reverse,
            y_reverse,
            task["face_i"],
            sample_radius_px,
        )

    return visible


def final_pair_atlas_grid(ctx, size, requested_cols, requested_rows):
    max_texture_size = int(ctx.info.get("GL_MAX_TEXTURE_SIZE", 8192))
    max_cells_per_axis = max(1, max_texture_size // max(int(size), 1))
    cols = max(1, min(int(requested_cols), max_cells_per_axis))
    rows = max(1, min(int(requested_rows), max_cells_per_axis))
    return cols, rows


def candidate_visible_pairs_by_hulls(
    mesh,
    broad_phase,
    opposite_dot=-0.65,
    line_dot=0.15,
    max_pairs=None,
    ctx=None,
    program=None,
    vao=None,
    atlas_program=None,
    size=None,
):
    if not use_fbo_candidate_broad_phase or ctx is None or atlas_program is None:
        return candidate_visible_pairs_by_hulls_cpu(
            mesh,
            broad_phase,
            opposite_dot=opposite_dot,
            line_dot=line_dot,
            max_pairs=max_pairs,
        )

    hulls = broad_phase["hulls"]
    hull_face_ids = broad_phase["hull_face_ids"]
    hull_visibility = broad_phase["hull_visibility"]
    hull_centers = np.array([np.mean(vertices, axis=0) for vertices, _faces in hulls])
    pairs = []
    seen = set()
    fbo_tasks = []
    atlas_capacity = int(FBO_grid_cols) * int(FBO_grid_rows)

    def add_item(item):
        key = (item[0], item[1])
        if key in seen:
            return False
        seen.add(key)
        pairs.append(item)
        return max_pairs is not None and len(pairs) >= max_pairs

    def flush_fbo_tasks():
        if not fbo_tasks:
            return False

        target_cells = render_candidate_atlas(ctx, atlas_program, mesh, fbo_tasks, reverse=False)
        source_cells = render_candidate_atlas(ctx, atlas_program, mesh, fbo_tasks, reverse=True)
        for task, source_ids, target_ids in zip(fbo_tasks, source_cells, target_cells):
            visible_i = unique_visible_faces_from_ids((source_ids, target_ids), task["faces_i"])
            visible_j = unique_visible_faces_from_ids((source_ids, target_ids), task["faces_j"])
            pair_ids = make_oriented_pair_ids(visible_i, visible_j)
            for item in filter_candidate_pair_ids(
                mesh,
                pair_ids,
                opposite_dot=opposite_dot,
                line_dot=line_dot,
            ):
                if add_item(item):
                    fbo_tasks.clear()
                    return True

        fbo_tasks.clear()
        return False

    for hull_i, faces_i in enumerate(hull_face_ids):
        if len(faces_i) == 0:
            continue

        if include_same_hull_cpu_candidates and hull_visibility[hull_i, hull_i]:
            same_phase = {
                "hull_face_ids": [faces_i],
                "hull_visibility": np.ones((1, 1), dtype=bool),
            }
            for item in candidate_visible_pairs_by_hulls_cpu(
                mesh,
                same_phase,
                opposite_dot=opposite_dot,
                line_dot=line_dot,
                max_pairs=None,
            ):
                if add_item(item):
                    return pairs

        for hull_j in range(hull_i + 1, len(hull_face_ids)):
            if not hull_visibility[hull_i, hull_j]:
                continue

            faces_j = hull_face_ids[hull_j]
            if len(faces_j) == 0:
                continue

            if len(faces_i) * len(faces_j) <= candidate_cpu_block_pair_limit:
                for item in candidate_pairs_for_face_sets(
                    mesh,
                    faces_i,
                    faces_j,
                    opposite_dot=opposite_dot,
                    line_dot=line_dot,
                ):
                    if add_item(item):
                        return pairs
                continue

            direction = normalize(hull_centers[hull_j] - hull_centers[hull_i])
            if direction is None:
                continue

            axis_clip, bounds_points = hull_pair_axis_clip_and_bounds(
                hulls,
                hull_i,
                hull_j,
                direction,
            )
            _mvp, _bounds, basis = make_ortho_matrix_for_view(bounds_points, direction)
            fbo_tasks.append(
                {
                    "faces_i": faces_i,
                    "faces_j": faces_j,
                    "direction": direction,
                    "axis_clip": axis_clip,
                    "bounds_points": bounds_points,
                    "basis": basis,
                }
            )

            if len(fbo_tasks) >= atlas_capacity and flush_fbo_tasks():
                return pairs

    flush_fbo_tasks()

    return pairs


def segment_is_outside_mesh(mesh, face_i, face_j, eps_scale=1e-5):
    centers = np.asarray(mesh.triangles_center, dtype=np.float64)
    normals = np.asarray(mesh.face_normals, dtype=np.float64)

    p0 = centers[face_i] + normals[face_i] * eps_scale
    p1 = centers[face_j] + normals[face_j] * eps_scale
    mid = 0.5 * (p0 + p1)
    direction = p1 - p0
    length = np.linalg.norm(direction)
    if length < EPS:
        return False

    # A visible outside connector has its midpoint outside the volume and no
    # mesh intersection strictly between the two lifted face centers.
    if mesh.is_watertight and mesh.contains([mid])[0]:
        return False

    locations, _ray_ids, tri_ids = mesh.ray.intersects_location(
        ray_origins=[p0],
        ray_directions=[direction / length],
        multiple_hits=True,
    )
    if len(locations) == 0:
        return True

    t = (locations - p0) @ (direction / length)
    internal_hits = (t > eps_scale * 10.0) & (t < length - eps_scale * 10.0)
    internal_hits &= (tri_ids != face_i) & (tri_ids != face_j)
    return not np.any(internal_hits)


def find_visible_triangle_pairs(
    mesh,
    size=512,
    opposite_dot=-0.65,
    line_dot=0.15,
    max_pairs=25000,
    exact_outside=True,
    coacd_broad_phase=True,
    return_broad_phase=False,
):
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)

    mesh = mesh.copy()
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()

    ctx = moderngl.create_context(standalone=True)
    program = ctx.program(vertex_shader=VERTEX_SHADER, fragment_shader=FRAGMENT_SHADER)
    atlas_program = ctx.program(
        vertex_shader=ATLAS_VERTEX_SHADER,
        fragment_shader=ATLAS_FRAGMENT_SHADER,
    )
    vao = make_mesh_vao(ctx, program, mesh)

    broad_phase = None
    if coacd_broad_phase:

        broad_phase = build_coacd_broad_phase(mesh)

        candidates = candidate_visible_pairs_by_hulls(
            mesh,
            broad_phase,
            opposite_dot=opposite_dot,
            line_dot=line_dot,
            max_pairs=max_pairs,
            ctx=ctx,
            program=program,
            vao=vao,
            atlas_program=atlas_program,
            size=candidate_fbo_size_for_broad_phase,
        )

    else:
        candidates = candidate_visible_pairs(
            mesh,
            opposite_dot=opposite_dot,
            line_dot=line_dot,
            max_pairs=max_pairs,
        )

    print(f"triangle candidates after broad phase: {len(candidates)}")

    visible_pairs = []
    atlas_cols, atlas_rows = final_pair_atlas_grid(
        ctx,
        size,
        final_pair_atlas_cols,
        final_pair_atlas_rows,
    )
    batch_capacity = atlas_cols * atlas_rows
    print(
        f"final pair atlas: {atlas_cols} x {atlas_rows} cells, "
        f"{size} px/cell, batch={batch_capacity}"
    )
    final_atlas_fbo, final_atlas_texture = make_face_id_fbo(
        ctx,
        (size * atlas_cols, size * atlas_rows),
    )

    next_progress = 1000
    for start in range(0, len(candidates), batch_capacity):
        end = min(start + batch_capacity, len(candidates))
        batch = candidates[start:end]
        batch_visible = final_pair_visibility_batch(
            ctx,
            program,
            vao,
            mesh,
            batch,
            size,
            atlas_cols,
            atlas_rows,
            fbo=final_atlas_fbo,
            texture=final_atlas_texture,
        )

        for local_index, (face_i, face_j, _direction, distance) in enumerate(batch):
            if not batch_visible[local_index]:
                continue

            if exact_outside and not segment_is_outside_mesh(mesh, face_i, face_j):
                continue

            visible_pairs.append((face_i, face_j, distance))

        if end >= next_progress or end == len(candidates):
            print(f"checked {end}/{len(candidates)} candidates, visible={len(visible_pairs)}")
            while next_progress <= end:
                next_progress += 1000

    final_atlas_fbo.release()
    final_atlas_texture.release()
    ctx.release()
    result = np.asarray(visible_pairs, dtype=np.float64), len(candidates)
    if return_broad_phase:
        return result + (broad_phase,)
    return result


def display_coacd_hulls(
    broad_phase,
    enabled=True,
    renderer=None,
    offset=None,
    name_prefix="",
    show_centers=True,
):
    if renderer is None:
        import polyscope as ps
    else:
        ps = renderer

    if broad_phase is None:
        return

    hulls = broad_phase.get("hulls")
    if not hulls:
        return

    label_prefix = f"{name_prefix} " if name_prefix else ""
    hull_group = ps.create_group(f"{label_prefix}coacd convex hulls")
    palette = np.array(
        [
            [0.90, 0.22, 0.20],
            [0.16, 0.56, 0.88],
            [0.18, 0.72, 0.38],
            [0.95, 0.64, 0.18],
            [0.62, 0.42, 0.86],
            [0.08, 0.72, 0.74],
        ],
        dtype=np.float64,
    )

    centers = []
    offset = np.zeros(3, dtype=np.float64) if offset is None else np.asarray(offset, dtype=np.float64)
    for hull_id, (hull_vertices, hull_faces) in enumerate(hulls):
        hull_vertices = np.asarray(hull_vertices, dtype=np.float64) + offset
        hull_faces = np.asarray(hull_faces, dtype=np.int32)
        centers.append(hull_vertices.mean(axis=0))

        ps_hull = ps.register_surface_mesh(
            f"{label_prefix}coacd hull {hull_id}",
            hull_vertices,
            hull_faces,
            smooth_shade=False,
            color=tuple(palette[hull_id % len(palette)]),
            transparency=0.42,
        )
        ps_hull.set_enabled(enabled)
        ps_hull.add_to_group(hull_group)

    if not show_centers:
        return

    centers = np.asarray(centers, dtype=np.float64)
    center_cloud = ps.register_point_cloud(
        f"{label_prefix}coacd hull centers",
        centers,
        radius=0.006,
        color=(0.04, 0.04, 0.04),
    )
    center_cloud.set_enabled(enabled)
    center_cloud.add_scalar_quantity(
        "hull id",
        np.arange(len(centers), dtype=np.float64),
        enabled=True,
    )
    center_cloud.add_to_group(hull_group)


def display_visible_triangle_pairs(
    mesh,
    pairs,
    broad_phase=None,
    renderer=None,
    show=True,
    offset=None,
    name_prefix="",
    show_mesh=True,
    show_hulls=True,
):
    if renderer is None:
        import polyscope as ps
    else:
        ps = renderer

    pairs = np.asarray(pairs)
    offset = np.zeros(3, dtype=np.float64) if offset is None else np.asarray(offset, dtype=np.float64)
    label_prefix = f"{name_prefix} " if name_prefix else ""
    centers = np.asarray(mesh.triangles_center, dtype=np.float64)
    normals = np.asarray(mesh.face_normals, dtype=np.float64)
    vertices = np.asarray(mesh.vertices, dtype=np.float64) + offset
    faces = np.asarray(mesh.faces, dtype=np.int32)
    shifted_centers = centers + offset

    if renderer is None:
        ps.init()
        ps.set_up_dir("z_up")

    if show_mesh:
        ps_mesh = ps.register_surface_mesh(
            f"{label_prefix}original mesh",
            vertices,
            faces,
            smooth_shade=False,
            color=(0.72, 0.74, 0.78),
            transparency=0.35,
        )
        ps_mesh.set_enabled(False)

    if show_hulls:
        display_coacd_hulls(
            broad_phase,
            enabled=True,
            renderer=ps,
            offset=offset,
            name_prefix=name_prefix,
        )

    if len(pairs) == 0:
        if show:
            ps.show()
        return

    pair_faces = pairs[:, :2].astype(np.int64)
    unique_faces = np.unique(pair_faces.reshape(-1))
    highlight_mesh = ps.register_surface_mesh(
        f"{label_prefix}visible-pair triangles",
        vertices,
        faces[unique_faces],
        smooth_shade=False,
        color=(1.0, 0.34, 0.12),
        transparency=0.82,
    )
    highlight_mesh.set_enabled(False)

    pair_nodes = np.empty((len(pairs) * 2, 3), dtype=np.float64)
    pair_nodes[0::2] = shifted_centers[pair_faces[:, 0]]
    pair_nodes[1::2] = shifted_centers[pair_faces[:, 1]]
    pair_edges = np.column_stack(
        (
            np.arange(0, len(pairs) * 2, 2, dtype=np.int32),
            np.arange(1, len(pairs) * 2, 2, dtype=np.int32),
        )
    )
    connectors = ps.register_curve_network(
        f"{label_prefix}visible pair connectors",
        pair_nodes,
        pair_edges,
        radius=0.0019,
        color=(0.05, 0.48, 1.0),
    )
    connectors.add_scalar_quantity(
        "pair id",
        np.arange(1, len(pairs) + 1, dtype=np.float64),
        defined_on="edges",
        enabled=True,
    )
    connectors.add_scalar_quantity(
        "distance",
        pairs[:, 2].astype(np.float64),
        defined_on="edges",
    )

    endpoint_cloud = ps.register_point_cloud(
        f"{label_prefix}pair endpoints",
        pair_nodes,
        radius=0.00550,
        color=(1.0, 0.92, 0.1),
    )
    endpoint_cloud.add_scalar_quantity(
        "face id",
        (pair_faces.reshape(-1) + 1).astype(np.float64),
        enabled=True,
    )
    endpoint_cloud.add_scalar_quantity(
        "pair id",
        np.repeat(np.arange(1, len(pairs) + 1), 2).astype(np.float64),
    )

    normal_face_ids = pair_faces.reshape(-1)
    normal_points = shifted_centers[normal_face_ids]
    normal_vectors = normals[normal_face_ids] * max(mesh.bounding_box.extents) * 0.06
    normal_cloud = ps.register_point_cloud(
        f"{label_prefix}paired face normals",
        normal_points,
        radius=0.009,
        enabled=True,
    )
    normal_cloud.add_vector_quantity(
        "normal",
        normal_vectors,
        enabled=True,
        color=(0.0, 0.85, 0.25),
    )

    if show:
        ps.show()


def load_mesh(path):
    mesh = trimesh.load_mesh(path, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)
    return mesh


@dataclass
class VisFacePairConfig:
    mesh_path: str = fname
    mesh: trimesh.Trimesh | None = None
    filament_critical_angle: float = 60.0
    renderer: object | None = None
    opposite_normal_dot: float = 0.01
    normal_line_dot: float = 0.15
    sample_radius_px: int = 1
    max_candidate_pairs: int | None = 25000
    use_exact_outside_test: bool = True
    use_coacd_broad_phase: bool = True
    show_polyscope: bool = False
    use_fbo_candidate_broad_phase: bool = True
    fbo_max_size: int = 256
    fbo_grid_cols: int = 32
    fbo_grid_rows: int = 32
    
    coacd_threshold: float = 0.1
    coacd_resolution: int = 100
    coacd_mcts_nodes: int = 10
    coacd_mcts_iterations: int = 10
    coacd_mcts_max_depth: int = 3
    coacd_hull_assign_scale: float = 1.02
    coacd_hull_occluder_scale: float = 1.02
    coacd_hull_visible_scale: float = 0.98
    coacd_visibility_samples: int = 4
    candidate_fbo_size_for_broad_phase: int = 128
    candidate_sample_radius_px: int = 2
    include_same_hull_cpu_candidates: bool = False
    candidate_cpu_block_pair_limit: int = 5000
    final_pair_atlas_cols: int = 16
    final_pair_atlas_rows: int = 16
    cache_visible_pairs: bool = True
    cache_dir: str | None = None


class VisFacePair:
    CACHE_VERSION = 1

    def __init__(self, config=None, **overrides):
        if config is None:
            config = VisFacePairConfig()
        elif isinstance(config, TSE6Config):
            config = VisFacePairConfig(
                mesh=config.mesh,
                filament_critical_angle=config.critical_angle,
                renderer=config.renderer,
            )
        elif isinstance(config, dict):
            config = VisFacePairConfig(**config)

        for key, value in overrides.items():
            if not hasattr(config, key):
                raise AttributeError(f"Unknown VisFacePairConfig field: {key}")
            setattr(config, key, value)

        self.config = config
        self.mesh = None
        self.pair_infos = None
        self.broad_phase = None
        self._apply_config()

    def _apply_config(self):
        global sample_radius_px
        global use_fbo_candidate_broad_phase
        global FBO_grid_cols, FBO_grid_rows
        global coacd_threshold, coacd_resolution
        global coacd_mcts_nodes, coacd_mcts_iterations, coacd_mcts_max_depth
        global coacd_hull_assign_scale, coacd_hull_occluder_scale, coacd_hull_visible_scale
        global coacd_visibility_samples
        global candidate_fbo_size_for_broad_phase, candidate_sample_radius_px
        global include_same_hull_cpu_candidates, candidate_cpu_block_pair_limit
        global final_pair_atlas_cols, final_pair_atlas_rows

        cfg = self.config
        sample_radius_px = cfg.sample_radius_px
        use_fbo_candidate_broad_phase = cfg.use_fbo_candidate_broad_phase
        FBO_grid_cols = cfg.fbo_grid_cols
        FBO_grid_rows = cfg.fbo_grid_rows
        coacd_threshold = cfg.coacd_threshold
        coacd_resolution = cfg.coacd_resolution
        coacd_mcts_nodes = cfg.coacd_mcts_nodes
        coacd_mcts_iterations = cfg.coacd_mcts_iterations
        coacd_mcts_max_depth = cfg.coacd_mcts_max_depth
        coacd_hull_assign_scale = cfg.coacd_hull_assign_scale
        coacd_hull_occluder_scale = cfg.coacd_hull_occluder_scale
        coacd_hull_visible_scale = cfg.coacd_hull_visible_scale
        coacd_visibility_samples = cfg.coacd_visibility_samples
        candidate_fbo_size_for_broad_phase = cfg.candidate_fbo_size_for_broad_phase
        candidate_sample_radius_px = cfg.candidate_sample_radius_px
        include_same_hull_cpu_candidates = cfg.include_same_hull_cpu_candidates
        candidate_cpu_block_pair_limit = cfg.candidate_cpu_block_pair_limit
        final_pair_atlas_cols = cfg.final_pair_atlas_cols
        final_pair_atlas_rows = cfg.final_pair_atlas_rows

    def load_mesh(self, path=None):
        if path is None and self.config.mesh is not None:
            return self.config.mesh.copy()
        return load_mesh(path or self.config.mesh_path)

    def minimal_fbo_size(self, mesh):
        return minimal_power_of_2_fbo_size(mesh, max_size=self.config.fbo_max_size)

    def default_cache_dir(self):
        return Path(__file__).resolve().parents[2] / ".cache" / "vis_face_pair"

    def cache_dir(self):
        if self.config.cache_dir is None:
            return self.default_cache_dir()
        return Path(self.config.cache_dir)

    @staticmethod
    def _hash_array(hasher, label, array):
        contiguous = np.ascontiguousarray(array)
        hasher.update(label.encode("utf-8"))
        hasher.update(str(contiguous.shape).encode("utf-8"))
        hasher.update(str(contiguous.dtype).encode("utf-8"))
        hasher.update(contiguous.view(np.uint8))

    def mesh_cache_hash(self, mesh):
        hasher = hashlib.blake2b(digest_size=16)
        self._hash_array(hasher, "vertices", np.asarray(mesh.vertices, dtype=np.float64))
        self._hash_array(hasher, "faces", np.asarray(mesh.faces, dtype=np.int64))
        return hasher.hexdigest()

    def cache_metadata(self, mesh, size):
        cfg = self.config
        return {
            "cache_version": self.CACHE_VERSION,
            "mesh_hash": self.mesh_cache_hash(mesh),
            "face_count": int(len(mesh.faces)),
            "fbo_size": int(size),
            "opposite_normal_dot": float(cfg.opposite_normal_dot),
            "normal_line_dot": float(cfg.normal_line_dot),
            "sample_radius_px": int(cfg.sample_radius_px),
            "max_candidate_pairs": None if cfg.max_candidate_pairs is None else int(cfg.max_candidate_pairs),
            "use_exact_outside_test": bool(cfg.use_exact_outside_test),
            "use_coacd_broad_phase": bool(cfg.use_coacd_broad_phase),
            "use_fbo_candidate_broad_phase": bool(cfg.use_fbo_candidate_broad_phase),
            "fbo_max_size": int(cfg.fbo_max_size),
            "fbo_grid_cols": int(cfg.fbo_grid_cols),
            "fbo_grid_rows": int(cfg.fbo_grid_rows),
            "coacd_threshold": float(cfg.coacd_threshold),
            "coacd_resolution": int(cfg.coacd_resolution),
            "coacd_mcts_nodes": int(cfg.coacd_mcts_nodes),
            "coacd_mcts_iterations": int(cfg.coacd_mcts_iterations),
            "coacd_mcts_max_depth": int(cfg.coacd_mcts_max_depth),
            "coacd_hull_assign_scale": float(cfg.coacd_hull_assign_scale),
            "coacd_hull_occluder_scale": float(cfg.coacd_hull_occluder_scale),
            "coacd_hull_visible_scale": float(cfg.coacd_hull_visible_scale),
            "coacd_visibility_samples": int(cfg.coacd_visibility_samples),
            "candidate_fbo_size_for_broad_phase": int(cfg.candidate_fbo_size_for_broad_phase),
            "candidate_sample_radius_px": int(cfg.candidate_sample_radius_px),
            "include_same_hull_cpu_candidates": bool(cfg.include_same_hull_cpu_candidates),
            "candidate_cpu_block_pair_limit": int(cfg.candidate_cpu_block_pair_limit),
            "final_pair_atlas_cols": int(cfg.final_pair_atlas_cols),
            "final_pair_atlas_rows": int(cfg.final_pair_atlas_rows),
        }

    def cache_path_for_metadata(self, metadata):
        key_json = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
        key = hashlib.blake2b(key_json.encode("utf-8"), digest_size=16).hexdigest()
        return self.cache_dir() / f"vis_face_pair_{key}.npz"

    def load_cached_result(self, cache_path):
        if not cache_path.exists():
            return None
        try:
            with np.load(cache_path, allow_pickle=False) as data:
                pair_infos = data["pair_infos"]
                candidate_count = int(data["candidate_count"][0])
        except Exception as exc:
            print(f"VisFacePair cache ignored: failed to read {cache_path} ({exc})")
            return None
        print(f"VisFacePair cache hit: {cache_path}")
        return pair_infos, candidate_count

    def save_cached_result(self, cache_path, pair_infos, candidate_count):
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                cache_path,
                pair_infos=np.asarray(pair_infos),
                candidate_count=np.array([int(candidate_count)], dtype=np.int64),
            )
            print(f"VisFacePair cache saved: {cache_path}")
        except Exception as exc:
            print(f"VisFacePair cache save skipped: {exc}")

    def build_coacd_broad_phase(self, mesh):
        self._apply_config()
        return build_coacd_broad_phase(mesh)

    def candidate_visible_pairs_by_hulls(self, mesh, broad_phase, **kwargs):
        self._apply_config()
        kwargs.setdefault("opposite_dot", self.config.opposite_normal_dot)
        kwargs.setdefault("line_dot", self.config.normal_line_dot)
        kwargs.setdefault("max_pairs", self.config.max_candidate_pairs)
        return candidate_visible_pairs_by_hulls(mesh, broad_phase, **kwargs)

    def find_visible_triangle_pairs(
        self,
        mesh,
        size=None,
        opposite_dot=None,
        line_dot=None,
        max_pairs=None,
        exact_outside=None,
        coacd_broad_phase=None,
        return_broad_phase=False,
    ):
        self._apply_config()
        cfg = self.config
        if size is None:
            size = self.minimal_fbo_size(mesh)
        if opposite_dot is None:
            opposite_dot = cfg.opposite_normal_dot
        if line_dot is None:
            line_dot = cfg.normal_line_dot
        if max_pairs is None:
            max_pairs = cfg.max_candidate_pairs
        if exact_outside is None:
            exact_outside = cfg.use_exact_outside_test
        if coacd_broad_phase is None:
            coacd_broad_phase = cfg.use_coacd_broad_phase

        return find_visible_triangle_pairs(
            mesh,
            size=size,
            opposite_dot=opposite_dot,
            line_dot=line_dot,
            max_pairs=max_pairs,
            exact_outside=exact_outside,
            coacd_broad_phase=coacd_broad_phase,
            return_broad_phase=return_broad_phase,
        )

    def display_coacd_hulls(self, broad_phase, enabled=True, **kwargs):
        return display_coacd_hulls(broad_phase, enabled=enabled, **kwargs)

    def display_visible_triangle_pairs(self, mesh, pairs, broad_phase=None, renderer=None, show=True, **kwargs):
        return display_visible_triangle_pairs(
            mesh,
            pairs,
            broad_phase=broad_phase,
            renderer=renderer,
            show=show,
            **kwargs,
        )

    def run(self, mesh_path=None):
        cfg = self.config
        path = mesh_path or cfg.mesh_path

        t0 = time.perf_counter()
        mesh = self.load_mesh(mesh_path)

        size = self.minimal_fbo_size(mesh)

        print()
        print(f"mesh: {path if mesh_path is not None or cfg.mesh is None else '<TSE6Config.mesh>'}")
        print(f"faces: {len(mesh.faces)}")
        print(f"watertight: {mesh.is_watertight}")
        print(f"fbo size: {size} x {size}")
        print(f"pair normal dot <= {cfg.opposite_normal_dot}")
        print(f"normal-line dot >= {cfg.normal_line_dot}")
        print(f"coacd broad phase: {cfg.use_coacd_broad_phase}")
        print()

        cache_path = None
        cached_result = None
        if cfg.cache_visible_pairs:
            metadata = self.cache_metadata(mesh, size)
            cache_path = self.cache_path_for_metadata(metadata)
            cached_result = self.load_cached_result(cache_path)

        if cached_result is None:
            pair_infos, candidate_count, broad_phase = self.find_visible_triangle_pairs(
                mesh,
                size=size,
                return_broad_phase=True,
            )
            if cache_path is not None:
                self.save_cached_result(cache_path, pair_infos, candidate_count)
        else:
            pair_infos, candidate_count = cached_result
            broad_phase = None

        print()
        print(f"candidate pairs: {candidate_count}")
        print(f"visible pairs: {len(pair_infos)}")

        visible_face_pairs = None if len(pair_infos)== 0 else np.array(pair_infos[:, 0:2]).astype(int)
        print("face_i,face_j=", visible_face_pairs)

        self.mesh = mesh
        self.pair_infos = pair_infos
        self.broad_phase = broad_phase

        if cfg.show_polyscope and cfg.renderer is None:
            self.render(show=True)

        log_time("VisFacePair time=", t0)
        return visible_face_pairs

        # return pair_infos, candidate_count, broad_phase

    def render(self, renderer=None, show=False):
        renderer = self.config.renderer if renderer is None else renderer
        if renderer is None or self.mesh is None or self.pair_infos is None:
            return

        self.display_visible_triangle_pairs(
            self.mesh,
            self.pair_infos,
            broad_phase=self.broad_phase,
            renderer=renderer,
            show=show,
        )


if __name__ == "__main__":
    VisFacePair().run()
    
