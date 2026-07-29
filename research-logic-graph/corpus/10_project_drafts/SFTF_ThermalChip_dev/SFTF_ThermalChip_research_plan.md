# SFTF → 반도체 열방출(heat dissipation) : PoC 연구기획

> SFTF(Support Flow Tensor Field)와 분할 변형(SFTF-Clustering)을 **반도체 칩의
> 열방출 설계(히트싱크/써멀비아 배치 · 열도메인 분할)** 로 이식하기 위한 수식 매핑과
> 최신문헌 대비 차별점. (작성 2026-06, `SFTF_ThermalChip_dev`)

---

## 0. 한 줄 정리

> SFTF에서 **소스 = 발열밀도 `P`**, **receiver = 최저열저항 싱크 경로**,
> **bottom-plate(ground node) = 히트싱크/써멀비아(T=T_amb)** 로 치환하면, *서포트
> 흐름 트리*가 *열유속망*이 되고, *서포트 물량 최소화*가 *온도상승 최소화*가 된다.
> 푸리에 `q=−k∇T`는 중력 `−∇Φ`와 같은 "퍼텐셜→싱크" 구조라 전기장보다 깨끗하다.

---

## 1. ★ PDN과의 동형성 (출발점)

정상상태 열전도와 정적 IR-drop은 **같은 방정식**이다:
```
열  :  ∇·(k ∇T) = −P_dissipation ,  싱크 T=T_amb   (k=열전도)
IR  :  ∇·(σ ∇V) = −I_inject      ,  패드 V=0       (σ=전기전도)
상사:  V↔T,  전류 I↔열유속 q,  컨덕턴스 σ↔열전도 k,  패드↔히트싱크
```
따라서 `SFTF_PDNElectric_dev` 의 저항망 솔버 `G·v=i` 는 **단위만 바꾸면 그대로 열
솔버** `K·t=P` 이고, 패드항 `B=Σ I·dist` 는 그대로 **`Σ P·dist` = 온도상승 1차
법칙**이 된다. 이 PoC는 PDN을 포크하되 **목적이 peak 온도(max)** 라는 한 가지
본질적 차이를 추가한다(§3).

---

## 2. 기호 대응표 (SFTF ↔ Thermal) 와 수식

| SFTF | 기호 | Thermal | 기호 |
|---|---|---|---|
| 빌드방향 | `n∈S²` | 백사이드 싱크 시 수직 `−z`(거의 균일) | `n` |
| 면 i | `i` | 칩 격자 셀/타일 | `i` |
| 오버행 `O_i(n)` | 소스 | 발열밀도 | `P_i ≥ 0` |
| receiver(레이캐스트) | | 최저열저항 경로의 최근접 싱크 | |
| 지지 높이 `h_ij` | | 열저항거리(거리×열저항) | `r_ij` |
| 바닥판(ground node) | `B` | **히트싱크/써멀비아 항** | `B_th` |
| 분할+재배향 | | **열도메인 분할 + 다(多)싱크/비아** | |

핵심 점수(PDN과 동형):
```
φ_i      = 셀 i → 최근접 싱크 거리(거리변환)         # "표고" 역할
B_sum    = Σ_i P_i (1 + α φ_i)                       # 평균/총 온도상승 프록시
R(d)     = max(0, −dᵀ F_sym d),  F=Σ w_ij A_iA_j m_im_jᵀ,  w=P_i/(1+α r_ij)
P_pair   = Σ P_i A_i A_j
J        = wR R + wP P_pair + wB B_sum
```

## 3. ★ 핵심 차이: peak 온도(max) 목적

PDN/하수에서 비용은 **합(sum)** 이었지만, 칩 열의 1차 신뢰성 지표는 **최고온도
(peak/hotspot)** 다. 합 기반 `B_sum` 은 *평균* 온도를 잘 예측하지만 *peak* 는 못
잡는다. 그래서 **peak-aware 프록시**를 추가한다 — 싱크에서 셀로 가는 경로의
열저항×누적열을 누적한 값:
```
t_proxy_i = t_proxy_{rec(i)} + α · accum_i · r_i      # rec=싱크쪽 이웃, accum=누적 발열
B_peak    = max_i  t_proxy_i
```
`B_sum` 은 평균-T, `B_peak` 는 peak-T 랭킹을 예측한다는 것을 검증한다(§5). 이것이
PDN 대비 ThermalChip의 고유 기여다(목적함수 형태의 도메인 적응).

