# SFTF → 반도체 전력공급망(PDN) IR-drop : PoC 연구기획

> SFTF(Support Flow Tensor Field)와 분할 변형(SFTF-Clustering)을 **반도체 PDN의
> 전원/접지 패드(C4 범프) 배치와 전력도메인 분할** 로 이식하기 위한 수식 매핑과
> 최신문헌 대비 차별점. (작성 2026-06, `SFTF_PDNElectric_dev`)

---

## 0. 한 줄 정리

> SFTF에서 **소스 = 셀 전류수요 `i_load`**, **receiver = 최소저항 패드 경로**,
> **bottom-plate(ground node) = VDD/GND 패드**로 치환하면, *서포트 흐름 트리*가
> *전류 분배망*이 되고, *서포트 물량 최소화*가 *IR drop(전압강하) 최소화*가 된다.
> SFTF에서 B(빌드플레이트)항이 비용을 지배했듯, IR drop은 **"전류 × 패드까지
> 거리(저항)"** 가 지배한다 — 같은 자리.

---

## 1. 기호 대응표 (SFTF ↔ PDN)

| SFTF (적층제조) | 기호 | PDN PoC (반도체) | 기호 |
|---|---|---|---|
| 빌드방향 | `n ∈ S²` | (단일방향 없음) 또는 층별 선호배선 방위 | `d ∈ S¹` |
| 삼각면 i | `i` | 다이 격자 셀(또는 인스턴스 타일) | `i` |
| 면 법선 | `m_i` | 국소 전류흐름 방향(셀→패드) | `m_i` |
| 면 면적 | `A_i` | 셀 면적/타일 가중 | `A_i` |
| 면 중심 | `c_i` | 셀 좌표 `(x_i, y_i)` | `c_i` |
| 오버행 `O_i(n)` | 흘릴 양 | 스위칭 전류수요 `q=C·V·f·…` | `i_load` |
| receiver 탐색(레이캐스트) | | 최소저항 경로로 최근접 패드 | `p = pad(i)` |
| 지지 높이 | `h_ij` | 저항거리(거리×시트저항) | `r_ij` |
| 면-대-면 가중 | `w_ij=O_i/(1+α h_ij)` | `w_ij = i_load/(1+α r_ij)` | |
| 바닥판(ground node) | `B(n)` | **VDD/GND 패드(C4 범프) 항** | `B_pdn` |
| 통합 Rayleigh | `R̃=R+B` | 통합 IR-비용 텐서항 | `R̃_pdn` |
| 분할+부품별 재배향 | | **전력도메인 분할 + 다패드** | domains + multi-pad |
| TOMO 국소검증 + AVE | | **정밀 IR/EM 사인오프 + 적응검증** | grid-solve + escalate |

`α = 1/D`, `D` = 다이 대각(특성길이).

---

## 2. 수식 매핑 (SFTF 원식 → PDN 대응식)

### 2.1 소스 항 — overhang → 전류수요
SFTF의 `O_i(n)` 자리에 **셀 전류수요** `i_load,i ≥ 0` 를 둔다(스위칭 활동도·용량·
전압·주파수에서 추정). 방향성(빌드방향 의존)은 PDN의 고정-패드 케이스에서 사라지고
`i_load` 가 그 자리를 대신한다(하수 `q_i` 와 동일 구조).

### 2.2 receiver 탐색 — 레이캐스트 → 최소저항 패드
SFTF: 면 i에서 `−n` 으로 첫 유효 receiver. PDN: 셀 i에서 **최소 저항거리**의 패드 p.
유효쌍 집합 `R` = 전류 분배 아크. (정밀하게는 저항망 위 최단/최소저항 경로,
PoC에서는 최근접 패드 Voronoi로 근사.)

### 2.3 흐름 텐서 — F(d)
```
SFTF :  F(n)   = Σ  w_ij A_i A_j m_i m_jᵀ
PDN  :  F_e(d) = Σ  w_ij A_i A_j m_i m_jᵀ ,   w_ij = i_load/(1+α r_ij)
```
재배선 가능 케이스에서 `R(d)=−dᵀ F_e,sym d` 의 Rayleigh가 **층별 선호배선 방위별
혼잡/IR 프록시**가 된다. 고정-패드 케이스에서는 텐서가 스칼라로 축약된다(2차적).

