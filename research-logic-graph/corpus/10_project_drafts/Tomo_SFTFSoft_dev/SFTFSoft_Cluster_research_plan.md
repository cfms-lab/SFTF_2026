# 미분가능 SFTF 분할기 (Differentiable SFTF Partitioner) — 연구계획

> 미분가능 SFTF(`L_SFTF(V,n)`, §8 / `diff_sftf_method.tex`)를 **메쉬 분할**(SFTF_Cluster)에
> 접목하는 방안. 핵심: SFTF_Cluster의 **cut-induced + reorientation** 두 비용을 §8의
> soft attention `π`와 **소프트 멤버십 `M`** 으로 묶어 **단일 미분가능 목적** `L_part`로
> 만들고, k-medoids 이산 배정 대신 **GNN이 `M`을 내놓아 라벨 없이** 학습한다.

## 0. 한 줄 아이디어
SFTF_Cluster의 두 비용 — **cut-induced**(파트 경계에서 지지컬럼 절단)와
**reorientation**(조각별 재배향 이득) — 을 §8 soft attention `π`와 **소프트 멤버십 `M`**
으로 묶어 **단일 손실 `L_part(V, M, {n_k})`** 로 만든다.

## 1. 변수
- 면 `i = 1..n`. 파트 수 `K` 고정.
- **소프트 멤버십** `M ∈ [0,1]^{n×K}`, `Σ_k M_ik = 1` — GNN 출력 `z_i`에 대해
  `M_ik = softmax_k(z_i / τ_c)`.
- **조각별 빌드방향** `n_k = u_k / ‖u_k‖ ∈ S²` (학습 파라미터 또는 작은 head).
  윗첨자 `(k)` = 방향 `n_k`에서 평가한 양.

## 2. 핵심: 멤버십이 수신 어텐션을 게이팅한다 (cut-induced 비용이 *자동* 발생)
파트는 따로 프린트되므로 면 `i`는 **같은 파트의 수신면**만 받을 수 있다. §8 soft 게이트
`a_ij^(k)`(아래·횡정렬·상향·최근접, `diff_sftf_method.tex` 식 (soft 수신배정))에 수신면
멤버십을 곱한다:

```
a_ij^(k) = [§8 soft gates at n_k] · M_jk
π_ij^(k)     = a_ij^(k) / (Σ_j a_ij^(k) + a_0)
π_i,bed^(k)  = a_0       / (Σ_j a_ij^(k) + a_0)
```

→ 경계를 넘는 지지쌍은 `M_jk → 0`으로 끊겨 **바닥항 B로 이동** = cut-induced 비용이
별도 항 없이 발생.

## 3. 조각별 soft 지지 (텐서 가산성 F(part)=ΣF 재사용)
§8의 `P̃, B̃, F̃`에 `M_ik` 가중을 얹어 파트별로 합산:

```
P̃_k = Σ_i M_ik · Õ_i^(k) A_i · Σ_j π_ij^(k) A_j
B̃_k = Σ_i M_ik · Õ_i^(k) A_i · π_i,bed^(k) · (1 + α relu η_i^(k))
F̃_k = Σ_{i,j} M_ik · π_ij^(k) · [ Õ_i^(k) A_i A_j / (1 + α relu h_ij^(k)) ] · m_i ⊗ m_j
R̃_k = softplus_β( − n_kᵀ sym(F̃_k) n_k )
```

각 파트가 **자기 n_k** 로 평가되므로 `Õ_i^(k)`가 작아지는 것 = reorientation 이득이
자동 반영.

## 4. 손실
```
L_part =  Σ_k ( w_R R̃_k + w_P P̃_k + w_B B̃_k )      # 지지비용 (cut+reorient 통합)
        + λ_s L_smooth                               # 연결성/공간일관성 (k-medoids 대체)
        + λ_b L_bal                                  # 붕괴 방지 (K=1 자명해 차단)

L_smooth = Σ_{(i,i')∈E_adj} ℓ_ii' · ‖M_i − M_i'‖²    # 인접면=같은 파트 선호, ℓ=공유엣지 길이
L_bal    = Σ_k ( (Σ_i M_ik A_i)/(Σ_i A_i) − 1/K )²   # 파트크기 균형 (또는 음의 엔트로피)
```

