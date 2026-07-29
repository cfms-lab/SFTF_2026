# SFTFSoft 보완 계획 (검토일: 2026-07-06)

> 대상: `SFTFSoft_TDP_draft.tex`(= main_en 계열) + `SFTFSoft_TDP_supplementary.tex`
> 기준점: **개정된 SFTF·SFTFCluster**. 두 형제 논문이 이번 개정에서 "자기 대표
> 주장을 반증하는 대조군 + 완전 공개 재현 인프라 + frozen held-out"이라는 세
> 규율을 새로 갖추면서 방법론 기준선을 올렸다. 그 잣대로 보면 SFTFSoft는
> novelty의 천장은 여전히 셋 중 가장 높으나(수만 정점 형상최적화에서 실제
> 슬라이서 지지 96–100% 제거는 형제들에 없는 급), **방법론적 규율에서 삼부작 중
> 가장 뒤처진 상태**다. 처방은 형제들의 수를 그대로 따른다.
> 우선순위: P1 = 형제 기준 대비 핵심 격차, P2 = 재현성·정직성 보강, P3 = 정리.

---

## P1. 형제 논문이 갖추고 SFTFSoft만 없는 핵심 규율

### 1-1. "SFTF 텐서가 예측에 기여하는가"를 격리하는 대조군 [최우선]

**문제(가장 날카로운 격차).** SFTF는 uniform-axis matched control로, Cluster는
matched-part-count control로 각자 "대표 방법이 단순 베이스라인 대비 실제 값을
하는가"를 스스로 검증했고, Cluster는 그 결과 "feature set이 아니라 part budget이
1차 요인"이라며 자기 방법을 2차 요인으로 정직하게 강등했다. SFTFSoft의 대응
질문은 명확하다: **제목의 주인공 SFTF 텐서(L_SFTF)가 예측에 기여하는가?**
논문 자신의 tab:cura가 이미 답을 시사한다 — L_SFTF 단독 +0.26, 이기는 항 S_g
+0.79. 그리고 S_g는 정의상(식 slicer-gate) Σ sigmoid(gate)·A·η, 즉 **텐서도
receiver attention도 쓰지 않는 순수 per-face 게이트 오버행×높이 합**이다.
순위상관(Spearman)은 평활화에 둔감하므로 하드 게이트로 분류한 오버행×높이 합도
+0.79 근처가 나올 개연성이 크다. 즉 헤드라인 예측 성과가 텐서·soft·미분가능
기계장치와 사실상 무관할 수 있는데, 이를 격리하는 대조가 없다.
(gate-sharpness 절제는 형상최적화 gradient만 다루지 예측 순위를 다루지 않는다.)

**보완 실험 (캐시 재슬라이싱 불필요, Spearman 재계산만).**
- **예측 대조**: 동일 15메시·48방향에서 아래 예측자들의 실제 Cura Spearman을
  한 표에 나란히:
  ① 하드 게이트 오버행×높이 합(텐서·soft 전혀 없음),
  ② S_g(현행, soft 게이트),
  ③ L_SFTF(텐서),
  ④ L_SFTF+S_g.
  ①과 ②가 사실상 같으면 → "예측에서 텐서·미분가능성은 불필요, 게이트가 전부"를
  정직하게 명시. ①이 ②보다 유의하게 낮으면 → soft/텐서의 예측 기여를 최초로
  입증(강한 방어).
- **형상최적화 대조(선택, 배치)**: shape-opt 목적함수에서 텐서(L_SFTF) 항을
  끄고 게이트 높이항만으로 동일 9메시 재최적화. 텐서가 shape-opt gradient에도
  기여하지 않으면 → "SFTF 텐서는 예측·형상최적화 어느 헤드라인도 견인하지
  않으며, 역할은 '이전 SFTF 목적함수의 미분가능 재현(fidelity)'에 한정"임을
  Cluster식으로 명시적 강등.