> **★ 검증 후 정정 (2026-06, 40~30시드 · 실제 `K·t=P` 솔버 대비).** 위 주장은
> *질문을 올바로 던질 때만* 성립한다. 두 질문을 분리해야 한다:
> 1. **싱크 개수가 다른 배치들의 peak-T 랭킹** → `B_peak` **실패**. 배치마다 싱크
>    개수(=총 열접근량)가 다르면 그 접근량이 peak·mean을 *함께* 좌우해 둘이 ρ≈0.94로
>    강결합되고, 닫힌형 `B_sum` 이 peak-T까지 이미 잘 잡는다(불규칙 40시드: `B_peak`
>    11/40승, 평균 Δρ=−0.015). 물리기반 대체 프록시 3종(국소 `P·φ`, Jacobi 확산
>    스무딩, 이미지법 2D 로그 그린함수)도 전부 `B_sum`에 패배. SFTF의 *이산 서포트
>    트리*와 달리 열은 *확산*이라 sum↔max 구분이 그대로 전이되지 않는다(§6 한계 참조).
> 2. **비아 예산을 고정하고 배치만 최적화**(진짜 설계 질문 "어디 둘까") → `B_peak`
>    **부활**. 개수가 고정되면 총 접근량이 일정해 peak/mean이 분리(ρ≈0.78)되고, 시험한
>    예산 9·16·25에서 `B_peak` 가 배치를 peak-T로 각각 **73.3%·83.3%·76.7% 승**(순수
>    랜덤 30시드, 평균 ρ_peak 0.85 > ρ_sum 0.80)으로 더 잘 랭킹한다. 승률은 예산에
>    다소 민감하다(예산 12: 63.3%승 — 단 평균 ρ_peak 0.845>ρ_sum 0.801로 우세 유지).
>    예산=4(과소)는 고정해도 접근량이 지배해 실패.
>
> **결론: peak-awareness의 가치는 "비아를 몇 개" 가 아니라 "어디에" 를 정할 때 있다.**
> §5 검증 데모도 이 고정예산·배치전용 비교를 기본으로 삼아야 한다.
>
> **top-1 정확도 — 후보생성기로서의 진짜 지표.** 고정예산에서도 단일 최적배치 적중
> (hit@1)은 ~32%로 낮지만, 이는 **최상위 배치들이 거의 동률**이기 때문이다(프록시
> 결함이 아님): B_peak이 고른 #1의 실제 T_peak는 진짜 최적보다 평균 ~4%(best→worst
> 정규화)만 높다. 실제 사용법인 **"프록시로 top-k 추려 그 k개만 정밀해석"** 의 regret
> 으로 보면(60시드, 배치 60개, 예산 16): B_peak top-3 → **regret 1.4%**, top-5 → 0.9%,
> top-10 → 0.2% (랜덤 베이스라인은 각각 17.8%·11.4%·6.8%). 즉 **값싼 프록시 + 극소
> 검증예산(k=3~5 solve)으로 거의 최적 배치 도달** — 이것이 PoC의 핵심 가치 명제다(D1
> 무학습 후보생성→소수 정밀검증). B_peak은 작은 k(1~3)에서 B_sum보다 regret이 낮아
> (k=1: 4.1% vs 4.6%, k=3: 1.4% vs 1.8%), 검증예산이 빠듯할수록 이득이 집중된다
> (k≥5에선 수렴). `cli demo --budget K` 가 hit@k·regret 출력.
>
> **재현성 (2026-07-02 전면 재검증).** 이 박스의 수치 전체는
> `scripts/repro_paper_data.py`(40·30·60시드, ~11,000회 solve, 약 70초) 한 번으로
> 재현된다. 17개 회귀 테스트와 README 데모 2종도 동일 시점에 전부 통과·재현 확인.

## 4. 분할 = 열도메인/다싱크 (SFTF-Clustering 이식)
- **cut-induced**: 한 열도메인을 분리해 별도 싱크/써멀비아 군을 다는 비용.
- **reorientation**: 각 도메인이 자기 최적 싱크 집합에 서는 이득 — **텐서 가산성
  `F(part)=ΣF_part` 로 재최적화 없이** 추정.
- 반직관 이식: "하나의 큰 싱크보다 **분산형 다(多)써멀비아**가 총·peak 온도를
  줄인다"(SFTF: 조각별 재배향이 지지를 줄인다와 동형). 백사이드 히트싱크의 경우
  **수직 방향 n이 거의 균일**해 SFTF 텐서 R항이 PDN보다 더 유효하다.

## 5. 최소 PoC 설계
1. 입력: 합성 칩 발열맵 + 후보 싱크/써멀비아 위치 집합.
2. 싱크 할당(= receiver): 최근접/최저열저항 Voronoi → `φ`.
3. 점수: `B_sum`, `B_peak`, `J`.
4. 정밀검증: 정상상태 열전도 `K·t=P` 를 `scipy.sparse` 로 풀어 **peak/mean 온도** 측정.
5. 검증지표: **고정 비아예산(9·16·25 시험) · 배치전용 풀에서 `Spearman(B_peak, Tpeak) >
   Spearman(B_sum, Tpeak)`** (peak 목적엔 peak 프록시가 우월 — 단 §3 정정대로
   *개수고정* 조건에서만) + 베이스라인(균일격자·랜덤) 대비 우위. 싱크 개수가 섞인
   풀에서는 이 부등식이 성립하지 않으니 비교조건을 반드시 명시한다.
