# SFTF gate 벤치 결과 — patch(A) × ste_smooth(B) 동시 적용

작성일: 2026-07-11 · 스크립트: `scripts/sftf_gate_bench.py` (결정론, seed=1) · 그림: `sftf_gate_bench.png`

## A·B는 동시 적용하는가? — 그렇다 (직교·상보)
- **A = patch aggregation**: 게이트를 *어디에* 적용하나 → 동일평면 triangle을 묶어 면적가중 평균법선으로 **patch당 1회** 평가.
- **B = STE 계열**: forward/backward를 *어떻게 분리*하나 → forward=hard(누출 0), backward=surrogate(`ste_smooth`는 compact smootherstep′).
- 서로 다른 축을 건드리므로 `patch+ste_smooth`로 **겹쳐 쓸 수 있고**, 벤치가 그 조합이 최적임을 보인다.

## 벤치 설계 (핸드오프 Phase C, 진단변수로 격리)
실제 S-항 누적 `S = Σ_i A_i·gate(x_i)`, `x=-(m·n)`, `t=sin θc(60°)`. 합성 기계부품(임계각 ±12° 걸친 14개 평판, 총면적 1)을 동일형상 3-tessellation으로: **coarse**(patch당 1면·정확법선), **subdiv**(K면·정확법선), **remesh**(K면·법선잡음 sd≈7°·랜덤면적분할). receiver routing은 진단원인이 아니라 제외.

## 결과

| strategy | S_coarse | hard-fid↓ | subdiv-inv | **remesh-inv↓** | **grad-cos↑** | sign |
|---|--:|--:|--:|--:|--:|--:|
| hard | 0.5801 | 0.0000 | 0 | 5.97e-2 | n/a | — |
| sigmoid (기존) | 0.5196 | 0.0605 | 0 | 1.00e-2 | 0.472 | 1.00 |
| smoothstep (C1) | 0.5644 | 0.0158 | 0 | 4.51e-2 | 0.734 | 1.00 |
| smoother (C2) | 0.5683 | 0.0118 | 0 | 4.86e-2 | 0.834 | 1.00 |
| ste | 0.5801 | **0.0000** | 0 | 5.97e-2 | 0.472 | 1.00 |
| ste_smooth (B) | 0.5801 | **0.0000** | 0 | 5.97e-2 | **0.834** | 1.00 |
| patch+sigmoid (A) | 0.5196 | 0.0605 | 0 | 2.23e-4 | 0.472 | 1.00 |
| patch+smoother (A) | 0.5683 | 0.0118 | 4e-16 | 1.92e-3 | 0.834 | 1.00 |
| patch+ste (A+B) | 0.5801 | **0.0000** | 0 | **1e-16** | 0.472 | 1.00 |
| **patch+ste_smooth (A+B)** | **0.5801** | **0.0000** | 0 | **1e-16** | **0.834** | 1.00 |

- `hard-fid` = |S_coarse − S_hard| (0 = 완벽 hard 충실도)
- `remesh-inv` = |S_remesh − S_coarse| (0 = 법선잡음/remesh 불변 — **임계각 근처 핵심지표**)
- `grad-cos` = 전략 gradient vs 참 hard finite-diff 방향 코사인 (1 = 최적화 방향 일치)

## 해석 — 세 축이 서로 다른 도구를 원한다
1. **Forward 충실도**: hard-forward만 0 → **STE 계열**(ste/ste_smooth/patch+ste*)이 완벽. sigmoid는 0.06(꼬리 손실)로 최악.
2. **Remesh 불변(near-t)**: **patch aggregation이 1~2+자릿수 붕괴**시킴(sigmoid 1e-2→patch 2e-4, ste 6e-2→patch+ste **1e-16**). 반대로 **compact 단독(smoothstep/smoother)은 sigmoid보다 오히려 나쁨**(4.5e-2 vs 1e-2) — 검토서 §3-2 예측 재확인(밴드 곡률 급→Jensen 갭↑). STE 단독도 forward가 hard라 remesh에 hard만큼 취약(6e-2).
3. **Gradient 정렬**: compact backward(`*_smoother`)가 0.834 vs sigmoid backward 0.472 — 더 국소적이라 hard 하강방향과 잘 맞음.

## 결론
- **어느 하나로는 부족**하다: STE 단독은 remesh 취약(6e-2), patch 단독은 forward 부정확(0.06). **A와 B를 동시에** 써야 세 축이 동시에 해결된다.
- **`patch+ste_smooth`(A+B, compact surrogate)가 전 축 지배**: forward 정확히 hard(누출 0) · remesh 불변 기계정밀도(1e-16) · gradient 정렬 최고(0.834).
- 즉 "더 나은 게이트 함수"가 아니라 **집계-후-게이트(A) + hard-forward/compact-surrogate(B)** 조합이 답이라는 검토 결론이 수치로 확정됨.

## 주의 (정직)
- 이 벤치는 게이트/집계/STE만 격리(receiver routing 제외) — 실 엔진 full-loss(R·P·B·S 결합, receiver π)에서의 shape-opt 최종성능은 별도 검증 필요.
- patch membership은 `no_grad` 사전고정·crease 보존 전제(topology 변하는 shape-opt 중 재클러스터는 비미분 스텝). remesh-inv의 patch 이득은 이 전제 하에서 성립.
- `1e-16`은 부동소수 0(면적가중 평균이 x₀ 복원). 실측 remesh에선 평면성 tolerance에 따라 소폭 증가 가능.
- 다음: `diff_sftf.py`에 `gate_mode="ste_smooth"` + `aggregate="patch"`(no_grad 고정 클러스터)를 실제 구현해 full-loss shape-opt·Cura 지표로 재확인.
