# Gate 판정: 하이브리드 예산 배분 정책 (1-1) — 2026-07-06

> 대응 문서: [SFTF_revision_plan.md](draft/SFTF_revision_plan.md) §1-1, [DIAGNOSIS_2026-07-04](DIAGNOSIS_2026-07-04_sftf_vs_uniform.md)
> 실행: `python scripts/experiment_budget_matched_g5.py --output-stem sftf_budget_matched_g5_hybrid`
> 산출: `Experimental/etc/sftf_budget_matched_g5_hybrid_summary.csv` (+ `.json`)

## 사전 고정 판정 기준 (실험 전)

하이브리드(SFTF top-K/2 ∪ uniform-axis K/2, 동일 예산 cap)가 **uniform 단독을
mean·max 모두에서 동률-이상으로 지배**하면 → 재프레이밍("적응형 예산 배분") 승격.
못 이기면 → 정직 보고 + K·윈도·배분비 재튜닝 금지(체리피킹) + 1-2 라우팅으로 전환.

## 결과 (21 ratio-valid 레코드, ALL)

| 정책 | mean | max | ≤2.0 |
|---|---|---|---|
| SFTF top-20 | 3.344 | 34.04 | 15/21 |
| **Uniform matched** | **1.198** | **2.099** | **20/21** |
| Random (median) | 1.323 | 2.560 | 20/21 |
| Hybrid 25:75 | 1.284 | 4.016 | 20/21 |
| Hybrid 50:50 | 1.502 | 4.016 | 17/21 |
| Hybrid 75:25 | 1.671 | 5.676 | 17/21 |

- SFTF·uniform 열은 committed diagnosis(3.34 / 1.20)를 정확히 재현 → 하네스 신뢰.
- 모든 배분비에서 하이브리드가 uniform보다 mean·max 열세. SFTF 가중↑ → 단조 악화.
- 원인: 고정 예산 안에서 SFTF 윈도가 좁은 오답 basin에 예산을 소모, uniform
  광역 커버리지(안전망)를 crowd-out. 진단의 예측과 일치.

## 판정: **NO-GO (재프레이밍 기각)**

계획서 "하지 않을 것" §1에 따라 재튜닝하지 않는다. 논문은 분기 B로.

## 분기 B를 뒷받침하는 건설적 신호 (그룹 분해)

SFTF는 **유기형(C)에서 uniform을 이긴다** — 라우팅의 실증 토대.

| C그룹 | SFTF | Uniform | | D/E | SFTF | Uniform |
|---|---|---|---|---|---|---|
| Bunny 69k | **1.015** | 1.170 | | D 평균 | 6.85 | **1.09** |
| dragon | **1.000** | 1.122 | | E 평균 | 2.90 | **1.44** |
| lucy | **1.000** | 1.032 | | | | |
| manikin | **1.000** | 1.018 | | | | |

- C그룹: Hybrid 25:75 mean=1.049가 전 정책 최고(uniform 1.083, SFTF 1.135).
- 결론: 방어 가능한 서사 = 유기형 한정 해석가능 순위기(진단) + 후보-풀 신호 기반
  사전 라우팅(1-2, 유기→SFTF / 기계→uniform) + 사후 AVE. "적응형 예산 배분이
  uniform을 지배한다"는 주장은 하지 않는다.

## 다음 단계 (분기 B)

1. **1-2 라우팅**: 후보 풀 신호(NMS floor 밀집도, 점수 분산/평탄도, 대칭 텐서 M의
   Rayleigh R_sym)로 유기/기계 판별 → 그룹별 승자 라우팅. 21레코드 후향 평가.
2. **2-2 R̃ 단독 랭킹**: deployed score를 R̃로 교체 가능성 확인(캐시 재계산).
3. Abstract/기여: "적응형 배분 지배" 대신 "유형 인지 라우팅 + 정직한 한계".

---

# 후속: 라우팅 규칙(1-2) 후향 평가 — 2026-07-06

