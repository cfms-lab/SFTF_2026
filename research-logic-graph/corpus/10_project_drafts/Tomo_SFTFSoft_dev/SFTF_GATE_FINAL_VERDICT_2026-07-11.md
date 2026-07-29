# SFTF 임계각 게이트 — 최종 판정 (softmax/sigmoid 대체 검토 종결)

작성일: 2026-07-11 · 대상: `Tomo_SFTFSoft_dev`
질문: "SFTFsoft의 연속 게이트가 기계부품 임계각 근처에서 구분이 모호 → STE 꼼수로 개선 → softmax 같은 걸 다른 걸로 바꿀 수 있나?"

## 0. 한 줄 결론 (tight-budget 실험 후 정정판)
답의 핵심은 특정 함수가 아니라 **forward/backward 분리(STE)** 다: **forward=hard**가 near-t 랭킹 누출을 0으로 없앤다(실 Cura fail-4 +0.93 vs sigmoid +0.82). backward는 **trade-off** — 컴팩트(smootherstep′)는 밴드 내 정렬이 더 좋지만 밴드 밖 gradient=0이라 cold-start에서 정체하고, 넓은(sigmoid′)은 정렬은 낮아도 어디서든 도달한다. **shape-opt 안전 기본은 `ste`(hard-forward + sigmoid backward)** — 랭킹 최적 + 견고한 gradient(논문 기존 기본값이 옳았음). `ste_smooth`는 순수 우위가 아니라 근-해 정밀화/annealing용 옵션. patch aggregation은 (seed-plane 수정 후) 무해하나 랭킹 이득 0 → remesh-robustness 전용.

## 1. "softmax 같은 함수"는 셋 — 진단은 게이트
1. 임계각 게이트 `sigmoid(k(x−t))` — 실은 로지스틱(soft Heaviside). **진단된 주원인.**
2. receiver 배정 `π=affinity/Σ` — 진짜 softmax 자리지만 진단 원인 아님(범위 밖).
3. softplus overhang / soft-min plate — soft-ReLU/min.

## 2. 증거 (4개 벤치)

### (i) 격리 게이트 벤치 (`sftf_gate_bench.py`, `bench_gate_mesh_invariance.py`)
- sigmoid 꼬리 누출이 compact 게이트의 ~3–4배. 그러나 compact "함수 모양"만으로 near-t가 안 풀림 —
  임계각 근처 normal-noise Jensen 갭은 compact가 오히려 더 큼. 근본책은 (A)집계-후-게이트, (B)hard-forward.

### (ii) 실 Cura 랭킹 — 격리 skeleton (`bench_gate_ranking.py`, 21 메쉬, seed-plane 확정본)
| subset | sigmoid\|f | smoother\|f | **hard\|f (=ste=ste_smooth)** |
|---|--:|--:|--:|
| **L_SFTF fail-4** | +0.82 | +0.90 | **+0.93** |
| MECHANICAL A/B/D | +0.66 | +0.68 | +0.65 |
| organic C | +0.89 | +0.89 | +0.88 |
- **fail-4(cyl/cone/D5/D9)에서 hard/ste +0.93 > smoother +0.90 > sigmoid +0.82** — 게이트 효과가 실 Cura에서 확증.
- **patch−face 델타(seed-plane 수정 후)**: 전 subset ~0 (organic −0.003, 이전 union-find −0.22 붕괴 해소). patch 무해·중립.

### (iii) full 미분가능 predictor 랭킹 (`predict_ste_gate.py`, fast-S 검증 max|diff|=2.8e-17)
| col | MEAN | fail-4 |
|---|--:|--:|
| S_g_hard(순수) | +0.74 | +0.925 |
| S_g (sigmoid) | +0.67 | +0.78 |
| S_g_ste | +0.65 | +0.83 |
| S_g_ste_smooth | +0.65 | +0.83 |
| S_g_smoother | +0.66 | +0.82 |
- `S_g_ste_smooth ≡ S_g_ste`(paired diff 정확히 0) — **forward 동일 검증** ✓.
- **full predictor에선 게이트가 2차 효과**: ste−sigmoid=−0.018(p=.05), ste−hard=−0.085(p=5e-6).
  랭킹을 깎는 진짜 주범은 게이트가 아니라 **softplus overhang + soft-min plate 소프트니스**(D9 −0.29). 게이트 이득은 blur 케이스(cyl/cone/D5)에 국소.
- 시사: **논문엔 게이트 효과를 격리 skeleton(ii)으로 보여야 깨끗**; full predictor 평균은 다른 소프트 항이 희석.

### (iv) shape-opt gradient 품질 (`bench_gate_shapeopt.py`, 실 mechanical, S-only 손실)
gradient 정렬 `cos(grad_soft, grad_hard-FD)` — **backward가 정렬을 결정**:
| mesh | sigmoid | ste | **ste_smooth** | smootherstep |
|---|--:|--:|--:|--:|
| cylinder | +0.34 | +0.34 | **+0.51** | +0.50 |
| cone | +0.21 | +0.21 | **+0.30** | +0.31 |
| D5 | +0.19 | +0.22 | **+0.41** | +0.41 |
| u_bracket | +0.41 | +0.53 | **+0.76** | +0.75 |
| pipe_elbow | +0.43 | +0.44 | **+0.61** | +0.61 |
| **평균** | **0.32** | **0.35** | **0.52** | **0.52** |
- sigmoid·ste(sigmoid′ backward) 낮게 뭉치고, ste_smooth·smootherstep(compact backward) 높게 뭉침.
- **ste와 ste_smooth는 forward 동일이므로 이 차이는 순수 backward** — ste_smooth가 모든 메쉬에서 ste를 이김(평균 +0.17, +49%).
- 랭킹(ii,iii)이 못 보던 ste vs ste_smooth 차이가 여기서 드러남 → **ste_smooth 채택 근거**.