## 5. 담금질 (annealing)
§8 온도 일정(`σ_ℓ:0.05→0.01, a_0:0.05→0.01, β_n:6→24, β:16→64, γ=64`) 그대로 +
**멤버십 온도 `τ_c`: 높음→낮음**(소프트 멤버십 → 거의 one-hot). soft↔hard 일관성:
모든 온도를 sharpen하면 `π → 1[j=t_i]`, `M → one-hot` → `L_part →` SFTF_Cluster의
이산 분할비용.

## 6. 학습 & 평가 (일반화 = 진짜 가치)
- **GNN θ**: 면그래프(노드=면, 엣지=인접+지지쌍) → `M` (+ `n_k` head). 손실
  `E_mesh[L_part]` 로 **라벨 없이** 학습.
- **추론(warm-start)**: `M → argmax` = 하드 라벨, `n_k` 확정 → 기존 `predicted_support`/
  TOMO로 **검증**(§3·§6 정직한 한계: 미분가능 분할기도 대체 아닌 warm-start).
- **eval**: leave-one-mesh-out, 미지 메쉬에서 *예측 분할의 실제 지지질량 백분위* vs
  random(0.50)/oracle — §8 GNN 데모(~0.28)의 분할판. **이 수치가 SFTF_Cluster
  k-medoids보다 낮으면(=좋으면) 가치 입증.**

## 7. PoC 마일스톤 (점증)
1. **단일 메쉬, 자유 `M`+`n_k`**, full-batch 경사하강+담금질 → 하드화 분할의
   `predicted_support`를 k-medoids 베이스라인과 비교. *(통합 목적 동작 + soft→hard 갭 측정)*
2. `L_smooth / L_bal` 추가 → 연결성/균형 확인.
3. 자유 `M` → **GNN θ**, 다중 메쉬 학습, leave-one-mesh-out으로 §6 지표 측정.
   *(여기서 SFTF_Cluster 대비 우열 결정)*

## 진행 상황 (PoC)
구현: `python/src/SFTF_Derivative/diff_sftf_partition.py` (데모: `-m
SFTF_Derivative.diff_sftf_partition [--m2] <mesh_stem>`).
- **M1 완료** — 통합 손실 `L_part` + `(M, n_k)` 공동 경사하강 + 담금질, 정적
  spatial-kNN 1회 precompute. 실 메쉬(torus 2304면, hook 1560면)에서 footprint·
  `predicted_support` 모두 **no-split을 명확히 이기고 이산 최적과 동률**(hook은
  k-medoids 0.00086 대비 0.0으로 근소 추월).
- **M2 완료** — `L_smooth`(엣지길이 가중, scale-free) + `L_bal` + 연결성 후처리
  (`enforce_connectivity`). 면인접 그래프(`face_adjacency`)·연결성분 진단
  (`connected_components`/`fragmentation`) 추가. 결과: **단편화(fragmentation)
  hook 22→1, torus 15→0, 지지비용 추가 0** (각 파트가 단일 연결성분으로 수렴).
- **M3 완료** — `diff_sftf_gnn.py`. 면그래프 메시지패싱 GNN이 면별 part logits +
  **그래프수준 조각방향**을 출력, `L_part`만으로 라벨 없이 다중메쉬 학습. 핵심:
  - **dead-cluster 문제**가 최대 난관 — 빈 파트는 방향이 정의 안 돼 아무 면도
    안 끌려옴 → 붕괴. 해결 3종: (i) 방향을 멤버십 풀링이 아닌 **그래프수준 readout**
    에서(빈 파트도 의미 있는 방향), (ii) **Sinkhorn** 부하균형(두 파트 항상 채움),
    (iii) **per-face 엔트로피** 항(uniform 붕괴 방지) + best-epoch 체크포인트.
  - **결과(4메쉬 leave-one-mesh-out, footprint)**: **zero-shot은 취약**(3개 메쉬로만
    학습 시 미지 메쉬 2/4 붕괴, 평균 백분위 0.75). **test-time adaptation**(미지 메쉬에서
    라벨 없이 60스텝, 학습된 init에서 출발)으로 **평균 백분위 0.75→0.31**, cylinder→0(최적),
    hook 0.035→0.009. §8 빌드방향 GNN(~0.28)과 같은 급.
  - **시사점**: 미분가능 분할기는 per-mesh 솔버(M1/M2)로는 k-medoids와 대등/근소우위.
    **학습형 일반화의 고유가치는 더 많은 학습메쉬 또는 TTA가 있어야 발현**됨. 쉬운
    메쉬에선 두 방식 모두 0에 수렴해 결정적 우열 없음 → **다음: 어려운 메쉬(dragon/lucy,
    D/E군) + 큰 학습세트**로 격차 정량화.

