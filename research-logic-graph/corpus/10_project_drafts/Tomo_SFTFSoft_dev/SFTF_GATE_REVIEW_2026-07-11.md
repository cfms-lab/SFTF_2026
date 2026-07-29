# SFTF gate / softmax 대체 가능성 검토

작성일: 2026-07-11
대상: `D:\__SFTF_Projects(2026)\Tomo_SFTFSoft_dev`
근거 코드: `python/src/SFTF_Derivative/diff_sftf.py`, `tests/test_gate_modes.py`, `CODEX_HANDOFF_SFTF_GATE.md`

---

## 0. 요약 (TL;DR)

- 지금 "softmax 같은 함수"는 **하나가 아니라 셋**이다. 서로 다른 실패모드를 가지므로 뭉뚱그리면 안 된다.
  1. **임계각 gate** `g(x)=sigmoid(k(x−t))` — *진단된 주원인*. 실은 softmax가 아니라 **로지스틱(soft Heaviside)**.
  2. **receiver 배정** `π = affinity / (Σaffinity + bed)` — 이게 진짜 **softmax 유사(정규화 배정)**. 핸드오프가 명시적으로 *범위 밖*.
  3. **softplus / logsumexp** — overhang `max(0,·)`, plate soft-min. soft-ReLU/soft-min 계열.
- 핸드오프의 진단(문제는 "softmax 하나"가 아니라 **sigmoid gate의 긴 꼬리 + triangle별 합산**)은 **옳다**. 그리고 수치로 재확인된다.
- **핵심 반전(수치 근거)**: 더 부드러운 1-D 게이트(smootherstep 등 compact support)는 *먼 영역의 꼬리 누출*은 ~3× 줄이지만, **정작 임계각 바로 근처(문제의 그 영역)에서는 normal-noise에 대해 sigmoid보다 더 민감**해질 수 있다. 밴드 안 곡률이 급해 Jensen 갭 `E[g(x₀+noise)]−g(x₀)`이 커지기 때문.
- 따라서 "softmax/sigmoid보다 근본적인 함수"를 찾는 프레임은 **부분적으로 잘못**이다. 진짜 지렛대는 함수 모양이 아니라:
  - **(A) 게이트 전에 집계하라 (patch aggregation)** — 임계각 근처 tessellation/normal-noise 민감도의 *근본책*. 게이트 모양과 거의 독립.
  - **(B) forward와 backward를 분리하라 (STE 계열)** — 보고값을 hard와 동일(누출 0)로 두고 gradient만 surrogate. STE는 "꼼수"가 아니라 **hard-forward surrogate-gradient estimator**라는 정식 기법.
  - **(C) receiver softmax를 정말 바꾸고 싶다면** → **sparsemax / α-entmax** (희소·미분가능·꼬리 없음)가 문헌의 정답. 단 이건 진단된 원인이 아니라 별개 지렛대.
- 1-D 게이트 함수 교체(smootherstep)는 *2차 knob*으로 유지·병행할 가치는 있으나, 단독으로 임계각 문제를 풀지는 못한다.

---

## 1. 현재 구조 — 세 개의 soft 메커니즘 분리

`diff_sftf.py` 기준 정확한 위치:

**① 임계각 gate** (`overhang_gate`, L210–233). `x=-(m·n)`, `t=sin(θc)`. 모드: `sigmoid` (기본, L221), `smoothstep`(C1 compact, L222–225), `ste`(hard forward + sigmoid backward, L226–229), `hard`(L230). 두 곳에서 호출: overhang 곱(L368)과 supvol 게이트(L524).

**② receiver 배정** (`soft_receiver_assignment`, L326–439). affinity = `below_gate · lateral · recv_up · near` (모두 sigmoid/가우시안 커널의 곱, L426–431), 그 뒤 `π = affinity/(Σaffinity + bed_bias)` (L436–438). **이게 softmax 자리** — 정확히는 exp(logit) 정규화가 아니라 *커널곱을 후보+bed로 합-정규화*한 categorical.

**③ soft-ReLU/soft-min**: `softplus(-m·n)` overhang(L366), `softplus(-rayleigh)`(L511), plate `logsumexp` soft-min(L492).