**판정/재프레이밍.**
- 텐서가 어느 헤드라인도 견인하지 않으면 → 초록·기여에서 "SFTF 텐서"를 전면에
  두는 대신 "**슬라이서-게이트 미분가능 지지 목적**"을 주 기여로 올리고, 텐서
  완화는 fidelity·형상최적화 전제로 역할 한정(이미 서론에 있는 논지를 데이터로
  못박음). **이기도록 재튜닝 금지** — Cluster의 자기강등과 같은 톤 유지.

### 1-2. Frozen held-out 규율 강화

**문제.** SFTF는 "모든 가중치·임계값 동결 후 온보딩한 유기형상 3종"이라는
명시적 frozen-then-test를 세우고, liver가 organic인데도 실패하는 걸 routing이
잡는 강한 일반화 서사를 만들었다. SFTFSoft의 15메시 +0.79는 S_g에 적합
파라미터가 없어 held-out이 덜 critical하나(이 점은 본문에 한 줄 명시 권장),
학습·튜닝 성분(GNN, shape-opt 레시피)의 일반화 근거는 형제 새 표준 대비 얇다.

**보완.**
- S_g가 무적합(fit-free)임을 본문에 한 줄 명시 → "held-out 불필요"의 근거를
  선제 제시(리뷰어의 train/test 질문 차단).
- GNN·shape-opt 레시피의 하이퍼파라미터가 어느 메시에서 고정됐고 어느 메시가
  그 이후 평가됐는지 frozen 경계를 명시. 가능하면 shape-opt 9메시 중 일부를
  "레시피 동결 후 평가"로 재배치.

---

## P2. 재현성·정직성 보강 (개정 후 SFTFSoft만 남은 예외)

### 2-1. 공개 repo + internal 참조 실체화 [필수]

**문제.** SFTF는 `github.com/cfms-lab/SFTF_2026`(캐시 그리드·스크립트, 캡션에
재현 진입점 명시), Cluster는 `SFTFCluster_2026`(12형상 벤치마크·평가 스크립트)를
공개했다. 반면 SFTFSoft는 여전히 참고문헌에서 `sftf_engine`,`tomonv`를
**"(internal reference implementation)"**로 인용하고, 데이터 가용성은
**"corresponding author on reasonable request"**다. 이제 셋 중 유일한 outlier이며,
인용 불가능한 internal 참조 두 건은 저널 데스크에서 바로 걸린다.

**보완.**
- SFTFSoft 코드·15메시 Cura 캐시·게이트 각 민감도/5.13 이식 스크립트를 공개 repo
  (예: `github.com/cfms-lab/SFTFSoft_2026`)로 올리고 캡션에 재현 진입점 명시
  (SFTF·Cluster와 동일 형식).
- **[2026-07-10 추가] JAX 포트 동봉 필수**: 다음 스냅샷 갱신 시
  `Tomo_SFTFjax_dev`(SFTF_DerivativeJAX + 패리티 스위트 + 대형 메쉬 GNN LOO
  스크립트/결과)를 포함할 것. 본문 Data availability와 Supplementary 신설
  섹션(교차 프레임워크 검증·GPU 런타임·대형 메쉬 LOO 재실험)이 이 코드를
  재현 진입점으로 인용하므로, 미포함 시 문구-실체 불일치. 상세는 루트
  WORKLOG.md 2026-07-10 항목 참조.
- `sftf_engine` → 실제 SFTF 원고 인용으로 교체(§1-3 참조). `tomonv`는 공개
  구현/DOI 또는 본 repo 내 구현으로 실체화. "on request" 문구를 repo URL로 교체.

### 2-2. GNN 기여의 지위 재조정

**문제.** 기여 4번(label-free amortized inference)이 TomoNV 백분위(0.28 vs random
0.41)에선 성립하나 **실제 Cura 지표에선 0.60 vs 0.40으로 이점 없음**(본인 정직
기술). SFTF·Cluster는 헤드라인에 건 주장이 결정 지표에서 뒤집히는 경우가 없다.
정직성은 지켰으나, 결정 지표에서 실패하는 다리를 기여 목록·초록에 얹고 있어
상대적으로 약하다.