## 하드 메쉬 벤치마크 (per-mesh 품질, M1 vs k-medoids vs k-means)
`sftf_Mesh_Data` 10개 메쉬(소형 기계부품 thingi10k + 대형 유기형은 grid 데시메이션,
KD-tree kNN으로 대형 허용), K∈{2,4}, footprint·predicted_support 동일 척도.
- **결과: 대등 — 어느 쪽도 압도 못 함.** DIFF(M1)이 k-medoids를 이긴 건 footprint 6/20,
  predicted_support 6/20. **기계부품(D5 468면·D8 3910면·hook)에선 DIFF 우위**(예: D8 K=2
  DIFF 0.015 < k-medoids 0.031), **매끄러운 유기형(bunny·nefertiti·manikin)에선 k-medoids
  근소 우위**(예: nefertiti 0.0006 vs DIFF 0.0015), 나머지 다수는 둘 다 0으로 동률.
- **버짓 무관**: steps 200→700, knn 24→40 늘려도 격차 안 줄어 → 언더핏 아님, **구조적 차이**.
- **원인(정직)**: 평가 척도는 45° 게이트 footprint/predicted_support인데 미분가능
  손실은 게이트 없는 softplus 오버행+높이(R,P,B)라 **목적-척도 불일치**. k-medoids는
  게이트 지지피처에 직접 클러스터링(척도에 맞춤)이라 매끄러운 메쉬에서 유리.

## 종합 결론 (원 질문: "SFTF_Cluster보다 좋은가?")
- **per-mesh 분할 품질로는 "더 좋다"가 아니라 "대등"** — 메쉬류에 따라 승패 갈림. k-means도
  일부에서 최강. 즉 **드롭인 품질 향상은 아님**.
- 미분가능 분할기의 진짜 차별가치는 품질이 아니라 (a) **단일 미분가능 목적의 공동최적화**
  (분할+조각방향+형상 co-design), (b) **학습형 amortized 추론**(M3). (b)도 소량학습 zero-shot은
  취약, TTA 필요.
### 목적-척도 정렬 시도 (가설 기각)
학습 손실 오버행에 45° soft 게이트(`use_critical_angle`, sharpness 8·16)를 넣어 평가척도와
맞춰봄 → **격차가 안 줄고 오히려 전반 악화**: D5 .0000→.0005, D8 .0156→.022, bunny .0006→
.0011, nefertiti .0015→.0019 (s8·s16 모두). **원인**: 45° 임계 바로 아래 면은 게이트
기울기가 0(dead zone)이라 옵티마이저가 임계 너머로 면을 못 민다 — `diff_sftf.py`의 "게이트는
랭킹엔 좋지만 최적화 목적으론 더 나쁨" 경고를 재현. → **매끄러운 메쉬 격차는 게이트 정렬로
못 닫음. 게이트 없는 매끄러운 손실이 이미 더 나은 옵티마이저.**

### co-design 시도 (옵션 2) — 효과 미미 (정직한 음성결과)
`codesign_partition`: 분할+조각방향+**정점 V**를 `L_part`로 동시 경사하강, 변위/엣지보존
정규화. 결과:
- 약한 정규화(변위 4~8%)는 **지지 악화**(surrogate의 느슨함을 악용해 형상만 왜곡:
  D8 .0156→.054, torus 0→.031).