> 손실은 `(overhang · areas · …)` 형태(L489,496,531)라 **triangle 면적을 이미 반영**한다. 그래서 "평면을 몇 개 triangle로 쪼갰나(단순 개수)"는 자동 상쇄된다. 남는 민감도는 **normal noise**(쪼갤 때 각 triangle 법선이 흔들림)에서 온다 — 아래 §3.

핸드오프의 진단(L17–19)과 완전히 일치: 원인은 **sigmoid의 무한 꼬리 × 임계각 근처 면적 누적**이지 receiver softmax가 아니다.

---

## 2. 핸드오프 3제안 평가 — 각각 *다른* 실패모드를 공격한다

| 제안 | 공격하는 실패모드 | 평가 |
|---|---|---|
| **① C2 smootherstep** (quintic, compact) | 먼 영역 **꼬리 누출**(angular leakage) | 타당. sigmoid 대비 꼬리 ~3–4×↓, C1 smoothstep 대비 경계 2차 0 → remesh에 살짝 더 매끈. **단 임계각 *바로* 근처는 개선 안 됨(§3).** |
| **② degree-band** (`θc_deg`, `band_deg`) | band 폭의 **해석성/일관성** | 순수 개선(부작용 없음). `sin(θc±δθ)`로 경계 계산은 slicer convention과 정합. 꼭 하자. 정확도엔 중립. |
| **③ coplanar-patch aggregation** | 임계각 근처 **tessellation/normal-noise 민감도** | **가장 근본적.** §3에서 수치로 확인 — 이게 near-t 문제의 실제 해법. 게이트 모양과 거의 독립. |

즉 ①과 ③은 **직교하는 다른 문제**를 푼다. ①만으로 near-t 문제가 풀린다고 기대하면 안 된다.

---

## 3. 수치 근거 (재현 스크립트 `sftf_gate_probe.py`)

θc=60°, t=sin60=0.866, sigmoid k=24, compact band d=0.05.

### (1) 꼬리 누출 — 먼 영역
| gate | FP 누출(<t의 헛지지) | FN 누락(>t) | grad 지지폭(x단위) |
|---|--:|--:|--:|
| sigmoid | 2.89e-2 | 2.72e-2 | **0.48** (≈21°) |
| smoothstep (C1) | 9.38e-3 | 9.37e-3 | 0.10 |
| **smootherstep (C2)** | **7.81e-3** | 7.81e-3 | 0.098 |
| raised-cos (C1) | 9.09e-3 | 9.08e-3 | 0.10 |
| hard | 0 | 0 | 0 |

→ compact support가 꼬리를 ~3–4× 줄인다. smootherstep이 smoothstep보다 약간 더 낫다(7.8 vs 9.4e-3). 게이트 gradient 지지폭도 sigmoid는 0.48(과도) vs compact 0.10(밴드).

### (2) normal-noise Jensen 갭 — *임계각 근처*가 핵심
평판 patch(총면적 1)를 N=2000 triangle로 remesh, 법선 잡음 sd(=x공간, 0.02≈2.5°, 0.06≈7°). `S_tri=ΣAᵢg(xᵢ)` vs 참값 `A·g(x₀)`의 편차:

| x₀−t | noise | sigmoid | smoothstep | smootherstep | **patch-agg** |
|--:|--:|--:|--:|--:|--:|
| −0.10 | 0.02 | 6.4e-3 | 3.5e-5 | 1.1e-5 | **0** |
| −0.03 | 0.02 | **8.4e-3** | 6.2e-2 | 8.3e-2 | **7e-4** |
| −0.03 | 0.06 | **4.2e-2** | 2.1e-1 | 2.5e-1 | **3.5e-3** |
| +0.03 | 0.02 | **8.8e-3** | 6.2e-2 | 8.3e-2 | **1.2e-3** |
| +0.03 | 0.06 | **3.8e-2** | 2.1e-1 | 2.5e-1 | **1.1e-2** |
| +0.10 | 0.02 | 6.1e-3 | 6.3e-5 | 2.5e-5 | **0** |

