import time

import polyscope

from python_src.SupportFlowTensorField import (
    MESH_PATHS,
    print_time,
    render_sftf_results,
    run_sftf_mesh,
    show_tomo_sftf_plotly_comparison,
)

USE_TOMO_GPU2026_FOR_COMPARISON = True


def main() -> None:
    total_start = time.perf_counter()
    results = [
        run_sftf_mesh(polyscope, mesh_path)
        for mesh_path in MESH_PATHS
    ]

    polyscope.init()
    polyscope.set_up_dir("z_up")
    render_sftf_results(polyscope, results)
    if USE_TOMO_GPU2026_FOR_COMPARISON:
        show_tomo_sftf_plotly_comparison(results)

    print_time("TSE6_SFTF.py total time before Polyscope window", time.perf_counter() - total_start)
    polyscope.show()


if __name__ == "__main__":
    main()
