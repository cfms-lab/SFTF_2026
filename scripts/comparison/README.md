# scripts/comparison — SFTF 분할 성능 비교

대형 물체를 **조각 출력**할 때의 분할 품질을, SFTF와 3개의 baseline으로 같은 입력
메쉬·같은 지표로 비교하기 위한 스크립트 모음입니다. 목표는 **지지구조 최소화**와
**이음매(seam) smoothness** 두 가지입니다.

## baseline 3종

| 방법 | 파일 | 성격 | 핵심 아이디어 |
|---|---|---|---|
| Planar BSP (Chopper류) | `baseline_planar.py` | 기하 중심 | 평면으로 재귀 분할 → 이음매가 평평(가장 smooth). 후보 평면 중 지지+이음매 비용 최소를 선택 |
| Graph-cut (MRF) | `baseline_graphcut.py` | 명시적 최적화 | 오목한 골에서 싸게 잘리도록 가중한 min-cut을 재귀 이분. 지지/공간 bias를 데이터항에 |
| Spectral (Normalized-cut) | `baseline_spectral.py` | 클러스터링 | 오목 경계에서 분리되는 face affinity로 스펙트럴 군집 → 자연스러운 매끈 경계 |

세 방법 모두 **원본 face에 라벨을 붙이는 형태**로 통일되어 있어(`labels[i]` = i번 face의
조각 번호) 한 가지 지표 세트로 공정하게 비교됩니다.

## 공통 지표 (`metrics.py`) — 모두 낮을수록 좋음

- `support_proxy` : 조각별 **최적 방향**에서의 지지량 추정(부피 단위 proxy)의 합.
  오버행 면(법선이 빌드방향 대비 45°↑ 하향)을 베이스까지 기둥으로 적분.
- `support_per_part_max` : 가장 지지 많이 드는 조각의 값(병목).
- `seam_length` : 절단 경계 총 길이.
- `seam_roughness_deg` : 경계의 평균 꺾임각(deg). 평면 절단은 ~0.
- `seam_planarity` : 경계점들의 최적평면 RMS 거리 / 경계 크기. 평면 절단 ~0.
- `parts_fit / parts_total` : 빌드 볼륨에 들어가는 조각 수.

## 실행

```bash
# 기본 3종 비교
uv run python scripts/comparison/run_comparison.py MeshData/big_part.stl \
    --parts 4 --printer-dims 250 250 300

# 조각별 방향 후보를 구(球) 샘플 64개로(더 현실적, 느림)
uv run python scripts/comparison/run_comparison.py ... --directions fib:64

# 매우 큰 메쉬는 먼저 데시메이션(스펙트럴 비용 절감)
uv run python scripts/comparison/run_comparison.py ... --decimate 20000

# 시각화용 색칠 메쉬도 저장
uv run python scripts/comparison/run_comparison.py ... --export-parts
```

결과는 `scripts/comparison/out/` 에 `comparison.csv`, `comparison.html`(+`.png`),
방법별 `*_labels.npy`(+`*_colored.ply`)로 저장됩니다.

## SFTF 결과 포함하기

SFTF에서 **face당 정수 라벨 하나**를 같은 메쉬 기준으로 내보낸 뒤(`.npy` 또는 `.csv`,
길이 = face 수) 넘기면 한 표에 같이 들어갑니다.

```bash
uv run python scripts/comparison/run_comparison.py MeshData/big_part.stl \
    --parts 4 --sftf-labels out/sftf_labels.npy
```

> SFTF가 라벨이 아니라 잘린 조각 메쉬로 결과를 내면, 각 원본 face의 중심이 어느 조각에
> 속하는지로 라벨을 만들어 `.npy`로 저장해 주세요(가장 가까운 조각). 필요하면 변환
> 헬퍼도 추가해 드리겠습니다.

## 설치

trimesh / numpy / scipy / scikit-learn / plotly 는 이미 프로젝트에 있습니다.
graph-cut baseline만 PyMaxflow가 추가로 필요합니다:

```bash
uv add pymaxflow      # import 이름은 maxflow
```

## 튜닝 포인트

- 지지 정의 각도: `--overhang-deg` (기본 45).
- graph-cut의 경계 위치: `lambda_smooth`(전체 강도), `k_concave`(오목 절단 비용↓),
  `k_convex`(볼록/평탄 절단 비용↑) — `baseline_graphcut.partition(...)` 인자.
- spectral의 경계 성향: `eta_concave`/`eta_convex`(오목 vs 볼록 거리), `beta_spatial`
  (공간 근접도 혼합; 균등 크기 조각을 원하면↑).
- 공정성: 네 방법 모두 `metrics.evaluate` 의 동일 평가기·동일 방향 후보로 채점됩니다.