### 2.4 ground node = 패드 (★ 핵심 일치)
SFTF에서 받쳐 줄 면이 없는 오버행은 빌드플레이트가 받친다. PDN에서 셀의 전류는
결국 **전원/접지 패드**로 빠진다. 패드를 **가상 receiver(ground node)** 로 두면:
```
B_pdn = Σ_i i_load,i · (1 + α L_iP) ,   L_iP = 셀 i → 최근접 패드 저항거리
R̃_pdn = R + B_pdn
```
즉 **패드 = 빌드플레이트**의 1:1 대응. SFTF에서 B가 가장 강한 예측자였다는 결과
(Spearman 평균 0.58)는 PDN에서 **IR drop ≈ "전류 × 패드까지 거리"가 지배**한다는,
정전기·전력망의 잘 알려진 1차 성질과 일치한다. SFTF의 ground-node 텐서는 그
1차 성질에 **닫힌형(closed-form) 텐서 해석**을 부여한다.

### 2.5 후보 점수와 생성
```
SFTF :  J(n) = R̃(n) + P(n) ,   P = Σ O_i A_i A_j
PDN  :  J_e  = R̃_pdn + P_e ,   P_e = Σ i_load A_i A_j
```
후보 = **패드 위치 × 패드 개수 × 전력도메인 분할**(고정-패드) 및 선호배선 방위 `d`
(재배선). 생성·NMS·rank 정렬은 SFTF와 동형.

### 2.6 분할 = 전력도메인/다패드 (SFTF-Clustering 이식)
- **cut-induced** : 한 도메인을 본류 패드망에서 끊어 별도 패드/레귤레이터를 다는 비용.
- **reorientation** : 각 도메인이 자기 최적 패드 집합에 서는 이득 — **텐서 가산성
  `F(part)=ΣF_part` 로 재최적화 없이** 추정.
- **반직관 발견 이식**: "하나의 큰 단일 전원망보다 **분산형 다패드/다도메인**이 총 IR
  drop·금속면적을 줄인다"(SFTF: 조각별 재배향이 지지를 줄인다와 동형).

### 2.7 ray-free 추정자 & 검증
SFTF-Clustering: footprint `s[i,k]=A_i·O_i(d_k)` → Spearman 0.80, height-field 보정
0.90. PDN 대응: 격자 IR 솔버를 돌리지 않고 **`Σ i_load × 패드거리`(footprint)** +
**누적 전류밀도 보정**(heightfield 대응)으로 IR 랭킹 예측. **AVE → 적응적 IR/EM
검증 확대**: 후보 간 근소차·경계해·전류밀도(EM) 위반 플래그가 켜질 때만 정밀 솔버
호출.

---

## 3. 최신문헌 대비 차별점

PDN/IR-drop 연구의 대표 갈래:

1. **수치 사인오프(정적 IR)**: 전력망을 대형 선형계 `G·v = i`(저항 컨덕턴스 행렬)로
   풀어 노드 전압강하 산출. 정확하나 대형 그리드에서 비싸다(상용 사인오프 솔버).
2. **ML 대체모델(surrogate)**: CNN/GNN으로 IR-drop 맵을 빠르게 예측.
   [Fast IR drop estimation with ML, ICCAD 2020; IncPIRD; GridNet(EM-induced);
   PDNNet(GNN-CNN, 2024); 2023 ICCAD CAD Contest Problem C(static IR ML)].
   빠르지만 **학습데이터·기술/설계별 재학습 필요, 블랙박스**.
3. **Decap 배치 최적화**(심층강화학습 등). [2.5D PDN decap RL, arXiv 2407.04737]
4. **패드/C4 범프 배치·백사이드 전력공급(BSPDN)**: 패드 배치·후면 전력으로 IR
   ~10% 절감. [IRDS 2024 packaging; backside power delivery]
5. **IR-aware 배치·스큐 스케줄링**(타이밍 슬랙으로 IR 완화).
6. **ML 핫스팟 검출 + 병렬 시뮬**(가속). [Parallel sim + ML hotspot, MLCAD 2024]

**SFTF-PDN이 다른 점 (포지셔닝):**

- **(D1) 사인오프 솔버도, 학습형 대체모델도 아닌 무학습(training-free) 후보생성기.**
  ML 대체모델(문헌 2)은 라벨 IR 맵으로 학습하고 기술/설계마다 재학습한다.
  SFTF-PDN은 **닫힌형 텐서 + ground-node 스칼라**로 패드배치·도메인분할을 학습
  데이터 0으로 ms에 랭킹한 뒤, 상위 소수만 정밀 솔버에 넘긴다.
