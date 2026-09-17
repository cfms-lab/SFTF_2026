# 사전 등록 — 후보 영역의 전향 슬라이서 확증 (2026-09-16, 결과 계산 전 동결)

3DP-2026-0119 1차 리뷰(2026-09-12) 지적 2: "슬라이서 워크플로우·복합 형상·타이트 예산의
우세는 사후 소집단(n=12, CI가 0 포함)에서 나온 것이므로 지도는 '후보'로만 제시하라."
개정 원고는 그 후보를 "엔진당 복합 메쉬 약 70개의 전향 확인 연구로 검증할 것"이라 썼다.
이 문서는 그 확인 연구를 **결과를 하나도 계산하기 전에** 고정한다.
스크립트·매니페스트·이 문서의 SHA256은 `Experimental/Prospective_slicer_confirm_2026-09/prereg_lock.json`
(이 문서 저장 직후, 실행 직전에 생성)에 있다.

## 가설

슬라이서로 검증하는 복합 형상(≥50k faces)에서 검증 예산 B=10일 때, ungated SFTF v2
top-10 셀의 최소 지지량이 matched-uniform 10셀의 최소 지지량보다 작다
(짝지은 NRR 차의 평균 < 0). 엔진별로 각각 검정한다.

## 표본 (n=70, 기하 전용 선정, `prospective_manifest.csv`, SHA256 13b35181be709cb2831df9f637cf6897c18c042641b72010295074bc89137b63)

- **Part A (33)**: v2.1 3차 확증 세트 N001–N080 중 복합층 메쉬 전부 (50k–150k 20, 150k–250k 13).
  슬라이서로 한 번도 평가된 적 없음. dense TOMO 그리드는 2026-07-29에 다른 가설(v2.1 vs V0)
  용으로 이미 계산돼 있어 재사용한다(`Experimental/R_term_recalib/confirm80_grids/`).
  - 공개: 그 세트의 TOMO 기반 V0(=논문 v2)·uniform NRR은 `confirm80_rows.json`
    (SHA256 d3f6e4ed8a08272bf98419f2cd5cf06eb8bd9707537a126163b6cadf950b690e)에 존재한다.
    본 프로토콜 작성 전에 열람한 것은 RESULTS.md의 전체(80메쉬·전 계층) 요약 문장뿐이며,
    복합층 33개의 예산 10 V0−uniform 대비는 층별로 검토하지 않았다. 따라서 이 33개에
    대한 **TOMO 2차 지표는 전향이 아니다**; 슬라이서 1차 지표는 전향이다.
- **Part B (37)**: 동일 소스(thingi10k_strict 3,817개), 동일 salted-hash 순서
  (salt `sftf-tdp-v2-holdout-v1`), 동일 기하 검사(유한·watertight·단일 성분·헤더 면수 일치),
  홀드아웃 60·확증 80·개발 ID 제외 후 복합층에서 계속 뽑음. 150k–250k는 남은 유효 후보가
  4개뿐이라 전부(4), 나머지 33은 50k–150k. 기하 검사 거부 0건. TOMO·슬라이서 결과 없음.
- 최종 구성: 50k–150k 53, 150k–250k 17. 선정 감사: `prospective_selection_audit.json`.
- 표본수 근거: 개정 원고 토론의 계획값 — 원 12메쉬 소집단의 평균·SD로 80% 검정력·양측 5%에
  Cura 71, Prusa 68 → 70.

## 정책 (논문 예산 스윕·소예산 슬라이서 연구와 동일; 재구현 없이 원 스크립트 함수 사용)

- SFTF: `sftf_v2.py` 무차원 점수, K=8,192 결정론적 표면 샘플, 2,048 Fibonacci 방향,
  임계각 60° → 24개 12°-NMS 분지 → 1° yaw–pitch 격자의 canonical 셀을 분지 근접도 순으로
  확장 → top-B (B=5,10,20은 top-20의 접두). **게이트 미적용(ungated)**; 게이트 진단은 보고만.
- uniform: `uniform_cells(yaw, pitch, B)` (B개 Fibonacci 방향의 최근접 셀; B별 별개 설계).
- 두 정책 모두 셀 인덱스는 `np.arange(0,361)` 정수 격자 기준(TOMO 그리드 인덱싱과 동일).

## 슬라이싱 프로토콜 (`run_tdp_v2_budget_slicer.py`와 동일)