- 형상보존 정규화(변위 ≤0.4%)는 **지지 이득 없음**(D8 .0156→.017 오히려 약간 나쁨,
  torus 0 유지).
- **두 원인**: (a) 물리적으로 지지는 45°를 한참 넘는 가파른 오버행이 지배 → 미세변형
  (≤1%)으론 임계 아래로 못 끌어내림; 큰 변형은 형상을 바꿔버림. (b) 옵션1과 같은
  **surrogate-metric 갭** — `∂(ungated L)/∂V`가 게이트 지지척도 감소 방향을 안 가리킴.

### 최종 종합 (전체 조사 결론)
- **품질**: 미분가능 분할기 = k-medoids와 **대등이 상한**. 이를 넘는 손쉬운 레버 2종
  (게이트 정렬·형상 co-design) **모두 실패** — 공통 원인은 미분가능 SFTF surrogate의
  세밀한 최적점이 진짜 45°-게이트 지지척도와 어긋난다는 것(=SFTF 원논문 §3 "rank-only는
  단독 최적화기로 불충분, warm-start+검증만" 한계의 재확인).
- **확인된 고유가치**: (1) warm-start/basin 탐색(M1/M2), (2) **amortized 학습 분할기(M3)**
  — zero-shot은 취약하나 TTA로 회복(평균 백분위 0.31), 그리고 라벨 없는 매끄러운 물리
  신호로 NN 학습에 쓰는 용도. **"SFTF_Cluster보다 더 좋은가"에 대한 답: 품질로는 아니오,
  대등. 가치는 학습형 일반화·미분가능 신호라는 다른 축에 있음.**

## 논문 originality 그림 (baseline = 비미분 원본 SFTF, NOT TOMO)
`scripts/make_diff_sftf_figures.py` → `draft/pics/`. 미분가능판의 본질("샘플만 되는
블랙박스 점수 → 역전파 가능한 손실")을 정직하게 보이는 2장:
- **`diff_sftf_relaxation.{svg,png}`**: (a) 온도 sharpen 시 `L_SFTF→J_SFTF` **점별 수렴**
  (mean|L−J|/range가 0.88→0.10 단조감소), (b) 해석적 기울기 = 중심차분 (y=x, rel.err
  **1.2×10⁻⁶**, float64). → *"매끄럽게 폈고, 극한에서 정확히 원본, 기울기 검증됨."*
- **`diff_sftf_highdim.{svg,png}`**: **고차원 최적화 = 미분가능성이 여는 것.** 4612-DOF
  분할(2304×2 멤버십+방향)에서 경사하강은 ~10스텝에 footprint 지지 **0** 도달, 무작위
  샘플링(비미분 점수의 유일한 수단)은 600샘플에도 **0.06에서 정체**. → *"2D 방향은 격자스캔도
  되지만 고차원은 기울기만 가능."*
- **정직성 주의(폐기한 그림)**: "soft가 hard와 같은 최적점"·"방향최적화 격자 대비 적은 평가"
  주장은 기각 — 실측상 soft/hard 최적점이 bunny에서 67° 어긋나고(=annealing 필요), 방향은
  2D라 격자스캔이 충분. 그래서 위 2장만 사용. **claim은 "더 나은 최적/방향"이 아니라
  "매끄러운·검증된 완화 + 고차원/학습을 여는 미분가능성".**

## 구현 재사용
- `reorientation_support_matrix`(`Tomo_SFTFCluster_dev/.../mesh_partition.py`)의 `s[i,k]`
  구조가 §3 footprint의 하드판 → 위 soft 식으로 교체.
- soft 텐서/게이트는 `python/src/SFTF_Derivative/diff_sftf.py`(§8 참조구현)를 파트축으로 확장.

## 정직한 리스크
- (a) soft→hard 라운딩 갭, (b) `K` 고정·국소최소, (c) 연결성은 `L_smooth`로 *유도*될 뿐
  *보장* 안 됨(필요시 후처리 connected-component 분리), (d) 결국 검증 단계는 그대로 필요.
- → "대체"가 아니라 **통합 목적 + 학습형 일반화**가 차별점.
