# SFTF-Cluster 보완 계획 (검토일: 2026-07-06)

> **상태: 2026-07-11 재검증으로 대체됨.** 이 문서는 당시의 문제 발견과 실험 계획을
> 보존한 역사적 스냅샷이며, 아래의 수치와 미완료 표시는 현재 결과가 아니다. 새 라우팅 정책,
> 재생성 결과, matched-K 및 seed 결론은
> `../outputs/INTEGRATION_AUDIT_20260711.md`와 최신 주·보충 원고를 기준으로 한다.

> 대상: `SFTF_Cluster_TDP_draft.tex` + `SFTF_Cluster_TDP_supplementary.tex`
> 목적: 투고 전 보완 항목 정리. 우선순위 순으로 배열했으며, P1은 "리뷰에서
> 논문이 깨질 수 있는 구멍", P2는 "지적당하면 방어가 궁색한 항목", P3은
> "저비용 정리 항목"이다. 각 항목에 예상 작업량과 판정 기준을 명시한다.

---

## P1. 핵심 주장의 통계적 구멍 (필수 — 이것 없이 상위 저널 불가)

### 1-1. 파트 수 confound 통제 실험 [최우선]

**문제.** 논문의 핵심 발견("지지 감소는 support column 보존이 아니라 재배향
자유도가 지배")이 역설적으로 헤드라인 주장("SFTF feature-fusion k-medoids가
최고 mean rank 2.00")을 갉아먹는다. 재배향 자유도가 지배 요인이라면,
k-medoids의 승리가 SFTF feature 때문인지 **단순히 연결 파트 수가 더 많기
때문인지**(manikin: k-means 10개 vs SFTF medoids 24개; Nefertiti: 6 vs 28)
현재 실험 설계로는 구분할 수 없다. 좌표-only k-means 대비 우위가 Wilcoxon
p=0.47로 유의하지 않다는 사실이 이 confound와 결합하면, 리뷰어는 "SFTF
feature의 기여는 입증되지 않았다"고 정당하게 결론 낼 수 있다.

**보완 실험 (택1 이상, 둘 다 하면 확실).**
- (a) **동일 파트 수 대조**: 각 형상에서 k-means의 요청 클러스터 수 K를
  올려, *연결성분 분리 후* 최종 파트 수가 k-medoids(SFTF fusion)와 ±1 이내로
  같아지도록 맞춘 뒤 동일 48방향 CuraEngine 프로토콜로 재평가. 12형상 전부가
  부담이면 지지 질량이 큰 6형상(manikin, Nefertiti, dragon, happy, lucy,
  liver)만이라도 수행.
- (b) **feature 절제(ablation)**: 동일 k-medoids 알고리즘에서 입력 행렬만
  3종 비교 — ①좌표만 `z(C)`, ②좌표+SFTF features(현행 Eq. 9), ③SFTF
  features만. 클러스터 수·시드·후처리 완전 동일. SFTF feature의 한계 기여를
  직접 분리한다.

**판정 기준.**
- 파트 수를 맞춰도 SFTF fusion이 이기면 → 본문 승격, 헤드라인 주장 확정.
- 파트 수를 맞추면 차이가 사라지면 → 주장을 "SFTF feature는 *같은 지지
  수준을 더 적은/더 해석 가능한 파트로* 달성한다" 또는 "role-coherent
  분해 + 경쟁력 있는 지지"로 재프레이밍. **이기도록 재튜닝 금지**
  (SFTFSoft 대응 원칙과 동일: 체리피킹 금지, 결과 정직 기술).

**예상 작업량**: (a) 야간 배치 1회(~수천 슬라이스), (b) 반나절 + 배치.

### 1-2. n=12 유의성 서술 정밀화

**문제.** "mean rank 2.00이 최고"와 "k-means 대비 p=0.47"이 같은 절에 있어
서술이 위태롭다. 현재 문장은 방어적으로 잘 쓰였지만, Abstract와 Conclusions
에는 p=0.47이 언급되지 않아 헤드라인만 읽으면 과대 해석된다.

**보완.**
- Abstract에 "best mean rank" 문구 옆에 한정어 추가(예: "…although its
  pairwise advantage over coordinate k-means is not significant on twelve
  shapes"). 1-1 실험이 성공하면 그 수치로 대체.
- 12형상 mean rank의 신뢰구간(부트스트랩)을 Supplementary에 추가하면
  Friedman/Wilcoxon과 서술이 일관된다. (재계산만, 실험 불필요)

---

## P2. 방어가 궁색한 항목 (리뷰 1라운드에서 반드시 질문 나옴)

### 2-1. Purity 지표의 이중성 정리

**문제.** SFTF-정의 클래스 기준 purity에서는 flow_region/support_flow가
최고(0.79/0.78)인데, 슬라이서 유래 클래스 기준에서는 k-medoids가 최고(0.82)
이고, 두 정의 간 방법 순위 상관은 중앙값 ρ≈0.27로 약하다. 현재는 "robustness
check"로 처리했지만, 리뷰어는 "그럼 purity로 무엇을 주장할 수 있는가"라고
물을 것이다.

**보완.**
- 본문에서 purity 주장을 한 문장으로 명확히 한정: SFTF-클래스 purity는
  "설계 의도(role-coherence) 달성도"의 내부 지표, Cura-유래 purity는 "실제
  지지 접촉과의 정합"의 외부 지표로 역할을 분리 서술.
- precision 0.17–0.62의 원인(희소 line-pattern 지지가 보호 대상 면의 일부만
  접촉)을 본문 한 줄로 승격 — 지금은 Methods에만 있어 Results에서 낮은
  precision을 처음 본 리뷰어가 놀란다.

### 2-2. 조립·접합의 부재를 스코프로 명시

**문제.** manikin 24파트, Nefertiti 28파트 분해는 접합면 처리·조립 순서·
연결부 강도 없이는 실제 제작 제안이 되지 못한다. Discussion에 한 줄 인정은
있으나, 파트 수가 큰 결과일수록 이 공백이 커 보인다.

**보완 (실험 없이 가능).**
- 스코프 문장을 Introduction 기여 목록 직후에 전진 배치: "본 논문의 산출물은
  *분할 그 자체*이며, 접합 설계는 Chopper류 후처리와 직교(orthogonal)"임을
  명시.
- 저비용 방증(선택): 대표 2형상에 대해 파트별 절단면 면적/최소 두께를
  trimesh로 **측정만** 하여 Supplementary 표 1개 추가 — "결과 파트가
  병리적으로 얇거나 파편적이지 않음"의 증거. (SFTFSoft R2 대응에서 쓴
  검사-only 전략과 동일)

### 2-3. Gao 재구현 비교의 공정성 방어

**문제.** 핵심 경쟁자(Gao et al. 2019)를 원저자 코드 없이 재구현으로
비교했고, Gao가 슬라이서 프로토콜에서 크게 진다(manikin 6.59 vs 1.62 g).
"재구현이 원본보다 약한 것 아니냐"는 질문이 나온다.

**보완.**
- Supplementary에 재구현 검증 근거 추가: 원논문 보고 사례 중 재현 가능한
  형상 1개에서 파트 수/지지 경향이 원논문과 일치함을 보이거나, 최소한
  재구현의 각 단계(greedy set-cover, ICM)가 원논문 수식과 1:1 대응함을
  표로 정리.
- Gao에게 유리한 조건 하나를 명시적으로 부여했음을 강조(자연 파트 수 사용
  등). 이미 본문에 있으면 문구를 "faithful reimplementation"에서 구체적
  검증 문장으로 강화.

### 2-4. anat-D1 패배 사례의 원인 분석 승격

**문제.** no-split이 anat-D1에서 최강(4.68 g)이고 모든 분할이 지지를
늘린다. 현재 "already-elongated"라는 짧은 설명뿐이다. 이는 오히려 기회다 —
"어떤 형상에서 분할 자체가 손해인가"의 판별 기준을 제시하면 논문의 실용
가치가 올라간다.

**보완.** 세장비(elongation)·볼록도 등 간단한 형상 지표와 "분할 이득
(no-split 대비 최선 분할의 지지 감소율)"의 관계를 12형상 산점도 1장으로
Supplementary에 추가. 재계산만으로 가능.

---

## P3. 저비용 정리 항목 (투고 전 일괄 처리)

### 3-1. 인용 동기화 [SFTF 행선지 확정 즉시]

- `\bibitem{sftf}`가 현재 "Prog Addit Manuf. 2026. Forthcoming."인데, SFTF
  본편은 3D Printing and Additive Manufacturing(TDP)으로 간다. **행선지 확정
  후 즉시 수정**. 미게재 상태로 투고하는 경우 저널 정책에 맞는 표기
  (submitted/under review + 사본 첨부)로 통일.
- 같은 저널(TDP)에 SFTF 본편과 Cluster를 모두 투고할 경우 커버레터에 두
  논문의 관계(본편=방향 후보 생성, 본 논문=per-face 데이터 재사용 분할)와
  중복 없음(살라미 아님)을 선제 명시.

### 3-2. 데이터 공개 수준 상향

- 현재 "upon acceptance / on reasonable request"는 SFTF 본편(공개 GitHub
  repo)보다 후퇴. 최소한 분할 코드와 12형상 CuraEngine 평가 스크립트,
  요약 CSV는 투고 시점에 공개 repo로 올리고 URL을 명시할 것. 검증 중심
  논문에서 재현성 인프라는 심사에 실질 가점.

### 3-3. 하드웨어 기술 교차 확인

- Cluster: "RTX 5070 Ti, 64 GB RAM" vs SFTF 본편: "RTX 5080, 125 GB RAM"
  (동일 Ryzen 9 9950X3D). 같은 머신이면 한쪽이 오기이므로 실측으로 확인 후
  통일. 다른 머신이면 그대로 두되 각 논문 수치가 해당 머신에서 나온 것인지
  확인.

### 3-4. 원고 체재 점검

- TDP 제한(본문 4000단어, 표 ≤5, 그림 ≤8) 대비 실측 단어 수 확인. 현재
  본문에 표 4개는 준수하나 단어 수가 경계선일 가능성 — pandoc plain export
  로 카운트해 여유 확보. 1-1 실험 표가 추가되면 기존 표 1개(예:
  Table `tab:validate`)의 Supplementary 이동 검토.
- `fig_method_taxonomy_from_pdf-1.png`(PDF 변환 래스터) 해상도 확인 —
  인쇄 기준 300dpi 미달이면 벡터 재출력.
- 단독 저자인데 본문이 "we" 서술 — TDP 스타일상 허용되지만 "the author"
  혼용 여부 일관성 확인.
- Supplementary Note S1(스크리닝 추정이 순위를 뒤집는 2형상) 상호참조가
  본문 두 곳에서 걸리는데, 해당 Note의 수치 표가 실제로 존재하는지 컴파일
  후 미해결 참조 0건 확인.

---

## 실행 순서 제안

| 단계 | 내용 | 소요 |
|---|---|---|
| D1 | 1-2, 2-1, 2-2, 3-3, 3-4 (문구·재계산·점검) | 반나절 |
| D1 야간 | 1-1(a) 동일 파트 수 배치 + (여유 시) 1-1(b) 절제 | 배치 |
| D2 | 1-1 결과 판정·표화, 필요 시 헤드라인 재프레이밍 | 반나절 |
| D2 | 2-3 Gao 검증 근거, 2-4 산점도, 3-2 repo 준비 | 반나절 |
| D3 | 3-1 인용 동기화(행선지 확정 후), PDF 재빌드, lockstep 검증 | 짧게 |

## 하지 않을 것

- 1-1에서 SFTF fusion이 지는 결과가 나왔을 때 이기도록 파라미터 재튜닝
  (체리피킹). 지면 재프레이밍으로 대응한다 — 논문의 나머지 가치(외부 검증
  체계, 재배향 자유도 발견, role-coherent 분해)만으로도 성립한다.
- p=0.47을 숨기거나 각주로 강등하는 것. 오히려 1-1 실험과 함께 정면 배치.
- Gao 결과를 표에서 제외하는 것.
