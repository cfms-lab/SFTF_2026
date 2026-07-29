# SFTFCluster_2026 공개 repo 업로드 매니페스트

> 대상: https://github.com/cfms-lab/SFTFCluster_2026
> 근거: 본문 Data availability — "The partitioning code, the twelve-shape CuraEngine
> benchmark and evaluation scripts, and the summary result records ... are openly
> available at ..." (원고가 현재형으로 단언하므로 **투고 전 업로드 필수**)
> 작성: 2026-07-06

## 1. 분할 코드 (필수 — "partitioning code")

| 파일 | 근거 |
|---|---|
| `python_src/sftf_clustering/mesh_partition.py` | 방법 전체(Eq. 1–9): PartitionConfig, 두 partitioning family, ray-free objective, auto-K, connected_part_labels |
| `python_src/sftf_clustering/__init__.py` | 패키지 |
| `python_src/__init__.py` | 패키지 루트 |

## 2. 벤치마크·평가 스크립트 (필수 — "benchmark and evaluation scripts")

| 파일 | 생성하는 논문 산출물 |
|---|---|
| `scripts/benchmark_shapes_cura.py` | Table 4 (tab:broad) 12형상×9방법, Friedman/Wilcoxon 원자료 |
| `scripts/benchmark_ablation_features.py` | Supp Note S4 + Table S13 (절제 3-arm) |
| `scripts/benchmark_matched_k.py` | Supp Note S5 + Table S14 (matched-K 통제 — 헤드라인 반전 실험) |
| `scripts/benchmark_seed_variance.py` | Supp Table S15 (시드 분산) |
| `scripts/verify_gao_coverage.py` | Supp Note S3 + Table S12 (Gao 자기지표 검증) |
| `scripts/slicer_derived_purity.py` | Supp Table S9 (반순환성 purity), recall 1.0 근거 |
| `scripts/bootstrap_meanrank_ci.py` | Supp Table S11 (mean rank 부트스트랩 CI) ※ scratchpad→scripts로 이동 완료 |
| `scripts/validate_cura_oracle.py` | Table 3 (tab:siloop) 48방향 프로토콜 |
| `scripts/optimize_partition_cura.py` | slicer-in-the-loop 최적화(본문 sec:cura) |
| `scripts/compare_gao.py` | Gao 비교 절 |
| `scripts/benchmark_shapes.py` | Supp Table S7 (스크리닝 8형상) |
| `scripts/bench_engine_speed.py` | Supp Table S10 + Note S1 (110× 속도) |
| `scripts/validate_predicted_support[_cura].py` | Table 2 (ray-free 검증) |
| `scripts/eval_application_partition.py` | Table 1 (application shapes) |
| `scripts/validate_auto_partition.py` | auto-K (Eq. 10) |
| `scripts/_mesh_paths.py` | 메시 경로 헬퍼 (`../sftf_Mesh_Data` 규약 문서화 필요) |
| `scripts/comparison/` 전체 (`baseline_gao.py`, `baseline_planar.py`, `baseline_graphcut.py`, `baseline_spectral.py`, `common.py`, `metrics.py`, `run_comparison.py`, `_selftest.py`, `README.md`, `requirements-comparison.txt`) | 비교 베이스라인 (Fig 1 좌측 가지) |

## 3. 그림 스크립트 (권장 — 그림 재현성)

`scripts/render_partcount_confound.py` (Fig S8) · `render_split_benefit_scatter.py` (Fig S9) ·
`render_ablation_arms.py` (Fig S10) · `render_g5_partition_grouped.py` (Fig S6) ·
`render_g5_representative_methods.py` (Fig S7) · `render_lambda_sweep_manikin.py` (Fig S3) ·
`make_cura_validation_figs.py` (Fig S5) · `render_manikin_support_review.py` (Fig 3) ·
`render_support_structure.py`, `render_figure2/3/4*.py` (본문·SFTF front-end 그림)

## 4. 요약 결과 레코드 (필수 — "summary result records")

