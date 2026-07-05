import numpy as np
from pathlib import Path
from scipy.spatial import ConvexHull
from types import SimpleNamespace

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from python_src.tse6_config import COOLWARM_COLORSCALE, print_v_ss_extreme_orientations, summarize_v_ss_extremes

# find approximation of 3D printing support structure volume between two visible triangles

triA = np.array(
    [
        [0.0, 0.0, 3.0],
        [0.0, 1.0, 3.0],
        [1.0, 0.0, 3.0],
    ],
    dtype=np.float64,
)
triB = np.array(
    [
        [0.0, 0.0, 1.0],
        [1.0, 0.0, 1.0],
        [0.0, 1.0, 1.0],
    ],
    dtype=np.float64,
)

mcenter = np.array([0.0, 0.0, 2.0], dtype=np.float64)
filament_critical_angle = 60.0
angle_test = 5.0
plot_figure_width = 550
plot_figure_height = 260


def polygon_signed_area(points: np.ndarray) -> float:
    points = np.asarray(points, dtype=np.float64)
    if len(points) < 3:
        return 0.0
    x = points[:, 0]
    y = points[:, 1]
    return float(0.5 * np.sum(x * np.roll(y, -1) - y * np.roll(x, -1)))


def polygon_area(points: np.ndarray) -> float:
    return abs(polygon_signed_area(points))


def ensure_counter_clockwise(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    if polygon_signed_area(points) < 0.0:
        return points[::-1].copy()
    return points


def triangle_area(vertices: np.ndarray) -> float:
    edge0 = vertices[1] - vertices[0]
    edge1 = vertices[2] - vertices[0]
    return float(0.5 * np.linalg.norm(np.cross(edge0, edge1)))

def triangle_normal(vertices: np.ndarray) -> np.ndarray:
    edge0 = vertices[1] - vertices[0]
    edge1 = vertices[2] - vertices[0]
    normal = np.cross(edge0, edge1)
    return normal / np.linalg.norm(normal)


def rotation_matrix(yaw_deg: float, pitch_deg: float) -> np.ndarray:
    yaw = np.deg2rad(yaw_deg)
    pitch = np.deg2rad(pitch_deg)
    rot_x = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, np.cos(yaw), -np.sin(yaw)],
            [0.0, np.sin(yaw), np.cos(yaw)],
        ],
        dtype=np.float64,
    )
    rot_y = np.array(
        [
            [np.cos(pitch), 0.0, np.sin(pitch)],
            [0.0, 1.0, 0.0],
            [-np.sin(pitch), 0.0, np.cos(pitch)],
        ],
        dtype=np.float64,
    )
    return rot_y @ rot_x


def rotate_triangle(vertices: np.ndarray, center: np.ndarray, yaw_deg: float, pitch_deg: float) -> np.ndarray:
    rot = rotation_matrix(yaw_deg, pitch_deg)
    return (vertices - center) @ rot.T + center


def support_needs_support(support_angle_deg: float, critical_angle_deg: float) -> bool:
    return critical_angle_deg <= 0.0 or (critical_angle_deg < 90.0 and support_angle_deg >= critical_angle_deg)