**해석 (중요):**
- **먼 영역**(±0.10): compact가 압도적(잡음에 거의 불변). sigmoid는 꼬리 때문에 잔차.
- **임계각 근처**(±0.03, 바로 그 문제 영역): **compact 게이트가 sigmoid보다 5–10× 더 민감**해진다. 밴드 안에서 곡률이 급해 `E[g(x₀+ε)]≠g(x₀)`(Jensen) 갭이 커지기 때문. smootherstep은 곡률이 더 급해 smoothstep보다도 살짝 나쁨.
- **patch-agg**(법선을 면적가중 평균해 게이트를 *한 번만* 평가)만 전 구간에서 강건. near-t에서도 잡음 sd 0.06에 편차 ~1e-2로 다른 방식의 수배~수십배 우수(x₀=t 정확점의 잔차는 유한표본 평균 drift 아티팩트).

**결론**: "임계각 근처 구분 모호"의 근본 원인은 게이트의 *꼬리*가 아니라 **밴드 안 비선형성 × 법선잡음의 Jensen 갭**이고, 이는 **더 매끄러운 함수로 악화**된다. 유일한 근본책은 **집계 후 게이트(patch aggregation)**.

---

## 4. "softmax/sigmoid보다 근본적" 후보 — 우선순위별

### A. 1-D 게이트 함수 교체 (compact-support family) — *2차 knob, 근본책 아님*
smootherstep(C2), raised-cosine(C1), 그 외 유한지지 다항. **공통 필요조건은 "compact support(유한 밴드)"** — 무한 꼬리 제거가 핵심이고 특정 함수의 우열은 미미(§3-1). 유지·병행하되 이걸로 near-t가 풀린다고 보지 말 것. 핸드오프 Phase A대로 `smootherstep` 추가는 찬성(저위험·소이득).

### B. Aggregate-before-gate (patch aggregation) — **near-t의 근본책**
`A_P=ΣAᵢ`, `m_P=normalize(ΣAᵢmᵢ)`, `E_P=A_P·g(-(m_P·n))`. 게이트를 patch당 *한 번* 평가 → Jensen 갭 제거(§3-2). 핸드오프 제안③과 동일. 주의(핸드오프대로): patch membership은 `torch.no_grad()`로 사전고정, sharp crease 넘어 병합 금지, adjacency+법선각+평면offset tolerance 병용, 우선 critical-angle support term에만 적용. **가장 먼저 프로토타입할 가치.**

### C. Hard-forward surrogate-gradient (STE 계열) 정식화 — *"꼼수" 아님*
현재 `ste`(L226–229)는 forward=hard(누출 0), backward=sigmoid′. 이는 딥러닝의 정식 estimator(Bengio 2013 straight-through; 양자화/이진 네트워크 표준). 논문엔 반드시 **"미분가능 hard gate"가 아니라 hard-forward surrogate-gradient estimator**로 명기(핸드오프 L185와 일치).
- **자연스러운 합성(신규 제안)**: STE의 *backward를 sigmoid′ 대신 compact-support(smootherstep′)*로 바꾸면 — forward는 hard(누출 0), gradient는 유한 지지(먼 영역에서 정확히 0, 밴드에서만 신호). "hard 랭킹 + 국소 gradient"를 한 몸으로. `ste_smooth` 모드로 추가 실험 권장.
- 단점(정직): forward가 불연속이므로 **finite-difference 검증 시 진짜 forward 미분은 없음**. shape-opt에는 강하나 forward 민감도 해석엔 부적합.

### D. Annealing / graduated non-convexity — *수렴 정확도용*
sigmoid k(또는 band d)를 최적화 진행에 따라 soft→sharp로 annealing(코드에 anneal 훅 존재, L41,588). 초반엔 넓은 gradient로 전역 탐색, 후반엔 hard에 수렴해 *누적오차 소멸*. B(patch)와 직교·병용 가능. 저위험.