**보완.**
- GNN을 4대 기여에서 내려 본문 각주급/부록 proof-of-concept로 강등하거나,
  초록에서 수치는 유지하되 "TomoNV 한정, 실제 Cura에선 소형 테스트베드 한계로
  이점 없음"을 초록에도 한 구절로 노출(현재는 본문에만 있음).
- 확보되는 지면을 1-1의 예측 대조 표와 S_g 서사 강화로 재배치.

### 2-3. shape-opt 표의 무효 레코드 처리

**문제.** tab:shapeopt-multi의 28면 U-bracket/c-clamp(Cura 0.00→0.00) 행이
설득력을 깎는다. 형제들은 "무효/비양성 레코드 제외" 규율(SFTF의 ratio-valid,
Cluster의 평가축 분리)을 세웠다.

**보완.** 지지가 처음부터 0인 행은 "지지 불필요 대조군"으로 별도 표기하거나
각주로 내리고, 헤드라인 "96–100% 제거"는 지지 요구 6메시에만 적용됨을 표에서
시각적으로 분리(현재 서술로는 되어 있으나 표에서 섞여 보임).

---

## P3. 저비용 정리 (투고 전 일괄)

### 3-1. 삼부작 상호인용 동기화
- SFTFSoft만 실제 SFTF 원고를 인용하지 않고 internal engine으로만 참조 → SFTF
  행선지(3DP&AM) 확정 시 세 편 동시 정리. Cluster의 `sftf`는 현재 "Prog Addit
  Manuf. 2026. Forthcoming"인데 실제 3DP&AM이면 세 곳 모두 교체.
- θc 규율: SFTFSoft·SFTF는 60°(DP103)로 일치, Cluster는 45°(generic FDM). 세
  논문 공통 커버레터/각주에 "각 논문은 대상 슬라이서 프로파일의 각도를 따른다"로
  일관 설명(SFTF가 이미 쓴 문구 재사용).

### 3-2. tex 헤더 stale 메모 정리
- `main_en.tex` 헤더의 `WORDCOUNT: 2129 words (…2026-07-01)`가 stale(본문은 이미
  ~4,300단어). 갱신 또는 삭제 — 셋 중 유일하게 남은 메모.

### 3-3. 원고 체재 점검
- 단독 저자 표기 일관성("the author" vs "author(s)") — Declarations 확인.
- TDP 제한(본문 4000단어, 표 ≤5, 그림 ≤8) 실측. 1-1 예측 대조 표 추가 시 기존
  표 1개의 Supplementary 이동 검토.
- Fig. 1 계열(unified flow)이 SFTF·Cluster와 공유 그림 — 동시 투고 시 캡션에
  "author's SFTF manuscript series" 출처 명시(SFTF는 이미 반영).
- 미해결 참조 0건, PDF 재빌드 확인.

---

## 실행 순서 제안

| 단계 | 내용 | 소요 |
|---|---|---|
| D1 | 1-1 예측 대조(캐시 Spearman 재계산) + 2-2 GNN 강등 + 3-2/3-3 정리 | 반나절 |
| D1 야간 | 1-1 형상최적화 대조(텐서 off 재최적화, 9메시) | 배치 |
| D2 | 판정 → 초록·기여 재프레이밍(텐서 역할 한정), 1-2 frozen 경계 명시 | 반나절 |
| D2 | 2-1 공개 repo 정비 + internal 참조 실체화, 2-3 표 정리 | 반나절 |
| D3 | 3-1 상호인용 동기화(SFTF 행선지 확정 후), PDF 재빌드·참조 0건 | 짧게 |

## 하지 않을 것

- 1-1에서 텐서가 예측·형상최적화에 무기여로 나올 때, 기여하도록 목적함수를
  재튜닝하는 것(체리피킹). Cluster처럼 정직하게 강등하고 주 기여를 게이트
  목적으로 재프레이밍한다 — 논문의 진짜 자산(미분가능성이 여는 형상최적화)은
  그대로 살아남는다.
- GNN의 실제 Cura 실패를 숨기거나 TomoNV 수치만 노출하는 것.
- "internal reference implementation"·"on reasonable request" 유지 — 셋 중
  유일한 재현성 예외 상태를 그대로 두지 않는다.
