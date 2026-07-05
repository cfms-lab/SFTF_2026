import time
from pathlib import Path

import numpy as np
import polyscope

from python_src.tse6_config import (
    compute_v_ss,
    make_tse6_config,
    mesh_label,
    mesh_vertices_faces_at_origin,
    print_runtime_estimate,
    print_time,
)
from python_src.VisFacePair import VisFacePair
from python_src.VisFacePair.vis_face_pair import display_coacd_hulls
from python_src.VisPairAApprx import VisPairAApprx
from python_src.VisPairAApprx.plotting import make_tomo_vs_project_validation_contour_figure
from python_src.VisPairAApprx.shadow_geometry import (
    append_mesh,
    compute_visible_pair_vss_grid,
    contour_angle_grid,
    mesh_rotation_center,
    representative_visible_pairs_from_coacd_hulls,
    support_prism_mesh,
)
from python_src.VisPairAApprx.tomo_cpu import (
    compute_tomo_cpu_reference_grid,
)


PROJECT_ROOT = Path(__file__).resolve().parent
TOMO_PROJECT_ROOT = PROJECT_ROOT.parent / "Tomo_GPU2024_CODEX"
COMMON_MESH_PATH = TOMO_PROJECT_ROOT / "Tomo_MeshData" / "FTree4x.stl"
MESH_PATHS = [str(COMMON_MESH_PATH)]

FILAMENT_CRITICAL_ANGLE = 60.0
ANGLE_STEP = 45.0
YAW_DEG = 0.0
PITCH_DEG = 0.0
APPROXIMATION_ORDER = 0
MAX_RENDERED_SHADOW_PAIRS = 80
CONTOUR_OUTPUT_DIR = Path("comparison_outputs") / "tri_pair_shadow_regression"
MERGED_CONTOUR_PATH = CONTOUR_OUTPUT_DIR / "tri_pair_shadow_merged_v_ss_contour.html"
REGRESSION_CONTOUR_PATH = CONTOUR_OUTPUT_DIR / "tri_pair_shadow_regression_v_ss_v_nv_contour.html"
TOMO_REGRESSION_COMPARISON_PATH = CONTOUR_OUTPUT_DIR / "tomo_cpu_vs_tse6_validation_contour.html"


def print_grid_stats(label: str, grid: np.ndarray, suffix: str = "") -> None:
    print(
        f"{label}: shape={grid.shape}, min={np.min(grid):.6g}, "
        f"max={np.max(grid):.6g}, sum={np.sum(grid):.6g}{suffix}",
        flush=True,
    )


def coacd_hull_visible_pair_proxy(cfg) -> tuple[VisFacePair, np.ndarray]:
    vis_face_pair = VisFacePair(cfg, cache_visible_pairs=False)
    broad_phase = vis_face_pair.build_coacd_broad_phase(cfg.mesh)
    pair_infos = representative_visible_pairs_from_coacd_hulls(
        cfg.mesh,
        broad_phase,
        line_dot=vis_face_pair.config.normal_line_dot,
        include_same_hull=False,
    )
    vis_face_pair.mesh = cfg.mesh
    vis_face_pair.broad_phase = broad_phase
    vis_face_pair.pair_infos = pair_infos

    hull_visibility = np.asarray(broad_phase["hull_visibility"], dtype=bool)
    visible_hull_pairs = int(np.count_nonzero(np.triu(hull_visibility, k=1)))
    print(
        f"coacd hull proxy visible pairs: {len(pair_infos)} "
        f"from {visible_hull_pairs} visible hull pairs",
        flush=True,
    )
    return vis_face_pair, pair_infos[:, :2].astype(int)


