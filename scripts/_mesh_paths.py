from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _first_existing_path(candidates: tuple[Path, ...]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


SHARED_MESH_ROOT = _first_existing_path(
    (
        PROJECT_ROOT / "sftf_Mesh_Data",
        PROJECT_ROOT.parent / "sftf_Mesh_Data",
    )
)
MESH_DATA = SHARED_MESH_ROOT
G5_RAW_MESH = SHARED_MESH_ROOT / "g5test"
TOMO_ETC_MESH_DATA = PROJECT_ROOT / "Experimental" / "etc"