- 메쉬를 bbox 대각선 140 mm로 스케일, `mesh_rotation.write_oriented_stl(yaw, pitch)`.
- CuraEngine 5.13.0 (`cura_cli.CuraSlicer(engine="modern", critical_angle=60)`,
  SHA256 36e36d46…afde2), PrusaSlicer 2.9.6 console (SHA256 7fd50b52…9704),
  프로파일 `draft/src/legacy/TDP_v2/profiles/prusa_support_tdp_v2.ini`, threshold 30°.
- 지지량: feature-tagged G-code 파싱(`parse_gcode_support`), mm³.
- 슬라이싱 대상: 메쉬당 uniform(5)∪uniform(10)∪uniform(20)∪SFTF top-20의 합집합(≈55방향),
  두 엔진 모두. 결과는 append-only JSONL(`slicer_raw.jsonl`), 재개 가능. 워커 6.

## 지표

- NRR(엔진, 메쉬, 정책, B) = (정책 top-B 셀 중 최소 지지량 − ref_min) / (ref_max − ref_min),
  ref_min/max = 그 메쉬·엔진에서 성공적으로 슬라이스된 합집합 셀 전체의 최소/최대
  (원 소예산 슬라이서 연구와 동일한 유한 패널 기준). 범위 0이면 NRR=0.
- 대비 Δ = NRR(SFTF) − NRR(uniform); 음수가 SFTF 우세.
- **1차 (엔진별 2개)**: B=10, complete-case(그 엔진에서 uniform-10과 SFTF-10 셀 20개가
  모두 성공한 메쉬만). 평균, 중앙값, SD, 메쉬 부트스트랩 95% 백분위 CI(10,000회;
  seed Cura 20260916, Prusa 20260917), 부호 뒤집기 순열 양측 p(100,000회, 같은 seed),
  승/무/패.
- **판정 규칙**: 엔진별로 평균 < 0 이고 Holm 보정(2개 엔진, 가족 α=0.05) p < 0.05이면
  "confirmed"; 평균 > 0 이고 Holm p < 0.05이면 "reversed"; 그 외 "not confirmed".
  후보 영역은 두 엔진 모두 confirmed일 때 "confirmed", 하나면 "partially confirmed",
  아니면 "not confirmed". 결과가 어느 쪽이든 원고 §3(새 소절)과 답변서에 그대로 보고한다.
- **2차 (서술적, 다중성 보정 없음)**: B=5·20 대비(complete-case); 층별(50k–150k / 150k–250k)
  및 source_set별(Part A / B) B=10 대비; best-available 민감도(원 연구 방식: 성공한 셀만으로
  최소값); TOMO 기준 대비 B=5/10/20(dense 그리드 전체 최소/최대 기준; Part A 비전향);
  두 엔진 간 및 TOMO–엔진 간 부호 일치 수; 게이트 수용 수; 비용(T_gen 평균·최대,
  엔진별 방향당 평균 슬라이싱 시간, 메쉬별 오버헤드 T_gen/(10·t_slice) 평균·최대).
- 결측·실패: 실패 행 수와 제외 메쉬 수를 보고. 슬라이싱 실패는 재시도하지 않는다
  (재개 시 미완료만 실행).
- 중간 열람 없음: 진행 모니터링은 `status`(개수만)로만 한다. 결과값은 `analyze`가 처음 출력.
- 일관성 점검(2차): Part A 33개의 TOMO B=10 대비를 `confirm80_rows.json`의
  (v0_nrr_b10 − uniform_nrr_b10)와 대조해 파이프라인 동일성을 확인한다(코드 경로가
  다르므로 소수점 차이는 허용, 부호·크기가 다르면 원인을 기록).

## 실행

1. `select_prospective70.py` (완료, 2026-09-16 15:04 KST; 결과값 미접촉)
2. `run_prospective.py all --jobs 6` : score → slice → tomo(Part B 37개 그리드) → analyze
3. 산출: `scores/`, `policy_cells.json`, `slicer_raw.jsonl`, `tomo_grids/`,
   `prospective_results.{json,csv}`, `RESULTS.md`.
- 계산 환경 주의: 실행 시점에 같은 워크스테이션에서 다른 실험(InjMold 워커 18, PINN 등)이
  돌고 있어 CPU 부하 ~60%. 따라서 이 연구의 시간 기록은 서술용이며 논문 Table 4의
  타이밍을 대체하지 않는다.

## 사후 변경 규칙

분석 스크립트의 버그 수정은 허용하되 추정량·표본·판정 규칙은 바꾸지 않는다. 변경이 있으면
이 문서 하단 "변경 기록"에 일시·내용·이유를 남기고 prereg_lock.json을 갱신하지 않는다
(원본 해시 보존).

## 변경 기록

(없음)
