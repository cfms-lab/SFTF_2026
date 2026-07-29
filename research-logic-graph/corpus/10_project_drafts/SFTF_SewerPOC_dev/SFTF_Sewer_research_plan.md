# SFTF → 자연유하 하수/우수 관망 라우팅 : PoC 연구기획

> SFTF(Support Flow Tensor Field, 적층제조 빌드방향 후보생성기)와 그 분할 변형
> (SFTF-Clustering)을 **건축/토목의 자연유하 하수·우수 관망 설계**로 이식하기 위한
> 수식 매핑과 최신문헌 대비 차별점 정리. (작성 2026-06, `SFTF_SewerPOC_dev`)

---

## 0. 한 줄 정리

> SFTF에서 **빌드방향 n = 중력/주배수방향**, **receiver 면 = 하류 노드**,
> **bottom-plate(ground node) = 방류구(outfall)** 로 치환하면, *서포트 흐름 트리*가
> 그대로 *배수망(dendritic arborescence)* 이 되고, *서포트 물량 최소화*가
> *굴착·관거 비용 최소화*가 된다. SFTF는 새 최적화기가 아니라 **값싼 후보생성기 +
> 적응적 정밀검증(SWMM)** 이라는 역할을 그대로 유지한다.

---

## 1. 기호 대응표 (SFTF ↔ Sewer)

| SFTF (적층제조) | 기호 | Sewer PoC (하수/우수) | 기호 |
|---|---|---|---|
| 빌드방향(단위벡터) | `n ∈ S²` | 중력방향(고정) 또는 재성토지의 주배수 방위 | `n` (고정 `ẑ`) 또는 방위 `φ ∈ S¹` |
| 삼각면 i | `i` | 배수 노드(맨홀·우수받이·DEM 셀) | `i` |
| 면 법선 | `m_i` | 노드의 국소 지표 경사벡터(법선) | `m_i` |
| 면 면적 | `A_i` | 노드 기여 집수면적 | `A_i` |
| 면 중심 | `c_i` | 노드 좌표 `(x_i,y_i,z_i)` | `c_i` |
| 오버행 계수 | `O_i(n)=max(0,−m_i·n)` | 유출 부하(합리식 `q_i=C·i_r·A_i`) | `q_i ≥ 0` |
| 레이캐스트 receiver 탐색 | `j = first hit along −n` | 하류 노드 탐색(D8/D∞ 최급강하) | `j = downslope(i)` |
| 지지 높이 | `h_ij(n)=(c_i−c_j)·n` | 표고 낙차 | `Δz_ij = z_i−z_j` |
| 면-대-면 가중 | `w_ij=O_i/(1+α h_ij)` | 구간 라우팅 비용 가중 | `w_ij=q_i/(1+α d_ij)` |
| 바닥판 높이 | `z_plate=min_v v·n` | 방류구 표고/도달거리 | `z_out`, `L_iP` |
| 바닥판 패널티 | `B(n)` | 방류구까지 누적유량·거리항 | `B_sewer` |
| 통합 Rayleigh | `R̃=R+B` | 통합 배수비용 텐서항 | `R̃_sewer` |
| 분할+부품별 재배향 | partition + reorient | 소유역 분할 + **다방류구(분산형)** | sub-basins + multi-outfall |
| TOMO 국소검증 + AVE | verify + escalate | **SWMM/EPANET 수리검증 + 적응확대** | verify + escalate |

여기서 `α = 1/D` 는 SFTF에서 바운딩박스 대각선 `D` 의 역수. Sewer에서는
대상 유역의 특성길이(예: 유역 대각선 또는 평균 관거 연장)로 `D`를 잡는다.

---

## 2. 수식 매핑 (SFTF 원식 → Sewer 대응식)

### 2.1 유출(소스) 항 — overhang → runoff
SFTF는 면이 빌드방향에 등돌린 정도 `O_i(n)=max(0,−m_i·n)` 를 "받쳐야 할 양"으로 본다.
Sewer에서 "흘려보내야 할 양"은 지형 법선이 아니라 **수문 부하**다:

```
q_i = C_i · i_r · A_i          (합리식; C=유출계수, i_r=강우강도, A=집수면적)
```

degenerate 케이스(고정 중력)에서는 `O_i` 의 방향성이 사라지고 `q_i` 가 그 자리를
대신한다. 재성토 가능 신규단지에서는 `O_i(φ)` 형태의 방향 의존성이 부분적으로
살아남아(설계 경사면이 어느 방위를 향하는가) SFTF의 방향 스윕이 유효해진다.