> 실행: `python scripts/experiment_routing_rule_g5.py`
> 산출: `Experimental/etc/sftf_routing_rule_g5{.json,_records.csv,_summary.csv}`

## 신호 (후보 풀만으로 계산, TOMO 예산 소비 0)

- **nn_frac**: 배치된 top-20(3° NMS 후)의 최근접 각거리가 1.5×NMS floor 이내인
  비율. **밀집 = 후보들이 소수 basin에 합의(유기형 신호)**, 분산 = 랭킹 무신호
  (기계부품). 계획서 §1-2의 예상("밀집=실패 신호")과 **방향이 반대**임에 주의 —
  탐색 결과 Cohen's d=+1.35로 최강 분리 신호.
- **score_cv**: top-20 tuned score의 변동계수. 극단값(E2 2.49, E9 2.95)이
  "밀집이지만 불안정한 랭킹"을 걸러내는 보조 신호.

라우팅: `nn_frac ≥ 0.8 ∧ score_cv ≤ 2.0` → SFTF 분기, 아니면 uniform 폴백.

## 결과 (21 레코드)

| 정책 | mean | max | ≤2.0 |
|---|---|---|---|
| SFTF 단독 | 3.344 | 34.04 | 15/21 |
| Uniform 단독 | 1.198 | 2.099 | 20/21 |
| Routed 고정 임계값 (in-sample) | 1.167 | 1.762 | 21/21 |
| Routed LOO (fold별 임계값 재적합) | 1.218 | 2.099 | 20/21 |
| **Routed 고정 → SFTF 분기를 h25로** | **1.144** | **1.762** | **21/21** |
| Routed LOO → h25 분기 | 1.191 | 2.099 | 20/21 |
| Oracle (메시별 승자) | 1.137 | 1.762 | 21/21 |

h25 분기 = 라우팅된 메시에서 순수 SFTF 대신 Hybrid 25:75 사용(오분류 시에도
예산의 75%가 uniform 안전망에 남음). 오분류 비용 완충: C4 happy 1.662→1.071.

## 판정

1. **실패 감지는 강건하다 (핵심 주장 가능).** 파국적 SFTF 실패 6건(D1 34.0,
   E9 5.7, E10 5.3, E1 3.1, E2 2.7, D6 2.2)이 고정·LOO **모두에서 전부 uniform으로
   라우팅**됨. 파국적 오분류 0건. "실패를 후보 풀만 보고 사전 감지·회피한다"는
   AVE의 자매 규칙 서사가 데이터로 성립.
2. **uniform 초과 성능은 in-sample 한정 (정직 서술 필요).** 고정 임계값
   (1.144/1.762/21 21)은 oracle에 근접하며 uniform을 3지표 모두 이기지만,
   LOO(1.191/2.099/20 21)는 uniform과 통계적 구분 불가(동률 수준, 열세 아님).
   n=21로는 임계값 일반화를 주장할 수 없음 — 본문에는 "파국 회피 + uniform
   동률-이상"으로 쓰고, 임계값 민감도는 표본 확대(계획서 2-3, n=5→8)의
   근거로 연결.
3. LOO 오분류는 전부 "SFTF 승리를 놓침"(A5, C3, E7) 또는 경미한 손실(D10 +0.02,
   C4는 h25로 +0.00) — 안전 방향으로만 틀림.

## 본문 반영 방향

- §AVE 뒤 소절: "Pre-verification routing" — nn_frac·score_cv 정의, 위 표,
  파국 회피 0/6 강조, LOO 정직 기술.
- Limitations: 임계값은 21레코드 후향 적합이며 일반화에는 표본 확대 필요.
- 재현성: 라우팅은 저장된 후보 CSV + 캐시 그리드만으로 재계산 가능(가점 요소).

---

# 후속 2: R̃ 단독 랭킹 검정(2-2) — 2026-07-06