- **(D2) ground-node 텐서 통합 = IR-drop 1차항의 닫힌형 해석.** "전류 × 패드거리"가
  IR을 지배한다는 사실에 `R̃=R+B` 라는 단일 텐서 contraction 근거를 부여.
- **(D3) 텐서 가산성으로 전력도메인 분할을 재-IR-solve 없이 추정.** 도메인 후보마다
  격자 IR을 다시 풀지 않고 `F(part)=ΣF_part` 로 분할 이득을 닫힌형으로 얻는다.
- **(D4) 적응적 IR/EM 검증 확대(AVE).** 모든 후보에 균일 시뮬을 돌리지 않고,
  불확실·핫스팟 케이스에만 정밀 솔버를 확대(문헌 6의 ML 핫스팟 검출과 목적은
  같으나 **무학습·신뢰도 트리거**라는 점이 다름).
- **(D5) 패드배치 + 도메인분할 + 핫스팟 스크리닝을 한 점수로 통합.**

**정직한 한계 (선점 서술):**
- PDN은 **메쉬(루프)·다중패드·스위칭 동적 droop·decap·EM 신뢰성**까지라, 단일방향
  텐서 `F(n)` 은 부적합 — 상수도/하수와 같은 **부분적합**. 텐서가 아니라 **B항 +
  분할 + 사인오프 앞단 warm-start** 가 살아남는다.
- SFTF-PDN은 **정적 IR의 1차 프록시·랭킹 도구**이지 절대 IR 값 예측이 아니다.
  절대정확도는 학습된 CNN/GNN이 더 높을 수 있다 — 본 기법의 가치는 **무학습·해석
  가능·warm-start**.
- 정밀 사인오프(`G·v=i`, 동적 droop, EM)는 여전히 전용 솔버 몫.

---

## 4. 최소 PoC 설계 (다음 단계)

1. **입력**: 합성 다이 격자 + 셀별 전류수요 맵 + 후보 패드 위치 집합.
2. **패드 할당**(= SFTF receiver): 최근접/최소저항 패드 Voronoi.
3. **SFTF-PDN 점수 `J_e`**: 패드배치 × 도메인 분할(× 재배선 방위 `d`).
4. **정밀검증**: 저항망 `G·v=i` 를 `scipy.sparse` 로 풀어 max/mean IR drop 측정
   (정적 IR 사인오프 대역). 향후 동적 droop·EM 추가.
5. **검증지표**: 값싼 `J_e`(또는 `B_pdn`)와 IR-solve 랭킹의 **Spearman ≥ 0.8**
   (Clustering과 동일 틀), 베이스라인(균일 패드격자·랜덤) 대비 우위.
6. **확장**: AVE(EM·근소차 트리거), 텐서가산성 도메인 탐색, decap 후보.

### 의존성 메모 (아직 pyproject 미반영)
- 그래프/도메인: `networkx`
- 정밀 사인오프: 전용 power-grid/SPICE 솔버(현재는 `scipy.sparse` 자체 IR 솔버로 대역)

---

## 참고문헌 (확인용 URL)

- Fast IR drop estimation with machine learning. *ICCAD* 2020.
  https://dl.acm.org/doi/10.1145/3400302.3415763
- PDNNet: PDN-Aware GNN-CNN Heterogeneous Network for Dynamic IR Drop Prediction. 2024.
  https://arxiv.org/html/2403.18569v2
- Invited: 2023 ICCAD CAD Contest Problem C — Static IR Drop Estimation Using ML.
  https://ieeexplore.ieee.org/document/10323767
- Hierarchical Decoupling Capacitor Optimization for PDN of 2.5D ICs via Deep RL.
  arXiv:2407.04737. https://arxiv.org/html/2407.04737v1
- A Parallel Simulation Framework Incorporating ML-Based Hotspot Detection for
  Accelerated Power Grid Analysis. *MLCAD* 2024.
  https://dl.acm.org/doi/10.1145/3670474.3685947
- 2024 IRDS Executive Packaging Tutorial (C4/backside power delivery).
  https://irds.ieee.org/images/files/pdf/2024/2024IRDS_EPT-Part1.pdf
- Machine Learning Methods for Fast Evaluation of Static IR Drop. *Technologies* 2026.
  https://www.mdpi.com/2227-7080/14/3/169