def support_volume_from_tri_a_to_tri_b(
    tri_a: np.ndarray,
    tri_b: np.ndarray,
    center: np.ndarray,
    yaw_deg: float = 0.0,
    pitch_deg: float = 0.0,
    critical_angle_deg: float = 0.0,
) -> dict[str, float | np.ndarray]:
    rotated_a = rotate_triangle(tri_a, center, yaw_deg, pitch_deg)
    rotated_b = rotate_triangle(tri_b, center, yaw_deg, pitch_deg)

    vertical_axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    pair_vector = rotated_b.mean(axis=0) - rotated_a.mean(axis=0)
    depth = abs(float(np.dot(vertical_axis, pair_vector)))

    normal_a = triangle_normal(rotated_a)
    area_a = triangle_area(rotated_a)
    projected_area_a = area_a * abs(float(np.dot(vertical_axis, normal_a)))

    support_direction = -vertical_axis if float(np.dot(pair_vector, vertical_axis)) < 0.0 else vertical_axis
    support_angle = np.rad2deg(np.arccos(np.clip(abs(float(np.dot(normal_a, support_direction))), 0.0, 1.0)))
    tri_a_needs_support = support_needs_support(float(support_angle), critical_angle_deg)
    volume = depth * projected_area_a if tri_a_needs_support else 0.0
    return {
        "support_volume": volume,
        "non_support_volume": 0.0 if tri_a_needs_support else depth * projected_area_a,
        "raw_pair_volume": depth * projected_area_a,
        "depth": depth,
        "projected_area_a": projected_area_a,
        "support_angle": support_angle,
        "support_direction": support_direction,
        "normal_a": normal_a,
    }


def support_volume_prism_points(
    source_tri: np.ndarray,
    target_tri: np.ndarray,
    center: np.ndarray,
    yaw_deg: float,
    pitch_deg: float,
) -> np.ndarray:
    rotated_source = rotate_triangle(source_tri, center, yaw_deg, pitch_deg)
    rotated_target = rotate_triangle(target_tri, center, yaw_deg, pitch_deg)
    vertical_axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    pair_vector = rotated_target.mean(axis=0) - rotated_source.mean(axis=0)
    delta_z = float(np.dot(vertical_axis, pair_vector))
    top = rotated_source + delta_z * vertical_axis
    return np.vstack((rotated_source, top))


