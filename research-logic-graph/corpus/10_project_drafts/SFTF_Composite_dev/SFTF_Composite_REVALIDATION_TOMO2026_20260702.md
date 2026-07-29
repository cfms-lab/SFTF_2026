# SFTF_Composite 재검증 감사 — 2026-07-02 (Tomo_Shell2026 기준 전환)

검증 기준 tomo 엔진이 `_shared_dll\Tomo_Shell2026.dll`(Tomo_Shell2026-dev 산출물,
sha256 `1cb968a1…ff80ff`)로 통일됨에 따라, 소스코드와 논문 데이터 전체를 처음부터
재검증한 기록.

## DLL / 의존 체인

- 이 프로젝트는 tomo DLL을 직접 갖지 않는다. tomo는
  `../Tomo_SFTFCluster_dev/python_src`의 `TOMO_Shell2026`(shell) /
  `TomoNV_GPU2024`(solid 호환 래퍼) 패키지를 통해 사용하며, 두 패키지 모두
  공유 `Tomo_Shell2026.dll`(sha256 일치 확인)만 로드한다.
- 구버전 DLL 제거: `Tomo_Shell2025.dll`, `Tomo_GPU2024.dll` 를
  Tomo_SFTFCluster_dev에서 git rm (코드 참조 0건 확인 후).
- 스모크 테스트(이 프로젝트 venv 경유): solid box(지지 0 g)·solid sphere
  (Mss 0.122 g)·shell 엔진 로드 모두 정상.
- R4 체인 복구: 상류 패키지 개명(`SupportFlowTensorField`→`sftf_clustering`) 및
  `Tomo_SFTF_dev/python_src` 의존을 `scripts/run_drape_partition.py`에 반영.
  엔드투엔드 재실행: manikin kmedoids k=6 → purity **0.977** (논문 tab:r4와 일치).

## 재검증 결과 요약

| 항목 | 결과 |
|---|---|
| pytest (python/src/drape) | **70개 전부 통과** |
| tab:cmp-agg / cmp-lock / cmp-flat (9메쉬 벤치마크) | 재실행 결과 **수치 완전 일치** (method_comparison md와 동일) |
| 응용 사례 순도 (kidney 0.852, liver 0.861, nefertiti 0.951, 조개 0.963/0.978/0.977, 항공기 0.915, 차체 0.949, 요트 0.632) | 캐시 고정 재실행 **일치**, App_*.png 전부 재생성 |
| tab:r4 (manikin 0.977/0.81 등) | **일치** |
| tab:r2 (멀티시드) | **부분 불일치 → 수정** (아래) |
| tab:r7 (Baraff sweep) | 범위 소폭 변경 → 현재 엔진 값으로 갱신 |
| fig:sftf-landscape (figure3, TOMO 의존 유일 항목) | 새 DLL로 재생성, 캡션 갱신 |

## 수정된 논문 수치

1. **tab:r2 / Fig2 / 본문·결론** — 재현 불가한 구 수치를 현행 코드 재실행 값으로 교체:
   - sphere cap: 0.40→0.01 (0.72→0.19) ⇒ **0.36→0.00 (0.63→0.18)**
   - manikin: 0.37 "(k=8)" ⇒ **0.42 (패치별 시드 ≈260)**, 13150→6.9.
     k-스윕으로 규명: 공표된 6.8은 k≈260(패치별 시드) 값이며 "(k=8)" 주석이 오류였음
     (k=8은 dart 0.88). 상세: R2 md 재검증 노트.
   - liver: min-shear 4.3 ⇒ **3.2** (dart 0.86→0.45는 그대로 재현)
2. **fig:sftf-landscape 캡션** — 새 기준 엔진(Tomo_Shell2026, θc=60°, 10° 격자)의
   1순위 최적 yaw 270°/pitch 220°, 최악 yaw 240°/pitch 0°. 그림은
   Tomo_SFTFCluster_dev `render_figure3_bunny_support.py`(TOMO2026)로 재생성 후 복사.
   (참고: 동일 DLL의 CPU/CUDA 경로가 근접-동률 최적점 순위를 다르게 낼 수 있음 —
   CUDA 탐색은 (300°,40°) Mss 0.962 g, CPU 탐색은 (270°,220°). 골짜기(basin) 결론은 동일.)
3. **tab:r7** — 재벤더링한 cfmsDrape 0.2로 cap 35/55/75/90° 재실행:
   dome proxy −0.03…0.05 / net −0.03…0.03, bowl proxy −0.02…0.33 / net 0.02…0.26.
   정성 결론(자유낙하 무상관·보울 약상관) 불변.

## 미해결 — 제출 전 필요 조치

- **성형(forming) 검증 재현 불가**: `form_pressure_demo.py`가 요구하는 외력 API
  (`set_node_forces`/`SDE_SetExternalForces`)가 현재 cfmsDrape 빌드에서 제거됨.
  본문 성형 수치(Spearman 0.1–0.2, 전단 ~19°, 잔차 ~0.7 cm)와 Fig6 트렐리스 빈
  (6.8/7.0/7.1/9.6°)은 구 엔진 산출로 남아 있음. cfmsDrape2026_dev에서 API 복원 후
  재실행 요망.
- `references.bib`의 `sul_sftf`/`sul_sftfclustering`은 여전히 unpublished 플레이스홀더.
- 선행 SFTF 논문(Tomo_SFTFCluster_dev) 쪽 figure3도 같은 재생성을 반영해야 두 논문이
  일치한다(이번에 그쪽 draft/pics도 갱신됨).

## 재현 명령

