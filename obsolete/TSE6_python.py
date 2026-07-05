import time

import numpy as np
import polyscope

from python_src.tse6_config import (
    compute_v_ss,
    make_grid_support_volume_figure,
    make_tse6_config,
    mesh_label,
    mesh_vertices_faces_at_origin,
    print_runtime_estimate,
    print_time,
    render_results_line,
)
from python_src.VisFacePair import VisFacePair


MESH_PATHS = [
    # "./Experimental/etc/box5cm_f16.stl",
    # "./Experimental/etc/sphere5cm_f169.stl",
    # "./Experimental/etc/FTree4x.stl",
    # "./Experimental/etc/(7)Bunny_1k.obj",
       "./Experimental/etc/(3)manikin.ply",
]


def run_mesh(mesh_path: str) -> dict[str, object]:
    cfg = make_tse6_config(
        renderer=polyscope,
        mesh_path=mesh_path,
        angle_step=5.0,
        critical_angle=60.0,
        fbo_voxel_size=128,
        deduplicate_orientations=True,
    )
    print(f"\n=== {mesh_path} ===", flush=True)
    print_runtime_estimate(cfg, pipeline="python")

    vis_face_pair = VisFacePair(cfg, max_candidate_pairs=None)
    vis_pairs = vis_face_pair.run()
    coacd_broad_phase = vis_face_pair.broad_phase
    if coacd_broad_phase is None and vis_face_pair.config.use_coacd_broad_phase:
        coacd_broad_phase = vis_face_pair.build_coacd_broad_phase(cfg.mesh)

    f_vtc, sh_tensor, v_tc, v_o, v_ss = compute_v_ss(cfg, vis_pairs)
    # Debug: skip orientation extrema summaries while investigating visible-pair generation.
    # min_v_ss_rows, max_v_ss_rows = summarize_v_ss_extremes(cfg, v_ss, count=1)
    min_v_ss_rows, max_v_ss_rows = [], []
    return {
        "mesh_path": mesh_path,
        "label": mesh_label(mesh_path),
        "cfg": cfg,
        "coacd_broad_phase": coacd_broad_phase,
        "vis_face_pair": vis_face_pair,
        "visible_pair_infos": vis_face_pair.pair_infos,
        "f_vtc": f_vtc,
        "sh_tensor": sh_tensor,
        "v_tc": v_tc,
        "v_o": v_o,
        "v_ss": v_ss,
        "min_rows": min_v_ss_rows,
        "max_rows": max_v_ss_rows,
    }


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


def main() -> None:
    total_start = time.perf_counter()
    results = [run_mesh(mesh_path) for mesh_path in MESH_PATHS]

    fig = make_grid_support_volume_figure(results)
    fig.show()

    polyscope.init()
    polyscope.set_up_dir("z_up")
    render_input_meshes(polyscope, results)
    # render_results_line() also renders result["coacd_broad_phase"] hull meshes.
    render_results_line(polyscope, results)

    print_time("TSE6_python.py total time before Polyscope window", time.perf_counter() - total_start)
    polyscope.show()


if __name__ == "__main__":
    main()
