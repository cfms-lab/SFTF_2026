# SFTF Phase-C 벤치 판정 (실 diff_sftf 손실)

작성일: 2026-07-11 · 스크립트: `scripts/bench_gate_mesh_invariance.py` (K=16, noise=0.10)

## 결론 한 줄
near-t 문제의 실제 해결 지렛대는 **patch가 아니라 STE(hard-forward)** 다. `gate_mode="ste_smooth"`(또는 `ste`)가
임계각 랭킹 누출을 **정확히 0**으로 만든다. patch aggregation은 **무회귀 추가 이득**(S가 충분한 곳 remesh 3~10×↓).

## 핵심 증거 — `hard-fid` = |S − S_hard| (forward 랭킹 충실도)

| 씬 | 참(S_hard) | sigmoid | smoothstep | smootherstep | **ste / ste_smooth / patch+ste\*** |
|---|--:|--:|--:|--:|--:|
| plate @ t−0.03 (아래, 지지 불필요) | 0 | **0.079 (가짜지지)** | 0.025 | 0.014 | **0** |
| plate @ t+0.03 (위, 지지 필요) | 0.213 | **0.327 (33%↓ 과소)** | 0.104 | 0.058 | **0** |
| wedge | 0.298 | 0.025 | 0 | 0 | **0** |

- sigmoid의 near-t 양방향 오차(아래 +0.079 가짜지지, 위 −0.327 과소평가)가 정확히 핸드오프의
  *"임계각 아래 sub-threshold 면적이 꼬리로 누적 → 랭킹 왜곡"* 이다. **hard-forward(STE)가 이를 0으로 제거.**
- compact 게이트(smoothstep/smootherstep)는 누출을 줄이지만(0.079→0.014) 없애지 못함.

## remesh 안정성 (절대편차 |ΔS|) — 미묘함
- **위-t 평판(S 충분)**: patch가 진짜 효과 — patch+smootherstep 1.2e-2 vs smootherstep 0.11 (**~10×↓**),
  patch+ste 4.3e-2 vs ste 0.14 (**~3×↓**). 격리 벤치 예측대로.
- **아래-t 평판(S≈0)**: 상대지표 폭발(2.65/5.49)은 ÷0 아티팩트 — 절대편차론 sigmoid가 오히려 낮음(부드러워서).
  단 sigmoid는 누출(hard-fid 0.079)을 대가로 함. patch+ste가 절대 remesh(0.063)와 누출 0을 동시 달성.
- **wedge(S 큼)**: 비-게이트 항(overhang softplus·drop eta·면적)이 remesh 민감도를 지배 → 게이트별 spread ~10%.
  즉 full 손실에서 게이트는 remesh 민감도의 주범이 아니다(격리 벤치는 게이트만 떼어 과대평가했음).

## grad-cos — 이 씬들에선 판별 불가
hard 제외 전 전략 균일 ±1(scene2의 −1은 hard-FD 참조 부호 아티팩트, 전략 무관). hard 목적함수 gradient가
계단이라 유한차분이 조건 나쁨. **gradient 품질은 실제 shape-opt 수렴으로 측정해야 함**(이 지표로는 안 됨).
→ 그래서 `ste`와 `ste_smooth`가 여기선 모든 행 동일; ste_smooth의 이론적 gradient 정렬 이점은 shape-opt에서만.

## 권고
1. **기본 후보를 `ste_smooth`(hard-forward)로** — near-t 랭킹 누출 0. 이번 조사의 직접 해답.
2. **patch aggregation은 켜두기**(무회귀, tessellation 다양할 때 remesh 이득). `ste`와 `ste_smooth`는 실질 동일 → 공짜인 ste_smooth 선택.
3. **다음 단계 = 핸드오프의 진짜 성공기준**: 실 기계부품 메쉬에서 **Cura/hard 대비 Spearman 랭킹**.
   hard-fid가 랭킹 충실도의 국소 대리지표였고, STE가 그걸 0으로 만든다는 게 확인됐으니, 실 메쉬 세트에서
   sigmoid vs ste_smooth의 Spearman을 직접 재면 결정적. (합성 벤치는 메커니즘을 확증했음.)

## 벤치 아티팩트 수정(재실행용)
- subdiv/remesh 열을 **절대편차 |ΔS|**로 변경(÷S≈0 폭발 제거).
- hard-FD step h=1e-2로 상향 + grad-cos 비판별성 주석. (재실행 시 표가 깨끗해짐.)
