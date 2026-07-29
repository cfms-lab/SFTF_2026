# SFTF → 리튬이온 배터리 발열(thermal) : PoC 연구기획

> SFTF와 분할 변형(SFTF-Clustering)을 **리튬이온 배터리 팩의 냉각수 채널 레이아웃·
> 냉각 존 분할** 로 이식하기 위한 수식 매핑과 최신문헌 대비 차별점.
> (작성 2026-06, `SFTF_BatteryThermal_dev`)

---

## 0. 한 줄 정리

> SFTF에서 **소스 = 셀 발열 `Q`**, **ground node = 냉각수 채널/콜드플레이트(단, 하류로
> 데워지는 비등온 싱크)**, 비용 = **온도 균일도(uniformity)** 로 치환한다. 냉각수
> 온도상승은 하수 PoC의 유량누적과 같은 구조라 `sewer/` 기계를 재사용한다.

---

## 1. ★ 배터리가 ThermalChip과 다른 세 가지

1. **콜드플레이트 전도** — 셀이 콜드플레이트로 열을 전도. ThermalChip과 동일
   (콜드플레이트 = 빌드플레이트). 여기까진 그대로 이식.
2. **냉각수 채널의 하류 가열(advection)** — 냉각수가 채널을 흐르며 상류 셀의 열을
   흡수해 **데워진다**. 출구쪽 셀은 더 뜨거운 냉각수를 만나 온도가 높다. 이는 하수의
   "유량이 하류로 누적"과 동형: `T_coolant(s) = T_in + α_conv · Σ_{상류} Q`.
   → **ground node가 등온이 아니다**(SFTF/ThermalChip은 등온 싱크였다).
3. **목적이 peak/합이 아니라 온도 균일도** — 셀 간 온도차가 노화·용량불균형을 부른다.
   `uniformity = max_i T_i − min_i T_i` (또는 표준편차). SFTF의 합/최댓값 비용과
   **함수 형태가 다르다** — 도메인 적응의 핵심.

## 2. 기호 대응표 (SFTF ↔ Battery)

| SFTF | Battery | 비고 |
|---|---|---|
| 오버행 `O_i` | 셀 발열 `Q_i` | I²R + 엔트로피 + 반응열 |
| receiver(레이캐스트) | 채널로의 전도(최근접 채널) + 채널 따라 advection | |
| 높이 `h` / 감쇠 | 전도 열저항거리 `φ`(채널까지 거리) | |
| 바닥판(ground node) | **냉각수 채널/콜드플레이트** | **비등온**(하류 가열) |
| `B` | 냉각수 온도장 + 전도 온도상승 | |
| 분할+재배향 | **다채널·역류·냉각 존 분할** | |
| 비용 | **온도 균일도(max−min)** | + peak·평균 보조 |

## 3. 수식 (값싼 프록시)

```
φ_i             = 셀 i → 최근접 채널셀 거리(거리변환)
assign(i)       = 최근접 채널셀,  order(c) = 채널 흐름순서 인덱스
T_coolant[c]    = T_in + α_conv · Σ_{order(c')≤order(c)} Q_pickup[c']   # advection 누적(=sewer)
T_proxy_i       = T_coolant[assign(i)] + α_cond · Q_i · φ_i             # +전도
peak  = max_i T_proxy_i,   mean = ⟨T_proxy⟩,   UNIFORMITY = max−min(또는 std)
```
`Q_pickup[c]` = 채널셀 c 자신의 발열 + c에 할당된 셀들의 발열. 후보 레이아웃을
`UNIFORMITY` 프록시로 랭킹한다.

## 4. 분할 = 다채널/냉각 존 (SFTF-Clustering 이식)  **[구현됨: `partition.py`]**
- **cut-induced**: 한 존을 분리해 별도 채널/인렛을 다는 비용.
- **reorientation**: 각 존이 자기 냉각수 경로에 서는 이득(텐서 가산성으로 재최적 없이).
- 반직관 이식: "하나의 긴 단일 채널보다 **다채널·역류(counter-flow)** 가 균일도를
  높인다"(긴 단일 채널은 출구 셀이 뜨거워 비균일). 이는 SFTF "조각별 재배향이
  유리"의 배터리판이며, 실제 BTMS 설계의 핵심 논점이다.
- **[실증]** 팩을 K개 밴드 존으로 나누고 각 존에 자기 채널·inlet을 주면, **advection
  비용이 존별 독립=가산적**(각 존이 자기 inlet에서 냉각수 리셋)이라 **밴드=독립
  sub-module로 재-solve 없이 평가**된다. (1) 존↑→균일↑(reorientation 이득, K=1→8에서
  std 89→9, 단조), (2) 존별 독립(가산) 평가가 전역 공액해를 **Spearman=1.00**으로 추종
  (경계 전도결합만 ~15–20% 과대평가, 랭킹엔 무영향), (3) `argmin_K [uniformity +
  λ·(K−1)]` 로 cut-cost vs 분할이득 절충해 유한 최적 K 선택(λ↑ → K↓). counter-flow와도
  합성 가능(`zoned_layout(counter=True)`).

