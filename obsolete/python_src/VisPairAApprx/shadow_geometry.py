import importlib.util
from pathlib import Path

import numpy as np
import trimesh


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERTICAL_AXIS = np.array([0.0, 0.0, 1.0], dtype=np.float64)


def load_tri_pair_shadow_functions():
    module_path = PROJECT_ROOT / "[function]tri_pair_shadow.py"
    spec = importlib.util.spec_from_file_location("tri_pair_shadow_functions", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"failed to load {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SHADOW = load_tri_pair_shadow_functions()


def mesh_rotation_center(mesh: trimesh.Trimesh) -> np.ndarray:
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    return vertices.mean(axis=0)


def contour_angle_grid(angle_step: float) -> tuple[np.ndarray, np.ndarray]:
    interval_count = int(360.0 / angle_step) + 1
    angles_yaw = np.linspace(0.0, 360.0, num=interval_count, endpoint=True, dtype=np.float64)
    angles_pitch = np.linspace(0.0, 360.0, num=interval_count, endpoint=True, dtype=np.float64)
    return angles_yaw, angles_pitch


def support_prism_mesh(
    source_tri: np.ndarray,
    target_tri: np.ndarray,
    center: np.ndarray,
    yaw_deg: float,
    pitch_deg: float,
) -> tuple[np.ndarray, np.ndarray]:
    rotated_source = SHADOW.rotate_triangle(source_tri, center, yaw_deg, pitch_deg)
    rotated_target = SHADOW.rotate_triangle(target_tri, center, yaw_deg, pitch_deg)
    pair_vector = rotated_target.mean(axis=0) - rotated_source.mean(axis=0)
    delta_z = float(np.dot(VERTICAL_AXIS, pair_vector))
    top = rotated_source + delta_z * VERTICAL_AXIS
    vertices = np.vstack((rotated_source, top))
    faces = np.array(
        [
            [0, 1, 2],
            [3, 5, 4],
            [0, 3, 4],
            [0, 4, 1],
            [1, 4, 5],
            [1, 5, 2],
            [2, 5, 3],
            [2, 3, 0],
        ],
        dtype=np.int32,
    )
    return vertices, faces


def append_mesh(
    all_vertices: list[np.ndarray],
    all_faces: list[np.ndarray],
    vertices: np.ndarray,
    faces: np.ndarray,
    offset: np.ndarray,
) -> None:
    base = sum(len(item) for item in all_vertices)
    all_vertices.append(np.asarray(vertices, dtype=np.float64) + offset)
    all_faces.append(np.asarray(faces, dtype=np.int32) + base)


def rotate_all_triangles(triangles: np.ndarray, center: np.ndarray, yaw_deg: float, pitch_deg: float) -> np.ndarray:
    rotation = SHADOW.rotation_matrix(yaw_deg, pitch_deg)
    return (triangles - center) @ rotation.T + center


def triangle_plane_z_coefficients(rotated_tri: np.ndarray) -> tuple[float, float, float] | None:
    normal = np.cross(rotated_tri[1] - rotated_tri[0], rotated_tri[2] - rotated_tri[0])
    if abs(float(normal[2])) <= 1e-12:
        return None
    constant = float(np.dot(normal, rotated_tri[0]))
    return (
        float(constant / normal[2]),
        float(-normal[0] / normal[2]),
        float(-normal[1] / normal[2]),
    )


def support_prism_info_from_rotated(
    rotated_source: np.ndarray,
    rotated_target: np.ndarray,
    critical_angle_deg: float,
) -> dict[str, object] | None:
    pair_vector = rotated_target.mean(axis=0) - rotated_source.mean(axis=0)
    delta_z = float(np.dot(VERTICAL_AXIS, pair_vector))
    normal_source = SHADOW.triangle_normal(rotated_source)
    support_direction = -VERTICAL_AXIS if delta_z < 0.0 else VERTICAL_AXIS
    support_angle = np.rad2deg(
        np.arccos(np.clip(abs(float(np.dot(normal_source, support_direction))), 0.0, 1.0))
    )
    needs_support = critical_angle_deg <= 0.0 or support_angle <= critical_angle_deg
    z_coeffs = triangle_plane_z_coefficients(rotated_source)
    xy = rotated_source[:, :2]
    if not needs_support or z_coeffs is None or SHADOW.polygon_area(xy) <= 1e-12:
        return None
    return {"xy": xy, "z_coeffs": z_coeffs, "delta_z": delta_z}


def z_from_coefficients(coeffs: tuple[float, float, float], point_xy: np.ndarray) -> float:
    c0, cx, cy = coeffs
    return c0 + cx * float(point_xy[0]) + cy * float(point_xy[1])


def approximate_volume_from_rotated_pair(
    rotated_a: np.ndarray,
    rotated_b: np.ndarray,
    critical_angle_deg: float,
    approximation_order: int,
) -> float:
    info_ab = support_prism_info_from_rotated(rotated_a, rotated_b, critical_angle_deg)
    info_ba = support_prism_info_from_rotated(rotated_b, rotated_a, critical_angle_deg)
    if info_ab is None or info_ba is None:
        return 0.0

    intersection_xy = SHADOW.polygon_intersection_2d(info_ab["xy"], info_ba["xy"])
    if len(intersection_xy) < 3 or SHADOW.polygon_area(intersection_xy) <= 1e-12:
        return 0.0

    triangles = [
        np.asarray([intersection_xy[0], intersection_xy[i], intersection_xy[i + 1]], dtype=np.float64)
        for i in range(1, len(intersection_xy) - 1)
    ]
    sample_triangles: list[np.ndarray] = []
    for triangle in triangles:
        sample_triangles.extend(SHADOW.refine_triangle_2d(triangle, max(0, int(round(approximation_order)))))

    def overlap_height(point_xy: np.ndarray) -> float:
        z_a0 = z_from_coefficients(info_ab["z_coeffs"], point_xy)
        z_a1 = z_a0 + float(info_ab["delta_z"])
        z_b0 = z_from_coefficients(info_ba["z_coeffs"], point_xy)
        z_b1 = z_b0 + float(info_ba["delta_z"])
        lower = max(min(z_a0, z_a1), min(z_b0, z_b1))
        upper = min(max(z_a0, z_a1), max(z_b0, z_b1))
        return max(0.0, upper - lower)

    total = 0.0
    for triangle in sample_triangles:
        for point_xy, weight in SHADOW.triangle_quadrature_points(triangle):
            total += overlap_height(point_xy) * weight
    return float(total)


def compute_visible_pair_vss_grid(
    mesh: trimesh.Trimesh,
    pair_infos: np.ndarray,
    center: np.ndarray,
    angles_yaw: np.ndarray,
    angles_pitch: np.ndarray,
    critical_angle_deg: float,
    approximation_order: int,
) -> tuple[np.ndarray, list[dict[str, float | int]]]:
    triangles = np.asarray(mesh.triangles, dtype=np.float64)
    pairs = np.asarray(pair_infos, dtype=np.float64)
    pair_faces = pairs[:, :2].astype(np.int64) if len(pairs) else np.empty((0, 2), dtype=np.int64)
    merged_vss = np.zeros((len(angles_pitch), len(angles_yaw)), dtype=np.float64)
    pair_max = np.zeros(len(pair_faces), dtype=np.float64)
    pair_sum = np.zeros(len(pair_faces), dtype=np.float64)

    if len(pair_faces) == 0:
        return merged_vss, []

    orientation_count = len(angles_pitch) * len(angles_yaw)
    orientation_id = 0
    for pitch_id, pitch in enumerate(angles_pitch):
        for yaw_id, yaw in enumerate(angles_yaw):
            rotated_triangles = rotate_all_triangles(triangles, center, float(yaw), float(pitch))
            total = 0.0
            for pair_id, (face_i, face_j) in enumerate(pair_faces):
                volume = approximate_volume_from_rotated_pair(
                    rotated_triangles[face_i],
                    rotated_triangles[face_j],
                    critical_angle_deg,
                    approximation_order,
                )
                total += volume
                pair_sum[pair_id] += volume
                if volume > pair_max[pair_id]:
                    pair_max[pair_id] = volume

            merged_vss[pitch_id, yaw_id] = total
            orientation_id += 1
            if orientation_id % 25 == 0 or orientation_id == orientation_count:
                print(f"merged v_ss orientations: {orientation_id}/{orientation_count}", flush=True)

    pair_grid_infos = [
        {
            "pair_id": pair_id,
            "face_i": int(face_i),
            "face_j": int(face_j),
            "max_volume": float(pair_max[pair_id]),
            "sum_volume": float(pair_sum[pair_id]),
        }
        for pair_id, (face_i, face_j) in enumerate(pair_faces)
    ]
    pair_grid_infos.sort(key=lambda item: float(item["max_volume"]), reverse=True)
    return merged_vss, pair_grid_infos


def representative_visible_pairs_from_coacd_hulls(
    mesh: trimesh.Trimesh,
    broad_phase: dict[str, object],
    line_dot: float = 0.15,
    include_same_hull: bool = False,
) -> np.ndarray:
    centers = np.asarray(mesh.triangles_center, dtype=np.float64)
    normals = np.asarray(mesh.face_normals, dtype=np.float64)
    hull_face_ids = broad_phase["hull_face_ids"]
    hull_visibility = np.asarray(broad_phase["hull_visibility"], dtype=bool)
    pairs: list[tuple[int, int, float, float, float]] = []

    hull_centers = []
    for face_ids in hull_face_ids:
        if len(face_ids) == 0:
            hull_centers.append(np.zeros(3, dtype=np.float64))
        else:
            hull_centers.append(centers[np.asarray(face_ids, dtype=np.int64)].mean(axis=0))
    hull_centers = np.asarray(hull_centers, dtype=np.float64)

    for hull_i, faces_i in enumerate(hull_face_ids):
        if len(faces_i) == 0:
            continue

        start_j = hull_i if include_same_hull else hull_i + 1
        for hull_j in range(start_j, len(hull_face_ids)):
            if not hull_visibility[hull_i, hull_j]:
                continue

            faces_j = hull_face_ids[hull_j]
            if len(faces_j) == 0:
                continue

            direction = hull_centers[hull_j] - hull_centers[hull_i]
            distance = float(np.linalg.norm(direction))
            if distance <= 1e-12:
                continue
            direction /= distance

            faces_i = np.asarray(faces_i, dtype=np.int64)
            faces_j = np.asarray(faces_j, dtype=np.int64)
            score_i = normals[faces_i] @ direction
            score_j = normals[faces_j] @ direction

            valid_i = np.flatnonzero(score_i >= line_dot)
            valid_j = np.flatnonzero(score_j <= -line_dot)
            face_i = int(faces_i[valid_i[np.argmax(score_i[valid_i])]]) if len(valid_i) else int(faces_i[np.argmax(score_i)])
            face_j = int(faces_j[valid_j[np.argmin(score_j[valid_j])]]) if len(valid_j) else int(faces_j[np.argmin(score_j)])

            if face_i == face_j:
                continue

            a = min(face_i, face_j)
            b = max(face_i, face_j)
            sorted_direction = centers[b] - centers[a]
            sorted_distance = float(np.linalg.norm(sorted_direction))
            if sorted_distance <= 1e-12:
                continue

            pairs.append(
                (
                    int(a),
                    int(b),
                    float(sorted_direction[0] / sorted_distance),
                    float(sorted_direction[1] / sorted_distance),
                    float(sorted_direction[2] / sorted_distance),
                )
            )

    if not pairs:
        return np.empty((0, 5), dtype=np.float64)

    pair_infos = np.asarray(pairs, dtype=np.float64)
    _, unique_ids = np.unique(pair_infos[:, :2].astype(np.int64), axis=0, return_index=True)
    return pair_infos[np.sort(unique_ids)]