### 2.2 receiver 탐색 — 레이캐스트 → 흐름방향(D8/D∞)
SFTF: 면 i에서 `−n` 으로 레이를 쏴 첫 유효 receiver 면 j를 찾고, 조건은
(자기 자신 아님) ∧ (양의 높이 `h_ij>0`) ∧ (receiver가 빌드방향을 충분히 향함
`m_j·n>0.05`).
Sewer: 노드 i에서 **최급강하**로 하류 노드 j를 찾고, 조건은
(자기 자신 아님) ∧ (양의 낙차 `Δz_ij>0`, 즉 자연유하) ∧ (j가 더 큰 누적유량을 받을 수
있는 유효 하류). → 이는 GIS 수문학의 **D8/D-infinity 흐름방향 + 흐름누적**과 동형.
유효쌍 집합 `R(n)` = 배수 아크 집합 `{(i→j)}`.

### 2.3 흐름 텐서 — F(n)
```
SFTF :  F(n)   = Σ_(i,j)∈R   w_ij · A_i A_j · m_i m_jᵀ
Sewer:  F_s(φ) = Σ_(i,j)∈R   w_ij · A_i A_j · m_i m_jᵀ ,   w_ij = q_i/(1+α d_ij)
```
재성토 케이스에서 `R(φ)=−nᵀ F_s(φ) n` 의 Rayleigh 지수가 **주배수 방위별 총 관거비용
프록시**가 된다. 고정 중력 케이스에서는 텐서 contraction이 스칼라 누적비용으로 축약된다.

### 2.4 ground node = 방류구 (★ 핵심 일치)
SFTF에서 받쳐 줄 면이 없는 오버행은 결국 빌드플레이트가 받친다:
```
z_plate(n) = min_v v·n ,   h_iP = c_i·n − z_plate
B(n) = Σ_{i∈B(n)} O_i(n) · A_i · (1 + α h_iP)
```
그리고 이는 **법선이 `n` 인 가상 receiver(=ground node)를 추가**한 augmented 텐서의
정확한 Rayleigh 기여임을 보였다(`R̃=R+B`, 수치오차 `1e-12`).

Sewer 대응: 어떤 노드의 흐름은 결국 **방류구/처리장**으로 빠진다. 방류구를
**법선이 배수방향인 가상 노드(ground node)** 로 두면:
```
B_sewer = Σ_{i→outfall} q_i · (1 + α L_iP) ,   L_iP = 노드 i→방류구 경로 비용(거리·낙차)
R̃_sewer = R + B_sewer
```
즉 **방류구 = 빌드플레이트**라는 1:1 대응이 성립하고, SFTF에서 `B`(빌드플레이트 항)가
가장 강한 단일 예측자였다는 결과(수정 엔진 재생성 기준 Spearman 평균 0.59, `R̃` 0.61;
단, organic freeform 군 한정 — 대형 기계부품군에서는 상관이 ≈0으로 소멸함이
SFTF v2에서 확인됨)는 Sewer에서
**"총유량 × 방류구까지 거리"가 망 비용을 지배**한다는 명제로 옮겨진다. 흥미롭게도
이는 기존 하수문헌의 **"누적유량 최소화(minimum cumulative flow) 레이아웃"** 목적과
같은 자리를 가리킨다(§3 참조) — 즉 SFTF의 ground-node 텐서가 그 휴리스틱에
**닫힌형(closed-form) 텐서 해석**을 부여한다.

### 2.5 후보 점수와 생성
```
SFTF :  J(n) = R̃(n) + P(n) ,   P = Σ O_i A_i A_j
Sewer:  J_s  = R̃_sewer + P_s ,  P_s = Σ q_i A_i A_j   (면-대-면 자가배수 항)
```
생성 절차도 동형으로 옮긴다: (고정중력) 후보 = 방류구 위치 × 소유역 분할 조합;
(재성토) 후보 = 512-Fibonacci 대신 **방위 `φ` 의 1차원 조밀 샘플 → 국소 정밀화 →
각도 NMS** 로 분산형 후보 방위 추출. 최종 정렬은 SFTF처럼 rank-정규화 피처
`[J, R, P, B, H, …]` 로.

### 2.6 분할 = 다방류구 (SFTF-Clustering 이식)
SFTF-Clustering의 핵심은 분할 비용을 두 항으로 분해한 것:
- **cut-induced** : 지지 컬럼을 receiver에서 끊는 비용
- **reorientation** : 각 조각이 자기 최적 방향에 서는 이득 — **텐서 가산성으로 공짜 계산**
```
F(partition) = Σ_parts F_part   ⇒   각 sub-basin 최적 방류방향을 재최적화 없이 추정
```
Sewer 대응: 유역을 소유역으로 나눠 **각 소유역이 자기 가까운 방류구로** 빠지게 한다.
- cut-induced : 간선(trunk)을 끊어 한 소유역을 본류 방류구에서 분리하는 비용
  (별도 방류구·펌프장 신설)
