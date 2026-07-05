import time

import polyscope

from python_src.tse6_config import (
    SHADER_ANGLE_STEP,
    SHADER_CRITICAL_ANGLE,
    SHADER_MESH_PATHS,
    SHADER_USE_TOMO_CPU_REFERENCES,
    TOMO_PROJECT_ROOT,
    attach_tomo_cpu_references,
    make_shader_volume_figure,
    print_time,
    render_input_meshes,
    render_shader_extreme_orientations,
    run_shader_mesh,
)


def main() -> None:
    total_start = time.perf_counter()
    results = [
        run_shader_mesh(
            polyscope,
            mesh_path,
            angle_step=SHADER_ANGLE_STEP,
            critical_angle=SHADER_CRITICAL_ANGLE,
        )
        for mesh_path in SHADER_MESH_PATHS
    ]

    if SHADER_USE_TOMO_CPU_REFERENCES:
        attach_tomo_cpu_references(
            results,
            tomo_project_root=TOMO_PROJECT_ROOT,
            critical_angle=SHADER_CRITICAL_ANGLE,
            angle_step=SHADER_ANGLE_STEP,
        )
    make_shader_volume_figure(results).show()

    polyscope.init()
    polyscope.set_up_dir("z_up")
    render_input_meshes(polyscope, results)
    render_shader_extreme_orientations(polyscope, results)
    print_time("TSE6_shader.py total time before Polyscope window", time.perf_counter() - total_start)
    polyscope.show()


if __name__ == "__main__":
    main()