**(B) orientation-opt 최종 도달 hard-S (0=전역최소):**
| 예산 | sigmoid | ste | ste_smooth | smootherstep |
|---|--:|--:|--:|--:|
| 16 start×120 step (충분) | −0.001 | −0.001 | −0.001 | −0.001 |
| **1 start×20 step (tight)** | **0.247** | **0.247** | **0.272** | **0.272** |
- 충분한 예산: 네 게이트 모두 전역최소 도달(ceiling, 무차별).
- **tight 예산에선 예상이 반증됨** — ste_smooth(0.272)가 sigmoid/ste(0.247)보다 **오히려 나쁨**. 판별 케이스 D5: sigmoid/ste −0.005 vs ste_smooth 0.117(갇힘).
- **원인(중요)**: 컴팩트 backward는 밴드 `[t−d,t+d]` 밖에서 gradient가 **정확히 0** → cold/far start에서 신호가 없어 정체. sigmoid/ste의 넓은 꼬리는 어디서든 하강 방향 제공 → 먼 시작에서도 도달.
- **∴ 컴팩트 backward는 양날의 검**: 밴드 내 정렬↑(A) but 밴드 밖 도달불가(B-tight). "ste_smooth가 gradient 축을 지배"는 **부분적으로 틀림** — 정렬은 이기나 cold-start 수렴은 짐.

## 3. 최종 권고 (정정판)
1. **예측/랭킹 기본 = hard-forward(STE 계열).** forward=hard가 near-t 누출 0(fail-4 +0.93 vs +0.82). ste·ste_smooth 랭킹 동일.
2. **shape-opt 기본 = `ste`(hard-forward + sigmoid backward).** 넓은 backward가 cold-start·tight-budget에서 견고(tight (B) 0.247 vs ste_smooth 0.272). 논문 기존 ste 기본값이 옳았음.
3. **`ste_smooth`는 순수 개선 아님 — 조건부 옵션.** 밴드 내 gradient 정렬은 최고(A: 0.52)지만 밴드 밖 gradient=0으로 cold-start 정체. 쓰려면 **broad→compact annealing**(sigmoid/넓은 밴드로 시작→`gate_band` 축소)로 도달성과 정밀도를 겸함. `smootherstep`(순수 C2)은 forward-미분 필요 시 랭킹 차선(+0.90).
4. **patch aggregation 기본 OFF.** seed-plane 수정으로 무해하나 clean 랭킹 이득 0 → clean 평면부품 remesh-robustness 전용.
5. **논문화**: 게이트 효과는 격리 skeleton(ii)으로 제시. full predictor의 softplus/soft-min 소프트니스 비용은 별도 논점. STE류는 "미분가능 hard gate"가 아니라 **hard-forward surrogate-gradient estimator**로 명기. 컴팩트 backward의 cold-start 정체(B-tight)는 compact-support 게이트의 알려진 trade-off로 기술.

## 4. 구현 상태 (모두 커밋됨)
- `diff_sftf.py`: gate_mode `smootherstep`·`ste_smooth` 추가, `coplanar_patch_ids`(seed-plane)·`patch_aggregated_gate`, `gate_aggregate`. 회귀 0.
- `tests/test_gate_modes.py`: 신규 테스트(C2·ste_smooth·patch·crease·full-loss) — torch 12 passed, numpy self-test 18/18.
- 벤치: `bench_gate_ranking.py`(seed-plane), `bench_gate_mesh_invariance.py`, `bench_gate_shapeopt.py`(S-only 가속), `predict_ste_gate.py`(fast-S 가속, 열 확장), `sftf_gate_bench.py`/`_probe.py`.
- 판정 노트: `SFTF_GATE_REVIEW`/`_BENCH_RESULTS`/`_PHASE_C_VERDICT`/`_RANKING_VERDICT`/`_IMPL_NOTES`/`_FOLLOWUP`/본 문서.

### 결론
"softmax/sigmoid를 다른 함수로 바꾼다"는 프레임의 진짜 답은 **forward/backward 분리(STE)** 다. forward=hard가 near-t 랭킹을 고치는 건 4개 벤치로 확고하다. 반면 backward는 trade-off이며, tight-budget 실험이 이를 결정적으로 보였다 — 컴팩트 backward(ste_smooth)는 정렬은 좋으나 밴드 밖 도달불가로 cold-start에서 짐. 따라서 **랭킹은 hard-forward, shape-opt 기본은 `ste`(넓은 backward)**, `ste_smooth`는 annealing과 함께 쓰는 조건부 옵션이 정직한 최종 처방이다. (초기 "ste_smooth 지배" 주장은 tight-budget에서 반증되어 본 정정판으로 대체함.)
