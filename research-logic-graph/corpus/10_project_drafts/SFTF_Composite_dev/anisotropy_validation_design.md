# warp/weft 막(膜) 이방성 검증 실험 설계 (v0.1 · 2026-07-06)

> 소속 라인: **복합재/소재 라인**(SFTF_Composite_dev). kDOP 논문에서 축소한 §6
> (orthotropic membrane term)의 **정식 검증**을 여기서 수행한다. 같은 대상 객체
> $a_2=\sum w\,pp^{T}/\sum w$(Advani–Tucker = SFTF의 M)를 쓰므로 복합재 논문의
> R7(정직한 음성 결과)도 함께 강화된다.
> 검증 규율: PFTF V1–V4(solver-in-the-loop, matched control, frozen held-out,
> pre-verification failure routing).

---

## 0. 무엇을 검증하나 (주장)

직물 rest 패턴에서 섬유 방향으로 읽은 orientation tensor가 **막 이방성 축**을
공급하고, 그 축으로 세운 orthotropic membrane 에너지
$E_m=\sum_e A_e[\tfrac{k_u}{2}(\|w_a\|-1)^2+\tfrac{k_v}{2}(\|w_b\|-1)^2
+\tfrac{k_s}{2}(w_a\!\cdot\!w_b)^2]$가 **실제 드레이프 형상의 방향 의존성**
(grain-aligned vs bias)을 물리적으로 맞는 방향으로 재현한다.

- 이미 확인된 것(단위 시험, 불충분): 에너지비 $=k_u/k_v$ 정확, 등방 극한에서
  축-회전 불변, 패턴 파일에서 프레임 추출 정상. → **대수(algebra)는 맞음**.
- 아직 없는 것: 이 항이 **실물/독립 기준**과 맞는지. 그게 이 실험의 목표.

---

## 1. 선결 조건 (반드시 먼저 — 이게 없으면 신호가 묻힌다)

**cfmsDrape 굽힘강성 버그 수정.** 현재 $B$가 실측 대비 **1/100**로 들어가고 있음.
특성 접힘 길이 $\ell_b\propto B^{1/3}$ 이므로 $B\!\to\!B/100$ 이면 폴드 스케일이
약 $100^{1/3}\!\approx\!4.6\times$ 작아진다. 과도하게 부드러운 굽힘이 만드는
잔주름이 **막 이방성 신호를 압도**한다. → **굽힘 수정 = 필요조건**.
단, 필요조건일 뿐 **충분조건 아님**: 굽힘을 고쳐도 아래의 독립 기준이 없으면
검증이 성립하지 않는다.

---

## 2. 순환성 함정 (설계의 핵심)

cfmsDrape에 새로 넣은 항을 **cfmsDrape 자기 출력**으로 검증하면 순환이다
(자기가 자기 ground truth). 반드시 **cfmsDrape 밖의 독립 앵커**가 있어야 한다.
아래 세 후보 중 **최소 하나**를 앵커로 고정한다(둘이면 더 강함).

| 앵커 | 무엇 | 독립성 |
|---|---|---|
| **A. 물리 실측** | Kawabata(KES)/FAST 또는 인장·bias-extension·picture-frame로 warp/weft 계수 실측 → cfmsDrape에 투입 → **실제로 드레이프시킨 원단 샘플** 형상과 대조 | 재료 파라미터·기준 형상 모두 엔진 밖 |
| **B. 표준 벤치마크** | double-dome(또는 hemisphere) 성형 — grain-aligned vs 45° bias. 문헌 double-dome 결과와 대조 | 기준 형상이 공개 벤치마크 |
| **C. 독립 솔버** | 동일 메시·재료를 **독립 막 FE**(Baraff–Witkin 레퍼런스 구현 또는 외부 FE)로 계산 → shear angle field 대조 | 솔버가 엔진 밖 |

권장: 저비용 시작은 **B + C**(실물 준비 없이 가능), 논문 신뢰도 최대는 **A**.

---

## 3. 실험 매트릭스 (V2 matched control)

두 축의 완전 교차 ablation. 각 셀에서 **컬링/접촉 무관**, 오직 막 항만 스위치.

- **재료 스위치:** (i) isotropic 단일 $k$(대조군), (ii) orthotropic $k_u\!\ne\!k_v$
  (처리군, 축은 $a_2$에서).
- **방향 스위치:** grain-aligned(0°) vs bias(45°).
- **형상:** double-dome, hemisphere draw-in, 그리고 (A 가능 시) 실물 드레이프.
- 굽힘·솔버 세팅은 **모든 셀에서 동일**(matched). 바뀌는 것은 막 항뿐.

**측정량(정량):** ① shear angle field(성형 이방성의 1차 지표), ② draw-in/dome
높이, ③ drape coefficient(원형 시료), ④ 폴드 수·주름 파장(굽힘 수정 검증 겸용).
grain vs bias의 **차이의 방향과 크기**가 앵커와 부합해야 통과.

---

## 4. V1–V4 매핑 (합격 규율)

- **V1 solver-in-the-loop:** 막 항을 cfmsDrape 정식 솔버 안에서 평가(후처리 아님).
- **V2 matched control:** isotropic vs orthotropic를 **동일 세팅**으로 대조(§3).
- **V3 frozen held-out:** 임계·계수를 소수 튜닝 케이스에서 **동결**한 뒤, 손대지
  않은 held-out 형상(예: bias hemisphere)에서 예측. 튜닝셋 성능은 근거로 쓰지 않음.
- **V4 pre-verification failure routing:** 통과 실패(예: bias 방향 차이가 앵커와
  반대)면 **음성 결과로 정직 보고** — 복합재 R7 라인과 동일 규율.

---

## 5. 합격/불합격 기준

- **합격:** orthotropic 처리군이 (a) grain vs bias 차이의 **부호가 앵커와 일치**,
  (b) held-out(V3)에서 shear angle 차이가 앵커 대비 정해둔 허용오차 내
  (예: $\le$ 문헌 double-dome 산포), (c) isotropic 대조군은 그 방향 차이를
  **재현 못 함**(즉 이방성 항이 실제로 신호를 만든다).
- **불합격/유보:** 위 중 하나라도 실패 → 음성 결과로 기록. 원인 분리(굽힘 잔여
  오차? 축 추출? 계수 스케일?)를 §4 V4로 라우팅.

---

## 6. 산출물 · 다음 단계

- 산출물: ablation 표(3×2×형상), shear angle 필드 그림, 앵커 대조 플롯, 재현
  스크립트(frozen 임계 포함).
- 귀속: 이 결과는 **복합재/소재 논문**의 본문 결과가 되며, 통과 시 kDOP 논문
  Discussion의 "Toward material fields" 포인터가 **이 논문을 인용**하도록 갱신.
- 선결: (1) 굽힘 1/100 버그 수정 완료 확인 → (2) 앵커 B(double-dome) 파이프라인
  구축 → (3) 가능하면 앵커 A(실측) 추가 → (4) V3 동결·held-out 실행.

## 하지 않을 것
- cfmsDrape를 자기 ground truth로 쓰는 순환 검증.
- 굽힘 수정 전 이방성 신호 판정(잔주름이 신호를 압도).
- 튜닝셋 성능을 검증 근거로 제시(V3 위반).