def run_mesh_regression_only(
    mesh_path: str,
    vis_pair_aapprx: VisPairAApprx,
    angles_yaw: np.ndarray,
    angles_pitch: np.ndarray,
) -> dict[str, object]:
    cfg = make_tse6_config(
        renderer=polyscope,
        mesh_path=mesh_path,
        angle_step=ANGLE_STEP,
        critical_angle=FILAMENT_CRITICAL_ANGLE,
        fbo_voxel_size=256,
        deduplicate_orientations=True,
    )
    print(f"\n=== tri-pair regression ===\nmesh={mesh_path}", flush=True)
    print_runtime_estimate(cfg, pipeline="python")

    vis_face_pair, vis_pairs = coacd_hull_visible_pair_proxy(cfg)
    center = mesh_rotation_center(cfg.mesh)
    regression_grids = vis_pair_aapprx.compute_v_ss_v_nv_rg_grids(
        cfg.mesh,
        vis_face_pair.pair_infos,
        center,
        angles_yaw,
        angles_pitch,
    )
    v_ss_rg = regression_grids["v_ss"]
    v_nv_rg = regression_grids["v_nv"]
    _, v_tc_bt, v_o_bt, v_nv_bt, v_ss_bt = compute_v_ss(cfg, vis_pairs)
    tse6_v_ss = v_tc_bt - v_o_bt - v_nv_rg
    tse6_v_nv = v_nv_bt - v_ss_rg
    visible_pair_suffix = f", visible pairs={len(vis_face_pair.pair_infos)}"
    for label, grid, suffix in (
        ("v_tc", v_tc_bt, ""),
        ("v_ss_rg", v_ss_rg, visible_pair_suffix),
        ("v_nv_rg", v_nv_rg, visible_pair_suffix),
        ("v_ss_bt", v_ss_bt, ""),
        ("v_o_bt", v_o_bt, ""),
        ("v_nv_bt", v_nv_bt, ""),
        ("TSE6_v_ss", tse6_v_ss, ""),
        ("tse6_v_nv", tse6_v_nv, ""),
    ):
        print_grid_stats(f"{label} contour grid", grid, suffix)
    return {
        "mesh_path": mesh_path,
        "label": mesh_label(mesh_path),
        "cfg": cfg,
        "center": center,
        "angles_yaw": np.asarray(angles_yaw, dtype=np.float64),
        "angles_pitch": np.asarray(angles_pitch, dtype=np.float64),
        "v_tc": v_tc_bt,
        "v_ss_rg": v_ss_rg,
        "v_nv_rg": v_nv_rg,
        "v_ss_bt": v_ss_bt,
        "tse6_v_ss": tse6_v_ss,
        "tse6_v_nv": tse6_v_nv,
        "v_o_bt": v_o_bt,
        "v_nv_bt": v_nv_bt,
        "coacd_broad_phase": vis_face_pair.broad_phase,
        "vis_face_pair": vis_face_pair,
        "visible_pair_infos": vis_face_pair.pair_infos,
    }

