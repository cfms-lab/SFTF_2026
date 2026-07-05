# Support Flow Tensor Field (SFTF)

Reviewer data note: the GitHub review snapshot includes `sftf_Mesh_Data/`
inside the repository, but mesh files larger than 10 MB are intentionally
excluded to keep the snapshot small. See
[`DATA_AVAILABILITY.md`](DATA_AVAILABILITY.md) for the excluded-file list and
download/placement instructions.

이 저장소는 3D 프린팅에서 지지체(support)가 적게 필요한 빌드 방향을 빠르게 찾기 위한
**Support Flow Tensor Field (SFTF)** 실험 코드와 논문 작성 자료를 모아 둔 프로젝트입니다.

핵심 아이디어는 모든 yaw/pitch 방향을 슬라이서 또는 TOMO로 전수 탐색하지 않고, 메쉬의
면-면 지지 흐름을 방향별 텐서와 스칼라 feature로 계산하여 유망한 빌드 방향 후보만 먼저
고르는 것입니다. 논문 초안은 [`draft/SFTF_draft.tex`](draft/SFTF_draft.tex)에 있습니다.

## 논문 작성자를 위한 한 줄 요약

SFTF는 기존 PCA/Support Tensor처럼 형상 또는 법선 분포만 보는 방법과 달리, 후보 빌드
방향 `n`마다 오버행 면에서 아래쪽 지지 면으로 ray를 쏘아 **실제 self-support 관계**를
추정하고, 이를 비대칭 support-flow tensor와 `R/P/B` 비용으로 요약해 TOMO 전수 sweep 전에
좋은 후보 방향 basin을 빠르게 제안한다.

## 기존 방법과의 차이

| 방법 | 무엇을 보는가 | 장점 | 한계 | SFTF와의 차이 |
| --- | --- | --- | --- | --- |
| PCA | 정점/면 중심의 공간 분포 | 매우 빠르고 단순함 | 지지체 물리를 직접 반영하지 않음 | SFTF는 형상 주축이 아니라 방향별 오버행과 지지 흐름을 평가 |
| 기존 Support Tensor | 면 법선 분포의 대칭 텐서와 고유벡터 | 수학적으로 해석이 쉬움 | face-to-face visibility, bed support, self-support를 약하게 반영 | SFTF는 ray hit로 지지 source/receiver 관계를 만들고 비대칭 흐름을 사용 |
| TOMO_CPU / slicer sweep | yaw/pitch grid마다 support volume `v_ss` 계산 | 기준값/검증값으로 신뢰도 높음 | grid가 촘촘할수록 비용이 큼 | SFTF는 전수 sweep 대체라기보다 TOMO/slicer에 넘길 후보를 줄이는 전처리 |
| SFTF | 방향별 오버행, 면-면 지지, bed penalty, rank-tuned feature | 빠른 후보 생성, 비용 항 분해 가능, 후보 basin 제공 | 최종 support volume ground truth는 TOMO/slicer 검증 필요 | 본 연구의 제안 방법 |

## Originality / 기여점

1. **방향 의존 support-flow tensor**  
   후보 방향 `n`에 대해 오버행 source face와 support receiver face를 연결하고,
   `m_i m_j^T` 형태의 비대칭 텐서 `F(n)`로 지지 흐름을 표현한다.

2. **지지 물리량의 분해 가능한 목적함수**  
   최종 점수는 단일 블랙박스 support volume이 아니라 Rayleigh cost `R`, face-face support
   amount `P`, build-plate penalty `B`, hit count, singular-value feature 등으로 분해된다.
   논문에서는 각 feature의 기여도와 ablation을 설명하기 쉽다.

3. **coarse-to-refine 후보 생성**  
   512개 Fibonacci sphere 방향을 먼저 평가한 뒤, 상위 후보 주변 cone을 재샘플링한다.
   이 방식은 yaw/pitch grid 전체를 촘촘히 도는 TOMO 방식보다 후보 생성 비용이 작다.

4. **TOMO_CPU와의 정량 비교 프레임**  
   저장된 `1 deg / theta_c=60 deg` TOMO grid에 SFTF 후보를 매핑하여 best-of-k ratio,
   contour, basin 비교를 만든다. 논문 표와 그림의 재생성 스크립트가 포함되어 있다.

> **참고:** SFTF per-face feature를 이용한 mesh partition(clustering) 확장 연구는
> 별도 프로젝트 `Tomo_SFTFCluster_dev`로 분리되었다. 이 저장소는 SFTF
> (빌드 방향 후보 생성) 본체만 유지한다.

## 알고리즘 개요

후보 빌드 방향 `n`에 대해 SFTF는 다음 정보를 계산한다.

```text
O_i(n) = max(0, -m_i . n)              # face i의 overhang 정도
F(n)   = sum w_ij A_i A_j m_i m_j^T    # source i -> receiver j support-flow tensor
R(n)   = max(0, -n^T F_s(n) n)         # symmetric part 기반 Rayleigh support cost
P(n)   = face-face support amount      # 지지 면-면 관계의 총량
B(n)   = build-plate support penalty   # bed로 떨어지는 지지 penalty
```

