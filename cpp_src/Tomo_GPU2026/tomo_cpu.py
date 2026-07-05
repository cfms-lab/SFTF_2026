from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from . import tomo_shell_cpp, tomo_shell_io


PACKAGE_ROOT = Path(__file__).resolve().parent
ANGLE_STEP = float(os.environ.get("TOMO_ANGLE_STEP", "1.0"))
# Critical (overhang) angle in degrees. Overridable per-process via the
# TOMO_CRITICAL_ANGLE env var so a batch driver can sweep several angles by
# launching one subprocess per angle (the constant is read at import time).
CRITICAL_ANGLE = float(os.environ.get("TOMO_CRITICAL_ANGLE", "90.0"))


def load_tomo_modules():
    return tomo_shell_cpp, tomo_shell_io


def tomo_cpu_printer_settings() -> dict[str, float | bool]:
    return {
        "wall_thickness": 0.8,
        "PLA_density": 0.00121,
        "Fclad": 1.0,
        "Fcore": 0.15,
        "Fss": 0.2,
        "Css": 1.0,
        "dVoxel": 1.0,
        "nVoxel": 256,
        "bUseExplicitSS": False,
    }


def configure_tomo_cpu_printer(tomo, critical_angle: float = CRITICAL_ANGLE) -> None:
    settings = tomo_cpu_printer_settings()
    tomo.wall_thickness = settings["wall_thickness"]
    tomo.PLA_density = settings["PLA_density"]
    tomo.Fclad = settings["Fclad"]
    tomo.Fcore = settings["Fcore"]
    tomo.Fss = settings["Fss"]
    tomo.Css = settings["Css"]
    tomo.dVoxel = settings["dVoxel"]
    tomo.nVoxel = settings["nVoxel"]
    tomo.theta_c = tomo_shell_io.toRadian(critical_angle)
    tomo.bUseExplicitSS = settings["bUseExplicitSS"]
    tomo.BedType = (tomo_shell_io.enumBedType.ebtRaft, 0, 2, 0.3 + 0.27 + 2 * 0.2)


def tomo_mss_to_support_volume(
    mss: np.ndarray,
    settings: dict[str, float | bool] | None = None,
) -> np.ndarray:
    settings = tomo_cpu_printer_settings() if settings is None else settings
    mss = np.asarray(mss, dtype=np.float64)
    density = float(settings["PLA_density"])
    divisor = float(settings["Fss"]) * float(settings["Css"]) * density
    return np.divide(mss, divisor, out=np.zeros_like(mss), where=abs(divisor) > 1e-12)


def _compute_vss_grid(
    mesh_path: Path,
    cpp_function_name: str,
    *,
    critical_angle: float = CRITICAL_ANGLE,
    angle_step: float = ANGLE_STEP,
) -> dict[str, object]:
    """Run a full yaw/pitch sweep with the given DLL entry point and return the
    v_ss grid dict. ``cpp_function_name`` selects the compute backend
    (``"TomoSh_INT3"`` CPU or ``"TomoSh_CUDA"`` GPU); both share the same printer
    settings and 256^3 voxel grid, so only the backend differs."""
    mesh_path = Path(mesh_path).resolve()
    previous_cwd = Path.cwd()
    try:
        os.chdir(PACKAGE_ROOT)
        tomo = tomo_shell_cpp.TomoShellCpp((str(mesh_path), 0, 0, 0), angle_step, bVerbose=False)
        configure_tomo_cpu_printer(tomo, critical_angle)
        tomo.Run(cpp_function_name=cpp_function_name)
    finally:
        os.chdir(previous_cwd)

    grid_shape = (int(tomo.nYPR_Intervals), int(tomo.nYPR_Intervals))
    # 메시가 복셀 격자보다 커서 축소된 경우, 지지체적을 원본 단위로 환산한다
    # (부피는 scale^3로 작아지므로 1/scale^3을 곱한다; 최적 배향은 스케일 불변).
    mesh_scale = float(getattr(tomo, "mesh_scale", 1.0))
    volume_factor = 1.0 / (mesh_scale ** 3)
    vss_grid = tomo_mss_to_support_volume(np.asarray(tomo.Mss3D, dtype=np.float64)).reshape(grid_shape)
    return {
        "yaw_values": np.asarray(tomo_shell_io.toDegree(tomo.yaw_range), dtype=np.float64),
        "pitch_values": np.asarray(tomo_shell_io.toDegree(tomo.pitch_range), dtype=np.float64),
        "vss_grid": vss_grid * volume_factor,
        "mesh_scale": mesh_scale,
        "tomo_io": tomo_shell_io,
    }