def run_mesh(mesh_path: str, vis_pair_aapprx: VisPairAApprx | None = None) -> dict[str, object]:
    cfg = make_tse6_config(
        renderer=polyscope,
        mesh_path=mesh_path,
        angle_step=ANGLE_STEP,
        critical_angle=FILAMENT_CRITICAL_ANGLE,
        fbo_voxel_size=256,
        deduplicate_orientations=True,
    )
    print(f"\n=== {mesh_path} ===", flush=True)
    print_runtime_estimate(cfg, pipeline="python")

    vis_face_pair, _vis_pairs = coacd_hull_visible_pair_proxy(cfg)
    center = mesh_rotation_center(cfg.mesh)
    angles_yaw, angles_pitch = contour_angle_grid(ANGLE_STEP)
    merged_vss, pair_grid_infos = compute_visible_pair_vss_grid(
        cfg.mesh,
        vis_face_pair.pair_infos,
        center,
        angles_yaw,
        angles_pitch,
        FILAMENT_CRITICAL_ANGLE,
        APPROXIMATION_ORDER,
    )
    v_ss_rg = None
    v_nv_rg = None
    if vis_pair_aapprx is not None:
        regression_grids = vis_pair_aapprx.compute_v_ss_v_nv_rg_grids(
            cfg.mesh,
            vis_face_pair.pair_infos,
            center,
            angles_yaw,
            angles_pitch,
        )
        v_ss_rg = regression_grids["v_ss"]
        v_nv_rg = regression_grids["v_nv"]
    positive_count = sum(1 for item in pair_grid_infos if float(item["max_volume"]) > 0.0)

    print(f"pair shadow grids: {positive_count}/{len(pair_grid_infos)} positive")
    for rank, item in enumerate(pair_grid_infos[:5], start=1):
        print(
            f"{rank}. pair={int(item['pair_id'])}, "
            f"faces=({int(item['face_i'])}, {int(item['face_j'])}), "
            f"max v_ss~={float(item['max_volume']):.6g}, "
            f"grid sum~={float(item['sum_volume']):.6g}"
        )
    print(
        f"merged contour grid: shape={merged_vss.shape}, "
        f"min={np.min(merged_vss):.6g}, max={np.max(merged_vss):.6g}, sum={np.sum(merged_vss):.6g}",
        flush=True,
    )
    return {
        "mesh_path": mesh_path,
        "label": mesh_label(mesh_path),
        "cfg": cfg,
        "center": center,
        "angles_yaw": angles_yaw,
        "angles_pitch": angles_pitch,
        "merged_vss": merged_vss,
        "v_ss_rg": v_ss_rg,
        "v_nv_rg": v_nv_rg,
        "pair_grid_infos": pair_grid_infos,
        "coacd_broad_phase": vis_face_pair.broad_phase,
        "vis_face_pair": vis_face_pair,
        "visible_pair_infos": vis_face_pair.pair_infos,
    }

def render_shadow_prisms(renderer, result: dict[str, object], offset: np.ndarray) -> None:
    mesh = result["cfg"].mesh
    triangles = np.asarray(mesh.triangles, dtype=np.float64)
    center = np.asarray(result["center"], dtype=np.float64)
    selected = [
        item
        for item in result["pair_grid_infos"]
        if float(item["max_volume"]) > 0.0
    ][:MAX_RENDERED_SHADOW_PAIRS]

    if not selected:
        return

    ab_vertices: list[np.ndarray] = []
    ab_faces: list[np.ndarray] = []
    ba_vertices: list[np.ndarray] = []
    ba_faces: list[np.ndarray] = []

    for item in selected:
        face_i = int(item["face_i"])
        face_j = int(item["face_j"])
        vertices, faces = support_prism_mesh(
            triangles[face_i],
            triangles[face_j],
            center,
            YAW_DEG,
            PITCH_DEG,
        )
        append_mesh(ab_vertices, ab_faces, vertices, faces, offset)

        vertices, faces = support_prism_mesh(
            triangles[face_j],
            triangles[face_i],
            center,
            YAW_DEG,
            PITCH_DEG,
        )
        append_mesh(ba_vertices, ba_faces, vertices, faces, offset)

    label = str(result["label"])
    ab_mesh = renderer.register_surface_mesh(
        f"{label} support prisms A->B",
        np.vstack(ab_vertices),
        np.vstack(ab_faces),
        smooth_shade=False,
        color=(0.14, 0.66, 0.28),
        transparency=0.30,
    )
    ba_mesh = renderer.register_surface_mesh(
        f"{label} support prisms B->A",
        np.vstack(ba_vertices),
        np.vstack(ba_faces),
        smooth_shade=False,
        color=(0.54, 0.20, 0.72),
        transparency=0.30,
    )

    group = renderer.create_group(f"{label} tri-pair shadow")
    ab_mesh.add_to_group(group)
    ba_mesh.add_to_group(group)

    centers = np.asarray(mesh.triangles_center, dtype=np.float64) + offset
    pair_nodes = np.empty((len(selected) * 2, 3), dtype=np.float64)
    pair_nodes[0::2] = centers[[int(item["face_i"]) for item in selected]]
    pair_nodes[1::2] = centers[[int(item["face_j"]) for item in selected]]
    pair_edges = np.column_stack(
        (
            np.arange(0, len(selected) * 2, 2, dtype=np.int32),
            np.arange(1, len(selected) * 2, 2, dtype=np.int32),
        )
    )
    connectors = renderer.register_curve_network(
        f"{label} positive shadow pair connectors",
        pair_nodes,
        pair_edges,
        radius=0.0022,
        color=(1.0, 0.82, 0.10),
    )
    connectors.add_scalar_quantity(
        "approx v_ss",
        np.asarray([float(item["max_volume"]) for item in selected], dtype=np.float64),
        defined_on="edges",
        enabled=True,
    )
    connectors.add_to_group(group)


