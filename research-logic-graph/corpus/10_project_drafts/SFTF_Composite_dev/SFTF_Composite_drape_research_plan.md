# SFTF / SFTF-Clustering → 복합재 드레이프 패치 분할 연구 기획

> SFTF(Support Flow Tensor Field)와 SFTF-Clustering(출력지향 메쉬 분할)을 **복합재
> 제조성(드레이프 가능 패치 분할)** 문제로 이식하는 연구 줄기. 구조성(가변강성·FEM)이
> 아니라 **실험이 가벼운 제조성(기하 field)** 부터 시작한다 — "TOMO 자리"에 무거운
> 이방성 FEM이 아니라 가벼운 kinematic drape 시뮬레이터를 끼울 수 있기 때문.

선행연구
- SFTF: *Support Flow Tensor Field for Fast Build-Orientation Candidate Generation* (Sul et al.)
- SFTF-Clustering: *Output-Aware Mesh Partitioning Based on a Support Flow Tensor Field*

---

## 0. 한 줄 요약

SFTF-Clustering의 핵심 자산은 "지지구조"라는 *응용*이 아니라 **면별 방향-의존 field를
클러스터링 피처로 보존 + 각 part가 자기만의 유리한 방향을 갖게 분할 + cut-vs-reorient
ray-free 목적함수** 라는 골격이다. 이 골격은 **복합재 곡면을 드레이프 가능한 플라이/패치로
분할**하는 문제에 거의 그대로 옮겨간다. 면별 지지흐름(`O,τ,η,ρ,h,r`)을 면별 **드레이프
흐름**(전단각·곡률·섬유각·드레이프 레짐)으로 교체하면, `mesh_partition.py`의 분할
패밀리와 ray-free 목적함수, purity 지표가 대부분 재사용된다.

그리고 SFTF-Clustering이 발견한 비직관적 결론 — *"지지 감소는 support column 보존보다
각 part의 reorientation freedom이 지배한다"* — 가 복합재 버전으로 직역된다:
**드레이프성은 단일 전역 섬유 레이아웃을 지키는 것보다, 각 패치가 자기 국소 발전가능
(developable) 드레이프 시드를 따르도록 분할하되 이음매(seam)를 cost로 다는 데서 결정된다.**

---

## (a) 수식 매핑

### 문제 재정의
복잡 곡면(곡면 셸, 인체적합 형상 등)을 **제조 가능한 플라이/패치로 분할**한다. 각 패치는
평면 프리프레그/직물에서 *주름·locking 없이 드레이프* 되어야 하고(전단각 ≤ locking
angle), 섬유 배향이 일관되며, 이음매·dart를 최소화한다. **각 패치는 자기만의 드레이프
시드(기준 방향/원점)를 선택** 한다 — AM에서 각 part가 자기 빌드 방향을 갖던 것과 동형.

### 면별 "드레이프 흐름" 피처 (지지흐름 대체)
면 `i`에 대해, 선택된 드레이프 시드에서 kinematic drape mapping(핀-조인트 네트/측지
fishnet)을 풀어 면별 기술자를 기록한다. SFTF 기술자와의 대응:

| SFTF 지지흐름 (AM) | 복합재 드레이프 흐름 |
|---|---|
| overhang `O_i = max(0, -m_i·n)` | **전단각** `γ_i` (warp–weft 직교 이탈; locking 위반량) |
| 부호 배향 `τ_i = m_i·n` | **국소 섬유각** `θ_i` (드레이프 후 warp 방향) |
| 빌드플레이트 높이 `η_i` | **측지거리/드레이프 깊이** `g_i` (시드로부터) |
| 지지 역할 `ρ∈{none,face,bed}` | **드레이프 레짐** `ρ∈{developable, shear, dart-needed}` |
| 지지 높이 `h_i`, receiver `t_i` | **전단 누적**(측지 전파 경로) / 인접 전단 receiver |
| receiver count `r_i` | 곡률 응력 집중도 (가우스곡률 `K_i` 보조) |

피처 행렬도 같은 형태:
`Φ_drape = zscore([γ, θ, g, K, shear_accum]) ∈ R^{N×5}` 가 `Φ_SFTF` 자리를 대체.

### 분할 패밀리 — `mesh_partition.py` 그대로
- **pure 드레이프-흐름**(= `support_flow`/`flow_region`): union-find로 (i) 전단 누적
  경로 쌍, (ii) 같은 레짐 + 유사 법선(`m_i·m_j ≥ cosθ_sim`) 인접면을 병합 →
  *발전가능 패치 베이슨*. 한 패치 = 일관된 드레이프 거동.