## 5. 최소 PoC 설계
1. 입력: 합성 셀 발열맵 + 후보 채널 레이아웃(직선/serpentine/역류 2채널/다채널/에지 플레이트).
2. 프록시: §3의 `T_proxy` → peak/mean/**uniformity**.
3. 정밀검증(공액 stand-in): (a) advection으로 채널 냉각수온 `T_coolant` 계산 →
   (b) 전도 `K·t=Q` 를 채널셀 Dirichlet=`T_coolant`로 풀어(`scipy.sparse`) 셀온도장.
   peak/mean/uniformity 측정.
4. 검증지표: **`Spearman(proxy_uniformity, solve_uniformity) ≥ 0.8`** + 베이스라인 대비.
   **[검증 강화]** 단일 모듈·6 레이아웃의 ρ(n=6)은 취약하므로 **다중 seed × 확장 세트
   (16 레이아웃)** 로 ρ **분포**를 본다(`validate_ensemble`/CLI `validate`). 20 seed,
   32×48 실측: regime B(`rise5`,`std`) mean ρ(uni)=**0.914**, min 0.81, **frac≥0.8=1.00**;
   regime A(`rise1`,`spread`) mean **0.785**, frac≥0.8=0.35. → **정직한 결론**: 단일 seed
   ~0.9는 낙관적 artifact였고, 프록시는 **trade-off가 사는 advection regime에서 오히려
   견고**(frac≥0.8=1.0)하다. 전도-only regime의 약함은 §6 한계로 명시.
   그리고 **peak-최적 레이아웃 ≠ uniformity-최적 레이아웃** 을 정량 제시(배터리 통찰).
   **[구현·실증됨]** advection이 충분히 큰 regime(`rise≳3`, 긴 채널·고 C-rate)에서
   균일도를 **std(분포형상)** 로 보면, 기하학적으로 동일한 `multi_channel`(평행)과
   `counterflow_channels`(역류) 중 **평행이 peak-최적, 역류가 uniformity-최적**으로
   갈린다(seed 0, 32×48: 역류가 peak +25%, std −6%). 이때 프록시는 solve를 거의
   완벽히 추종(Spearman(uni)=1.00). **단, 핵심 미묘함**: max−min(`spread`)은 극값에
   지배되어 peak와 collinear → trade-off가 안 보인다. trade-off는 **분포형상(std)** 에
   살고, 이것이 셀-노화 균일도가 실제로 보는 양이다. 전도 우세 regime(`rise=1`)에선
   peak·균일도가 일치한다(데모 regime A).
5. 확장: ~~AVE(국소 hotspot/비균일 트리거)~~ ✅`ave.py`, ~~텐서가산성 존 분할~~
   ✅`partition.py`, ~~미분가능 SFTF(§8)로 채널 경로 경사하강 최적화~~ ✅`diffsftf.py`,
   과도(드라이브사이클)·전기-열 결합(별도 정밀 솔버 몫).

---

## 6. 최신문헌 대비 차별점

대표 갈래:
1. **CFD/공액 토폴로지 최적화**: 콜드플레이트 미니/마이크로채널을 CFD-in-loop로 위상
   최적화(분기형·유선형·바이오닉 leaf-vein·divergent). 정확하나 매우 비싸다.
   [branched/streamlined mini-channel topopt; bionic leaf-vein; divergent channel]
2. **다목적 메타휴리스틱**: peak T·균일도·압력강하를 NSGA-II 등으로.
   [Thermal Non-Uniformity NSGA-II; microchannel multi-objective]
3. **ML 대체모델 + 최적화**: ANN/NN + cheetah/salp/marine-predator, 침지냉각 ML
   co-design. [NN+cheetah/salp; immersion-cooling ML; PCM+heatpipe+ANN]
4. **열저항망 해석 + 콜드플레이트 배치**.

**SFTF-Battery가 다른 점:**
- **(D1) 무학습·닫힌형 후보생성기/warm-start** — CFD topopt(문헌1)·ML 대체모델(문헌3)
  앞단에서 채널 레이아웃·인렛·존 분할을 ms에 랭킹.
- **(D2) 비등온 ground-node의 닫힌형** — 냉각수 하류 가열을 sewer식 누적으로 닫힌형화
  (등온 싱크 가정의 기존 1차 모델보다 advection을 싸게 반영).
- **(D3) 텐서 가산성으로 냉각 존 분할을 재-CFD 없이 추정.**
- **(D4) 적응검증(AVE)** — 비균일·hotspot 후보에만 공액 솔버 확대. **[구현됨: `ave.py`]**
  프록시는 완벽한 picker가 아니라 완벽한 shortlister(단일 best 적중 ~40%지만 참-최적은
  항상 top-2). 접전권(proxy-best의 (1+margin) 이내)·hotspot 후보만 공액 solve → **평균
  2/16 solve로 exhaustive-solve 최적을 100% 회수**(20 seed). margin이 적응적: 명확한
  승자면 적게, 접전이면 많이 verify.
- **(D5) uniformity-aware 프록시** — 합/최댓값이 아닌 **균일도** 목적에 맞춘 도메인 적응.
- **(D6) 미분가능화(§8)** — 채널 경로·인렛을 경사하강으로 최적화. **[구현됨: `diffsftf.py`]**
  하드 최근접-채널 레이캐스트(argmin)를 soft-attention `w[i,k]=softmax_k(−dist/τ)`로
  완화(τ→0이면 하드 복원) → 균일도가 채널행 `y`의 매끄러운 함수 → 경사하강. 채널이
  hotspot 쪽으로 이동해 **참 공액해 std를 even 배치 대비 ~20%↓**(seed 0–2). numpy-only라
  grad는 유한차분(K 작아 저렴); 해석적/autograd·NN 물리항은 §8 본 확장. soft 전도항은
  선형 `Q·phi`(미분가능)로 둔 최적화 surrogate(랭킹은 공액해로 검증).

**정직한 한계:**
- 전도장은 확산(이산 트리 아님) → 텐서는 부분적. **[실측]** 그래서 **전도-우세 regime
  에서 랭킹 프록시가 약하다**(다중-seed mean ρ≈0.79, frac≥0.8=0.35). 프록시의 전도항
  (8-이웃 최급강하 적분)이 truth(4-이웃 확산)와 가장 어긋나는 곳. advection이 신호를
  지배하는 regime에선 프록시·truth가 같은 advection식을 쓰므로 ρ가 견고해진다(≈0.91).
  **[조사·결론]** 전도항 "모양" 개선으로는 싸게 못 올린다: 다중수신자(MFD) 누적은
  무효(ρ 0.774→0.776), 참 연산자 Jacobi 스윕은 ρ≈0.97에 ~200스윕 필요(직접 solve보다
  안 쌈). 오분류는 **serpentine(긴 단일채널) 전용**(프록시가 n_rows를 구분 못함)이고
  multi/counter 채널 랭킹은 정확, **top-1(최적 레이아웃)은 맞음** → warm-start 목적엔
  충분. 전도항은 정확도 동일하게 **벡터화 완료**(level-동기, O(n) python 루프 제거,
  6–13× 속도↑, 결과 bit-identical). 정확도 향상은 별도 솔버/대체모델 몫.
- 정상상태·단순 advection만. **과도(드라이브사이클)·CFD 압력강하·전기화학 결합·PCM**
  은 별도(정밀 솔버 몫).
- 균일도 절대값 예측이 아니라 **레이아웃 랭킹/warm-start**. 절대 정확도는 학습된
  대체모델/CFD가 높다 — 가치는 무학습·해석가능·warm-start.

### 의존성 메모 (미반영)
- 정밀: CFD/공액열전달(현재 `scipy.sparse` advection+전도로 대역), 과도/전기-열.

## 참고문헌 (확인용 URL)

- Multi-objective topology optimization of cold plates (branched/streamlined mini-channels)
  for Li-ion battery module. *J. Energy Storage* 2023.
  https://www.sciencedirect.com/science/article/abs/pii/S2352152X23017590
- Topological optimization of cold plates with non-uniform heat sources. *AppThermEng* 2024.
  https://www.sciencedirect.com/science/article/abs/pii/S1359431124015904
- Optimization of Thermal Non-Uniformity in Liquid-Cooled Li-ion Packs using NSGA-II.
  *ASME J. Electrochem. En.* 2025.
  https://asmedigitalcollection.asme.org/electrochemical/article/22/4/041002/1206931
- Topology optimization of liquid cooling plate (bionic leaf-vein). *IJHMT* 2024.
  https://www.sciencedirect.com/science/article/abs/pii/S0017931024007294
- Design of a liquid-cooled BTMS using neural networks + cheetah/salp swarm. *Sci. Rep.* 2025.
  https://www.nature.com/articles/s41598-025-15359-0
- ML-enhanced control co-design of immersion-cooled BTMS. *J. Appl. Phys.* 2024.
  https://pubs.aip.org/aip/jap/article/136/2/025001/3302670
