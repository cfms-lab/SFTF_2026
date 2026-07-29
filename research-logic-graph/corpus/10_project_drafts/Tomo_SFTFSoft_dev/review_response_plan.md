# 리뷰 지적 대응 계획

# 2차 리뷰 대응 계획 (2026-07-03)

> 대상: 개정본(15메시 +0.79, 게이트 절제, E3 동일예산 완료 후). 평가는 전반 긍정
> (novelty·핵심결과·자기비판 모두 합격)이며, 지적된 리스크는 3건.

> **실행 상태 (2026-07-04 갱신)**: D1 항목 완료.
> - **G1 완료** — 한국어판 GNN 절(9메시 LOMO, 0.28/0.41/0.13)을 `main_en.tex` 본문
>   Applications 절에 이식, 초록·기여4의 "demonstrated"를 proof-of-concept+수치로
>   캘리브레이션, 부록 중복 GNN 그림 제거(본문 승격). 한국어 초록에도 GNN 수치 추가(lockstep).
> - **R2 완료** — "형상최적화 데모의 한계"(응력·최소두께·조립공차 등 제조성 제약 미포함)
>   독립 문단을 한(각주 포함)·영 양쪽에 추가.
> - **R3 옵션 a 완료** — θ_c 이식성 문단 + 게이트 각 민감도(45/50/55/60°, 15메시,
>   `scripts/sweep_thetac_gate.py`) 문단·그림(`demo_sftf_thetac_sensitivity`)을 한·영에 반영.
>   결과: 평균 Spearman 60°=+0.79, 55°=+0.79, 50°=+0.77, 45°=+0.71 —
>   ±5° 무손실, 15° 어긋나도 게이트 없는 변형(+0.26–0.40)·TomoNV(+0.27)를 크게 상회.
>   60° 값이 tab:cura 헤드라인 +0.79를 정확히 재현(정합성 확인).
> - **DLL** — `_shared_dll` 새 빌드(588,288B, sha 42657da5, commit f2439790 dirty)를
>   프로젝트로 반영. 구 DLL 캐시 대비 mss 순위 보존(Spearman +0.98–1.00), 절대값 3–5%↓.
>   순위상관 기반 결과는 불변, 그램 단위 TomoNV 수치는 G2 배치 때 새 DLL로 재검증 권장.
> - **빌드** — main.pdf / main_en.pdf / main_en_supplementary.pdf 모두 오류·미해결 참조 0.
> - **G2 완료(음성, 정직 기술)** — GNN 평가를 실제 Cura 백분위로 옮기고 게이트 손실
>   ($L_{\mathrm{SFTF}}+S_g$)로 학습(`gnn_selfsupervised.py --eval cura --gate`, 소형 8메쉬
>   A/B+D5, 대형은 leave-one-out 훈련비용으로 정직 제외). 결과: GNN 0.60 vs 무작위 0.40으로
>   **이점 없음**. 단 per-mesh oracle조차 0.43 — 소형 세트가 자기지지 프리미티브 위주라 Cura
>   랜드스케이프가 평평한 테스트베드 한계. **재튜닝 없이** TomoNV 개념증명 유지 + 한·영에
>   Cura 이점 없음·사유를 한 줄 정직 기술.
> - **③ 대칭 텐서 검토 완료** — 대칭 nᵀMn·오버행 이차형식이 비대칭 L_SFTF는 이기나(+0.41 vs
>   +0.26) S_g(+0.79)엔 못 미침. 상류의 기계부품 "+0.51"은 버그 TomoNV v_ss 기준으로 실제
>   Cura에선 불성립. 논문 변경 근거 없음(상세: UPSTREAM_FINDINGS_2026-07-04_RESPONSE.md).
> - **R3 옵션 b 완료(성공)** — 현대 슬라이서 UltiMaker CuraEngine 5.13 standalone 래퍼
>   (`_cura5_slice.py`, 프론트엔드 없이 수식 기본값 설정 명시)로 4메쉬(원환·후크·파이프엘보·
>   Thingi D9)×48방향 재슬라이싱(`transfer_cura5.py`). S_g가 현대 슬라이서 순위를 평균
>   Spearman +0.68로 예측하고, **레거시(15.04)↔현대(5.13) 두 엔진이 +0.90으로 거의 동일**하게
>   순위 매김 → DP103/15.04 검증이 엔진 인공물이 아님을 실측. 한·영 §결과에 "현대 슬라이서로의
>   이식" 문단 추가. **R3 완전 종결**(옵션 a 각도 민감도 + 옵션 b 세대 간 이식).

