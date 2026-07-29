# SFTF → 사출 금형 발형(發型) 방향 최적화 연구 기획

> SFTF(Support Flow Tensor Field, AM 빌드 배향 후보 생성기)를 **사출/주조 금형의
> 발형(draw) 방향·언더컷 최소화** 문제로 이식하는 연구 줄기. 목표는 impact factor가
> 아니라 **현장(견적·금형 설계 자동화)에 실제로 도움이 되는 것**.

원본 논문: *Support Flow Tensor Field for Fast Build-Orientation Candidate
Generation in Support-Requiring Additive Manufacturing* (Sul et al.).

---

## 0. 한 줄 요약

SFTF의 진짜 재사용 자산은 "서포트 배향"이라는 *응용*이 아니라 세 가지 *엔진* —
**(1) 방향 의존 비대칭 flow tensor(ray-cast 내부 가시성), (2) ground-node Rayleigh
통합, (3) 값싼 warm-start + 적응 국소 검증(AVE)** — 이다. 이 셋은
**금형 발형 방향 = S²(정확히는 RP²) 위의 고비용 블랙박스 최적화** 문제에 거의 그대로
옮겨간다. 가장 비싼 부분(언더컷/이형성 검증)을 SFTF가 수 ms 사전선별로 줄여, 견적
단계에서 발형 방향·side action 유무·die-lock을 빠르게 스크리닝한다.

---

## (a) SFTF 수식의 금형 매핑

### 문제 재정의
부품(고정 메시) + 발형 축 `d ∈ S²`. 2판 금형이면 `+d`(캐비티)·`−d`(코어) 두 반쪽으로
면이 갈리며, **언더컷** = 자기 반쪽 방향으로 빠지려는데 다른 면에 가려져(occlusion)
못 빠지는 면 → 슬라이드/리프터(side action)를 강제. 목표는 언더컷(→ side action
수·부피) 최소화하는 `d` 탐색. AM의 "서포트 부피 최소 배향 = S² 탐색"과 동형.

### 대응표
| SFTF (AM) | 금형 발형 |
|---|---|
| build direction `d` (중력, 한쪽) | draw axis `d`, **±d 양쪽 패스** |
| critical angle `θc` | **draft angle `α`** (이형 구배) |
| overhang coeff `oᵢ(d)` | draft-deficiency / 이형 대상 가중치 |
| ray로 receiver 탐색 (internal visibility) | ray로 **occlusion(언더컷) 판정** |
| face-to-face support | 내부 언더컷 (면 `i`가 `j`에 가려 못 빠짐) |
| height `h_ij`, 감쇠 `w_ij` | 언더컷 깊이 = 슬라이드 행정 |
| no receiver → build plate (ground node) | ray가 부품 밖 탈출 → 파팅면 직접 이형 |
| support volume `v_ss` (비싼 TOMO) | 언더컷 부피 / side-action 수 (비싼 CAE) |
| AVE 하드케이스 확대 | 경쟁 basin·경계 언더컷 많은 부품에 동일 적용 |

### 통합 Rayleigh 비용의 이식
원본: `R(d) = Σ_{(i,j)∈S} oᵢ w_ij (nᵢ·d)(nⱼ·d) + Σ_{i∈G} oᵢ`.
금형판: 양쪽 패스 합산 + 면 가중치를 이형 면적 기반으로 + **ground 항을
penalty→reward로 부호 반전**:

```
U(d) = Σ_{entrapped, ±} gᵢ w_ij (nᵢ·d)(nⱼ·d)  −  λ · Σ_{clean release} gᵢ
```

`F⁺(d)=Σ gᵢ⁺ w_ij (nᵢ⊗nⱼ)` (그리고 `−d`로 `F⁻`)가 "어느 면이 어느 면에 갇히는가"라는
**방향 의존 entrapment 관계**를 비대칭 텐서로 인코딩 — SFTF 원래 구조 그대로.
ground-node 항등식 `dᵀ(d⊗d)d=1`도 부호만 바뀐 채 보존.

### 핵심: 거의 안 건드린다
그대로 재사용 — 512 Fibonacci 샘플 → 콘 재샘플 → 각도 NMS top-K basin → 비싼 검증기는
±10° 윈도우에서만 → AVE. **교체되는 건 면 단위 커널(`oᵢ→gᵢ`, receiver 유효조건,
양쪽 패스)과 검증기뿐.**

---

## (b) 새로 생기는 구현 이슈 (AM엔 없던 것)

### Tier A — 골격을 바꿔야 하는 것 (필수)
- **A1. 탐색 공간이 S²가 아니라 RP².** `d`와 `−d`는 같은 발형 축 → antipodal 식별,
  후보 절반, NMS도 antipodal 병합. (덤으로 2× 가속.)
- **A2. 언더컷 = "feasible side-action 방향이 존재하는가"라는 중첩 문제.** AM에선
  overhang이 서포트로 *항상* 해소되지만, 금형에선 언더컷마다 부품과 충돌하지 않는
  이형 방향이 있어야 하고 없으면 **die-lock**. entrapment 텐서가 알려주는 차폐
  방향을 side-action 후보의 seed로 사용. 진짜 비용은 *언더컷 부피*가 아니라
  **side-action 개수** → 언더컷 면을 호환 이형 방향으로 **클러스터링**. ← 진짜 코어.
- **A3. Draft를 언더컷과 분리된 별도 하드 채널로.** `nᵢ·d≈0` 수직 벽은 언더컷이
  아니어도 스커핑·이형 손상. 실패 모드 2개(언더컷 채널 vs draft 채널)가 trade-off →
  논문의 rank-normalized scoring이 다채널 결합에 그대로 적합.
