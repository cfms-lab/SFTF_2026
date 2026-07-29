# SFTF gate 랭킹 벤치 판정 — 실제 Cura 지표 (g5test 21 메쉬)

작성일: 2026-07-11 · 스크립트: `scripts/bench_gate_ranking.py` (48 dirs, cached real Cura, θc=60)

## 결론 두 줄
1. **가설 확증(실 지표)**: mechanical 취약 케이스(fail-4)에서 sigmoid +0.82 → 컴팩트 게이트 +0.90 → **hard/ste +0.93**.
   `ste_smooth`(hard-forward)가 hard 수준 랭킹을 완전 회복하고, `smootherstep`이 대부분 회복. sigmoid가 명확히 최악.
2. **patch aggregation은 랭킹 도구로 기각**: clean 평면 mechanical엔 무이득(+0.000), **곡면/organic엔 −0.22 심각 악화**(union-find가 곡면을 leak해 과병합). patch는 clean 평면부품 remesh-robustness 전용.

## 핵심 표 — Spearman vs 실 Cura 지지질량 (subset 평균)

| subset | sigmoid\|f | smoothstep\|f | **smoother\|f** | **hard\|f (=ste)** |
|---|--:|--:|--:|--:|
| **L_SFTF fail-4** (cyl/cone/D5/D9) | +0.82 | +0.90 | **+0.90** | **+0.93** |
| MECHANICAL A/B/D (13) | +0.66 | +0.67 | +0.68 | +0.65 |
| organic C (8) | +0.89 | +0.89 | +0.89 | +0.88 |
| MEAN (21) | +0.75 | +0.75 | +0.76 | +0.74 |

- **fail-4가 시그널**: sigmoid +0.82 vs hard/ste **+0.93**(+0.11), smoother **+0.90**(+0.08). cone·D5에서 극적
  (cone sig+0.81→smoother+0.93; D5 sig+0.78→+0.93). **핸드오프의 "mechanical에서 sigmoid가 랭킹 손해"를 실 Cura로 재확인, 그리고 hard-forward/컴팩트가 그걸 고침.**
- **MECHANICAL 전체 평균은 밋밋**(~0.66, 게이트 무차별): cube(F=12 퇴화)·sphere(회전 평탄)·hollow_box(내부 공동)·
  u_bracket(hard+0.48<sig+0.68)·torus(hard+0.82<sig+0.97) 등 ill-posed 케이스가 평균을 희석·역전. 논문 각주 c가
  헤드라인에서 cube/sphere/hollow_box를 뺀 이유와 일치. **신호는 fail-4에 있다.**
- organic은 게이트 무차별(~0.89) — 법선이 broadband라 blur가 평균화됨(핸드오프 진단대로).

## patch − face 델타 (patch 집계의 랭킹 이득)

| subset | hard | sigmoid | smoothstep | smoother |
|---|--:|--:|--:|--:|
| MECHANICAL A/B/D | **+0.000** | +0.000 | +0.000 | +0.000 |
| L_SFTF fail-4 | +0.000 | +0.000 | +0.000 | +0.000 |
| organic C | **−0.223** | −0.253 | −0.204 | −0.204 |
| MEAN | −0.085 | −0.096 | −0.078 | −0.078 |

- **clean 평면 mechanical = 정확히 +0.000** — 평면은 face 법선이 이미 하나라 patch와 동일(예측 확증).
- **organic = −0.20~−0.25 심각 악화**. 원인은 구현 결함: coplanar union-find가 **인접 쌍 tolerance만** 보므로
  smooth 곡면을 전이적으로 leak-병합(liver 19416F→648P 38×, kidney 12394→324 38×, lucy 49999→16494).
  곡면의 법선 변화(지지 신호)를 평균으로 뭉개 랭킹 붕괴.

## 실행 시사점 (수정된 권고)
1. **기본 게이트 = `ste_smooth`** — 실 Cura fail-4에서 hard 수준 랭킹(+0.93) + 컴팩트 gradient. 이번 조사의 최종 답.
   순수 forward-미분값이 필요(STE 불가)하면 **`smootherstep`(+0.90)**이 차선.
2. **patch aggregation은 기본 OFF**. clean 평면부품의 remesh-robustness(Phase C)에서만, 그리고 반드시:
   - normal-tol을 매우 좁게 + **patch당 고정 기준평면 전역검사**(현재 쌍별 검사는 곡면 leak) — organic/fillet엔 금지.
   - 즉 현재 `coplanar_patch_ids`는 **진짜 평면 메쉬에서만 안전**. 곡면 leak 방지엔 seed-plane 방식 재구현 필요(후순위).
3. **C2 vs C1**: 랭킹 동률(둘 다 +0.90) → smootherstep의 이득은 랭킹이 아닌 gradient 매끄러움(shape-opt). C2 채택 근거는 최적화 쪽.

## 종합 (전체 조사 결론)
- 문제(임계각 근처 mechanical 랭킹 열화)의 원인은 **sigmoid 꼬리 = forward 충실도**였고, 실 Cura에서 확증됨(fail-4 −0.11).
- 해결책은 **hard-forward(STE) 우선, 컴팩트 게이트 차선** — 둘 다 sigmoid를 실 지표에서 이김. `ste_smooth`가 최적(랭킹 hard + gradient 컴팩트).
- **patch aggregation은 clean 랭킹엔 무익·곡면엔 유해** — 초기 격리벤치의 patch 낙관은 실 메쉬에서 과대평가였음(정직한 정정).
  patch의 유일한 정당 용도는 clean 평면부품의 tessellation robustness이며, 그마저 구현을 seed-plane으로 고쳐야 안전.