def convex_hull_halfspaces(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    if len(np.unique(np.round(points, decimals=12), axis=0)) < 4:
        return np.empty((0, 4), dtype=np.float64)
    try:
        return np.asarray(ConvexHull(points).equations, dtype=np.float64)
    except Exception:
        return np.empty((0, 4), dtype=np.float64)


def halfspace_intersection_volume(halfspaces: np.ndarray, tol: float = 1e-9) -> float:
    halfspaces = np.asarray(halfspaces, dtype=np.float64)
    if len(halfspaces) < 4:
        return 0.0

    coeffs = halfspaces[:, :3]
    offsets = halfspaces[:, 3]
    candidates = []
    count = len(halfspaces)
    for i in range(count - 2):
        for j in range(i + 1, count - 1):
            for k in range(j + 1, count):
                matrix = coeffs[[i, j, k]]
                if abs(float(np.linalg.det(matrix))) <= 1e-12:
                    continue
                try:
                    candidates.append(np.linalg.solve(matrix, -offsets[[i, j, k]]))
                except np.linalg.LinAlgError:
                    continue

    if not candidates:
        return 0.0
    candidate_points = np.asarray(candidates, dtype=np.float64)
    inside = np.all(candidate_points @ coeffs.T + offsets[None, :] <= tol, axis=1)
    if not np.any(inside):
        return 0.0
    points = np.unique(np.round(candidate_points[inside], decimals=10), axis=0)
    if len(points) < 4:
        return 0.0
    try:
        return float(ConvexHull(points).volume)
    except Exception:
        return 0.0


def support_intersection_volume(
    yaw_deg: float,
    pitch_deg: float,
    tri_a: np.ndarray = triA,
    tri_b: np.ndarray = triB,
    center: np.ndarray = mcenter,
    critical_angle_deg: float = filament_critical_angle,
) -> float:
    return support_intersection_volume_components(
        yaw_deg,
        pitch_deg,
        tri_a=tri_a,
        tri_b=tri_b,
        center=center,
        critical_angle_deg=critical_angle_deg,
    )["v_ss"]


def support_intersection_raw_volume(
    yaw_deg: float,
    pitch_deg: float,
    tri_a: np.ndarray = triA,
    tri_b: np.ndarray = triB,
    center: np.ndarray = mcenter,
) -> float:
    prism_ab = support_volume_prism_points(tri_a, tri_b, center, yaw_deg, pitch_deg)
    prism_ba = support_volume_prism_points(tri_b, tri_a, center, yaw_deg, pitch_deg)
    halfspaces_ab = convex_hull_halfspaces(prism_ab)
    halfspaces_ba = convex_hull_halfspaces(prism_ba)
    if len(halfspaces_ab) == 0 or len(halfspaces_ba) == 0:
        return 0.0
    return halfspace_intersection_volume(np.vstack((halfspaces_ab, halfspaces_ba)))


def support_pair_needs_support(
    source_tri: np.ndarray,
    target_tri: np.ndarray,
    center: np.ndarray,
    yaw_deg: float,
    pitch_deg: float,
    critical_angle_deg: float = filament_critical_angle,
) -> bool:
    rotated_source = rotate_triangle(source_tri, center, yaw_deg, pitch_deg)
    rotated_target = rotate_triangle(target_tri, center, yaw_deg, pitch_deg)
    vertical_axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    pair_vector = rotated_target.mean(axis=0) - rotated_source.mean(axis=0)
    support_direction = -vertical_axis if float(np.dot(vertical_axis, pair_vector)) < 0.0 else vertical_axis
    normal_source = triangle_normal(rotated_source)
    support_angle = np.rad2deg(np.arccos(np.clip(abs(float(np.dot(normal_source, support_direction))), 0.0, 1.0)))
    return support_needs_support(float(support_angle), critical_angle_deg)


def support_intersection_volume_components(
    yaw_deg: float,
    pitch_deg: float,
    tri_a: np.ndarray = triA,
    tri_b: np.ndarray = triB,
    center: np.ndarray = mcenter,
    critical_angle_deg: float = filament_critical_angle,
) -> dict[str, float]:
    volume = support_intersection_raw_volume(yaw_deg, pitch_deg, tri_a=tri_a, tri_b=tri_b, center=center)
    is_support_support = (
        volume > 1e-12
        and support_pair_needs_support(tri_a, tri_b, center, yaw_deg, pitch_deg, critical_angle_deg)
        and support_pair_needs_support(tri_b, tri_a, center, yaw_deg, pitch_deg, critical_angle_deg)
    )
    return {
        "v_ss": volume if is_support_support else 0.0,
        "v_nv": volume if volume > 1e-12 and not is_support_support else 0.0,
        "total": volume,
    }


def support_non_visible_intersection_volume(
    yaw_deg: float,
    pitch_deg: float,
    tri_a: np.ndarray = triA,
    tri_b: np.ndarray = triB,
    center: np.ndarray = mcenter,
    critical_angle_deg: float = filament_critical_angle,
) -> float:
    return support_intersection_volume_components(
        yaw_deg,
        pitch_deg,
        tri_a=tri_a,
        tri_b=tri_b,
        center=center,
        critical_angle_deg=critical_angle_deg,
    )["v_nv"]


def line_intersection_2d(
    p0: np.ndarray,
    p1: np.ndarray,
    q0: np.ndarray,
    q1: np.ndarray,
    tol: float = 1e-12,
) -> np.ndarray:
    r = p1 - p0
    s = q1 - q0
    denom = float(r[0] * s[1] - r[1] * s[0])
    if abs(denom) <= tol:
        return p1.copy()
    qp = q0 - p0
    t = float((qp[0] * s[1] - qp[1] * s[0]) / denom)
    return p0 + t * r


def clip_polygon_by_edge(
    subject: np.ndarray,
    edge_start: np.ndarray,
    edge_end: np.ndarray,
    tol: float = 1e-12,
) -> np.ndarray:
    if len(subject) == 0:
        return subject

    edge = edge_end - edge_start

    def inside(point: np.ndarray) -> bool:
        rel = point - edge_start
        return float(edge[0] * rel[1] - edge[1] * rel[0]) >= -tol

    output: list[np.ndarray] = []
    previous = subject[-1]
    previous_inside = inside(previous)
    for current in subject:
        current_inside = inside(current)
        if current_inside:
            if not previous_inside:
                output.append(line_intersection_2d(previous, current, edge_start, edge_end, tol=tol))
            output.append(current.copy())
        elif previous_inside:
            output.append(line_intersection_2d(previous, current, edge_start, edge_end, tol=tol))
        previous = current
        previous_inside = current_inside

    if not output:
        return np.empty((0, 2), dtype=np.float64)
    return np.asarray(output, dtype=np.float64)


def polygon_intersection_2d(subject: np.ndarray, clipper: np.ndarray) -> np.ndarray:
    output = ensure_counter_clockwise(subject)
    clipper_ccw = ensure_counter_clockwise(clipper)
    for edge_id in range(len(clipper_ccw)):
        output = clip_polygon_by_edge(
            output,
            clipper_ccw[edge_id],
            clipper_ccw[(edge_id + 1) % len(clipper_ccw)],
        )
        if len(output) < 3:
            return np.empty((0, 2), dtype=np.float64)
    return ensure_counter_clockwise(output)


def triangle_plane_z_function(vertices: np.ndarray):
    normal = np.cross(vertices[1] - vertices[0], vertices[2] - vertices[0])
    if abs(float(normal[2])) <= 1e-12:
        return None
    constant = float(np.dot(normal, vertices[0]))

    def z_at(point_xy: np.ndarray) -> float:
        x, y = point_xy
        return float((constant - normal[0] * x - normal[1] * y) / normal[2])

    return z_at


def support_prism_approx_info(
    source_tri: np.ndarray,
    target_tri: np.ndarray,
    center: np.ndarray,
    yaw_deg: float,
    pitch_deg: float,
    critical_angle_deg: float,
) -> dict[str, object] | None:
    rotated_source = rotate_triangle(source_tri, center, yaw_deg, pitch_deg)
    rotated_target = rotate_triangle(target_tri, center, yaw_deg, pitch_deg)
    vertical_axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    pair_vector = rotated_target.mean(axis=0) - rotated_source.mean(axis=0)
    delta_z = float(np.dot(vertical_axis, pair_vector))

    normal_source = triangle_normal(rotated_source)
    support_direction = -vertical_axis if delta_z < 0.0 else vertical_axis
    support_angle = np.rad2deg(np.arccos(np.clip(abs(float(np.dot(normal_source, support_direction))), 0.0, 1.0)))
    needs_support = support_needs_support(float(support_angle), critical_angle_deg)
    z_at = triangle_plane_z_function(rotated_source)
    xy = rotated_source[:, :2]
    if not needs_support or z_at is None or polygon_area(xy) <= 1e-12:
        return None
    return {"xy": xy, "z_at": z_at, "delta_z": delta_z}


def refine_triangle_2d(points: np.ndarray, order: int) -> list[np.ndarray]:
    if order <= 0:
        return [points]
    a, b, c = points
    ab = 0.5 * (a + b)
    bc = 0.5 * (b + c)
    ca = 0.5 * (c + a)
    children = [
        np.asarray([a, ab, ca], dtype=np.float64),
        np.asarray([ab, b, bc], dtype=np.float64),
        np.asarray([ca, bc, c], dtype=np.float64),
        np.asarray([ab, bc, ca], dtype=np.float64),
    ]
    refined: list[np.ndarray] = []
    for child in children:
        refined.extend(refine_triangle_2d(child, order - 1))
    return refined


def triangle_quadrature_points(points: np.ndarray) -> list[tuple[np.ndarray, float]]:
    barycentric_weights = np.array(
        [
            [2.0 / 3.0, 1.0 / 6.0, 1.0 / 6.0],
            [1.0 / 6.0, 2.0 / 3.0, 1.0 / 6.0],
            [1.0 / 6.0, 1.0 / 6.0, 2.0 / 3.0],
        ],
        dtype=np.float64,
    )
    weight = polygon_area(points) / 3.0
    return [(barycentric @ points, weight) for barycentric in barycentric_weights]


def approximate_support_intersection_volume(
    yaw_deg: float,
    pitch_deg: float,
    tri_a: np.ndarray = triA,
    tri_b: np.ndarray = triB,
    center: np.ndarray = mcenter,
    critical_angle_deg: float = 0.0,
    approximation_order: int = 0,
) -> float:
    info_ab = support_prism_approx_info(tri_a, tri_b, center, yaw_deg, pitch_deg, critical_angle_deg)
    info_ba = support_prism_approx_info(tri_b, tri_a, center, yaw_deg, pitch_deg, critical_angle_deg)
    if info_ab is None or info_ba is None:
        return 0.0

    intersection_xy = polygon_intersection_2d(info_ab["xy"], info_ba["xy"])
    if len(intersection_xy) < 3 or polygon_area(intersection_xy) <= 1e-12:
        return 0.0

    triangles = [
        np.asarray([intersection_xy[0], intersection_xy[i], intersection_xy[i + 1]], dtype=np.float64)
        for i in range(1, len(intersection_xy) - 1)
    ]
    sample_triangles: list[np.ndarray] = []
    for triangle in triangles:
        sample_triangles.extend(refine_triangle_2d(triangle, max(0, int(round(approximation_order)))))

    def overlap_height(point_xy: np.ndarray) -> float:
        z_a0 = info_ab["z_at"](point_xy)
        z_a1 = z_a0 + float(info_ab["delta_z"])
        z_b0 = info_ba["z_at"](point_xy)
        z_b1 = z_b0 + float(info_ba["delta_z"])
        lower = max(min(z_a0, z_a1), min(z_b0, z_b1))
        upper = min(max(z_a0, z_a1), max(z_b0, z_b1))
        return max(0.0, upper - lower)

    total = 0.0
    for triangle in sample_triangles:
        for point_xy, weight in triangle_quadrature_points(triangle):
            total += overlap_height(point_xy) * weight
    return float(total)


def compute_v_ss_grid(
    tri_a: np.ndarray,
    tri_b: np.ndarray,
    center: np.ndarray,
    angle_step: float,
    critical_angle_deg: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    interval_count = int(360.0 / angle_step) + 1
    angles_yaw = np.linspace(0.0, 360.0, num=interval_count, endpoint=True, dtype=np.float64)
    angles_pitch = np.linspace(0.0, 360.0, num=interval_count, endpoint=True, dtype=np.float64)
    v_ss = np.empty((len(angles_pitch), len(angles_yaw)), dtype=np.float64)

    for pitch_id, pitch in enumerate(angles_pitch):
        for yaw_id, yaw in enumerate(angles_yaw):
            v_ss[pitch_id, yaw_id] = support_intersection_volume(
                float(yaw),
                float(pitch),
                tri_a=tri_a,
                tri_b=tri_b,
                center=center,
                critical_angle_deg=critical_angle_deg,
            )

    return angles_yaw, angles_pitch, v_ss


def compute_approx_v_ss_grid(
    tri_a: np.ndarray,
    tri_b: np.ndarray,
    center: np.ndarray,
    angles_yaw: np.ndarray,
    angles_pitch: np.ndarray,
    critical_angle_deg: float = 0.0,
    approximation_order: int = 0,
) -> np.ndarray:
    v_ss = np.empty((len(angles_pitch), len(angles_yaw)), dtype=np.float64)
    for pitch_id, pitch in enumerate(angles_pitch):
        for yaw_id, yaw in enumerate(angles_yaw):
            v_ss[pitch_id, yaw_id] = approximate_support_intersection_volume(
                float(yaw),
                float(pitch),
                tri_a=tri_a,
                tri_b=tri_b,
                center=center,
                critical_angle_deg=critical_angle_deg,
                approximation_order=approximation_order,
            )
    return v_ss


def relative_error_grid(exact_grid: np.ndarray, approximate_grid: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    exact = np.asarray(exact_grid, dtype=np.float64)
    approximate = np.asarray(approximate_grid, dtype=np.float64)
    both_zero = (np.abs(exact) <= eps) & (np.abs(approximate) <= eps)
    rel = np.abs(approximate - exact) / np.maximum(np.abs(exact), eps)
    rel[both_zero] = 0.0
    return rel


def error_rate_report(exact_grid: np.ndarray, approximate_grid: np.ndarray) -> dict[str, float]:
    exact = np.asarray(exact_grid, dtype=np.float64)
    approximate = np.asarray(approximate_grid, dtype=np.float64)
    abs_error = np.abs(approximate - exact)
    rel_error = relative_error_grid(exact, approximate)
    nonzero_rel_error = rel_error[np.abs(exact) > 1e-12]
    return {
        "max_absolute_error": float(np.max(abs_error)),
        "mean_absolute_error": float(np.mean(abs_error)),
        "max_relative_error_percent": float(100.0 * np.max(rel_error)),
        "mean_relative_error_percent": float(100.0 * np.mean(rel_error)),
        "mean_relative_error_percent_nonzero_exact": float(
            0.0 if nonzero_rel_error.size == 0 else 100.0 * np.mean(nonzero_rel_error)
        ),
    }


def format_error_summary(error_stats: dict[str, float]) -> str:
    return (
        "approx error: "
        f"max abs={error_stats['max_absolute_error']:.5g}, "
        f"mean abs={error_stats['mean_absolute_error']:.5g}, "
        f"max rel={error_stats['max_relative_error_percent']:.3f}%, "
        f"mean rel={error_stats['mean_relative_error_percent']:.3f}%, "
        f"mean rel (nonzero exact)={error_stats['mean_relative_error_percent_nonzero_exact']:.3f}%"
    )


def make_tri_pair_v_ss_figure(
    angles_yaw: np.ndarray,
    angles_pitch: np.ndarray,
    v_ss: np.ndarray,
    approx_v_ss: np.ndarray,
    error_summary: str,
):
    cfg = SimpleNamespace(angles_yaw=angles_yaw, angles_pitch=angles_pitch)
    min_rows, max_rows = summarize_v_ss_extremes(cfg, v_ss, count=1)
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Original overlap support volume v_ss", "Approx overlap support volume v_ss"),
        horizontal_spacing=0.12,
    )
    for col, grid, title in (
        (1, v_ss, "original"),
        (2, approx_v_ss, "approx"),
    ):
        fig.add_trace(
            go.Contour(
                x=angles_yaw,
                y=angles_pitch,
                z=grid,
                colorscale=COOLWARM_COLORSCALE,
                contours=dict(showlabels=True),
                colorbar=dict(title="v_ss") if col == 2 else None,
                showscale=col == 2,
                hovertemplate=f"{title}<br>yaw=%{{x:.1f}}<br>pitch=%{{y:.1f}}<br>v_ss=%{{z:.6g}}<extra></extra>",
            ),
            row=1,
            col=col,
        )
    yaw_range = [float(np.min(angles_yaw)), float(np.max(angles_yaw))]
    pitch_range = [float(np.min(angles_pitch)), float(np.max(angles_pitch))]
    for col in (1, 2):
        x_anchor = "x" if col == 1 else "x2"
        fig.update_xaxes(title_text="Yaw angle (deg)", range=yaw_range, constrain="domain", row=1, col=col)
        fig.update_yaxes(
            title_text="Pitch angle (deg)",
            range=pitch_range,
            scaleanchor=x_anchor,
            scaleratio=1.0,
            constrain="domain",
            row=1,
            col=col,
        )
    fig.update_layout(width=plot_figure_width * 2, height=plot_figure_height)
    fig.update_layout(title=f"triA <-> triB<br><sup>{error_summary}</sup>")
    return fig, min_rows, max_rows


def register_triangle(name: str, vertices: np.ndarray, color: tuple[float, float, float]) -> None:
    import polyscope as ps

    faces = np.array([[0, 1, 2]], dtype=np.int32)
    ps.register_surface_mesh(
        name,
        vertices,
        faces,
        smooth_shade=False,
        color=color,
        transparency=0.65,
    )


def register_paired_face_normals(triangles: np.ndarray) -> None:
    import polyscope as ps

    centers = triangles.mean(axis=1)
    normals = np.asarray([triangle_normal(tri) for tri in triangles], dtype=np.float64)
    extents = triangles.reshape(-1, 3).max(axis=0) - triangles.reshape(-1, 3).min(axis=0)
    normal_vectors = normals * max(extents) * 0.06
    normal_cloud = ps.register_point_cloud(
        "paired face normals",
        centers,
        radius=0.009,
        enabled=True,
    )
    normal_cloud.add_vector_quantity(
        "normal",
        normal_vectors,
        enabled=True,
        color=(0.0, 0.85, 0.25),
    )


def main() -> None:
    import polyscope as ps

    angles_yaw, angles_pitch, v_ss = compute_v_ss_grid(
        triA,
        triB,
        mcenter,
        angle_step=angle_test,
        critical_angle_deg=filament_critical_angle,
    )
    approx_v_ss = compute_approx_v_ss_grid(
        triA,
        triB,
        mcenter,
        angles_yaw,
        angles_pitch,
        critical_angle_deg=0.0,
        approximation_order=0,
    )
    error_stats = error_rate_report(v_ss, approx_v_ss)
    error_summary = format_error_summary(error_stats)
    print(error_summary)

    fig, min_rows, max_rows = make_tri_pair_v_ss_figure(angles_yaw, angles_pitch, v_ss, approx_v_ss, error_summary)
    print("triA <-> triB overlap")
    print_v_ss_extreme_orientations(min_rows, max_rows)
    output_dir = Path("comparison_outputs") / "tri_pair_shadow_regression"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "tri_pair_v_ss_contour.html"
    fig.write_html(output_path)
    print(f"wrote {output_path.resolve()}")
    fig.show()

    volume_ab = support_volume_from_tri_a_to_tri_b(
        triA,
        triB,
        mcenter,
        yaw_deg=0.0,
        pitch_deg=0.0,
        critical_angle_deg=filament_critical_angle,
    )
    volume_ba = support_volume_from_tri_a_to_tri_b(
        triB,
        triA,
        mcenter,
        yaw_deg=0.0,
        pitch_deg=0.0,
        critical_angle_deg=filament_critical_angle,
    )
    print("yaw=0, pitch=0")
    print(f"depth triA -> triB: {volume_ab['depth']:.6f}")
    print(f"projected area triA: {volume_ab['projected_area_a']:.6f}")
    print(f"support angle triA: {volume_ab['support_angle']:.6f} deg")
    print(f"support volume triA -> triB: {volume_ab['support_volume']:.6f}")
    print(f"depth triB -> triA: {volume_ba['depth']:.6f}")
    print(f"projected area triB: {volume_ba['projected_area_a']:.6f}")
    print(f"support angle triB: {volume_ba['support_angle']:.6f} deg")
    print(f"support volume triB -> triA: {volume_ba['support_volume']:.6f}")
    print(f"overlap v_ss: {support_intersection_volume(0.0, 0.0):.6f}")

    ps.init()
    ps.set_up_dir("z_up")

    register_triangle("triA", triA, (0.95, 0.32, 0.22))
    register_triangle("triB", triB, (0.18, 0.44, 0.96))
    register_paired_face_normals(np.array([triA, triB], dtype=np.float64))

    ps.register_point_cloud(
        "mcenter",
        mcenter.reshape(1, 3),
        radius=0.04,
        color=(0.08, 0.08, 0.08),
    )

    ps.show()


if __name__ == "__main__":
    main()