## 0. 지적 요지와 실태 대조

| # | 지적 | 실태 확인 결과 | 타당성 |
|---|---|---|---|
| R1 | GNN 미완결: 초록·기여4에 "label-free amortized inference demonstrated"인데 본문에 실체 없음 | **영문판만의 문제.** 한국어판 본문에는 실험이 이미 있음(9메시 LOMO, GNN 0.28 vs random 0.41 vs oracle 0.13, `fig:gnn`, 실패 3메시까지 정직 기술). 영문판은 부록 그림 1장뿐 → **lockstep 규칙 위반이 곧 원인** | 전적으로 타당 |
| R2 | 본문 2,129단어 얇음 + shape-opt가 응력·제조성 제약 없는 데모 | 분량은 이미 ~4,300단어로 증량됨(리뷰어가 구판 기준일 가능성). PoC 명시는 서론에 1회뿐 | 부분 타당 |
| R3 | legacy Cura 15.04 + 단일 프로파일(DP103) 일반화 | Future work로만 인정. θ_c가 프로파일 파라미터라는 이식성 논증 부재 | 타당 (이미 인정) |

## 1. R1 — GNN: 2단계 (즉시 이식 → 선택 승격)

### G1. [즉시, ~1시간] 한국어판 GNN 절을 영문 본문에 이식 + 문구 캘리브레이션
- `main.tex` §"신경망(개념증명)" 문단(L907–929)과 `fig:gnn`을 `main_en.tex` 본문
  Applications 절에 동일 구조로 이식(부록 그림은 본문 승격으로 대체). 수치 그대로:
  LOMO 9메시, GNN(1 forward) 백분위 0.28 vs random 0.41 vs oracle 0.13, 6/9 승·3 실패 명기.
- 초록: "label-free amortized inference is **demonstrated**" →
  "**a proof-of-concept** label-free amortized-inference experiment shows a GNN trained
  only on the differentiable loss predicts held-out-mesh directions at mean percentile
  0.28 (random 0.41, per-mesh oracle 0.13)". 기여4도 동일 톤(proof-of-concept + 수치).
- 원칙: 수치가 본문에 있으면 "그 결과 어디 있냐"는 질문 자체가 소멸. "demonstrated"라는
  단어는 수치 없이는 유지 금지.

### G2. [선택 승격, 반나절+배치] GNN 평가를 실제 Cura 지표로 업그레이드
리뷰어의 다음 질문 예상: "GNN 평가가 TomoNV 백분위인데, 본문 스스로 TomoNV를
추정기로 강등하지 않았나." 재료는 전부 있음:
- `scripts/_slicer_cache/*.npz` = 15메시 × 48방향 실제 Cura support-only 질량 → **추가
  슬라이싱 0**으로 GNN 예측 방향의 Cura 백분위·초과질량[g] 산출 가능.
- `scripts/gnn_selfsupervised.py` 수정 3점:
  ① 평가 지표: TomoNV mss 백분위 → Cura 캐시 백분위 + 초과 지지질량[g] (E5 지표 체계와 통일)
  ② 훈련 손실: `SFTFConfig(w_supvol=1.0)` → 본문 승자 조합(L_SFTF + S_g 게이트 항)으로 정합
     ("같은 gated loss가 학습 신호로도 작동" — 논문 서사와 일치)
  ③ 메시 확장: 9(A/B) → C/D그룹 추가(대형 100k는 face-graph 비용 확인, 불가 시 정직 제외)
- 판정: Cura 백분위에서도 random을 유의하게 이기면 본문 표로 승격, 못 이기면 TomoNV
  결과만 유지하고 "Cura 평가에서는 이점이 약함"을 한 줄 정직 기술. **재튜닝 금지.**

## 2. R2 — 본문 분량 / shape-opt PoC

- 분량: 현재 ~4,300단어(구판 2,129 대비 이미 2배). G1 이식 + G2 표가 추가되면 자연 해소.
  리뷰 회신에는 "개정본 기준 X,XXX단어"로 명시.