> 실행: `python scripts/experiment_rtilde_ranking_g5.py` (K=5/10/20 스윕)
> 산출: `Experimental/etc/sftf_rtilde_ranking_g5{.json,_summary.csv,_records.csv}`
> R̃ = rayleigh + bed (R+B), 오름차순. 동일 배치 파이프라인(3° NMS, 10° 윈도,
> 캐시 1°/60° int3 그리드)으로 튜닝 랭킹과 정면 비교.

## 결과 1: budget curve — R̃가 순위기로서 동률-이상 (사전 판정 기준 충족)

| scope | tuned@20 | rtilde@20 |
|---|---|---|
| ALL mean/max/≤2.0 | 3.344 / 34.04 / 15 21 | **2.001 / 10.91 / 18 21** |
| C (결정 척도) | 1.135 / 1.662 / 5 5 | 1.142 / 1.662 / 5 5 (동률) |
| D | 6.852 / 34.04 / 4 6 | **1.304 / 1.642 / 6 6** (D1 34.0→1.54) |
| E | 2.898 / 5.68 / 3 7 | 3.620 / 10.91 / 4 7 (E10 5.3→10.9 악화) |

K=5/10에서도 동일 방향. 계획서 판정 기준("동률-이상이면 승격")을 curve상 충족.

## 결과 2: 단 R̃ 풀에서는 라우팅 신호가 죽는다 (아키텍처 상호작용)

R̃-랭킹 top-20으로 신호를 재계산하면 score_cv≈0(0.00~0.15), nn_frac≈1.0으로
퇴화 → E9(5.68)·E1·E2 파국이 라우팅을 통과, routed mean 1.529로 붕괴.
**튜닝 점수는 순위기로는 열등하지만 풀 기하(밀집도·분산)가 형상 유형을
드러내는 유일한 진단 신호** — 상호보완 관계.

## 결과 3: 복합 구성 (라우팅=튜닝-풀 신호, 검증 분기=R̃ 랭킹)

| 구성 (고정 임계값) | mean | max | ≤2.0 |
|---|---|---|---|
| Routed → h25(tuned) 분기 | **1.144** | 1.762 | 21/21 |
| Routed → tuned 분기 | 1.167 | 1.762 | 21/21 |
| Routed → R̃ 분기 | 1.182 | 1.762 | 21/21 |
| Uniform 단독 | 1.198 | 2.099 | 20/21 |
| Routed(LOO) → R̃ 분기 | 1.217 | 2.099 | 20/21 |

## 판정 (2-2)

- **승격 권고: deployed ranker = R̃** — ground-node 항등식이 정당화하고(적합
  가중치 0개), curve에서 동률-이상이며, 과적합 비판(메시 5개로 가중치 7개)을
  원천 차단. **7-가중치 점수는 "calibration ablation + 라우팅 진단 신호"로
  강등** — 계획서의 강등 시나리오에 더해, 라우팅 신호로서의 새 역할이
  데이터로 확인됨(순위기로 실패하는 바로 그 풀-분산 패턴이 유형 감지 신호).
- 정직 기술 필요: E10은 R̃에서 악화(5.3→10.9)되나 라우팅이 uniform으로
  보내므로 시스템 결과에는 무영향. C1 Bunny는 1.015→1.050 미세 열화.
- 선택 과제(저비용): R̃ 센터 기반 h25 분기 재계산 — 복합 구성의 mean을
  1.182→1.15 수준으로 더 좁힐 가능성.

## 논문 최종 아키텍처 (분기 B 확정판)

1. **R̃ 랭킹**(항등식 정당화, 무적합) — 유기형 basin 탐지
2. **사전 라우팅**(튜닝-풀 nn_frac ∧ score_cv) — 파국 6/6 사전 감지, uniform 폴백
3. **h25 안전망**(라우팅된 분기 내 25:75 배분) — 오분류 비용 완충
4. **사후 AVE**(escalation) — 잔여 hard case
   → "실패를 감지·회피·완충하는 4단 검증 제어", uniform 대조군 정직 보고 유지.

---

