# SFTF gate 후속 (a)(b)(c) 처리 노트

작성일: 2026-07-11

## (a) 논문 예측 열에 ste_smooth / smootherstep 추가 — `scripts/predict_ste_gate.py`
- `ste_landscape` → 일반 `gate_landscape(..., gate_mode)`로 리팩터(캐시 키 `gate_<mode>_...`), 하위호환 wrapper 유지.
- 열 확장: `S_g`(sigmoid) · `S_g_hard` · `S_g_ste` · **`S_g_ste_smooth`** · **`S_g_smoother`**.
- paired 통계 추가: `smoother vs S_g`, `ste_smooth vs ste`(후자는 forward 동일 → ~0이어야 함, 검증열).
- 기대: `S_g_ste_smooth == S_g_ste`(forward=hard 동일), `S_g_smoother`는 컴팩트 C2 forward의 랭킹(fail-4 ~+0.90).
- 실행: `uv run python scripts/predict_ste_gate.py` (기기, torch).

## (b) patch 곡면 leak 수정 — seed-plane 재구현
`diff_sftf.coplanar_patch_ids` 및 `scripts/bench_gate_ranking.py`의 partition을 **union-find → seed-plane region grow**로 교체.
- 문제: 쌍별 union-find는 `A~B, B~C` 전이 병합으로 smooth 곡면을 관통(랭킹 벤치: organic −0.22, liver 19k면→648패치 38× 과병합).
- 수정: 각 patch를 seed에서 자라되 후보를 **이웃이 아니라 seed의 법선·평면**에 검사 → patch가 진짜 coplanar 면으로 국한.
- **검증(컨테이너 실행)**:
  - crease 단위테스트 통과(평면 사각형 병합·crease 분리, ids=[0,0,1]).
  - **곡면 icosphere 1280면 → 468패치(2.7×)** — leak 없음(union-find의 38× 붕괴 대비 국소 cap). `assert npatch>0.15·F` 통과.
- 효과: clean 평면 CAD는 여전히 완전 병합(면 법선 동일), 곡면은 국소만 병합 → organic 랭킹 붕괴 해소 예상.
- 재실행 권장: `uv run python scripts/bench_gate_ranking.py` — organic `patch−face` 델타가 −0.22에서 크게 완화되는지 확인.

## (c) ste_smooth의 gradient 이점 — `scripts/bench_gate_shapeopt.py` (신규)
랭킹 벤치가 못 보는 부분: ste와 ste_smooth는 forward(hard) 동일, **backward만 다름**(sigmoid′ vs 컴팩트 smootherstep′).
두 지표로 실 mechanical 메쉬(fail-4 + u_bracket/pipe_elbow)에서 측정:
- **(A) gradient 정렬**: 랜덤 방향에서 `cos(grad_soft, grad_hard-FD)` — 게이트 gradient가 실제 hard 지지 감소 방향을 가리키나. 격리벤치 예측 compact 0.83 vs sigmoid 0.47.
- **(B) orientation-opt 결과**: multi-start Adam으로 각 게이트의 soft S 최소화 → 도달한 **진짜 hard-S**(0=전역최소 방향). 정렬 좋은 gradient가 더 낮은/신뢰가능한 hard 최적 도달.
- `hard`는 opt에서 제외(gradient 항등 0 → 구동 불가, STE가 필요한 이유).
- 기대: `ste_smooth 정렬 ≥ ste`(순수 backward 차이). 이게 확인되면 "ste보다 ste_smooth" 근거 완성.
- 실행: `uv run python scripts/bench_gate_shapeopt.py --starts 16 --steps 120` (기기, torch).

## 상태
- (a)(b)(c) 코드 작성·구문확인·(b) 로직 컨테이너 검증 완료. torch 필요한 실행은 기기에서.
- 회귀: 기존 gate_mode·기본 경로 불변. `test_gate_modes.py`의 crease/patch 테스트는 seed-plane에서도 통과(로직 동형).
- 재실행 3개(predict_ste, bench_gate_ranking, bench_gate_shapeopt) 결과 붙여주면: (a) 논문표 열 확정,
  (b) organic leak 해소 정량, (c) ste_smooth gradient 우위 확정까지 마무리.