6. 확장: AVE(핫스팟 트리거), 텐서가산성 열도메인 분할, 마이크로채널(대류) → 하수
   PoC 기계 재사용, **미분가능 SFTF(§8)로 비아/싱크 위치 경사하강 최적화**.

---

## 6. 최신문헌 대비 차별점

대표 갈래:
1. **수치 열 사인오프**: 열방정식 FEM/FDM(컴팩트 열모델, HotSpot 류). 정확하나 비싸다.
2. **열-인지 플로어플랜/배치**: SA/해석적/force-directed로 블록·TSV·마이크로채널·열도메인
   배치하며 peak T 최소화. [3D IC thermal floorplanner (TSV/liquid microchannel/thermal
   domains), arXiv:2402.14627; ATPlace2.5D 해석적 칩렛 배치, ICCAD 2024;
   thermal-via planning force-directed]
3. **써멀비아/TSV 플래닝**.
4. **ML 열 대체모델**: CNN/연산자학습/트랜스포머로 온도맵 고속예측.
   [Thermal ML Solver, MLCAD 2022; surrogate-assisted chiplet placement, arXiv:2504.03808;
   self-attention/operator-learning 3D-IC thermal, arXiv:2510.15968]

**SFTF-Thermal이 다른 점:**
- **(D1) 무학습 후보생성기/warm-start.** ML 대체모델(문헌 4)은 기술/설계별 재학습
  필요. SFTF는 닫힌형 텐서+ground-node로 싱크·비아 배치·열도메인 분할을 학습데이터
  0으로 랭킹한 뒤 상위 소수만 정밀 솔버로.
- **(D2) ground-node 닫힌형 = 온도상승 1차항의 텐서 해석.**
- **(D3) 텐서 가산성으로 열도메인 분할을 재-FEM 없이 추정.**
- **(D4) 적응검증(AVE) — 무학습·신뢰도 트리거 핫스팟 정밀화.**
- **(D5) peak-aware 프록시** — 합이 아닌 max 목적에 맞춘 도메인 적응(§3). *단, 검증
  결과 그 효력은 **고정 비아예산 하의 배치 랭킹**에 한정된다(§3 정정 박스).* 싱크
  개수가 변하는 비교에서는 `B_sum`이 peak-T까지 잡으므로 D5의 적용 범위를 "배치
  최적화"로 좁혀 주장해야 한다.
- **(D6) 미분가능화(§8)** — 열 비용은 매끄러우니 soft-attention으로 `L_thermal`을
  만들어 비아·싱크 위치를 **경사하강**으로 최적화하거나 NN 물리일관성 항으로.

**정직한 한계:**
- 전도장은 확산(이산 트리 아님) → 텐서는 부분적(백사이드 수직 싱크면 개선). **같은
  이유로 peak-aware 프록시(D5)의 우위도 부분적**: 싱크 *밀도*가 바뀌면 peak·mean이
  강결합돼 `B_sum`이 충분하고, peak 프록시는 *고정예산 배치선택*에서만 이긴다(§3).
- 정상상태 전도만 다룸. **과도(드라이브사이클)·대류(마이크로채널)·전기-열 결합**은
  별도(대류 채널은 하수 PoC 흐름망 재사용 가능).
- SFTF는 정밀 FEM/CFD 사인오프 대체가 아니라 그 앞단 후보생성·warm-start.
  절대온도 정확도는 학습된 대체모델이 더 높을 수 있다 — 가치는 무학습·해석가능·warm-start.

### 의존성 메모 (아직 pyproject 미반영)
- 정밀 사인오프: 컴팩트 열모델/FEM(현재는 `scipy.sparse` 정상상태 전도로 대역)
- 대류/과도: CFD/transient (현재 미포함)

## 참고문헌 (확인용 URL)

- Thermal-Aware Floorplanner for 3D IC (TSVs, liquid microchannels, thermal domains).
  arXiv:2402.14627. https://arxiv.org/abs/2402.14627
- ATPlace2.5D: Analytical Thermal-Aware Chiplet Placement, ICCAD 2024.
  https://yibolin.com/publications/papers/PLACE_ICCAD2024_Wang.pdf
- A Thermal Machine Learning Solver for Chip Simulation, MLCAD 2022.
  https://arxiv.org/pdf/2209.04741
- Fast Thermal-Aware Chiplet Placement Assisted by Surrogate, 2025.
  https://arxiv.org/html/2504.03808v1
- Self-Attention to Operator-Learning-based 3D-IC Thermal Simulation, 2025.
  https://arxiv.org/html/2510.15968