# 후속 3: AVE 동예산 대조 공정화(1-3) — 2026-07-06

> 실행: `python scripts/experiment_ave_uniform_control.py`
> 산출: `Experimental/etc/sftf_ave_uniform_control_1deg60{.json,_summary.csv,_records.csv,_side_by_side.csv}`
> 프로토콜: 본문 AVE 감사와 **완전 동일**(1°/60° int3 캐시, 10° 윈도, 트리거
> eq.(ave-trigger) η≥0.008 ∧ (edge ∨ g≤1.5 ∨ g≥3.0), tier 10→50/200) —
> 시드만 SFTF 랭킹 대신 farthest-point uniform-axis 순서로 교체.

## 결과 (21 레코드, ALL)

| 정책 | mean | max | ≤2.0 | 예산 |
|---|---|---|---|---|
| SFTF+AVE (본문 tab:ave-g5) | 1.135 | 1.925 | 21/21 | 13.94% |
| **Uniform+AVE (신규 대조)** | **1.096** | **1.762** | 21/21 | 18.39% |
| Uniform base(top-10 창, 참고) | 1.170 | 1.762 | 21/21 | 3.32% |

**어느 쪽도 지배하지 않음**: uniform+AVE가 ratio는 근소 우위, 예산은 1.3×
소비. 리뷰어가 계산하면 나올 수치를 선제 확보 — "AVE 가치의 대부분은
seed-agnostic한 escalation 메커니즘"이 정직한 결론.

## 그룹 분해 — SFTF 시드의 진짜 가치는 유기형에서의 예산 효율

| 그룹 | SFTF+AVE (mean@budget) | Uniform+AVE (mean@budget) |
|---|---|---|
| **C 유기형** | 1.135 @ **9.99%** | 1.010 @ 26.29% (severe 3/5, 개당 ~41%) |
| D | 1.030 @ 23.58% | 1.064 @ 15.41% (D1 트리거 미스 1.364) |
| E | 1.259 @ 11.30% | 1.208 @ 16.34% (E10 트리거 미스 1.762) |

- 유기형에서 uniform 시드는 옳은 basin을 몰라 **severe escalation(200창)으로
  2.6× 예산**을 태워야 SFTF 수준에 도달 — SFTF 시드의 가치는 "이기는 것"이
  아니라 **같은 품질을 1/2.6 예산으로**(라우팅 서사와 정합).
- 트리거 미스는 양쪽에 존재(uniform: D1 1.364·E10 1.762 / SFTF: happy 1.662)
  — 트리거 자체의 한계로 정직 기술.
- E2(1.04M faces, 본문의 "practical ceiling" 1.925)는 uniform+AVE에서 1.106
  — "ceiling" 표현은 SFTF-시드 한정으로 완화 필요.

## 본문 반영

- tab:ave-g5에 Uniform+AVE 1행 추가(또는 Supp.) + 본문 한 단락:
  "escalation 정책은 seed-agnostic하며, SFTF 시드의 기여는 유기형에서의
  예산 효율(9.99% vs 26.29%)" — §limits의 스코프 축소와 일관.
- E2 "practical ceiling of coarse SFTF coverage" 문장 완화.

---

# 후속 4: 원고 반영 완료 — 2026-07-06

`draft/SFTF_TDP_draft.tex` + `draft/SFTF_TDP_supplementary.tex`에 전체 반영,
양쪽 pdflatex 컴파일 성공(미해결 참조 0), 본문 3,548단어(<4000),
표 5·그림 3(TDP 한도 내).