- **feature-fusion 클러스터링**: `M = [w_s·z(C) | w_f·Φ_drape] ∈ R^{N×8}` 에
  k-medoids/DBSCAN/agglomerative 적용. (논문에서 가장 robust했던 feature-fusion
  k-medoids가 1순위 후보.)

### multi-direction soft block → 제조 섬유각 메뉴
top-K 드레이프 시드 `{n_k}` 에 대해 `c_ik` = 시드 `k`로 드레이프 시 면 `i`의 전단량,
`b_i = argmin_k c_ik`(선호 시드), `w_ik = softmax(-β c_ik)`. **복합재에선 이게 그대로
이산 제조각 메뉴 {0/±45/90}에 대한 소프트 섬유각 장** 이 된다 — 연속 최적각을 제조
가능한 각으로 스냅/이산화하는 기능. 거의 복붙.

### ray-free 목적함수 → seam vs realign
`S(Π) ≈ S_whole + ΔS_cut − ΔS_realign`:
- `ΔS_cut`: 패치 경계가 만드는 **이음매**(강도 손실·연속성 단절). cut weight
  `w_i = A_i·γ_i·g_i`(면적 × 전단 × 드레이프 깊이)로 재해석, `Σ w_i`로 정규화.
- `ΔS_realign`: 각 패치가 자기 드레이프 시드를 채택해 줄어든 전단/주름.
- footprint proxy `Ŝ_fp(Π) = Σ_ℓ min_d Σ_{i∈P_ℓ} s_i(d)`, `s_i(d)=A_i·shear_i(d)` →
  값싼 드레이프-cost proxy. height-field 보정 `Ŝ_hf` 자리에는 전단 누적 보정.
  자동 part-count 선택 `K* = argmin_K score(K)/max + α·K/K_max` 그대로.

### 그대로 사는 것 vs 갈아끼우는 것
**갈아끼움**: 면별 피처 생성기(ray → kinematic drape solve), `Φ_SFTF→Φ_drape`, 검증기.
**그대로**: `mesh_partition.py` 분할 패밀리, feature-fusion `M`, union-find region
growing, multi-direction softmax, ray-free 목적함수 골격, purity 지표, 자동 part-count,
`pareto.py`(전단 vs 패치수 Pareto front).

---

## (b) 새로 생기는 구현 이슈 (AM엔 없던 것)

### Tier A — 골격을 바꿔야 하는 것
- **A1. 드레이프 field 생성기(= ray 대체).** SFTF는 면별 overhang을 ray 한 방으로
  독립 계산했지만, **전단은 경로 의존적**으로 시드에서 측지 전파하며 누적된다. kinematic
  drape mapping(핀-조인트 네트)을 푸는 새 모듈이 필요 — 단, FEM이 아니라 기하·결정론적
  이라 가볍다. SFTF-Clustering의 region-growing/union-find가 전파 골격으로 재사용됨.
- **A2. 드레이프 시드(원점/기준방향) 선택의 닭-달걀 문제.** 패치가 정해져야 시드가
  좋고, 시드가 정해져야 전단을 안다 → multi-direction soft assignment처럼 **top-K 시드
  후보 → 소프트 가중 → 분할 → 시드 재선택** 반복으로 푼다(SFTF-Clustering에 이미 있는 구조).
- **A3. dart-needed 레짐 = die-lock 유사 신호.** 이중곡률(돔/안장)에서 **어떤 시드로도
  전단을 locking 이하로 못 만드는** 영역이 생긴다 — 이건 dart(절개)나 별도 패치가
  강제되는 신호로, AM의 die-lock에 대응. 플래그하고 dart를 넣거나 패치를 더 쪼갠다.

### Tier B — 점수·피처에 추가
- **B1. 섬유 연속성/이음매 위치 제약.** 이음매는 구조적으로 허용 가능한 곳(저응력·비외관)
  에 떨어지도록 — AM의 파팅라인 복잡도·Class-A 제약에 대응하는 피처/마스크.
- **B2. 이산 제조각 스냅.** softmax 블록을 {0/±45/90} 메뉴로 양자화하는 후처리.
- **B3. 스택(다층) vs 단층.** 1차는 단일 플라이 드레이프로 한정, 다층 적층순서·각도
  시퀀스는 별도 항으로 확장.