현재 구현의 기본 후보 점수 `J`는 `R + P + B`이며, 최종 후보 정렬에는
`[J, R, P, B, hit count, nuclear score, sigma_1]`의 rank-normalized feature tuning을 쓴다.
상수와 weight는 [`support_flow_tensor_field.py`](python_src/SupportFlowTensorField/support_flow_tensor_field.py)
상단에 모여 있다.

## 주요 파일/폴더 위치

| 위치 | 설명 |
| --- | --- |
| [`TSE6_SFTF_main.py`](TSE6_SFTF_main.py) | Polyscope 시각화까지 포함한 SFTF 메인 실행 파일 |
| [`python_src/SupportFlowTensorField/support_flow_tensor_field.py`](python_src/SupportFlowTensorField/support_flow_tensor_field.py) | SFTF 핵심 구현: candidate sampling, ray hit, tensor/score 계산, TOMO contour 비교 |
| [`scripts/regenerate_sftf_vs_saved_tomo_summary.py`](scripts/regenerate_sftf_vs_saved_tomo_summary.py) | 저장된 TOMO grid와 SFTF를 다시 비교해 논문용 CSV/JSON 갱신 |
| [`scripts/plot_sftf_tomo_cpu_contours.py`](scripts/plot_sftf_tomo_cpu_contours.py) | TOMO `v_ss` contour와 SFTF 후보 marker 그림 생성 |
| [`scripts/validate_ccave_eigen_tomo.py`](scripts/validate_ccave_eigen_tomo.py) | TOMO_CPU를 재계산해 SFTF와 비교, GPU/DLL 의존 |
| [`cpp_src/Tomo_GPU2026/`](cpp_src/Tomo_GPU2026) | TOMO_CPU/TOMO CUDA 및 SFTF C++ DLL 연동 코드 |
| [`Experimental/etc/`](Experimental/etc) | 저장된 TOMO grid(`*_tomo_int3_vss_grid_1deg_60deg.npz`), 논문용 비교 CSV/JSON/HTML. **입력 메쉬는 공유 코퍼스 `../sftf_Mesh_Data/g5test/`로 이동됨**(아래 데이터 레이아웃 참고) |
| [`Experimental/G5Test/`](Experimental/G5Test) | A-E 그룹 검증 자료: `SFTF_result/` SFTF 결과, contour/cache, 표/그림 자료 (원본 메쉬는 `../sftf_Mesh_Data/g5test/`) |
| [`comparison_outputs/`](comparison_outputs) | 과거 TSE6/TOMO_CPU 비교 산출물 |
| [`draft/`](draft) | 논문 LaTeX, PDF, bib, 그림 |
| [`tests/`](tests) | SFTF 단위 테스트 |
| [`obsolete/`](obsolete) | 이전 FBO/VisFacePair/ShTensor 계열 코드. 현재 active pipeline 아님 |
| [`graphify-out/`](graphify-out) | Graphify 산출물. 현재는 community label metadata만 있음 |

## 설치

Python 3.12 이상을 사용한다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

또는 `uv`를 쓰는 경우:

```powershell
uv sync
```

주요 의존성은 `numpy`, `trimesh`, `scipy`, `polyscope`, `plotly`, `scikit-learn`,
`manifold3d`, `embreex`, `rtree`이다. concave volume 시각화에는 trimesh boolean backend인
`manifold3d`가 필요하다.

## 실행 방법

### 데이터 레이아웃 (재현 전 확인)

결과 동결 이후 두 가지가 정리되었으니 재현 시 참고한다.

- **저장 TOMO grid**: `Experimental/etc/({N}){stem}_tomo_int3_vss_grid_1deg_60deg.npz`
  (이전 `_tomo_cpu_` 이름에서 변경됨).
- **입력 메쉬**: 공유 코퍼스 `../sftf_Mesh_Data/g5test/Group_C{N}_{stem}.ply`로 이동
  (예: grid `(1)Bunny_69k_...` ↔ 메쉬 `Group_C1_Bunny_69k.ply`). 재현 스크립트는
  `scripts/_mesh_paths.py`를 통해 이 위치를 자동 해석하며, 공유 코퍼스·legacy `Experimental/etc`도
  폴백으로 시도한다.

별도 다운로드 없이 위 두 폴더만 제자리에 있으면 §2의 표/요약과 헤드라인 budget-curve가 그대로 재현된다.

### 1. SFTF 후보 방향 시각화

```powershell
.\.venv\Scripts\python.exe TSE6_SFTF_main.py
```

실행 내용:

1. [`support_flow_tensor_field.py`](python_src/SupportFlowTensorField/support_flow_tensor_field.py)의
   `MESH_PATHS`에 있는 메쉬를 읽는다.