| 위치 | 반영 내용 |
|---|---|
| Abstract | 4단 파이프라인(rank–route–verify–escalate)으로 재작성, 라우팅·seed-agnostic AVE 수치 포함 |
| Contribution (iv) | 라우팅+AVE를 "adaptive verification-control pair"로 통합 |
| Methods rescoring | R̃ 승격 권고 + 7-가중치를 calibration ablation·라우팅 진단으로 강등. 기존 표는 calibrated ordering 기준임을 명시(재계산 연쇄 회피) |
| §ave tab:ave-g5 | "All, uniform seeds 1.10/1.76/18.39%" 행 추가 + seed-agnostic 문단 + E2 ceiling을 "SFTF-seeded coverage의 ceiling"으로 완화 + 트리거 미스 양쪽 기술 |
| §limits | "top-20이 NMS floor에 뭉친다" 서술을 실측으로 교정(뭉침=유기형 신호, 0.83 vs 0.54). tab:budget-matched-g5에 Hybrid 2행·Routed 2행·Oracle 행 추가. Eq.(routing) 신설, LOO 정직 기술("detection은 주장, threshold 일반화는 미주장") |
| Positioning/Future work | 파이프라인 재정의. 구식 future work (i)(iii) 삭제(R̃ 승격으로 해소), 라우팅 임계값 검증을 1순위로 |
| Conclusions | 분기 B 서사로 재작성 |
| Supplementary | S13(R̃ vs calibrated, K스윕), S14(per-mesh 라우팅 신호·경로, 파국 6건 † 표기), S15(AVE seeding 대조 그룹 분해) 신설 — 각 캡션에 생성 스크립트 명기 |

## 남은 항목 (이번 세션 범위 외)
- (없음 — 계획서 전 항목 + 선택 과제 완료)

---

# 후속 8: R̃-h25 분기 재계산 — 기각 (2026-07-06)

> 실행: `experiment_budget_matched_g5.py`에 `Hybrid *:* Rtilde:uniform` 정책
> 추가 후 재실행(동일 cap·동일 uniform 창, SFTF 지분만 R̃-랭킹 센터로 교체).

## 결과 (routed fixed 복합, 24레코드)

| 분기 payload | mean | max | ≤2.0 |
|---|---|---|---|
| **h25 (tuned) — 현행 원고** | **1.266** | 2.613 | **22/24** |
| pure SFTF (tuned) | 1.277 | 2.613 | 22/24 |
| h25 (R̃) | 1.315 | 2.613 | 21/24 |

R̃-h25는 개선이 아니라 열화: Bunny 1.015→1.170, **E7 1.120→2.164**.
25% 예산에서 R̃ 센터가 tuned 센터의 basin을 못 잡음.

## 이론적 폐합 (원고에 1문장 반영)

라우팅 신호(nn_frac·cv)는 **tuned 풀의 기하**를 인증한다 → 라우팅된 분기의
검증 창도 tuned 후보여야 자기일관적. R̃ 풀은 그 인증을 물려받지 않는다.
R̃의 가치는 전역 랭킹 수준(D그룹 파국 구제), 분기 내부는 calibrated 센터.
→ Methods rescoring 절에 "router certifies the calibrated pool, not the
R̃ pool" 문장 추가(리뷰어의 일관성 질문 선제 차단). 컴파일 검증 완료.

**판정: 원고 분기 구성 무변경(tuned-h25 유지). 선택 과제 종결.**

---

# 후속 7: P2-1 실제 슬라이서 교차 검증 완료 (2026-07-06)

> 실행: `python scripts/experiment_cura_cross_validation.py`
> (_Cura_CLI 파이프라인 재사용: legacy CuraEngine 15.04 = 3DWOX DP103 내장
> 엔진, 60°/everywhere/lines, HWM gcode 파서, 3DWOX 재현 ρ=0.99)
> 산출: `Experimental/etc/sftf_cura_cross_validation{.json,.csv}`
> 프로토콜: 유기형 8종 × 2방향(배치 파이프라인 방향 vs TOMO 전역 최적),
> 전 메시 대각 140mm 균일 스케일(비율은 스케일 불변), 총 16 슬라이스 ~2분.

## 결과 — "기준 자체가 추정기" 공격에 대한 방어 확보

