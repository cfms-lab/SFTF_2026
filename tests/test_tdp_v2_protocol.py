from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments" / "tdp_v2" / "protocol.json"


def test_protocol_is_internally_consistent() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    selection = protocol["external_selection"]
    assert sum(item["holdout_quota"] for item in selection["strata"]) == selection[
        "holdout_total"
    ]
    assert sum(item["cross_slicer_quota"] for item in selection["strata"]) == selection[
        "cross_slicer_total"
    ]
    assert selection["cross_slicer_total"] <= selection["holdout_total"]
    assert protocol["state"] == "development_open_external_outcomes_sealed"
    assert "ratio-only" in " ".join(protocol["integrity_rules"])


def test_protocol_json_round_trip_is_stable() -> None:
    raw = PROTOCOL.read_bytes()
    value = json.loads(raw)
    assert value["protocol_id"] == "sftf-tdp-v2-2026-07-13"
    assert len(hashlib.sha256(raw).hexdigest()) == 64


def test_holdout_selector_help_smoke() -> None:
    script = ROOT / "scripts" / "select_tdp_v2_holdout.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "geometry-only" in completed.stdout