- **A4. 검증기 출력이 스칼라가 아니라 구조화.** (i) 언더컷 클러스터, (ii) side-action
  수, (iii) die-lock 플래그. "ratio" 단일 지표 → 다중 지표. AVE confidence도 재정의.

### Tier B — 점수 벡터에 새 항 (중간)
- **B1.** 파팅 라인 일관성/복잡도 proxy(예: `nᵢ·d≈0` 밴드 면적·산포)를 피처로 추가.
- **B2.** `w_ij` 감쇠를 거의 계단형(슬라이드 필요/불필요)으로 재형성; 랭킹용은 부드럽게.

### Tier C — 산업 채택을 위한 제약·강건성
- **C1. 제약·가중 S² 탐색.** Class-A 면 파팅/게이트 금지, 이젝션 코어 측, 기능 축
  정렬 → 금지/선호 축 마스크 + 지정 면 통과 벌점.
- **C2. CAD 메시 강건성.** sliver/non-manifold/미세 필렛(경계 밴드) → ray epsilon,
  first-hit fallback, 가능하면 draft는 원본 B-rep에서.
- **C3. 단일 최적해가 아니라 다중 후보 의사결정 출력** (top-K basin + 항별 분해)
  → DFM 의사결정 자료.

> 정리: 새로 만들 건 딱 두 덩어리 — **(A2) side-action feasibility/클러스터링 +
> die-lock**, **(A4) 구조화된 moldability 검증기**. 나머지는 항·마스크 추가 수준.

---

## (c) 산업 검증 시나리오

### 부품 난이도 사다리
| Tier | 성격 | 정답 자명? | 검증 목적 |
|---|---|---|---|
| T0 | draft만 있는 단순 부품 | 자명 | 위생 검사 |
| T1 | side-action 1개 명백 | 거의 자명 | 단일 언더컷·이형방향 시드 |
| T2 | 경쟁 발형·다중 슬라이드 | 모호 | basin 경쟁·side-action 수 (핵심) |
| T3 | die-lock / 재설계 필요 | 함정 | die-lock recall (가장 비싼 실패) |

출처: Thingi10K 사출 적합 필터 + DFM 교재 예제 + (가능하면) **실제 양산 부품(채택된
발형·실제 슬라이드 수가 골드)**.

### 정답(GT) — 세 겹
1. exact moldability 검증기(=TOMO 자리, 본 프로토타입) — 언더컷/side-action/die-lock.
2. 전문가 주석(실제 발형·슬라이드 수) — 진짜 골드.
3. 상용 CAE(NX Mold Wizard / Moldflow) 교차검증.

### Baseline (이겨야 할 대상)
PCA 주축, 대칭 support tensor 고유벡터, **바운딩박스 6면 휴리스틱**,
budget-matched uniform/random, 엔지니어 수작업, 풀스윕+exact(oracle 상한).

### 지표 — 산업 언어
- **(1순위) side-action 수 일치율** (exact / ±1) — 슬라이드 1개 = 금형비·사이클 직결.
- **(2순위) die-lock recall** — 견적 단계에서 놓친 die-lock이 가장 비싼 사고.
- 검증 예산 %(풀스윕 대비), 첫 양호 후보까지 ms, draft 결손 면적, 전문가 일치(κ),
  툴링 비용 proxy(슬라이드 수 차 × 단가).

### 프로토콜 (논문 엄밀성 재사용)
LOMO/nested CV(과적합 통제), budget-matched 대조군(배치 vs 예산), AVE 전/후
최악 오차, T3(die-lock) 분리 보고, coarse-grid 타이밍·확장성 감사.

### "so what" — 표 너머
- 견적-단계 데모: 부품 투입 → <1s에 top-3 발형 전략 + 슬라이드 수 + Class-A 충돌 +
  die-lock 플래그.
- 시간-동작 비교(엔지니어 단독 vs +도구).
- **가장 강력한 한 방 — 회고적 파일럿**: 협력 금형사의 과거 N개 잡에 도구를 돌려
  (i) 추천 발형이 실제 채택과 일치했는가, (ii) 실제 발생한 비싼 ECO를 견적 시점에
  잡아낼 수 있었는가.

### 정직성(함정)
GT 순환(독립 GT 필수), 부품 선택 편향(T2·T3 필수 포함), 메시 품질 교란(공변량 기록),
범위 한정("발형/언더컷 사전선별"로 주장 못 박기 — 게이트·냉각·휨은 별개).

---

## 다음 단계 (구현 로드맵)

1. **[완료/프로토타입] exact moldability 검증기 (= TOMO 자리).**
   `python/src/moldability/` — ray-cast 접근성으로 면 단위 분류 + 언더컷 클러스터 +
   side-action 수 + die-lock + 발형 축 sweep. 분석적 테스트 부품(T0·T2·T3) 8개 통과.
   상세·확장은 `python/src/moldability/BUILDSPEC.md`.
2. **SFTF 후보 생성기의 금형판** — 위 (a) 커널 교체로 값싼 랭킹 구현, 검증기를
   ±10° 윈도우 warm-start로 호출.
3. **AVE 금형판** — die-lock 근접/경쟁 basin 신호로 escalation.
4. **데이터셋·벤치마크** — (c)의 난이도 사다리 + GT 구축.
5. **견적-단계 데모 + 회고적 파일럿**.
