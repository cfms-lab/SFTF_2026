from __future__ import annotations

import argparse
import time
from pathlib import Path

import polyscope

from python_src.tse6_config import (
    export_input_and_run_cpp,
    make_tse6_config,
    print_runtime_estimate,
    print_time,
)


def main() -> None:
    total_start = time.perf_counter()
    parser = argparse.ArgumentParser(
        description="Export current Python TSE6 data for the Visual Studio C++ v_ss benchmark."
    )
    parser.add_argument("--output", type=Path, default=Path("cpp_src/tse6_cpp_input.txt"))
    parser.add_argument("--exe", type=Path, default=Path("build/Release/tse6_vss.exe"))
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument(
        "--pipe",
        action="store_true",
        help="Pass input to tse6_vss.exe through stdin instead of writing a file.",
    )
    args = parser.parse_args()

    config = make_tse6_config(
        renderer=None,
        mesh_path="../Tomo_GPU2024_CODEX/Tomo_MeshData/(8)Bunny_1k.ply",
        angle_step=1.0,
        critical_angle=45.0,
        fbo_voxel_size=64,
        deduplicate_orientations=True,
    )
    print_runtime_estimate(config, pipeline="cpp")
    export_input_and_run_cpp(
        args.output,
        args.exe,
        config,
        renderer=polyscope,
        threads=args.threads,
        pipe=args.pipe,
    )
    print_time("TSE6_cpp.py total time", time.perf_counter() - total_start)


if __name__ == "__main__":
    main()