- shape-opt 한계 명시 강화(30분): 서론 1회 → **한계/Discussion에 독립 문단** 추가 —
  "기하 전용 데모이며 응력·최소두께·조립공차 등 제조성 제약 미포함; density 기반
  topology-opt 제약 문헌(\citep{langelaar2016selfsupp} 등)과의 결합이 후속"임을 이중 명시.
- (선택, 저비용) 최적화 후 메시에 대해 self-intersection·최소 두께 **검사만** 리포트
  (새 최적화 없음, trimesh로 계산만) — "제약은 없지만 결과물이 병리적이지 않음"의 방증.

## 3. R3 — 슬라이서/프로파일 일반화

- 옵션 a [즉시, 권장]: **θ_c 이식성 논증** — S_g의 게이트 각도는 슬라이서 프로파일에서
  읽는 파라미터이며(DP103=60°), 타 프로파일에는 그 프로파일의 overhang angle로 재게이트하면
  된다는 문단 추가. + 게이트 각 민감도(θ_c=45/50/55/60°)로 Spearman 유지 정도 곡선
  (예측자 쪽 재계산만, 슬라이싱 불필요, ~30분).
- 옵션 b [야간 배치, 시간 되면]: 현대 슬라이서 1종(CuraEngine 5.x CLI 또는 PrusaSlicer
  console) × 3–5메시 × 48방향 support 질량 → transfer 상관 표. 성공 시 R3 완전 종결,
  실패(설치/프로파일 이슈) 시 옵션 a로 충분.

## 4. 일정(제안)

| 단계 | 내용 | 소요 |
|---|---|---|
| D1 오전 | G1(영문 본문 이식+초록 캘리브레이션) + R2 한계 문단 + R3 옵션 a 문안 | 반나절 |
| D1 오후 | θ_c 민감도 계산 + (선택) 두께/자기교차 검사 | ~1시간 |
| D1 야간 | G2 배치(GNN 재훈련 LOMO×15) + 옵션 b 슬라이서 배치(가능 시) | 배치 |
| D2 | G2/b 결과 판정·표화, 한·영 lockstep 검증, PDF 재빌드 | 반나절 |

## 5. 하지 않을 것
- GNN 결과가 Cura 지표에서 나쁠 때 이기도록 재튜닝(체리피킹).
- 수치 없는 "demonstrated" 문구 유지.
- 한국어판만 고치고 영문판 방치(이번 R1의 근본 원인이 lockstep 위반).

---

# 1차 리뷰 지적 대응 계획 (2026-07-02)

> 대상: main_en.tex (PiAM 투고본). 수치는 Tomo_Shell2026.dll 재검증(2026-07-02) 기준.
> 참고: 리뷰어가 본 수치(+0.20/+0.26/0.286→0.273)는 구 DLL 기준이며, 재검증 후
> L_SFTF +0.12 / TomoNV +0.22 / 0.242→0.232 로 **지적된 미스매치는 오히려 더 선명해짐**.

## 0. 공격 요지 분해

| # | 공격 | 타당성 | 대응 축 |
|---|---|---|---|
| A1 | 핵심 기여(L_SFTF)가 검증에서 진 항이고, 이긴 항(S_g)은 soft-attention이 필요 없는 단순 항 | **타당** — 데이터가 그렇게 말함 | 재프레이밍(iii) + "미분가능성 필요성" 직접 실험 |
| A2 | "relaxation은 예측력이 없다" | 부분 타당 — 예측력은 없지만 예측이 목적이 아님 | L_SFTF 역할 재정의(SFTF-정합 목적) |
| A3 | end-to-end 개선 미미(0.286→0.273; 신판 0.242→0.232) | 타당 — 평균 백분위는 천장 효과 | 지표 교체(초과 질량 g, 케이스 분해) |
| A4 | 2,129단어 얇음 + 메쉬 8개 단순 형상뿐 | 타당 | C~E그룹 확장 + 본문 증량 |

## 1. 총괄 전략: 처방 (iii) 채택 + (ii)를 결정타로, (i)은 정직한 축소판

**주 기여를 "슬라이서-게이트 미분가능 지지 목적함수"로 재프레이밍**하고,
soft-attention SFTF 완화는 ①프레임워크(담금질/파장 이론) ②이전 SFTF 파이프라인과의
정합 인터페이스 ③정점-기울기 형상최적화의 전제로 **역할을 재정의**한다.
그 위에 "미분가능성이 돈값한다"는 **직접 증거 2종**(형상최적화 다중 메쉬 정량화,
하드-게이트 절제)을 추가한다.