| 경로 | 크기 | 내용 |
|---|---|---|
| `outputs/benchmark_cura/*.json` (114개) | 1.2 MB | 형상×방법 체크포인트: 파트별 best_g/best_dir 포함 → **재슬라이싱 없이 전체 재분석 가능** |
| `outputs/benchmark_cura/_gao_coverage.json` | 소형 | Table S12 원자료 |
| `outputs/benchmark_cura/_slicer_purity.json` | 소형 | Table S9 원자료 |
| `outputs/benchmark_ablation/*.json` (36개) | 0.5 MB | Table S13 원자료 |
| `outputs/benchmark_matchedk/*.json` (12개) | 소형 | Table S14 원자료 (matched-K 반전) |
| `outputs/benchmark_seedvar/*.json` (12개) | 소형 | Table S15 원자료 (시드 분산) |

## 5. 환경·메타 (필수)

| 파일 | 상태 |
|---|---|
| `pyproject.toml` + `uv.lock` | 있음 — `tomo-sftf`는 `../Tomo_SFTF_dev` 형제 규약(README에 문서화 완료) |
| `README.md` | ✅ **`README_public.md`로 작성 완료** (업로드 시 README.md로 개명): 형제 체크아웃 규약 3종, checkpoint-only 퀵스타트, 표↔스크립트 매핑, 메시 출처 표, 결과 레코드 포맷. **TODO 2곳**: SFTF 본편 repo URL 확정, 게재 후 인용 교체 |
| `LICENSE` | **없음 — 추가 필요** (MIT 또는 BSD-3 권장; SFTF 본편 repo와 동일하게. 저자 선택 사항이라 미생성) |

## 6. 제외 (업로드 금지/불필요)

- **메시 파일** (`../sftf_Mesh_Data/`): 제3자 라이선스(BodyParts3D, Thingi10k, Stanford) — 원고대로 원 출처 안내만. README에 파일명↔출처 매핑표 필요
- `draft/`, `draft_PiAM/` (원고·특허), `outputs/`의 대형 렌더 캐시, `__pycache__`
- `python_src/SupportFlowTensorField/`, `TomoNV_GPU2024/`, `TOMO_Shell2026/` — SFTF 본편 코드는 본편 repo가 정본(중복 vendoring 금지, pyproject 주석과 일치). 단 아래 이식성 문제 참조

## 7. 이식성 수정 (2026-07-06 코드 반영 완료 / 일부 README로 이관)

1. ✅ **`cura_cli` 하드코딩 경로 제거 완료** — 신규 `scripts/_external_paths.py`:
   `CURA_CLI_SRC` 환경변수 → 없으면 형제 디렉터리 규약(`../_Cura_CLI/python/src`),
   미발견 시 실행 가능한 안내 포함 ModuleNotFoundError. 적용 9파일:
   benchmark_shapes_cura, slicer_derived_purity, validate_cura_oracle,
   validate_predicted_support_cura, optimize_partition_cura, bench_engine_speed,
   proto_cura_aware_proxy, diag_r1/r2/r3(하드코딩 ROOT도 `__file__` 기준으로 수정).
   검증: 하드코딩 grep 0건, py_compile 통과, `benchmark_shapes_cura.py --summary`
   정상(Table 4 수치 불변), env 오버라이드 에러 메시지 확인.
2. ✅ **`tomo-sftf` 의존성** — README_public.md에 `../Tomo_SFTF_dev` 형제 체크아웃
   규약 + pyproject `[tool.uv.sources]` 문서화 완료 (SFTF repo URL만 TODO).
   추가로 **cura_cli import를 지연화**: `--summary`(체크포인트 재분석)는 _Cura_CLI
   없는 환경에서도 동작, run 모드만 안내 포함 에러 발생. 검증 완료(양 스크립트).
3. ✅ **`make_cura_validation_figs.py` 절대경로 제거 완료** — NPZ는
   `CURA_VALIDATION_NPZ` env → 기본 `CURA_CLI_SRC` 기준 상대경로, CSV는
   `MESH_DATA` 규약으로 통일.
4. ✅ **`_mesh_paths.py`** — `SFTF_MESH_DATA` 환경변수 오버라이드 추가(기본
   `../sftf_Mesh_Data` 형제 규약 유지). README 메시 배치 안내와 일치시킬 것.

## 8. 업로드 후 확인 (투고 게이트)

- [ ] repo 공개 상태 + 위 1·2·4·5 전부 존재
- [ ] 클린 클론에서 `uv sync` 후 `benchmark_shapes_cura.py --summary` (체크포인트만으로 표 재생성) 동작
- [ ] 본문 URL(2곳: sec:data, Data availability)과 repo 주소 일치 확인
