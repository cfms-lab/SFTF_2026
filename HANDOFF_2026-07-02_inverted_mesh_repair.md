# 작업 인수인계: 반전 메시 수리 + 새 E-그룹 온보딩 (2026-07-02)

로컬 PC에서 중단하고 학교 원격 PC에서 이어서 작업하기 위한 기록.
관련 저장소 2개: 이 저장소(`Tomo_SFTF_dev`)와 메시 코퍼스(`../sftf_Mesh_Data`, https://github.com/cfms-lab/sftf_Mesh_Data ) — **둘 다 pull 필요**.

## 1. 발견된 문제와 수리 (완료)

외부 리뷰 지적으로 조사한 결과, 검증 메시 35개 중 **5개가 inside-out**(음수 부호부피,
winding·저장 법선 모두 반전)이었다: A2 sphere, B4 pipe_elbow, D10 37416, E8 64445, E9 64446.
이 때문에 SFTF 오버행 판정 `-(normals@n)`이 뒤집혀 보충 S1/S2의 sphere hit=498/500·B≈0.02,
pipe_elbow hit=500/500, D10 B=1.3, E8/E9 hit=2288 행이 전부 아티팩트였다.

수리 내역 (모두 완료):

- **로더 가드 3곳**: `python_src/.../support_flow_tensor_field.py::load_mesh`,
  `cpp_src/Tomo_GPU2026/tomo_sftf.py::_load_mesh_arrays`,
  `cpp_src/Tomo_GPU2026/tomo_shell_io.py::LoadInputMesh` — 음수 부피 감지 시 경고 후
  `cpp_src/Tomo_GPU2026/mesh_orientation.py::orient_faces_outward`(신규, 순수 numpy)로 자동 수리.
  닫힌 컴포넌트는 부피 부호로 개별 플립, 열린 패치는 그룹 단위 플립. 회귀 테스트
  `tests/test_mesh_orientation.py` 7개 추가 (전체 26개 통과).
- **원본 메시 5개 파일 수리** (sftf_Mesh_Data 저장소): 각 파일 옆에 `*.inverted.bak` 백업.
  주의 — STL은 triangle soup라 **꼭짓점 병합 후** 수리해야 함(B4/D10의 혼합 winding 복구).
  trimesh 함정: `fix_normals()`는 networkx 필요 + STL 저장 법선이 캐시에 남음 → 반드시
  faces를 고쳐 Trimesh 재구성.
- **산출물 재생성**: A2/B4/D10 전체(각 14개 그리드 npz + JSON/HTML/CSV), E8은 SFTF + tomo_int3
  전부(1deg_60, 3deg×5, 5deg_60) 완료. 새 값: A2 hit=0·R=P=0·B=136.6, B4 hit=222, D10 hit=66,
  E8 hit=1594(py)/996(C++).

## 2. 논문 수정 (완료)

- `draft/SFTF_supplementary.tex` — S1 hit 열 5개 행(A2 0, B4 222, D10 66, E8/E9 1594),
  S2의 A2·D10 행 + 캡션(sphere를 볼록체 그룹에 포함). **타이밍 열은 측정 세션 일관성을 위해
  기존 값 유지** (재측정 시 머신 부하로 4~7배 느린 값이 나오므로 한 세션에서 일괄 재측정 권장).
- `draft/patent/SFTF_특허명세서.tex` — 표 6 sphere 행 + 본문 프로즈.
- 본문 집계 표(1–4, 6–9)는 재실행 결과 **논문 값과 정확히 일치** → 수정 불필요.
  (그룹 C는 반전 없음; 반전 5개는 θc=60°에서 nonpositive-best라 ratio-valid 집합에서 원래 제외)
- S3는 대표 메시(A1/B2/C1/C3/D1/D6/E1/E7)만 실려 교체 메시 없음 → 수정 불필요.

## 3. 분석 스크립트 수정 (완료)

- `scripts/analyze_sftf_feature_correlations.py`, `scripts/build_unified_comparison_table.py`:
  이동 전 메시 경로 → `_resolve_mesh_path` 사용으로 수정 (실행 불가였음).
- `scripts/experiment_happy_method_g5_audit.py`: 캐시 상수 `tomo_cpu_cache`→`tomo_int3_cache`
  (디스크의 저장 그리드는 구 명명 유지 중), `--grid-suffix` CLI 추가(논문 표 5는 1° 설정:
  `--grid-suffix _tomo_int3_1deg_60deg.npz --output-stem sftf_happy_method_g5_audit_1deg60`),
  메시 없는 고아 그리드는 skip 처리.
- 갱신된 출력: `Experimental/etc/` (표 1–4·6–9 재현 확인, 1° 감사 신규 `sftf_happy_method_g5_audit_1deg60.*`).

## 4. 메시 코퍼스 로스터 변경 (사용자, 07-02 12:23)

- E2 45809→**790253**, E3 45811→**931902**, E4 46012→**439142** 교체, 새 **E9 82675** 추가.
- 구 E9 64446은 `Group_E9_64446.obj.retired`로 개명해 로스터에서 제외 (신규 82675 사용 결정).
- 새 메시 4개는 방향 정상(양수 부피), 각 ~100만 면.
- 구 E2/E3/E4의 저장 그리드·JSON은 고아 상태로 남아 있음 (감사 스크립트는 skip).

## 5-α. 진행 결과 (원격 PC, 07-02 저녁 ~ 07-03)

아래 5절의 1~5·7번은 **완료**. 요약:

- **Phase A 완료**: 새 메시 4개 SFTF py/C++ + tomo_int3 1°/3°(60°) 전부 확보 (1°는 메시당 34~47분).
  네 메시 모두 1° best가 음수(nonpositive-best) → 표 5 ratio-valid에서 제외됨 (구 로스터의 E와 동일 양상).
- **E2 SFTF 재측정**: 로컬 부하 세션 값(t_py=95.73s/t_C++=8385ms)을 이 머신에서
  21.16s/4886.7ms로 재측정 (hit=2296 동일). 새 4행 모두 이 머신 한 세션 기준.
- **Phase B 완료** (`scripts/onboard_new_meshes_phaseB.py` 신규): 새 메시 4개 CUDA 1°/60° +
  E8 낡은 CUDA 6개 전부 재스윕. **CUDA 회귀 확정**: E8 1°가 27,646s(7.7h, 과거 212s의 ~130배),
  E3 20,037s, E4 12,392s vs E9 2,084s·E2 4,284s — 불규칙 발현.
- **⚠ E3 CUDA 1° 그리드 이상**: 정확히 0인 셀 7개, 그 0이 best로 선택됨(나머지 0~36k, int3는 |3.1M| 스케일).
  JSON의 `tomo_cuda_best`는 None + error 노트로 pending 처리, dll_sec(타이밍)은 유효로 유지.
  재스윕 전 best 사용 금지.
- **표 5 갱신**: 1° 감사 재실행 결과가 핸드오프 기대값과 정확히 일치 (n=13, ALL mean 1.137
  max 1.370 budget 4.89%, base mean 3.102 max 17.568 budget 2.51% 10/13).
  tab:ave-g5 표·캡션·초록(52행)·본문 프로즈 반영 완료.
- **S1 4행 교체 + 캡션에 세션 주석 추가, 표 10(tab:fivegroup-impl) E행 재계산**
  (CPU 1400.02s / CUDA 4345.17s / py 19.20s / C++ 4457.7ms, 8.3–123.0× / 56.8–526.4×).
  전체 35개 speedup 범위(8.3–381.9×, 56.8–56,027×)는 불변 → 기여문·본문 프로즈 무수정.
- **리뷰 2·3번 반영**(7번 항목): SFTF_draft.tex에 J=R+P+B 단위 종속성(R,P~s⁴ vs B~s²) 명시 +
  rank 정규화의 단위 불변성 연결, Eq.(4) 아래에 결정적 계통 샘플링 플러그인 추정량 F̂(n) 수식 추가.
  draft/supplementary 모두 pdflatex 통과.

**남은 미해결**: (a) 새 dll의 대형 메시 CUDA 성능(≈130×)+정확성(E3 0-셀) 회귀 원인 조사 및
E3 CUDA 재스윕, (b) 6번 E9_64446 잔재 정리(사용자 결정 대기), (c) S1 전체의 단일 세션
타이밍 재측정(장기 과제, 유휴 머신에서 일괄).

### 07-03 저녁 추가: CUDA 회귀 블랙박스 진단 + 정리 실행

- **E9_64446 잔재 18파일 삭제 완료** (커밋 cb96c7a). 구 로스터 E2_45809/E3_45811/E4_46012의
  고아 산출물은 이번 정리 범위에서 제외하고 유지 중.
- **E3 0-셀 위치**: (yaw 0–2°, pitch 323°)+(yaw 360°, pitch 323°; yaw 0°와 동일 방향) 및
  (yaw 177–180°, pitch 141–145°) — 두 좁은 방향 근방에 국한, 이웃 셀은 정상값.
  특정 기하 조건의 국소적 평가 실패로 보임. 결정성 확인용 재스윕 진행
  (`phaseB_E3_resweep_20260703.log`, suspect 그리드는 세션 스크래치에 백업).
- **백엔드 불일치는 대형 메시 전반**: int3↔CUDA Spearman 상관 E2 0.45 / E3 0.20 / E9 0.07.
  int3는 음수 수백만 값(-3.1e6 등) → 복셀 카운트 **int32 오버플로 의심** (TomoSh_INT3 명명과
  부합; nonpositive-best 제외 규칙이 걸러온 것). CUDA는 항상 비음수.
- **Tomo_Shell2026.dll은 이 저장소에 소스 없음** (프리빌트; SFTF 쪽 sftf_cpp.cpp만 소스 존재)
  → 근본 원인 수정은 dll 원 프로젝트에서. 재현 데이터: E8 1° 27,646s(과거 212s), E3 20,037s,
  E4 12,392s vs E2 4,284s·E9 2,084s(같은 밤, 같은 RTX 5080, 유휴).
- **07-04 새벽 — E3 CUDA 재스윕 판정**: 두 번째 1° 스윕(19,943s)도 정확히 7개 0-셀,
  같은 두 방향 근방이지만 셀 위치는 일부만 일치(3/7) + 0 아닌 셀도 런 간 불일치
  (완전 일치 20,773/130,310, 최대 차 831) → **확률적(비결정적) CUDA 커널 실패** 확정.
  E3 JSON의 tomo_cuda_best는 dll 수정 전까지 pending 유지. 저장 npz는 run2로 교체,
  run1은 Tomo_Shell2026-dev에 증거로 복사. dll 수정 후 CUDA 그리드 전체(특히 E3)
  재스윕 필요.
- **07-03 밤 추가 — 소스 확인 결과 int16 오버플로 확정**: dll 소스 사본
  (`D:\__SFTF_Projects(2026)\Tomo_Shell2026-dev`)에서 `SLOT_BUFFER_TYPE = short int`(int16)로
  슬롯별 z-합산(`createVss_Implicit`의 al/be/TC/NVB/NVA_sum, `createVoPixels`, `sumType` 반환형)이
  이뤄져 복잡 컬럼에서 래핑 → 음수 v_ss의 실체. 상세 분석·수정 제안·CUDA 이슈 2건(0-셀,
  ~130× 슬로다운) 포함 리포트를 **`Tomo_Shell2026-dev/BUGREPORT_2026-07-03_INT16_vss_overflow.md`**로 전달함.

## 5-β. 07-04: int16 수정 dll 배포 + 전 그리드 재스윕

- 수정 dll(07-03 20:26 빌드, int32 누산기) 배포·검증 완료 (커밋 04843a6):
  E3 3° 음수 0개·CUDA 스케일 일치, cube 해석적 기대치 일치. **단 Bunny 등 일반 메시도
  전 셀 ~15–20% 하향** — 구 dll 오염이 전 메시에 있었음 (sumType z-합이 int16 한계 직하).
- 사용자 결정: **전체 재스윕** (`scripts/resweep_int3_new_dll.py`, 마커 dll_int32fix).
  이 스윕의 dll_sec = 단일 세션 t_CPU 재측정 (S1의 장기 과제 (c) 겸함).
- 재스윕 후 할 일: ① 1° 감사 재실행 → 표 5, ② 표 1–4·6–9 재현 스크립트 재실행·논문 대조,
  ③ S1 t_CPU 열 + 표 10 갱신, ④ S2 상관분석 재실행 검토, ⑤ nonpositive-best 제외 규칙
  재검토(음수가 사라졌으므로 valid 집합이 커질 수 있음 — 표 5 n 변동 가능).
- CUDA 그리드는 레이스·슬로다운 미해결이라 재스윕 보류 (S1 t_CUDA는 기존 세션 값 유지).
- CUDA 이슈 2건은 dll 쪽 Claude Code 착수용 작업 문서로 정리해 전달:
  **`Tomo_Shell2026-dev/TODO_CUDA_issues_2026-07-04.md`** (0-셀 좌표의 기하 규칙성 —
  사실상 단일 물리 방향 ≈−37° 계열에서만 발생, atomicWrite.cu의 char atomicOr 의심 구현,
  TOMO_CUDA_STREAMS=1 판별 실험, E8 방향당 0.211s 고정 비용 분석, 수정 판정 기준 포함).

## 5. ★ 남은 작업 (원격 PC에서 이어서)

우선순위 순:

1. **Phase A 재개** — 새 메시 4개의 SFTF + TOMO_CPU 1°/60°·3°/60° 그리드.
   스크립트: 이 저장소에 없음 → 아래 "스크립트 위치" 참고, 또는 같은 로직 재작성.
   완료 상태: E2_790253의 SFTF py/C++만 완료(JSON/HTML/CSV 있음, hit=2296).
   **E2의 1° 스윕부터 재개** → E3, E4, E9_82675 (SFTF부터). 스크립트는 재실행 안전(있는 것 skip).
2. **E8_64445 CUDA 스윕 재실행** — 반전 메시로 계산된 낡은
   `tomo_cuda_cache/Group_E8_64445_tomo_cuda_*.npz` 6개와 `Group_E8_64445_tomo_cuda.html`이
   **아직 디스크/저장소에 낡은 상태로 남아 있음** (JSON의 tomo_cuda_* 필드는 pending으로
   표시해 둠). 주의: 로컬에서 E8 CUDA 1° 스윕이 6시간+ 걸리다 중단됨 (과거 기록 212초 —
   새 Tomo_Shell2026.dll의 대형 메시 CUDA 경로 성능 회귀 의심, 원인 조사 가치 있음).
3. **새 메시 4개의 CUDA 1°/60° 스윕** (S1 t_CUDA 열) — 2번과 같은 성능 리스크.
4. **표 5 갱신** — 그리드 완료 후:
   `python scripts/experiment_happy_method_g5_audit.py --grid-suffix _tomo_int3_1deg_60deg.npz --output-stem sftf_happy_method_g5_audit_1deg60`
   → `draft/SFTF_draft.tex`의 tab:ave-g5 (n, 그룹별 값, 캡션의 base 통계, 295행·318행 프로즈).
   현재(13개 valid) 기준: A 1.04, B 1.24, C 1.01/1.06, D 1.22/1.37, E(E5 55280만) 1.34;
   ALL mean 1.137 max 1.370 budget 4.89%, base mean 3.102 max 17.568.
5. **S1 행 교체** — E2/E3/E4/E9 행을 새 메시로 (faces: E2 1,039,452 / E3 1,050,398 /
   E4 1,038,714 / E9 916,548; hit·t_py·t_C++는 JSON에서, t_CPU/t_CUDA는 새 스윕 dll_sec).
   E2_790253 확보분: t_py=95.73s, t_C++=8385.4ms, hit=2296.
   본문 표 10(그룹 E 평균)도 S1에 연동해 재계산 필요.
6. **E9_64446 잔재 정리(선택)** — 은퇴 메시의 그리드/JSON/HTML이 저장소에 남아 있음.
   G5Test 로스터는 메시 파일 기준이라 무해하지만 정리하면 깔끔함.
7. **차원 비일관성(J=R+P+B 단위 종속)·Eq.(4) 추정량 명시** — 외부 리뷰의 2·3번 지적은
   논문 서술 수정 사안으로 미착수.

## 6. 재생성 스크립트 (저장소에 포함, 경로 이식성 적용)

- `scripts/regen_inverted_meshes.py` — 반전 5개 메시의 산출물 일괄 재생성 (재실행 안전:
  `regenerated` 마커 있는 npz는 skip). 인자 없이 5개 전부, 또는 stem 인자로 선택 실행.
  ※ E9_64446은 은퇴했으므로 STEMS에서 빼거나 인자로 제외하고 실행할 것.
- `scripts/onboard_new_meshes_phaseA.py` — 새 E-그룹 4개 온보딩(SFTF + CPU 1°/3° 60° 그리드).
  **원격에서 이것부터 재실행** (있는 스테이지는 skip하므로 그대로 실행하면 E2의 1° 스윕부터 재개).
  CUDA(Phase B)는 미구현 — 같은 패턴으로 `compute_tomo_cuda_vss_grid` 호출 추가하면 됨.
- 공통 규약: npz는 구 명명 `{stem}_tomo_int3_{step}deg_{ca}deg.npz`
  (keys: yaw_values/pitch_values/vss_grid/dll_sec), JSON은 `tomo_int3_*` 키
  (형제 레코드와 동일; 코드의 tomo_cpu_* 리네임은 진행 중이므로 저장 그리드는 구 명명 유지).

## 7. 주의사항

- 브랜치 리네임 과도기: 코드(G5Test.py)는 `tomo_cpu_cache`/`_tomo_cpu_` 명명을 쓰지만
  디스크 저장 그리드는 `tomo_int3_cache`/`_tomo_int3_`. G5Test의 TOMO 스테이지를 그대로 돌리면
  캐시 미스로 전체 재스윕되므로 주의.
- 타이밍 재측정은 반드시 유휴 머신에서 일괄로 (S1/표 10의 세션 일관성).
- `Group_D10_65942.stl` 중복 이슈는 기존 dedupe 로직이 처리 (README/G5Test 주석 참고).