### 핵심 반박 논리 (리뷰어 A1·A2에 대한 정면 대응)

1. **"S_g는 미분가능하게 만들 것도 없다"는 틀렸다.**
   하드 게이트(계단함수)는 거의 모든 곳에서 기울기 0 → 정점 기울기 ∂L/∂V 가 죽어
   형상최적화가 **원리적으로 불가능**하다. S_g의 가치는 '오버행×낙하높이'라는 항이
   아니라 **그 항을 매끄럽게 게이트해 기울기를 살린 것**이며, 이것이 정확히 본 논문의
   완화(파장) 기계장치다. → **실험 E2(게이트 sharpness 절제)로 입증**: soft 게이트는
   지지질량을 줄이고, sharp 극한은 변형이 정지(기울기 소멸)함을 같은 조건에서 보인다.
2. **L_SFTF의 목적은 지지량 예측이 아니라 SFTF-정합이다.**
   L_SFTF는 이전 SFTF(분할 방법)의 목적함수를 미분가능하게 재현하는 항으로,
   그 검증은 상관이 아니라 §결과의 수렴성(β→∞에서 J_SFTF로, 유한차분 3×10⁻¹⁰)이다.
   지지량 예측은 애초에 S/S_g의 몫 — 이 역할 분리를 서론에서 명시한다.
3. **미분가능성의 돈값은 2D 배향이 아니라 고차원(형상·학습)에서 나온다** — 논문이
   이미 주장하는 바("빌드방향은 2차원이라 샘플링으로 충분")를 실험으로 완성한다.

## 2. 실행 항목

### E1. [결정타, 처방 ii] 다중 메쉬 정점-기울기 형상최적화 표
- 메쉬 6–10개(sphere, torus, cone, hook, c_clamp, pipe_elbow, u_bracket, bunny-축소,
  FTree4x 후보), 레시피 고정: `--loss bed --lam-area 10 --theta-c 60` (검증된 캡션 레시피).
- 지표: ① 오버행 면적 −% ② TomoNV mss −% ③ **before/after 형상을 실제 Cura(legacy
  15.04/DP103)로 슬라이스한 support-only 질량 −%** ← 샘플링으로는 불가능한, 미분가능성
  전용 성과를 실제 슬라이서 그램으로 증명.
- 산출물: 새 표 1개(tab:shapeopt-multi) + 본문 문단. 예상 비용 1–2시간(배치).
- 리스크: 일부 메쉬 실패 가능. **레시피 재튜닝 금지** — 실패 메쉬는 한계절에 정직 기술.

### E2. [반박 실험] 게이트 sharpness 절제 (soft ↔ hard)
- 같은 메쉬·같은 예산에서 sigmoid sharpness를 8→24→∞(계단)로 올리며 형상최적화.
- 예상: sharp 극한에서 기울기 소멸로 변형 정지 → "미분가능성이 필요 없다"는 공격의
  직접 반증. 파장 서사(짧은 파장 = 입자 극한 = 기울기 소멸)와 정확히 접속.
- 비용: 메쉬 1–2개 × 3 설정, ~30분.

### E3. [처방 i, 정직 버전] 동일 예산 배향 탐색 — ✅ 완료 (2026-07-02)
- 프로토콜: 총 평가 예산 B∈{8,16,48} 고정. (a) Fibonacci 샘플링 B개
  vs (b) 샘플 B/2 + 최고점에서 기울기 정련 B/2 스텝. 최종 방향을 실제 Cura로 슬라이스.
- 예상 결과 두 갈래 모두 활용 가능: 이득 있으면 보조 증거, 없으면 "2D는 샘플링으로
  충분(이미 본문 주장) — 미분가능성의 가치는 E1의 고차원"으로 선제 방어.
- 비용: 8메쉬 × 3예산 × 최종슬라이스, ~1시간.
- **결과** (`scripts/equal_budget_orientation.py`, 목적 L_SFTF+S_g, 기울기 스텝=평가 1회로
  후하게 계산): 평균 백분위는 사실상 동률(샘플링/혼합 = 0.41/0.33, 0.32/0.39, 0.31/0.32
  @ B=8/16/48, 메쉬별 승패 엇갈림) → "2D는 샘플링 충분" 주장과 일관. 단 **초과 지지질량[g]은
  혼합이 전 예산에서 같거나 낫고 B=48에서 절반 이하**(3.16→1.40 g; 좁은 0-지지 골짜기를
  가진 준퇴화 형상에서 마지막 10–15° 정련이 효과). 두 갈래를 모두 살리는 문단+그림
  (`demo_equal_budget`, fig:equalbudget)을 main.tex·main_en.tex에 반영, PDF 재빌드 완료.
  원자료: `scripts/_slicer_cache/e3_equal_budget.json`.

