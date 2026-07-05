"""Python과 공유 Tomo_Shell2026.dll(solid TOMO_CPU 모드) 사이의 ctypes 브리지.

이 모듈은 메시를 NumPy 배열로 준비하고, C++/CUDA DLL 함수에 포인터를 넘긴 뒤
Mo, Mss, Vtc, 렌더링용 픽셀 데이터를 다시 NumPy 배열로 읽어온다.
"""

import ctypes as ct

import numpy as np

from . import tomo_shell_io as tio
from .tomo_shell_io import (
  Cptr1d,
  Cptr1i,
  Cptr1iL,
  Cptr1d_to_np,
  Cptr1i_to_np,
  EndTimer,
  FStr,
  Fore,
  LoadInputMesh,
  StartTimer,
  Style,
  enumBedType,
  enumPixelType,
  getBoundary,
  getRotationMatrix,
  g_PixelEnums,
  g_PixelVarNames,
  g_nPixelFormat,
  np_to_Cptr1d,
  np_to_Cptr1iL,
  toDegree,
  toRadian,
)


def ToMathematicaFormat(arr, precision=2):
  arr_str = np.array2string(arr, precision=precision, separator=',', suppress_small=True)
  return arr_str.replace('[', '{').replace(']', '}')


class TomoShellCpp:
  """한 입력 메시와 YPR 탐색 조건에 대한 Tomo_Shell2026 계산 컨텍스트."""

  def __init__(self, data, theta_YP, bVerbose):
    self.Filename, self.Yaw, self.Pitch, self.Roll = data
    self._init_printer_defaults()

    if theta_YP == 0:
      self.nYPR_Intervals = 1
      self.yaw_range = np.ones(self.nYPR_Intervals) * toRadian(self.Yaw)
      self.pitch_range = np.ones(self.nYPR_Intervals) * toRadian(self.Pitch)
      self.roll_range = np.ones(self.nYPR_Intervals) * toRadian(self.Roll)
    elif theta_YP > 0:
      self.nYPR_Intervals = int(360 / theta_YP) + 1
      self.yaw_range = np.linspace(
        toRadian(0),
        toRadian(360),
        num=self.nYPR_Intervals,
        endpoint=True,
        dtype=np.float32,
      )
      self.pitch_range = np.linspace(
        toRadian(0),
        toRadian(360),
        num=self.nYPR_Intervals,
        endpoint=True,
        dtype=np.float32,
      )
      self.roll_range = np.zeros(1)
    else:
      raise ValueError('theta_YP must be zero or positive.')

    (
      self.mesh0,
      self.tri,
      self.vtx,
      self.vtx_nrm,
      self.tri_nrm,
      self.tri_area,
      self.tri_center,
      self.chull_tri,
      self.chull_vtx,
      self.chull_trinrm,
    ) = LoadInputMesh(self.Filename)

    self.xx, self.yy, self.zz = np.meshgrid(
      self.yaw_range,
      self.pitch_range,
      self.roll_range,
    )
    self.YPR = np.column_stack([self.xx.ravel(), self.yy.ravel(), self.zz.ravel()]).astype(np.float32)
    self.YPR_unique, self.ypr_inverse = self._unique_ypr(self.YPR)
    self.bVerbose = bVerbose

    # 입력 메시가 복셀 격자(nVoxel*dVoxel, 기본 256)보다 크면 TomoSh_INT3/CUDA가
    # voxelize에 실패하므로, 격자에 들어가도록 균등 축소한다.
    self._fit_mesh_to_voxel_space()

    mesh1_min, mesh1_max, _ = getBoundary(self.vtx)
    x1, y1, z1 = list(map(int, mesh1_max))
    x0, y0, z0 = list(map(int, mesh1_min))
    max_dimension = max(max(x1 - x0, y1 - y0), z1 - z0)
    self.AABB2D = (0, 0, max_dimension, max_dimension)

    if self.bVerbose:
      print('vtx=', self.vtx.shape)
      print('tri=', self.tri.shape)
      print('YPR=', toDegree(self.YPR), self.YPR.shape)
      if self.YPR_unique.shape[0] != self.YPR.shape[0]:
        print('unique YPR=', self.YPR_unique.shape[0], '/', self.YPR.shape[0])

  def _fit_mesh_to_voxel_space(self, safety=0.98):
    """입력 메시가 복셀 공간(nVoxel*dVoxel)보다 크면 균등 축소한다.

    TomoSh_INT3/TomoSh_CUDA는 한 변이 nVoxel(기본 256)인 복셀 격자에서
    voxelize하므로, yaw--pitch sweep 중 어떤 배향에서도 격자에 들어가려면
    경계 구(bounding sphere)의 지름이 격자 크기를 넘지 않아야 한다.
    메시는 LoadInputMesh에서 이미 무게중심으로 이동되어 있으므로,
    중심으로부터의 최대 거리(반지름)를 기준으로 회전 불변하게 판정한다.

    스케일 인자는 self.mesh_scale에 저장한다(원본=1.0). 부피/질량 결과는
    scale^3 만큼 작아지므로, 호출 측에서 원본 단위로 환산하려면
    1/mesh_scale^3 을 곱하면 된다(배향 자체는 스케일 불변).
    법선은 단위벡터라 균등 스케일에 불변이므로 그대로 둔다.
    """
    self.mesh_scale = 1.0
    if self.vtx.size == 0:
      return

    voxel_extent = float(self.nVoxel) * float(self.dVoxel)
    if voxel_extent <= 0.0:
      return

    max_radius = float(np.max(np.linalg.norm(self.vtx, axis=1)))
    diameter = 2.0 * max_radius
    target = voxel_extent * float(safety)
    if diameter <= target or diameter <= 0.0:
      return

    scale = target / diameter
    self.mesh_scale = scale

    self.vtx = (self.vtx * scale).astype(np.float32)
    self.tri_center = (self.tri_center * scale).astype(np.float32)
    self.chull_vtx = (self.chull_vtx * scale).astype(np.float32)
    self.tri_area = (self.tri_area * (scale * scale)).astype(np.float32)
    self.mesh0.vertices = (self.mesh0.vertices * scale).astype(np.float32)

    print(
      Fore.YELLOW
      + f'[resize] {self.Filename}: mesh diameter {diameter:.1f} > voxel grid '
      + f'{voxel_extent:.0f} (x{safety:g}); scaled by {scale:.4f} to fit TomoShell. '
      + f'Volumes are in scaled units (multiply by {1.0 / scale ** 3:.3g} for original).'
      + Style.RESET_ALL
    )

  def _init_printer_defaults(self):
    """DLL에 전달할 프린터/재료/계산 기본값을 초기화한다."""
    self.wall_thickness = 1.0
    self.PLA_density = 0.00121
    self.Fclad = 1.0
    self.Fcore = 0.15
    self.Fss = 0.2
    self.Css = 1.0
    self.bVerbose = False
    self.bUseExplicitSS = False
    self.dVoxel = 1
    self.nVoxel = 256
    self.theta_c = toRadian(60.0)
    self.nYPR_Intervals = 0
    self.BedType = (enumBedType.ebtNone, 0, 0, 0)
    self.mesh_scale = 1.0  # 복셀 격자에 맞추려 적용한 균등 축소 인자(원본=1.0)

    self.CppDLL = None
    self.CppFunction = None
    self.Cdll_opt_id = 0
    self.Cdll_opt_unique_id = 0
    self.Mo3D = np.array([], dtype=np.float32)
    self.Mss3D = np.array([], dtype=np.float32)
    self.Mtotal3D = np.array([], dtype=np.float32)
    self.Vtc = np.array([], dtype=np.float32)
    self.vm_info = np.array([], dtype=np.float32)

  @staticmethod
  def _rotation_key(yaw, pitch, roll, rotation_tol=1e-6):
    rotation = getRotationMatrix(float(yaw), float(pitch), float(roll))[:3, :3]
    return tuple(np.round(rotation.reshape(-1) / rotation_tol).astype(np.int64))

  @classmethod
  def _unique_ypr(cls, ypr, rotation_tol=1e-6):
    unique_ypr = []
    key_to_id = {}
    inverse = np.empty(ypr.shape[0], dtype=np.int64)

    for ypr_id, (yaw, pitch, roll) in enumerate(np.asarray(ypr, dtype=np.float32).reshape(-1, 3)):
      key = cls._rotation_key(yaw, pitch, roll, rotation_tol)
      unique_id = key_to_id.get(key)
      if unique_id is None:
        unique_id = len(unique_ypr)
        key_to_id[key] = unique_id
        unique_ypr.append((float(yaw), float(pitch), float(roll)))
      inverse[ypr_id] = unique_id

    return np.asarray(unique_ypr, dtype=np.float32), inverse

  def Run(self, cpp_function_name):
    """선택한 DLL 함수(TomoSh_INT3 또는 TomoSh_CUDA)를 호출하고 결과를 읽는다."""
    tio.g_mesh0_surface_area = self.mesh0.get_surface_area()

    float32_info = np.array([
      self.dVoxel,
      self.theta_c,
      tio.g_mesh0_surface_area,
      self.wall_thickness,
      self.Fcore,
      self.Fclad,
      self.Fss,
      self.Css,
      self.PLA_density,
      self.BedType[1],
      self.BedType[2],
      self.BedType[3],
    ]).astype(np.float32)

    # Tomo_Shell2026.dll's TomoSh_INT3 reads 11 ints (S3DPrinterInfo::Set):
    # [bVerbose, bUseExplicitSS, shell_mesh, nVoxel, nTri, nVtx, nYPR,
    #  nCHull_Tri, nCHull_Vtx, BedType, shell_thickness_microns].
    # Solid TOMO_CPU mode => shell_mesh=0, shell_thickness=0.
    int32_info = np.array([
      self.bVerbose,
      self.bUseExplicitSS,
      0,
      self.nVoxel,
      self.tri.shape[0],
      self.vtx.shape[0],
      self.YPR_unique.shape[0],
      self.chull_tri.shape[0],
      self.chull_vtx.shape[0],
      self.BedType[0],
      0,
    ]).astype(np.int32)

    time0 = StartTimer()

    self.CppDLL = ct.WinDLL(tio.g_CppDLLFileName)
    self.CppFunction = getattr(self.CppDLL, cpp_function_name)
    self.CppFunction.argtypes = (
      Cptr1d,
      Cptr1iL,
      Cptr1d,
      Cptr1iL,
      Cptr1d,
      Cptr1d,
      Cptr1d,
      Cptr1iL,
      Cptr1d,
      Cptr1d,
    )
    self.CppFunction.restype = ct.c_int32
    self.Cdll_opt_unique_id = self.CppFunction(
      np_to_Cptr1d(float32_info),
      np_to_Cptr1iL(int32_info),
      np_to_Cptr1d(self.YPR_unique),
      np_to_Cptr1iL(self.tri),
      np_to_Cptr1d(self.vtx),
      np_to_Cptr1d(self.vtx_nrm),
      np_to_Cptr1d(self.tri_nrm),
      np_to_Cptr1iL(self.chull_tri),
      np_to_Cptr1d(self.chull_vtx),
      np_to_Cptr1d(self.chull_trinrm),
    )

    EndTimer(time0, self.Filename + '    ' + cpp_function_name)
    self._read_results()
    self._read_render_pixels()

    self.CppDLL.OnDestroy.argtypes = ()
    self.CppDLL.OnDestroy.restype = None
    self.CppDLL.OnDestroy()

  def _read_results(self):
    """DLL 전역 버퍼에서 질량/부피 결과를 읽어 Python 배열 형태로 복원한다."""
    self.CppDLL.getMo.argtypes = ()
    self.CppDLL.getMo.restype = Cptr1d
    self.CppDLL.getMss.argtypes = ()
    self.CppDLL.getMss.restype = Cptr1d
    self.CppDLL.getVtc.argtypes = ()
    self.CppDLL.getVtc.restype = Cptr1d

    n_unique = self.YPR_unique.shape[0]
    mo_unique = np.array(Cptr1d_to_np(self.CppDLL.getMo(), n_unique)).astype(np.float32)
    mss_unique = np.array(Cptr1d_to_np(self.CppDLL.getMss(), n_unique)).astype(np.float32)
    vtc_unique = np.array(Cptr1d_to_np(self.CppDLL.getVtc(), n_unique)).astype(np.float32)

    self.Mo3D = mo_unique[self.ypr_inverse]
    self.Mss3D = mss_unique[self.ypr_inverse]
    self.Mtotal3D = self.Mo3D + self.Mss3D
    self.Vtc = vtc_unique[self.ypr_inverse]

    opt_matches = np.flatnonzero(self.ypr_inverse == self.Cdll_opt_unique_id)
    self.Cdll_opt_id = int(opt_matches[0]) if opt_matches.size > 0 else int(self.Cdll_opt_unique_id)

    self.CppDLL.getVolMassInfo.argtypes = ()
    self.CppDLL.getVolMassInfo.restype = Cptr1d
    self.vm_info = np.array(Cptr1d_to_np(self.CppDLL.getVolMassInfo(), 21)).astype(np.float32)

    if self.bVerbose:
      result_shape = (self.nYPR_Intervals, self.nYPR_Intervals)
      print(Fore.BLUE, 'Mo3D=    ', Style.RESET_ALL, FStr(self.Mo3D.reshape(result_shape), precision=2))
      print(Fore.BLUE, 'Mss3D=   ', Style.RESET_ALL, FStr(self.Mss3D.reshape(result_shape), precision=2))
      print(Fore.BLUE, 'Mtotal3D=', Style.RESET_ALL, FStr(self.Mtotal3D.reshape(result_shape), precision=2))
      print(Fore.BLUE, 'Vtc=', Style.RESET_ALL, ToMathematicaFormat(self.Vtc.reshape(result_shape), precision=2))

  def _read_render_pixels(self):
    """verbose 모드에서 Plotly 렌더링에 사용할 픽셀 그룹을 읽어온다."""
    self.CppDLL.getnData2i.argtypes = (ct.c_short,)
    self.CppDLL.getnData2i.restype = ct.c_int32
    self.CppDLL.getpData2i.argtypes = (ct.c_short,)
    self.CppDLL.getpData2i.restype = Cptr1i

    if not self.bVerbose:
      return

    for p_type, p_name in zip(g_PixelEnums, g_PixelVarNames):
      p_enum = getattr(enumPixelType, p_type).value
      n_2i = self.CppDLL.getnData2i(p_enum)
      p_2i = self.CppDLL.getpData2i(p_enum)
      if n_2i == 0:
        setattr(self, p_name, np.array([[0, 0, 0, 0, 0, 0]]))
      else:
        setattr(self, p_name, Cptr1i_to_np(p_2i, n_2i * g_nPixelFormat).reshape(n_2i, g_nPixelFormat))

  def Print_tabbed(self):
    """최종 부피/질량 정보를 사람이 읽기 쉬운 표 형태로 출력한다."""
    if not self.bVerbose:
      return

    labels = (
      ('Va, Vb, Vtc, Vnv,', (0, 1, 2, 3)),
      ('Vss, Vss_clad, Vss_core, Ass_clad,', (4, 5, 6, 7)),
      ('Vo, Vo_clad, Vo_core,', (8, 9, 10)),
      ('Vbed, Mbed,', (11, 12)),
      ('Mss, Mss_clad, Mss_core,', (13, 14, 15)),
      ('Mo, Mo_clad, Mo_core,', (16, 17, 18)),
      ('Mtotal, SS_vol,', (19, 20)),
    )
    for title, indices in labels:
      print(title)
      print(*(self.vm_info[i] for i in indices), sep=' ')