| 메시 | 분기 | 예측(TOMO) | 측정(Cura) |
|---|---|---|---|
| Bunny | SFTF | 1.01 | **0.61** |
| Manikin/Dragon/Lucy | SFTF | 1.00 | 1.00 (방향 동일) |
| Happy (hard case) | SFTF | 1.66 | **0.64** |
| Nefertiti | uniform | 2.50 | **0.95** |
| liver | uniform | 2.61 | 2.08 |
| kidney | SFTF | 1.03 | 1.03 |

**핵심: 측정 비율이 예측 비율을 넘는 사례 0/8** → 논문의 TOMO 기반 비율은
실제 슬라이서 기준으로 **보수적(상한)**. 특히:
- Happy(본문 hard case 1.66)는 실기에서 배치 방향이 오히려 서포트 36% 적음
- Nefertiti(라우팅 미스로 uniform行)도 실기에선 사실상 동률(0.95)
- liver은 방향 일치(2.61 예측 → 2.08 측정) — 파국 판정도 실기로 확인
- Bunny: TOMO 동률(1.01) basin에서 실기가 0.61로 차별 → "근접 동률 후보의
  최종 tie-breaking은 대상 슬라이서로" 권고를 본문에 추가

주의(정직): 쌍별 Spearman(0.10)은 자명쌍 3개·n=8이라 무의미 — 주장은
"보수성(예측≥측정)"으로 한정. 단일 프로파일(DP103)·단일 임계각 조건.

## 원고 반영

- Supplementary **S16** 신설(8행 표, 스케일·프로토콜·보수성 캡션)
- §positioning에 검증 문단 추가("TOMO 기반 비율은 보수적" + tie-breaking 권고)
- Data availability: S16은 legacy CuraEngine 설치 필요 명시
- 검증: 본문·Supp 컴파일 성공, 미해결 참조 0, 본문(초록·백매터 제외) ~3,510(<4000)

**이로써 계획서(SFTF_revision_plan.md)의 전 항목(P1·P2·P3) 완료.**

---

# 후속 6: P2-3 표본 확대 n=5→8 — held-out 검증 완료 (2026-07-06)

> 온보딩: Nefertiti 100k(·obj)·liver 19k·kidney 12k(FMA stl) →
> `Group_C6/C7/C8` (.ply, sftf_Mesh_Data/g5test). Phase A 재사용
> (SFTF 후보 + TOMO 1°·3°/60° 스윕, 메시당 1~3분 — 야간 배치 불필요였음).
> **설계 원칙: 3종은 순수 held-out — 어떤 가중치·임계값도 재적합하지 않음.**

## Held-out 핵심 결과 (24 ratio-valid 레코드)

1. **liver = 유기형 파국 (경계 재정의).** SFTF 15.85 vs uniform 2.61.
   매끈한 준볼록 형상이라 내부 face-to-face flow 부재(top-1 hit=1).
   → "유기형/기계" 이분법이 아니라 **후보-풀 신호가 진짜 적용 경계**임을 입증.
2. **라우팅 규칙이 무수정 전이.** 기존 고정 임계값(nn_frac≥0.8 ∧ cv≤2.0)
   그대로: liver 파국 감지(f_NN=0.55→uniform), kidney 정확 라우팅(SFTF, 1.03 승),
   nefertiti는 uniform으로(+0.24 경미, 안전 방향). **파국 감지 8/8**
   (기존 6 + 신규 2). crowding 분리 0.81 vs 0.54 유지.
3. **AVE가 liver 구제: 26.7 → 1.48** (4개 트리거 신호 전부 발화, 21.5% 예산).
4. **AVE seeding 대조 역전.** 21레코드에서 "동률"이던 것이 24레코드에서
   SFTF+AVE가 **4지표 전부 우위**: 1.20/2.27/23 24/13.24% vs uniform+AVE
   1.22/2.61/22 24/16.51% (uniform 시드는 nefertiti·liver 모두 트리거 미스).
5. 잔여 한계: nefertiti는 양 시딩 모두 트리거 미스(SFTF 2.27) — 24레코드 중
   유일한 >2.0. 트리거 규칙 자체의 현행 상한으로 본문에 정직 기술.