2. 각 메쉬의 concave volume, SFTF 후보 방향, 방향별 점수를 계산한다.
3. Polyscope 창에서 입력 메쉬, concave volume, support/cavity 방향, 후보 방향으로 회전한 메쉬를 보여준다.
4. `USE_TOMO_GPU2026_FOR_COMPARISON = True`이면 TOMO contour 비교 HTML도 생성한다.

기본 입력 메쉬를 바꾸려면 `MESH_PATHS` 목록을 수정한다.

### 2. 논문용 SFTF vs 저장된 TOMO summary 갱신

GPU 없이 저장된 `*_tomo_int3_vss_grid_1deg_60deg.npz`를 재사용한다. 입력 메쉬는
`scripts/_mesh_paths.py`의 공유 코퍼스(`../sftf_Mesh_Data/g5test/Group_C{N}_{stem}.ply`)에서
자동 해석된다(grid stem `({N}){stem}` ↔ 메쉬 `Group_C{N}_{stem}`).

```powershell
.\.venv\Scripts\python.exe scripts\regenerate_sftf_vs_saved_tomo_summary.py
```

주요 출력:

```text
Experimental/etc/support_flow_tensor_field_vs_saved_tomo_int3_summary.csv
Experimental/etc/support_flow_tensor_field_vs_saved_tomo_int3_summary.json
```

> 검증됨: 위 출력은 저장된 5메쉬 요약과 정확히 일치하며, 헤드라인 budget-curve
> (`scripts\experiment_sftf_budget_curve.py`)도 K=20에서 mean 1.13 / max 1.58 / budget 3.57%를
> 그대로 재현한다.

SFTF weight나 sampling 상수를 바꾼 뒤 논문 표를 갱신할 때 먼저 실행하면 된다.

### 3. TOMO contour 그림 생성

```powershell
.\.venv\Scripts\python.exe scripts\plot_sftf_tomo_cpu_contours.py
```

출력 HTML은 `Experimental/etc/` 아래에 저장된다. 논문에서 SFTF 후보가 TOMO 지형의 어느 basin에
놓이는지 설명할 때 사용한다.

### 4. GPU/DLL 기반 TOMO 재검증

TOMO_CPU/TOMO CUDA DLL이 정상 동작하는 Windows 환경에서만 사용한다.

```powershell
.\.venv\Scripts\python.exe scripts\validate_ccave_eigen_tomo.py
```

빠른 논문 표 갱신에는 저장 grid 기반 스크립트를 우선 사용하고, 기준값 자체를 다시 계산해야 할
때만 이 경로를 쓰는 것이 좋다.

## 테스트

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

테스트 범위:

- spherical sampling과 후보 방향 중복 제거
- rank-normalized feature
- build direction rotation
- SFTF candidate pool invariants
- SFTF C++ DLL parity, 단 Windows에서 DLL이 있을 때만 실행

## 논문 작성 시 참고할 산출물

| 목적 | 파일 |
| --- | --- |
| 메인 논문 초안 | [`draft/SFTF_draft.tex`](draft/SFTF_draft.tex) |
| 참고문헌 | [`draft/references.bib`](draft/references.bib) |
| SFTF vs TOMO 요약 | [`Experimental/etc/support_flow_tensor_field_vs_saved_tomo_int3_summary.csv`](Experimental/etc/support_flow_tensor_field_vs_saved_tomo_int3_summary.csv) |
| 통합 비교 표 | [`Experimental/etc/sftf_unified_comparison.csv`](Experimental/etc/sftf_unified_comparison.csv) |
| feature correlation / ablation | [`Experimental/etc/sftf_feature_correlation_ablation.csv`](Experimental/etc/sftf_feature_correlation_ablation.csv) |
| A-E 그룹 검증 | [`Experimental/G5Test/`](Experimental/G5Test) |
| active mesh contour 비교 | [`Experimental/etc/tomo_int3_sftf_active_mesh_comparison.html`](Experimental/etc/tomo_int3_sftf_active_mesh_comparison.html) |

## 주의 사항

- `obsolete/`의 FBO, VisFacePair, ShTensor 코드는 이전 pipeline 보존용이다. 현재 논문과 실험의 중심은
  `python_src/SupportFlowTensorField/`이다.
- `TSE6_SFTF_main.py`에서 TOMO 비교를 켜면 DLL/환경 의존 문제가 생길 수 있다. SFTF만 보려면
  `USE_TOMO_GPU2026_FOR_COMPARISON = False`로 바꿔 실행한다.
- `MESH_PATHS`에 큰 메쉬를 여러 개 넣으면 Polyscope 렌더링과 ray casting 시간이 길어진다.
- 현재 Graphify 산출물은 `graphify-out/.graphify_labels.json` 중심의 community label metadata만 확인된다.
  구조 변경 전에는 코드의 import/call 관계를 직접 확인하고 수정해야 한다.
