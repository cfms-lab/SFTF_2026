import importlib.util
import os
import sys
import types
from pathlib import Path

import numpy as np

from python_src.tse6_config import mesh_label


def load_tomo_gpu2024_modules(tomo_project_root: Path):
    package_name = "tomo_gpu2024_python_src"
    source_dir = tomo_project_root / "python_src"
    if not source_dir.is_dir():
        raise FileNotFoundError(f"TOMO python_src not found: {source_dir}")

    if package_name not in sys.modules:
        package = types.ModuleType(package_name)
        package.__path__ = [str(source_dir)]
        sys.modules[package_name] = package

    def load_module(module_name: str):
        qualified_name = f"{package_name}.{module_name}"
        if qualified_name in sys.modules:
            return sys.modules[qualified_name]
        module_path = source_dir / f"{module_name}.py"
        spec = importlib.util.spec_from_file_location(qualified_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"failed to load {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[qualified_name] = module
        spec.loader.exec_module(module)
        return module

    tomo_io = load_module("tomoNV_io")
    tomo_cpp = load_module("tomoNV_Cpp")
    return tomo_cpp, tomo_io


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


def configure_tomo_cpu_printer(tomo, tomo_io, critical_angle: float) -> None:
    settings = tomo_cpu_printer_settings()
    tomo.wall_thickness = settings["wall_thickness"]
    tomo.PLA_density = settings["PLA_density"]
    tomo.Fclad = settings["Fclad"]
    tomo.Fcore = settings["Fcore"]
    tomo.Fss = settings["Fss"]
    tomo.Css = settings["Css"]
    tomo.dVoxel = settings["dVoxel"]
    tomo.nVoxel = settings["nVoxel"]
    tomo.theta_c = tomo_io.toRadian(critical_angle)
    tomo.bUseExplicitSS = settings["bUseExplicitSS"]
    tomo.BedType = (tomo_io.enumBedType.ebtRaft, 0, 2, 0.3 + 0.27 + 2 * 0.2)


def support_volume_to_tomo_mss(v_ss: np.ndarray, settings: dict[str, float | bool]) -> np.ndarray:
    v_ss = np.asarray(v_ss, dtype=np.float64)
    if bool(settings["bUseExplicitSS"]):
        positive = v_ss > 1e-6
        mss = np.zeros_like(v_ss, dtype=np.float64)
        radius = np.zeros_like(v_ss, dtype=np.float64)
        radius[positive] = np.power(v_ss[positive] / ((4.0 / 3.4) * np.pi), 1.0 / 3.0)
        ass_clad = 4.0 * np.pi * radius * radius
        vss_clad = ass_clad * float(settings["wall_thickness"])
        vss_core = v_ss - vss_clad
        mss[positive] = (
            vss_clad[positive] * float(settings["Fclad"]) * float(settings["PLA_density"])
            + vss_core[positive] * float(settings["Fcore"]) * float(settings["PLA_density"])
        )
        return mss

    return (
        v_ss
        * float(settings["Fss"])
        * float(settings["Css"])
        * float(settings["PLA_density"])
    )


def tomo_mss_to_support_volume(mss: np.ndarray, settings: dict[str, float | bool]) -> np.ndarray:
    mss = np.asarray(mss, dtype=np.float64)
    density = float(settings["PLA_density"])
    if not bool(settings["bUseExplicitSS"]):
        divisor = float(settings["Fss"]) * float(settings["Css"]) * density
        return np.divide(mss, divisor, out=np.zeros_like(mss), where=abs(divisor) > 1e-12)

    positive = mss > 1e-12
    volume = np.zeros_like(mss, dtype=np.float64)
    if not np.any(positive):
        return volume

    target = mss[positive]
    lo = np.zeros_like(target, dtype=np.float64)
    hi = np.maximum(target / max(float(settings["Fcore"]) * density, 1e-12), 1.0)

    for _ in range(80):
        mid = 0.5 * (lo + hi)
        mid_mss = support_volume_to_tomo_mss(mid, settings)
        hi = np.where(mid_mss >= target, mid, hi)
        lo = np.where(mid_mss < target, mid, lo)

    volume[positive] = 0.5 * (lo + hi)
    return volume


def tomo_mo_to_object_volume(mo: np.ndarray, surface_area: float, settings: dict[str, float | bool]) -> np.ndarray:
    mo = np.asarray(mo, dtype=np.float64)
    density = float(settings["PLA_density"])
    f_core = float(settings["Fcore"])
    f_clad = float(settings["Fclad"])
    v_o_clad = float(surface_area) * float(settings["wall_thickness"])
    divisor = f_core * density
    numerator = mo - (v_o_clad * (f_clad - f_core) * density)
    return np.divide(numerator, divisor, out=np.zeros_like(mo), where=abs(divisor) > 1e-12)


def compute_tomo_cpu_reference_grid(
    mesh_path: str,
    tomo_project_root: Path,
    critical_angle: float,
    angle_step: float,
) -> dict[str, object]:
    tomo_cpp, tomo_io = load_tomo_gpu2024_modules(tomo_project_root)
    mesh_path_obj = Path(mesh_path).resolve()
    if not mesh_path_obj.is_file():
        raise FileNotFoundError(f"mesh not found: {mesh_path_obj}")

    print(
        f"\n=== TOMO_CPU reference ===\n"
        f"mesh={mesh_path_obj}\ncritical_angle={critical_angle:g}, angle_step={angle_step:g}",
        flush=True,
    )

    previous_cwd = Path.cwd()
    try:
        os.chdir(tomo_project_root)
        tomo = tomo_cpp.tomoNV_Cpp((str(mesh_path_obj), 0, 0, 0), angle_step, bVerbose=False)
        configure_tomo_cpu_printer(tomo, tomo_io, critical_angle)
        tomo.Run(cpp_function_name="TomoNV_INT3")
    finally:
        os.chdir(previous_cwd)

    grid_shape = (int(tomo.nYPR_Intervals), int(tomo.nYPR_Intervals))
    settings = tomo_cpu_printer_settings()
    mo_grid = np.asarray(tomo.Mo3D, dtype=np.float64).reshape(grid_shape)
    mss_grid = np.asarray(tomo.Mss3D, dtype=np.float64).reshape(grid_shape)
    vtc_grid = np.asarray(tomo.Vtc, dtype=np.float64).reshape(grid_shape)
    vo_grid = tomo_mo_to_object_volume(mo_grid, tomo.mesh0.get_surface_area(), settings)
    vss_grid = tomo_mss_to_support_volume(mss_grid, settings)
    vnv_grid = vtc_grid - vo_grid - vss_grid
    return {
        "label": f"TOMO_CPU {mesh_label(str(mesh_path_obj))}",
        "yaw_values": tomo_io.toDegree(np.asarray(tomo.yaw_range, dtype=np.float64)),
        "pitch_values": tomo_io.toDegree(np.asarray(tomo.pitch_range, dtype=np.float64)),
        "grid": vtc_grid,
        "vtc_grid": vtc_grid,
        "vnv_grid": vnv_grid,
        "vss_grid": vss_grid,
        "vo_grid": vo_grid,
        "mo_grid": mo_grid,
        "mss_grid": mss_grid,
        "mass_settings": settings,
        "value_key": "V_tc",
    }