```bash
uv sync                                          # trimesh/networkx 의존성 추가됨
PYTHONPATH=python/src uv run pytest python/src/drape -q
uv run python scripts/make_paper_figures.py
uv run python scripts/make_application_figures.py
uv run python scripts/make_flat_patterns.py
uv run python -m drape.bench --folder <9개 앱 메쉬 폴더> --k 6 --out comparison.md
uv run python scripts/run_drape_partition.py --mesh ../sftf_Mesh_Data/g5test/Group_C2_manikin.ply
uv run python scripts/sync_cfmsdrape.py --verify
uv run python scripts/compare_kinematic_vs_baraff.py --sweep
```

---

# 부록 — 베이스 프로젝트 재동기화 (2026-07-05)

7/2 감사 이후 베이스 프로젝트들이 다시 갱신되어 재반영한 기록.

## 무엇이 바뀌었나 (베이스별)

| 베이스 | 변경 | 이 프로젝트 영향 |
|---|---|---|
| **cfmsDrape2026** | 바인딩 `__init__.py` 갱신: `set_gravity` 기본값 `-9.81`→**`-980` (CGS)**, `pin_vertex_at`/`last_error`/`abi_version` 추가. 소스에 **커밋된 병합충돌 마커**(`<<<<<<< HEAD` … `>>>>>>> 3b234ba`) 존재. DLL은 **비트 동일**(v0.2, `1563cf22…`, 6/28 이후 미재빌드). | **수치 영향 없음.** R7/성형 스크립트는 중력을 명시(`compare_kinematic_vs_baraff` −980, `form_pressure_demo` 0)하고 DLL도 그대로. |
| **Tomo_Shell2026** | 공유 DLL이 7/2 기준 `1cb968a1…`에서 갱신. | fig:sftf-landscape(figure3) — 유일한 TOMO 의존 항목. |
| **Tomo_SFTFCluster** (`sftf_clustering`) | 소스 갱신(`tomo_shell2026`, 2차 대응). | R4 재실행 — 결과 불변. |
| **drape** (자체 코드) | 베이스 변경 아님. | drape 전용 그림/벤치 동일. |

## 반영 조치

1. **cfmsDrape 재-벤더링**: `scripts/sync_cfmsdrape.py`로 바인딩+DLL 갱신 후,
   **벤더 사본(`python/src/cfmsdrape/__init__.py`)의 병합충돌만 해결** —
   `set_node_forces`(HEAD)와 `last_error`/`abi_version`(3b234ba) 양쪽을 모두 보존
   (인접 추가라 실제 충돌 아님). 바인딩 정상 로드, `abi_version()==-1`(구 DLL에서 정상
   tolerant). **베이스 저장소 cfmsDrape2026_dev의 커밋된 충돌은 손대지 않음 — 상류에서
   별도 해결 필요(알림용 기록).**
2. **R4 재실행**: `run_drape_partition.py` manikin k=6 → purity **0.977** (tab:r4 일치, 불변).
3. **drape pytest**: **70개 전부 통과**.
4. **Tomo 기준 정리 + figure3 재생성**: 배포 체인이 어긋나 있었음 —
   `_shared_dll` = `4ab18b79…`(commit `23b4591`, **clean**)이나 소비 패키지
   `Tomo_SFTFCluster_dev/python_src/{TOMO_Shell2026,TomoNV_GPU2024}` = `42657da5…`
   (commit `f2439790`, **DIRTY**). **clean 기준(4ab18b79)을 두 소비 패키지에 재배포**한 뒤
   `render_figure3_bunny_support.py`로 figure3 재생성 → 이 프로젝트
   `draft/pics/figure3_bunny_landscape_support.png`로 복사.
   - 새 1순위 최적 배향 **yaw 300° / pitch 40°** (기존 캡션 270°/220°에서 이동;
     clean 엔진의 CPU 탐색이 이전 CUDA 최적점과 수렴). 최악 **yaw 240° / pitch 0°** 불변.
   - 캡션 갱신: `main.tex` / `main_en.tex` fig:sftf-landscape.

## 성형(forming) 검증 재실행 완료 (7/2 미해결 항목 해소)

현행 v0.2 DLL(`1563cf22…`)이 `cfms_set_node_forces`를 다시 export함을 확인하고,
새 `scripts/form_trellis_analysis.py`(mesh/재료/압력은 `form_pressure_demo.py`와 동일)로
성형 검증을 재실행:

| 항목 | 구 논문값 | 재실행값 (cap 70°, press 2e3) |
|---|---|---|
| 잔차(중앙값) | ~0.7 cm | **~0.9 cm** (0.86) |
| Baraff 전단 mean/p90 | ~19° / ~36° | **19.2° / ~34°** |
| Spearman (proxy/fishnet) | ≈0.1–0.2 | **≈0** (−0.03…0.01, OpenMP 지터 ±0.03) |
| Fig6 트렐리스 빈 (\|sin 2φ\|) | 6.8 / 7.0 / 7.1 / 9.6° | **16.1 / 17.8 / 20.0 / 20.2°** |

- 4-fold 각도 패턴(warp/weft 축 낮음 → ±45° 대각 높음)은 단조 증가로 **유지**되나,
  성형 캡 전체가 주름으로 ~16° 바닥이 깔려 대비가 완만함.
- 상관이 0.1–0.2 → 0으로 내려가 **정직한 음성 결론이 강화**됨.
- 갱신: `Fig6_trellis.png/svg`(make_paper_figures), `main.tex`/`main_en.tex` 성형 문단,
  `SFTF_Composite_R7_baraff_validation_results.md`.
- ⚠️ 엔진이 OpenMP로 미세하게 비결정적 — Spearman은 0 부근 ±0.03 지터. 절대값 아닌
  "≈0" 정성 결론으로 기술함.

## 여전히 미해결

- `references.bib`의 `sul_sftf`/`sul_sftfclustering` 플레이스홀더 유지.

