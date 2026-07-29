# R7 고정엔진 재검증 기록 (2026-07-18)

## 배경
7/15 커밋 `dbfca99`("chore: sync shared TOMO engine")가 배포 DLL을 7/01 빌드
(`0435e06`, sha256 `1cb968a1…`)에서 7/11 빌드(`4380c4a9`, sha256 `d8765596…`)로
교체했으나, 논문 R7 수치(n=46)에 대한 재검증 기록이 없었다. 본 문서가 그 기록이다.

## 구조적 소견
R7 수치를 산출하는 `moldability` 파이프라인(스크린→off-principal→정밀 ingest)은
순수 Python(trimesh/embree) ray-cast oracle 기반으로 **Tomo_Shell2026.dll을 참조하지
않는다**. `TOMO_Shell2026` 패키지는 소비자 래퍼+스모크 테스트 전용. 따라서 DLL 교체는
원리상 R7 수치에 영향을 줄 수 없다 — 아래 재실행이 이를 실증한다.

## 실행
- 테스트: `uv run pytest -q` → **75/75 통과** (새 DLL sha256 핀 스모크 7개 포함).
- 파이프라인: `uv run python scripts/reverify_thingi10k.py --corpus-names <7/02 스크린 스냅샷>`
  — 302부품 풀 스크린(2306s) → 49 후보 → 46 off-principal 정밀 ingest(4188s, axes=160).

## 결과 — 논문 기준치(91f3d33, 7/02)와 전 항목 일치

| 항목 | 기준치 | 재검증(7/18) |
|---|---|---|
| n | 46 | 46 |
| mean_sa_oracle | 2.93 | 2.9348 |
| mean_sa_sftf | 3.20 | 3.1957 |
| mean_sa_pca | 3.85 | 3.8478 |
| mean_sa_bbox6 | 3.43 | 3.4348 |
| sftf_match_rate | 0.54 | 0.5435 |
| pca_match_rate | 0.28 | 0.2826 |
| mean_sftf_budget | 0.118 | 0.1182 |

- `draft/SFTF_InjMold_realparts.md` 재생성본: 기존 커밋본과 **내용 비트 동일**.
- `thingi10k_off_ingest_manifest.json` 재생성본: 내용 동일.
- `thingi10k_screen.json`: 동률 정렬 키의 행 순서 셔플만 존재(값 전부 동일) — 원복함.

## 결론
논문 R7 수치는 7/11 배포 DLL 환경에서 완전 재현된다. 7/15 엔진 동기화는 논문
수치에 영향 없음이 실행으로 확인됨 → 투고 전 고정엔진 재검증 게이트 **통과**.
