from __future__ import annotations

import numpy as np

from scripts import experiment_deployed_pipeline_runtime_g5 as runtime


def test_uniform_seed_specs_stop_at_severe_ave_limit() -> None:
    directions = runtime._spherical_sample_directions(512)
    yaw = np.arange(360, dtype=np.float64)
    pitch = np.arange(360, dtype=np.float64)

    specs, _elapsed = runtime._seed_specs(
        "uniform",
        [],
        directions,
        list(range(len(directions))),
        yaw,
        pitch,
    )

    assert len(specs) == runtime.DEFAULT_SEVERE_ESCALATE_TOP_K == 200
    assert 2 * len(specs) == 400


def test_full_scope_status_requires_exact_population_and_no_stale_meshes() -> None:
    fingerprint = "test-fingerprint"
    records = [
        {
            "mesh": f"mesh-{index}",
            "ratio_valid": index < runtime.EXPECTED_RATIO_VALID_COUNT,
            "fresh_candidates_used": True,
            "physical_tomo_executed": True,
            "selection_fingerprint": fingerprint,
        }
        for index in range(runtime.EXPECTED_RECORD_COUNT)
    ]
    skipped: list[dict[str, str]] = []
    config = {
        "full_scope": True,
        "fresh_candidates": True,
        "physical_tomo": True,
        "selection_fingerprint": fingerprint,
    }

    assert runtime._run_status(records, skipped, config) == "complete"
    assert runtime._run_status(records[:-1], skipped, config) == "partial"
    assert runtime._run_status(
        records, [{"mesh": "unexpected", "reason": "missing_mesh_file"}], config
    ) == "partial"


def test_resume_rejects_row_before_timing_rewrite() -> None:
    base = {
        "checkpoint_output_io_wall_s": 0.1,
        "end_to_end_wall_s_including_checkpoint_io": 1.0,
        "cache_replay_selection_component_sum_including_checkpoint_io_s": 0.2,
        "physical_selection_direct_wall_s": 0.8,
        "physical_selection_plus_primary_checkpoint_wall_s": 0.9,
    }
    assert runtime._row_has_checkpoint_fields(base, physical_tomo=True)

    interrupted = dict(base)
    interrupted.pop("physical_selection_plus_primary_checkpoint_wall_s")
    assert not runtime._row_has_checkpoint_fields(interrupted, physical_tomo=True)