## 24레코드 갱신 수치 (본문 표 반영값)

| 정책 | mean | max | ≤2.0 |
|---|---|---|---|
| SFTF top-20 | 3.72 | 34.04 | 16/24 |
| Uniform | 1.31 | 2.61 | 21/24 |
| Routed fixed→h25 | **1.27** | 2.61 | **22/24** |
| Routed LOO→h25 | 1.31 | 2.61 | 21/24 (uniform과 동률 도달) |
| Oracle | 1.24 | 2.61 | 22/24 |
| SFTF+AVE | 1.20 | 2.27 | 23/24 @13.24% |
| Uniform+AVE | 1.22 | 2.61 | 22/24 @16.51% |

R̃@20: ALL 2.85 vs tuned 3.72 (여전히 우위). 단 held-out C에서 liver가 R̃에서
더 악화(15.85→22.96, 라우팅이 제거하므로 시스템 무영향), kidney 1.03→1.10.
본문 R̃ 문구를 "five calibration meshes에서 동률"로 한정 수정함.

## 원고 반영 (본문+Supp 전체 24레코드화)

- Abstract 재작성(285단어): held-out 전이·liver 구제·AVE 역전 포함
- §datasets: C그룹에 held-out 3종 명시("모든 캘리브레이션 동결 후 온보딩")
- §limits: 제목을 "flow-poor shapes"로 확장, held-out 문단 신설,
  표·crowding 수치 갱신, LOO 동률(1.31 vs 1.31) 갱신
- §ave: 표 C행(n=8)·All행·uniform행 갱신, liver 구제 서술, nefertiti 상한,
  "seed-agnostic 동률" → "확장 감사에서 SFTF 시딩 전지표 우위"로 교체
- Supp S13/S14(‡ held-out 표기)/S15 갱신
- 검증: 컴파일 성공(24쪽)·미해결 참조 0·Abstract 285(<300)·
  본문(초록·백매터 제외) ~3,400(<4000)·표 5·그림 3

---

# 후속 5: P3 일괄 정리 완료 — 2026-07-06

컴파일 성공(본문 22쪽·미해결 참조 0), 본문 3,702단어(<4000), 표 5·그림 3,
docx 자동 동기화 확인.

| 항목 | 처리 |
|---|---|
| 3-1 θc=60° 근거 | protocol 절에 DP103 프로파일 근거 + "시리즈는 대상 프로파일 각도를 따른다" 한 줄 추가 (삼부작 45°/60° 불일치 방어) |
| 3-2 TOMO_CUDA vs gpumsst | "모순 아님" 문장 추가: 수정된 accumulator·32스레드 9950X3D 기준선·GPU 전송 오버헤드 미상각 구간 명시, \cite{gpumsst} 연결 |
| 3-3 overflow 일원화 | §AVE는 §limits로의 포인터로 축약, §limits에 본 설명 + 재검증 방식("전 그리드 int32 재스윕+마커, 모든 표는 재생성 그리드에서 재계산") 기술. 주의: 별도 회귀 테스트는 미존재 → 존재 주장 대신 실제 재스윕 절차를 기술함 |
| 3-4 체재 | author(s)→단수 2곳, placeholder \renewcommand{\includegraphics} 매크로 본문·Supp 모두 제거(그림 자산 전수 실재 확인 후), Fig.1 캡션에 "shared across the author's SFTF manuscript series" 명시, 낡은 unsrtnat 주석 2곳을 실태(수기 Vancouver thebibliography)로 정정 |
| 3-4 gpumsst 인용 | 웹 검증 완료: 2026;13(1):50-62, 2026-02-01 발행 확정 — 원고 표기 정확, 수정 불요 |
| 3-5 데이터 공개 | Data availability에 "라우팅·하이브리드·R̃·AVE 대조 분석은 캐시+후보 풀만으로 TOMO 재실행 없이 재현 가능, 캡션의 scripts/experiment_*.py 참조" 명시 |