def render_shadow_results(renderer, results: list[dict[str, object]]) -> None:
    extents = []
    for result in results:
        vertices, _faces = mesh_vertices_faces_at_origin(result["cfg"].mesh)
        extents.append(vertices.max(axis=0) - vertices.min(axis=0))

    max_extent = max(float(extent.max()) for extent in extents)
    row_step = 1.35 * max(max_extent, 1e-6)

    for result_id, result in enumerate(results):
        cell_origin = np.array([0.0, -result_id * row_step, 0.0], dtype=np.float64)
        mesh = result["cfg"].mesh
        mesh_min = np.asarray(mesh.vertices, dtype=np.float64).min(axis=0)
        display_offset = cell_origin - mesh_min
        label = str(result["label"])

        renderer.register_surface_mesh(
            f"{label} original mesh",
            np.asarray(mesh.vertices, dtype=np.float64) + display_offset,
            np.asarray(mesh.faces, dtype=np.int32),
            smooth_shade=False,
            color=(0.72, 0.74, 0.78),
            transparency=0.45,
        )
        display_coacd_hulls(
            result.get("coacd_broad_phase"),
            enabled=True,
            renderer=renderer,
            offset=display_offset,
            name_prefix=label,
            show_centers=False,
        )
        result["vis_face_pair"].display_visible_triangle_pairs(
            mesh,
            result["visible_pair_infos"],
            broad_phase=result.get("coacd_broad_phase"),
            renderer=renderer,
            show=False,
            offset=display_offset,
            name_prefix=label,
            show_mesh=False,
            show_hulls=False,
        )
        render_shadow_prisms(renderer, result, display_offset)


def main() -> None:
    total_start = time.perf_counter()
    mesh_path = str(COMMON_MESH_PATH)
    vis_pair_aapprx = VisPairAApprx()
    tomo_reference = compute_tomo_cpu_reference_grid(
        mesh_path,
        TOMO_PROJECT_ROOT,
        FILAMENT_CRITICAL_ANGLE,
        ANGLE_STEP,
    )
    regression_result = run_mesh_regression_only(
        mesh_path,
        vis_pair_aapprx,
        np.asarray(tomo_reference["yaw_values"], dtype=np.float64),
        np.asarray(tomo_reference["pitch_values"], dtype=np.float64),
    )

    fig = make_tomo_vs_project_validation_contour_figure(
        str(regression_result["label"]),
        np.asarray(tomo_reference["yaw_values"], dtype=np.float64),
        np.asarray(tomo_reference["pitch_values"], dtype=np.float64),
        np.asarray(tomo_reference["vtc_grid"], dtype=np.float64),
        np.asarray(tomo_reference["vnv_grid"], dtype=np.float64),
        np.asarray(tomo_reference["vss_grid"], dtype=np.float64),
        np.asarray(regression_result["v_tc"], dtype=np.float64),
        np.asarray(regression_result["v_nv_bt"], dtype=np.float64),
        np.asarray(regression_result["v_nv_rg"], dtype=np.float64),
        np.asarray(regression_result["tse6_v_nv"], dtype=np.float64),
        len(regression_result["visible_pair_infos"]),
        FILAMENT_CRITICAL_ANGLE,
        ANGLE_STEP,
    )
    CONTOUR_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.write_html(TOMO_REGRESSION_COMPARISON_PATH)
    print(f"wrote {TOMO_REGRESSION_COMPARISON_PATH.resolve()}")
    fig.show()

    print_time("[implement]tri_pair_shadow.py total time", time.perf_counter() - total_start)


if __name__ == "__main__":
    main()