### E. receiver softmax 자체 교체 — *별개 지렛대(핸드오프 범위 밖)*
정말 "softmax를 다른 걸로"라면 문헌의 정답은 **sparsemax**(Martins & Astudillo 2016) 또는 **α-entmax**(Peters 2019): softmax와 달리 **정확한 0을 출력(희소)** → 무관한 receiver의 꼬리 기여를 원천 제거, 미분가능. 현재 `π`는 exp(logit)이 아니라 커널곱의 합-정규화(L436)이므로, log-affinity를 logit으로 두고 entmax를 씌우거나, 이미 있는 top-k(L390,410)를 확률적으로 sparse화하는 방향. **단 §1대로 receiver routing은 진단된 원인이 아님** → 우선순위 낮음, near-t 해결 후 별도 검토.

### (참고) 근본적으로 다른 것을 원한다면
- **erf/Gaussian-CDF, algebraic sigmoid**(x/(1+|x|)) 등은 여전히 무한 꼬리 → 이득 없음(오히려 나쁨). 후보에서 제외.
- 게이트를 아예 없애고 **면적을 각도분포로 해석적 적분**하는 방향은 patch aggregation의 연속 극한과 동치 — B로 수렴.

---

## 5. 권장 실험 순서 (핸드오프와 정합, 우선순위 재배열)

1. **degree-band(제안②)** 먼저 — 부작용 0, 해석성↑. (핸드오프 Phase A와 병합)
2. **smootherstep(제안①/A)** 추가 — 저위험, 꼬리 누출 소이득. `tests/test_gate_modes.py`에 0/1 정확·중앙 0.5·경계 1·2차 미분 0(float64) 테스트. 기존 4모드 tolerance 내 불변 확인.
3. **mesh-invariance 벤치(Phase C)** — *반드시 normal-noise/remesh를 변수로*. §3-2가 예측: compact 단독은 near-t에서 개선 미미하거나 악화. 이 데이터가 patch 필요성의 증거가 됨.
4. **patch aggregation(제안③/B)** 프로토타입 — near-t의 실제 해법. subdivision-invariance를 §3-2 지표로 측정.
5. (선택) **ste_smooth**(STE + smootherstep backward, C) 및 **annealing**(D) 병행 실험.
6. (별도) receiver **entmax/sparsemax**(E)는 near-t 해결 후 독립 과제.

## 6. 성공기준 보강 (핸드오프 §성공기준에 추가)
- near-t(±3°) 영역에서 **normal-noise sd별 score 편차**를 게이트별로 표로: compact 단독 vs +patch. patch가 near-t 편차를 수배↓ 보이면 근본책 입증.
- STE류는 "differentiability 비용"을 finite-difference cosine으로 정량(핸드오프대로).

## 7. 위험 / 주의
- **patch membership 미분불가**: 최적화 중 topology 변하면 cluster가 바뀜 → 반드시 사전고정(`no_grad`) + crease 보존. 형상이 크게 변하는 shape-opt에선 주기적 재클러스터(비미분 스텝)로 절충.
- **smootherstep가 near-t를 악화**시킬 수 있음(§3-2) → 벤치에서 sigmoid 대비 near-t 편차를 반드시 확인하고 문구를 "먼 영역 꼬리 개선"으로 한정.
- 기본 `gate_mode`는 증거 확보 전 변경 금지(핸드오프 §범위밖 준수).
- 논문 문구: STE=hard-forward surrogate-gradient, smootherstep=piecewise-C2(clamp join 미분 테스트로 뒷받침).

---

### 결론
핸드오프의 방향(compact gate + degree-band + patch)은 옳고, 특히 **patch aggregation이 임계각 문제의 근본책**이다. 반면 "softmax/sigmoid를 더 나은 함수로 교체"라는 프레임은 near-t에서 역효과 가능(§3-2)하므로, **함수 모양보다 (A)집계-후-게이트, (B)hard-forward/surrogate 분리**가 더 근본적 지렛대다. softmax 자체를 바꾸려면 **sparsemax/entmax**가 문헌의 정답이나 진단된 원인이 아니므로 후순위. 즉 "다른 함수"보다 **"게이트를 적용하는 위치(집계)와 forward/backward 분리"**를 먼저 바꾸는 것이 검토 결론이다.