### E4. [처방 A4] 검증 메쉬 C~E그룹 확장
- 추가: C2 manikin, C3 dragon(100k), C4 happy(50k), C5 lucy(50k) + D그룹 2–3개
  (Thingi10k 기계부품; g5test에 D1–D10 존재).
- tab:cura를 8 → 12+ 메쉬로. 유기·대형 형상에서 S_g가 유지되는지 검증.
- 비용: 메쉬당 48방향 슬라이싱 — **야간 배치**(수 시간). 대형 메쉬는 슬라이스 시간 주의.
- 리스크: 대형 메쉬에서 S_g 하락 가능 → 하락하면 정직하게 보고하고 원인 분석
  (그래도 "8개 전부 양"보다 "12개 중 N개 양"이 더 강한 데이터).

### E5. [처방 A3] end-to-end 지표 보강
- 평균 백분위에 추가: ① **초과 지지질량 [g]** (선택 방향 − oracle 방향의 실제 Cura 질량)
  ② 메쉬별 분해(현재 5/8 메쉬가 백분위 ≤0.06 — 천장 효과로 평균 개선이 눌림을 명시)
  ③ median. 재계산만으로 가능(이미 slicer_fresh 데이터 보유), 추가 실험 불필요.

### E6. [처방 A4] 본문 증량 (2,129 → 4,500–5,500단어)
- 한국어판(main.tex)의 파동론 직관·게이트 절제 해설·두 마커 해설을 영문 본문에 승격
  (CLAUDE.md의 "설명 깊이 동등" 규칙과도 일치 — 현재 영문판이 규칙 미달).
- E1–E4 결과 표 2–3개와 논의 추가.
- 서론 재구성: 기여 1 = 슬라이서-게이트 미분가능 지지 목적(+0.83), 기여 2 = SFTF-정합
  완화 프레임(수렴성·담금질), 기여 3 = 정점-기울기 자기지지 형상최적화(다중 메쉬 정량).

## 3. 일정(제안)

| 단계 | 내용 | 소요 |
|---|---|---|
| D1 | E2(절제) + E5(지표 재계산) + 재프레이밍 초안(서론·초록) | 반나절 |
| D1 야간 | E1 배치(다중 메쉬 형상최적화 + Cura 검증) | 배치 |
| D2 | E3(동일 예산) + E1 결과 표화 | 반나절 |
| D2 야간 | E4 배치(C~E그룹 48방향 슬라이싱) | 배치 |
| D3 | E4 표 통합, E6 본문 증량, 한·영 lockstep, PDF 재빌드 | 1일 |

## 4. 재프레이밍 문안 스케치 (초록 골자)

> We present a **slicer-gated differentiable support objective** for build-orientation
> and shape optimization in FDM. The gated support-height term S_g tracks the
> support-only mass of a production slicer (legacy CuraEngine 15.04/DP103) at mean
> per-mesh Spearman **+0.83** across N meshes. Differentiability is not incidental:
> the same smooth gate that scores orientations also carries vertex gradients, and we
> quantify self-support **shape** optimization on M meshes (mean TomoNV support-mass
> reduction −X%, real-slicer reduction −Y%) — a regime where sampling-based search is
> inapplicable; a hard gate provably stalls (ablation). The objective is embedded in a
> **soft-attention relaxation of the SFTF partitioning cost**, which reproduces the
> hard SFTF objective in the annealing limit (finite-difference agreement 3×10⁻¹⁰),
> making the entire prior SFTF pipeline end-to-end differentiable.

## 5. 하지 않을 것
- S_g가 이기도록 L_SFTF 를 재튜닝하거나, 실패 메쉬를 표에서 빼는 것(체리피킹).
- E3에서 기울기가 안 이겨도 숨기지 않기 — 본문 주장("2D는 샘플링 충분")과 일관되게 사용.
- 구 DLL 수치로 되돌리기(재검증 완료본 유지).
