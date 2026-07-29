# SFTF_ThermalChip 투고 체크리스트 (2026-07-18 작성)

원고: `SFTF_ThermalChip_PoC_en.tex`(영문 투고본) / `SFTF_ThermalChip_PoC.tex`(한글 참조본, lockstep).
수치·그림: `scripts/build_paper_data.py` 단일 명령 재현 (`paper_data.json` + `pics/thermal_*{,_en}.{png,svg}`).

## P0. 남은 필수 (사람 판단)

- [ ] **게재지 확정.** 후보 (PoC·방법론 성격 감안):
  - *Integration, the VLSI Journal* (Elsevier, SCI-E) — 열-인지 물리설계 방법론 적합, PoC 수용적.
  - *IEEE Trans. Components, Packaging and Manufacturing Technology (TCPMT)* (SCI-E) — 써멀비아/패키징 열설계 직결. 단 실단위 보정 요구 가능성 높음.
  - *Microelectronics Journal* (Elsevier, SCI-E) — 스크리닝/프록시 방법론 수용적.
  - 워크숍 트랙: MLCAD / ISPD poster — 빠른 피드백용 대안.
- [ ] **Funding 선언** 기입 (`\section*{Declarations}` TBD 1곳).
- [ ] **공저자 확정** (현재 단독 저자).
- [ ] **특허/게재 순서** — 가족 규율 확인: SFTF 삼부작 출원과의 순서. peak-aware 프록시(식 2)와
  per-zone 분해가 청구항 후보인지 지도교수·산학협력단 검토.
- [ ] **repo 공개 여부** — Declarations의 code availability 약속과 연동. 공개 시
  `_copy_protected_configs.ps1` 계열 제외 목록 재확인.

## P1. 투고 전 권장 (기계적)

- [ ] 상호인용 상태 동기화: `pftf`/`sftf`(PiAM)/`sftfsoft` 게재 상태를 최종 시점 기준으로.
  (현재 sibling PDN PoC는 미인용 — 게재/공개 시점 맞춰 \cite 추가 검토)
- [ ] 실단위 보정 1례: TCPMT급 겨냥 시 example.config의 물성(k_Si=100W/mK 등)으로
  compact 모델 상수를 실단위화한 부록 1절 (PoC 단위 주장은 유지, 환산표만 추가).
- [ ] 벤치 확대: HotSpot 외 플로어플랜 1-2종(공개 칩렛/3D-IC 벤치) + 다른 워크로드 트레이스.
  §5.7의 "레짐 경계 맵 의존" 주장을 지도(map)-스윕 그림으로 승격하면 기여 강화.
- [ ] 그림 폰트/크기 저널 규격 확인 (현재 Segoe UI, 760px 계열).
- [ ] cover letter 초안: "정직한 2-레짐 규명 + regret 운용 지표"를 프레이밍 축으로.

## P2. 현재 상태 요약 (2026-07-18)

- 영문 원고 v0.3: 전 섹션 + Declarations + 재현 부록. 강건성 4종(§5.6-5.9) 포함.
- 검증 스택 4층: Dirichlet 스탠드인 → 컴팩트(유한 비아) → 과도(gcc 100프레임) → 3D 적층(EV6_3D).
- 실칩 2종: EV6/gcc(2D), EV6_3D(3층). 데이터 동봉(`data/hotspot_ev6{,_3d}/`, 공식 repo 사본).
- 테스트 34개, 수치 전량 단일 스크립트 재현(~5분).