- reorientation : 각 소유역이 자기 최적 방류구·경사에 서는 이득
- 텐서 가산성 → 분할안마다 SWMM/MIP 재실행 없이 소유역별 비용변화를 닫힌형으로 추정.

SFTF-Clustering의 **반직관적 발견**("컬럼을 온전히 두는 것이 아니라 조각별 재배향
자유도가 서포트를 줄인다")은 Sewer에서 **"하나의 깊은 간선관거보다 분산형
다방류구가 총 굴착량을 줄인다"** 로 옮겨지며, 이는 분산형 배수 레이아웃 연구와 일치.

### 2.7 ray-free 추정자 & 검증
SFTF-Clustering은 레이 없이 additive footprint 프록시로 내부 스크린 랭킹을
예측했다(v2 정정 기준: 마네킹에서 footprint 단독 Spearman 0.50, 높이장 보정
추가 시 5개 방법 순서 재현 ρ=1.00 — 단 형상 의존적이어서 "보정된 대리량"이
아니라 **후보 제안용**으로 위상 정리됨). Sewer 대응:
SWMM을 돌리지 않고 **누적유량+깊이 추정자**로 총비용 랭킹을 예측(목표 Spearman ≥0.8),
상위 후보만 SWMM으로 정밀검증. **AVE → 적응적 수리검증 확대**: 후보 간 근소차,
경계해, 월류(surcharge) 위험 플래그가 켜질 때만 검증 후보를 넓힌다.

---

## 3. 최신문헌 대비 차별점

기존 하수 관망 최적설계 연구는 크게 (a) 위상(layout) 최적화와 (b) 수리설계(diameter/
slope) 최적화로 나뉘며, 대표 갈래는 다음과 같다.

1. **MIP + 최단경로(Bellman-Ford) 수리설계, 비용계수 반복보정** — 레이아웃을
   혼합정수계획으로 풀고, 맨홀별 (관경×관저고) 조합 그래프에서 one-to-all 최단경로로
   수리설계. 정확하지만 **문제크기 지수증가**: 대형 사례에서 1 iteration 58분,
   총 113분 보고. [Sewer Network Layout Selection and Hydraulic Design, Water 2020]
2. **Spanning tree + 수정 PSO** — 신장트리로 레이아웃, PSO로 구성요소 크기 동시최적화.
   [Haghighi & Bakhshipour, Water Resour. Manag. 2016]
3. **Steiner tree 기반 도시 하수 레이아웃**. [Optimal urban sewer layout using Steiner trees]
4. **그래프이론 기반 (분산형) 드레인 레이아웃 생성** — (de)centralized 레이아웃을
   조합적 다목적 최적화로 생성. [Bakhshipour et al., Sustain. Cities Soc. 2022; 2018]
5. **누적유량 최소화 레이아웃**, **SWMM 기반 설계 알고리즘**, **수리기반 우수관망
   최적화(2024)**, **루프/이중화 고려 구조최적화(2022·2024)**.

**SFTF-Sewer가 다른 점 (포지셔닝):**

- **(D1) 최적화기가 아니라 후보생성기/웜스타트.** 위 1~5는 *직접* 트리/관망을
  최적화한다(정확하나 비싸거나, 메타휴리스틱이라 시뮬레이션 호출이 많다). SFTF-Sewer는
  **닫힌형 텐서 + ground-node 스칼라**로 유망한 배수방향·방류구·분할을 ms 단위로
  **랭킹**한 뒤, 상위 소수만 MIP/SWMM에 넘긴다. 적층제조에서 TOMO 대비
  Python 4.7–102.3×, C++ 86–16,075× 가속(수정 DLL·1° 스윕·35메쉬 기준)을
  보였던 그 역할을 그대로 이식.
- **(D2) ground-node 텐서 통합 = 방류구의 닫힌형 해석.** 기존 연구는 방류구까지
  비용을 그래프 가중치로 *직접* 더한다. SFTF는 방류구를 *가상 receiver*로 두어
  `R̃=R+B`라는 **단일 텐서 contraction**으로 통합한다(수치적으로 정확). 이는
  "누적유량 최소화" 휴리스틱(문헌 5)에 **물리적·텐서적 근거**를 부여하는 새 프레이밍.
- **(D3) 텐서 가산성으로 분할비용을 재최적화 없이 추정.** 그래프이론 분산형
  레이아웃(문헌 4)은 분할안마다 레이아웃 최적화를 다시 돌려 평가한다. SFTF는
  `F(partition)=ΣF_part` 가산성으로 **소유역별 재배향 이득을 닫힌형으로** 얻어
  분할 탐색을 값싸게 만든다.
- **(D4) 적응적 수리검증 확대(AVE).** 기존 메타휴리스틱은 모든 후보에 균일하게
  시뮬레이터를 호출한다. SFTF는 **불확실 케이스에만** SWMM 예산을 확대(경계해·근소차·
  월류 위험 트리거). 적층제조에서 최악비율을 17.57→1.37로 줄인 그 메커니즘.
- **(D5) DEM 흐름라우팅과 망 최적화의 명시적 결합.** receiver 탐색을 D8/D∞ 흐름방향과
  동일시함으로써, GIS 수문(흐름누적)과 최소비용 arborescence를 **하나의 텐서 점수**로
  잇는다. 보통 분리돼 다뤄지는 두 단계를 한 프록시로 통합.

**정직한 한계 (선점 서술):**
- SFTF가 주는 것은 **위상·방류구·분할의 웜스타트**이지 정밀 수리설계가 아니다.
  관경·경사·관저고·최소토피·자정유속(Manning) 같은 수리설계는 여전히 SWMM/MIP가 한다.
  (적층제조에서 "TOMO 정밀검증 앞단 후보생성기"였던 역할의 위치가 그대로 유지됨.)
- 굴착비용은 **하류로 깊이가 누적**되며 비선형으로 커진다. 단순 `1/(1+αd)` 감쇠는
  1차 근사이며, 깊이 누적 보정(자가지지 높이장에 해당하는 항)을 더해야 정확도가 오른다
  (Clustering의 0.80→0.90 보정과 동형).
- **가압식 상수도(루프·다중소스)** 에는 단일 방향 텐서 `F(n)` 이 부적합. 거기서는
  텐서가 아니라 **(D1)(D4)의 전략만** 전이된다(값싼 프록시→EPANET 메타휴리스틱).

---

## 4. 최소 PoC 설계 (다음 단계)

1. **입력**: 합성 평탄지형/실 DEM 1매 + 수요노드 + 지정 방류구.
2. **흐름라우팅 패스**(= SFTF receiver): D8/D∞로 후보 arborescence 생성.
3. **SFTF-Sewer 점수 `J_s`**: 후보 방류구 위치 × 소유역 분할 × (재성토 시) 방위 `φ`.
4. **정밀검증**: 상위-K 후보를 `pyswmm`/`swmm-toolkit`에 넘겨 총 관거비용·굴착·월류 측정.
5. **검증지표**: 값싼 `J_s` 와 SWMM 비용 랭킹의 **Spearman ≥ 0.8**(Clustering과 동일 틀),
   베이스라인(MST/최소비용 arborescence, uniform, random) 대비 우위.
6. **확장**: AVE 트리거(경계·근소차·월류), 텐서 가산성 기반 분할 탐색,
   재성토 방위 `φ` 스윕.

### 의존성 메모 (아직 pyproject 미반영)
- DEM 흐름라우팅: `rasterio`, `richdem`(D8/D∞)
- 그래프/arborescence: `networkx`(Edmonds 최소비용 arborescence)
- 수리검증: `pyswmm` / `swmm-toolkit`(EPA SWMM 5)

---

## 참고문헌 (확인용 URL)

- Sewer Network Layout Selection and Hydraulic Design Using a Mathematical Optimization
  Framework. *Water* 12(12):3337, 2020. https://www.mdpi.com/2073-4441/12/12/3337
- Haghighi & Bakhshipour, Layout and Component Size Optimization of Sewer Network Using
  Spanning Tree and Modified PSO. *Water Resour. Manag.* 2016.
  https://link.springer.com/article/10.1007/s11269-016-1378-7
- Optimal urban sewer layout design using Steiner tree problems.
  https://www.researchgate.net/publication/330596790
- Bakhshipour et al., Generation of optimal (de)centralized layouts for urban drainage
  systems: a graph-theory-based combinatorial multi-objective framework. *Sustain. Cities
  Soc.* 2022. https://www.sciencedirect.com/science/article/pii/S2210670722001548
- A Graph-Theory Based Algorithm to Generate Decentralized Urban Drainage Layouts, 2018.
  https://link.springer.com/chapter/10.1007/978-3-319-99867-1_109
- Hydraulic-based optimization algorithm for the design of stormwater drainage networks.
  *Appl. Water Sci.* 2024. https://link.springer.com/article/10.1007/s13201-024-02204-4
- Turan et al., Feasible Sanitary Sewer Network Generation Using Graph Theory. *Adv. Civ.
  Eng.* 2019. https://onlinelibrary.wiley.com/doi/10.1155/2019/8527180
- Layout Optimization of Sewer Network Using Minimum Cumulative Flow.
  https://link.springer.com/chapter/10.1007/978-981-13-0215-2_23