def compute_tomo_cpu_vss_grid(
    mesh_path: Path,
    *,
    critical_angle: float = CRITICAL_ANGLE,
    angle_step: float = ANGLE_STEP,
) -> dict[str, object]:
    """TOMO_CPU (CPU) yaw/pitch v_ss grid sweep."""
    return _compute_vss_grid(
        mesh_path, "TomoSh_INT3", critical_angle=critical_angle, angle_step=angle_step
    )


def compute_tomo_cuda_vss_grid(
    mesh_path: Path,
    *,
    critical_angle: float = CRITICAL_ANGLE,
    angle_step: float = ANGLE_STEP,
) -> dict[str, object]:
    """TOMO_CUDA (GPU) yaw/pitch v_ss grid sweep (same settings as TOMO_CPU)."""
    return _compute_vss_grid(
        mesh_path, "TomoSh_CUDA", critical_angle=critical_angle, angle_step=angle_step
    )


def compute_tomo_cpu_batch_mss(mesh_path: Path, rows: list[dict[str, float]]) -> list[tuple[float, float]]:
    if not rows:
        return []

    mesh_path = Path(mesh_path).resolve()
    previous_cwd = Path.cwd()
    try:
        os.chdir(PACKAGE_ROOT)
        tomo = tomo_shell_cpp.TomoShellCpp((str(mesh_path), 0.0, 0.0, 0.0), 0, bVerbose=False)
        tomo.YPR = np.asarray(
            [
                [
                    float(tomo_shell_io.toRadian(row["yaw"])),
                    float(tomo_shell_io.toRadian(row["pitch"])),
                    0.0,
                ]
                for row in rows
            ],
            dtype=np.float32,
        )
        tomo.YPR_unique, tomo.ypr_inverse = tomo._unique_ypr(tomo.YPR)
        configure_tomo_cpu_printer(tomo)
        tomo.Run(cpp_function_name="TomoSh_INT3")
    finally:
        os.chdir(previous_cwd)

    # 축소된 메시는 결과 질량/부피가 scale^3로 작아지므로 원본 단위로 환산한다.
    mesh_scale = float(getattr(tomo, "mesh_scale", 1.0))
    volume_factor = 1.0 / (mesh_scale ** 3)
    mss_values = np.asarray(tomo.Mss3D, dtype=np.float64).reshape(-1) * volume_factor
    vss_values = tomo_mss_to_support_volume(mss_values)
    return [(float(mss), float(vss)) for mss, vss in zip(mss_values, vss_values)]


def tomo_rotation_matrix(yaw_deg: float, pitch_deg: float) -> np.ndarray:
    return np.asarray(
        tomo_shell_io.getRotationMatrix(
            float(tomo_shell_io.toRadian(yaw_deg)),
            float(tomo_shell_io.toRadian(pitch_deg)),
            0.0,
        )[:3, :3],
        dtype=np.float64,
    )


def grid_value_at(yaw: float, pitch: float, yaw_values: np.ndarray, pitch_values: np.ndarray, grid: np.ndarray) -> float:
    yaw_id = int(np.argmin(np.abs(yaw_values - yaw)))
    pitch_id = int(np.argmin(np.abs(pitch_values - pitch)))
    return float(grid[pitch_id, yaw_id])


def tomo_best_row(yaw_values: np.ndarray, pitch_values: np.ndarray, vss_grid: np.ndarray) -> dict[str, float]:
    flat_id = int(np.nanargmin(vss_grid.reshape(-1)))
    pitch_id, yaw_id = np.unravel_index(flat_id, vss_grid.shape)
    return {
        "yaw": float(yaw_values[yaw_id]),
        "pitch": float(pitch_values[pitch_id]),
        "vss": float(vss_grid[pitch_id, yaw_id]),
    }