### Tier C — 산업·강건성
- **C1. material locking angle 의존성.** 직물 종류마다 locking angle(보통 ~30–50°)이
  달라 임계값을 파라미터화. AM의 critical angle `θc`에 대응.
- **C2. 곡면 메쉬 강건성.** 측지 계산·네트 전파가 sliver/비매니폴드에 취약 → 정칙화.

> 새로 만들 핵심은 딱 하나 — **(A1) kinematic drape field 생성기(= TOMO 자리)** — 이고,
> 나머지(시드 반복, dart-레짐 플래그, 이산 스냅, 이음매 제약)는 기존 골격에 항·마스크 추가 수준.

---

## (c) 검증 시나리오 (실험이 가벼운 이유 포함)

### "TOMO 자리"에 들어갈 검증기
무거운 이방성 FEM이 아니라 **kinematic drape 시뮬레이터**(핀-조인트 네트) 또는 더
값싸게는 **가우스곡률 적분 기반 주름 proxy**. 결정론적·고속·라이선스 불필요 — AM에서
TOMO를 값싼 검증기로 쓰던 자리를 그대로 차지한다. (이게 드레이프 경로가 구조성 경로보다
실험이 쉬운 핵심 이유.)

### 난이도 사다리
| Tier | 형상 | 정답 자명? | 검증 목적 |
|---|---|---|---|
| T0 | 발전가능 프리미티브(원기둥·원뿔) | 전단 0 | 위생 검사 |
| T1 | 단일곡률 셸 | 거의 자명 | 단일 시드 전단 정렬 |
| T2 | 이중곡률(돔·안장) | 모호 | 패치 경쟁·dart 필요 (핵심) |
| T3 | 실제 인체적합 메쉬(manikin·nefertiti·liver) | 함정 | 혼합 레짐, 기존 보유 데이터 |

(T3 메쉬는 SFTF-Clustering이 이미 쓰던 것 — 그대로 재사용.)

### Baseline
좌표 k-means, planar BSP, 기하 분할(SDF·곡률), 그리고 **developability 기반 분할**.
(SFTF-Clustering이 쓰던 baseline 구도를 그대로 차용.)

### 지표 — 제조 언어
- **(1순위) locking 초과 면적 비율** = 전단각 > locking angle 인 면적 / 총면적 → 주름 위험.
- **(2순위) 드레이프 purity** = 패치당 일관된 드레이프 레짐 비율(support-class purity의 직역).
- 최대/95퍼센타일 전단각, **이음매 총 길이**, dart 수, 패치 수.
- ray-free proxy(`Ŝ_fp`/전단누적)의 검증기 대비 순위상관(논문의 Spearman 0.80→0.90 구도 재현).

### 프로토콜
SFTF-Clustering 논문 그대로 — 패치별 자기 시드 채택 후 합산 vs 전체형상 baseline,
bbox 대각 정규화, 자동 part-count `Ŝ_hf` 구동, Pareto(전단 vs 패치수).

### 정직성(함정)
- kinematic drape는 *근사*(직물 역학·성형력 무시). 1차 검증엔 충분하나 절대 주름량은 아님.
- locking angle은 재료 의존 → 결과를 임계값과 함께 보고.
- 시드/원점 선택이 결과를 좌우 → 다후보·반복으로 통제하고 민감도 보고.
- 단층 한정 — 적층 시퀀스는 범위 밖으로 명시.

---

## 다음 단계 (구현 로드맵)

1. **[다음] kinematic drape field 생성기 (= TOMO 자리) 프로토타입.** 핀-조인트 네트로
   면별 `γ, θ, g, K, regime` 산출 + 발전가능 프리미티브(T0)에서 전단≈0 검증.
2. **`Φ_drape` 교체** — `SupportFlowTensorField`/`mesh_partition.py`의 피처 자리에 끼워
   기존 분할 패밀리(support_flow/flow_region/feature-fusion k-medoids) 그대로 구동.
3. **multi-direction → 이산 섬유각 스냅** 및 dart-레짐(die-lock 유사) 플래그.
4. **ray-free 목적함수**를 seam-vs-realign으로 재해석 + 자동 part-count.
5. **검증 하니스·벤치마크** — (c) 난이도 사다리 + baseline + 제조 지표.

> 핵심: 당신 코드의 ~80%(분할 패밀리·feature-fusion·union-find·ray-free·purity·pareto)는
> 그대로 살고, 새로 짤 건 **kinematic drape field 생성기** 하나다.
